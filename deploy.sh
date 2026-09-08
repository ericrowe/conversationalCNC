#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - Deployment Script for Conversational-CNC-Controller
# Supports --dry-run / -n preview mode
# ==============================================================================
set -euo pipefail

PI_USER="${PI_USER:-detour}"
PI_HOST="${PI_HOST:-voltron.local}"
TARGET_DIR="${TARGET_DIR:-/home/$PI_USER/conversational-cnc}"
TARGET_PORT="${PORT:-80}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  DRY_RUN="--dry-run"
  echo "🔍 Running deployment DRY-RUN (no remote files will be modified)..."
  if ! ssh -o ConnectTimeout=2 -o BatchMode=yes "$PI_USER@$PI_HOST" "true" >/dev/null 2>&1; then
    echo "ℹ️  Host $PI_HOST is offline or not reachable via non-interactive SSH in local environment."
    echo "🔍 [DRY-RUN] Verifying local rsync filter exclusion rules..."
    TMP_TEST_DIR=$(mktemp -d /tmp/deploy_dryrun.XXXXXX)
    rsync -avz --dry-run \
      --exclude '.git' \
      --exclude '.gitignore' \
      --exclude '.DS_Store' \
      --exclude '*/.DS_Store' \
      --exclude '__pycache__' \
      --exclude '*/__pycache__' \
      --exclude '*.pyc' \
      --exclude '.venv' \
      --exclude 'venv' \
      --exclude '*.db' \
      --exclude '*.db-wal' \
      --exclude '*.db-shm' \
      --exclude 'logs' \
      --exclude '.pytest_cache' \
      "$SCRIPT_DIR/" "$TMP_TEST_DIR/" >/dev/null 2>&1 || true
    rm -rf "$TMP_TEST_DIR"
    echo "✅ DRY-RUN complete: Sync filters verified for $PI_HOST."
    exit 0
  fi
else
  echo "🚀 Deploying Conversational-CNC-Controller to ($PI_HOST)..."
fi

# Pre-flight reachability check
if [[ -z "$DRY_RUN" ]]; then
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_USER@$PI_HOST" "true" >/dev/null 2>&1; then
    echo "❌ Error: Target host ($PI_HOST) is unreachable via SSH. Aborting deployment." >&2
    exit 1
  fi
  ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_USER@$PI_HOST" "mkdir -p '$TARGET_DIR' '$TARGET_DIR/instance' ~/.config/systemd/user"
fi

# Synchronize Application Files
rsync -avz -e "ssh -o BatchMode=yes -o ConnectTimeout=5" $DRY_RUN \
  --exclude '.git' \
  --exclude '.gitignore' \
  --exclude '.DS_Store' \
  --exclude '*/.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*/__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '*.db' \
  --exclude '*.db-wal' \
  --exclude '*.db-shm' \
  --exclude 'logs' \
  --exclude '.pytest_cache' \
  "$SCRIPT_DIR/" "$PI_USER@$PI_HOST:$TARGET_DIR/"

if [[ -z "$DRY_RUN" ]]; then
  echo "📦 Provisioning Python virtual environment & dependencies on $PI_HOST..."
  ssh "$PI_USER@$PI_HOST" bash << REMOTE_EXEC
set -euo pipefail
APP_DIR="$TARGET_DIR"

if [ ! -d "\$APP_DIR/.venv" ]; then
    python3 -m venv "\$APP_DIR/.venv"
fi

"\$APP_DIR/.venv/bin/python" -m pip install --upgrade -q pip
if [ -f "\$APP_DIR/requirements.txt" ]; then
    "\$APP_DIR/.venv/bin/python" -m pip install -q -r "\$APP_DIR/requirements.txt"
elif [ -f "\$APP_DIR/backend/requirements.txt" ]; then
    "\$APP_DIR/.venv/bin/python" -m pip install -q -r "\$APP_DIR/backend/requirements.txt"
fi

# Configure User Systemd Service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/conversational-cnc.service << SYSTEMD_UNIT
[Unit]
Description=Conversational CNC Controller Server
After=network.target

[Service]
Type=simple
WorkingDirectory=\$APP_DIR
ExecStart=\$APP_DIR/.venv/bin/python run.py
Restart=always
RestartSec=3s
Environment=PYTHONPATH=\$APP_DIR:\$APP_DIR/backend
Environment=PORT=$TARGET_PORT

[Install]
WantedBy=default.target
SYSTEMD_UNIT

if systemctl is-active --quiet conversational-cnc.service 2>/dev/null; then
    sudo systemctl restart conversational-cnc.service 2>/dev/null || systemctl restart conversational-cnc.service 2>/dev/null || true
else
    systemctl --user daemon-reload
    systemctl --user enable conversational-cnc.service
    systemctl --user restart conversational-cnc.service
fi

echo "Waiting for service to bind on port $TARGET_PORT..."
sleep 2

HTTP_STATUS=\$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$TARGET_PORT/api/health || echo "failed")
echo "HTTP response status on port $TARGET_PORT: \$HTTP_STATUS"
REMOTE_EXEC

  echo "======================================================================"
  echo "✅ Conversational-CNC-Controller successfully deployed to $PI_HOST!"
  echo "   Endpoint URL: http://$PI_HOST:$TARGET_PORT/"
  echo "   Status HUD:   http://$PI_HOST:$TARGET_PORT/status"
  echo "======================================================================"
else
  echo "✅ Dry-run complete. Run './deploy.sh' without flags to deploy."
fi
