#!/usr/bin/env bash
# ==============================================================================
# fetch_logs.sh - Error Log Harvester for Conversational-CNC-Controller
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PI_USER="${PI_USER:-detour}"
PI_HOST="${PI_HOST:-pi-lab.local}"
LINES="${LINES:-50}"
SERVICE_NAME="conversational-cnc"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-n|--lines <num>]"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo "======================================================================"
echo "📋 Fetching Conversational-CNC-Controller Logs ($PI_HOST | Last $LINES lines)"
echo "======================================================================"

# 1. Remote Systemd Service Journal
echo "--- [1/2] Remote Systemd Service Journal ($SERVICE_NAME.service) ---"
if ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_USER@$PI_HOST" "true" >/dev/null 2>&1; then
    ssh "$PI_USER@$PI_HOST" "sudo journalctl -u $SERVICE_NAME -n $LINES --no-pager" || echo "⚠️ Warning: Failed to read remote journal."
else
    echo "⚠️ Remote host $PI_HOST unreachable via SSH. Skipping remote journalctl."
fi

# 2. Local Application Logs (if present)
echo ""
echo "--- [2/2] Local Workspace Error Logs ---"
LOCAL_FOUND=0
for log_file in "$SCRIPT_DIR/logs/cnc.log" "$SCRIPT_DIR/logs/error.log"; do
    if [ -f "$log_file" ] && [ -s "$log_file" ]; then
        echo "📄 $log_file (tail $LINES):"
        tail -n "$LINES" "$log_file"
        LOCAL_FOUND=1
    fi
done

if [ "$LOCAL_FOUND" -eq 0 ]; then
    echo "✅ No local application error log files found or logs are empty."
fi

echo "======================================================================"
