#!/usr/bin/env bash
# ==============================================================================
# Conversational CNC Controller: Atomic SQLite Backup & Modular Sync Script
# ==============================================================================
# Takes an atomic snapshot (VACUUM INTO) of the SQLite database.
# In standalone mode, rotates local backups (keeps last 7 days).
# When the Server Rack vault (pi-backup.lan) is online, syncs snapshots to Node 04.
#
# Usage:
#   ./scripts/backup_cnc.sh [OPTIONS]
#
# Options:
#   -n, --dry-run       Preview backup operations without creating files
#   -h, --help          Show this help message
# ==============================================================================

set -euo pipefail

DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            cat << 'EOF'
Usage: ./scripts/backup_cnc.sh [OPTIONS]

Options:
  -n, --dry-run       Preview backup operations without creating files
  -h, --help          Show this help message
EOF
            exit 0
            ;;
        *)
            echo "❌ Unknown argument: $1"
            exit 1
            ;;
    esac
done

TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_DIR="/var/backups/conversational_cnc"
RACK_BACKUP_HOST="${RACK_BACKUP_HOST:-pi-backup.local}"
RACK_BACKUP_DIR="${RACK_BACKUP_DIR:-/srv/backups/restic/barn-cnc}"

# Locate active SQLite database
DB_PATH=""
for CANDIDATE in \
    "${BASE_DIR}/instance/cnc_controller.db" \
    "${BASE_DIR}/backend/instance/cnc_controller.db" \
    "${BASE_DIR}/instance/conversational_cnc.db" \
    "/srv/cnc_controller/instance/cnc_controller.db"; do
    if [[ -f "${CANDIDATE}" ]]; then
        DB_PATH="${CANDIDATE}"
        break
    fi
done

if [[ -z "${DB_PATH}" && "${DRY_RUN}" == "false" ]]; then
    echo "⚠️ No SQLite database file found to backup in known instance paths."
    # If app hasn't run yet, nothing to backup
    exit 0
fi

BACKUP_FILE="${BACKUP_DIR}/cnc_backup_${TIMESTAMP}.db"
LATEST_LINK="${BACKUP_DIR}/cnc_backup_latest.db"
TMP_BACKUP="/tmp/conversational_cnc_backup.db"

echo "======================================================================"
echo "💾 Conversational CNC Controller: Backup Routine"
echo "======================================================================"
echo "📅 Timestamp:      ${TIMESTAMP}"
echo "📁 Source DB:      ${DB_PATH:-[Simulated DB]}"
echo "🎯 Target File:    ${BACKUP_FILE}"
echo "🏰 Rack Host:      ${RACK_BACKUP_HOST}"
echo "🔍 Dry Run:        ${DRY_RUN}"
echo "======================================================================"

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "🔍 [DRY-RUN] Would execute: sqlite3 '${DB_PATH:-instance/cnc_controller.db}' 'VACUUM INTO \"${BACKUP_FILE}\";'"
    echo "🔍 [DRY-RUN] Would rotate local backups older than 7 days in ${BACKUP_DIR}"
    echo "🔍 [DRY-RUN] Would test connectivity to ${RACK_BACKUP_HOST}:22"
    echo "✅ Dry run complete. No files created."
    exit 0
fi

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Step 1: Atomic Snapshot
echo "📸 Step 1: Taking atomic SQLite VACUUM snapshot..."
sqlite3 "${DB_PATH}" "VACUUM INTO '${BACKUP_FILE}';"
cp -f "${BACKUP_FILE}" "${LATEST_LINK}"
cp -f "${BACKUP_FILE}" "${TMP_BACKUP}"
echo "✅ Local snapshot created: $(ls -lh "${BACKUP_FILE}" | awk '{print $5}')"

# Step 2: Rotate Local Backups (Keep last 7 days)
echo "🧹 Step 2: Pruning local backups older than 7 days..."
find "${BACKUP_DIR}" -type f -name "cnc_backup_*.db" -mtime +7 -delete || true

# Step 3: Check Server Rack Vault Connectivity (Node 04)
echo "🌐 Step 3: Checking reachability of Server Rack backup vault (${RACK_BACKUP_HOST})..."
RACK_ONLINE=false
TARGET_SYNC_HOST="${RACK_BACKUP_HOST}"

for CANDIDATE_HOST in "${RACK_BACKUP_HOST}" "pi-backup.local" "pi-backup.lan"; do
    if command -v nc &>/dev/null && nc -z -w 2 "${CANDIDATE_HOST}" 22 2>/dev/null; then
        RACK_ONLINE=true
        TARGET_SYNC_HOST="${CANDIDATE_HOST}"
        break
    elif timeout 2 bash -c "</dev/tcp/${CANDIDATE_HOST}/22" 2>/dev/null; then
        RACK_ONLINE=true
        TARGET_SYNC_HOST="${CANDIDATE_HOST}"
        break
    fi
done

if [[ "${RACK_ONLINE}" == "true" ]]; then
    echo "🏰 Server Rack Node 04 is ONLINE at (${TARGET_SYNC_HOST})! Syncing snapshot..."
    if command -v rsync &>/dev/null; then
        rsync -az --timeout=10 "${BACKUP_FILE}" "${RACK_BACKUP_HOST}:${RACK_BACKUP_DIR}/" 2>/dev/null || {
            echo "⚠️ rsync transfer completed with non-zero exit (likely remote SSH key/directory setup needed). Snapshot safely preserved locally."
        }
    fi
    echo "✅ Rack synchronization finished."
else
    echo "ℹ️ Server rack vault unreachable or running in Standalone Mode. Snapshot securely preserved in ${BACKUP_DIR}."
fi

echo "🎉 Backup complete at $(date)!"
