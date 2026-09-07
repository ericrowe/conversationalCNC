#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - Deployment Script for Conversational-CNC-Controller
# Supports --dry-run / -n preview mode
# ==============================================================================
set -euo pipefail

PI_USER="${PI_USER:-detour}"
PI_HOST="${PI_HOST:-pi-lab.local}"
TARGET_DIR="/opt/conversational-cnc"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  DRY_RUN="--dry-run"
  echo "🔍 Running deployment DRY-RUN (no remote files will be modified)..."
else
  echo "🚀 Deploying Conversational-CNC-Controller to ($PI_HOST)..."
fi

# Pre-flight reachability check
if [[ -z "$DRY_RUN" ]]; then
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_USER@$PI_HOST" "true" >/dev/null 2>&1; then
    echo "❌ Error: Target host ($PI_HOST) is unreachable via SSH. Aborting deployment." >&2
    exit 1
  fi
  ssh "$PI_USER@$PI_HOST" "sudo mkdir -p $TARGET_DIR /srv/database/cnc && sudo chown -R $PI_USER:www-data $TARGET_DIR /srv/database/cnc && sudo chmod 775 /srv/database/cnc"
fi

# Synchronize Application Files
rsync -avz $DRY_RUN \
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
  ssh "$PI_USER@$PI_HOST" bash << 'REMOTE_EXEC'
set -euo pipefail
APP_DIR="/opt/conversational-cnc"

if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/python" -m pip install --upgrade -q pip
if [ -f "$APP_DIR/backend/requirements.txt" ]; then
    "$APP_DIR/.venv/bin/python" -m pip install -q -r "$APP_DIR/backend/requirements.txt"
fi

sudo tee /etc/systemd/system/conversational-cnc.service >/dev/null << SYSTEMD_UNIT
[Unit]
Description=Conversational CNC Controller Microservice
After=network.target

[Service]
Type=simple
User=detour
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python run.py
Restart=always
RestartSec=5s
Environment=PYTHONPATH=$APP_DIR:$APP_DIR/backend
Environment=PORT=5001

[Install]
WantedBy=multi-user.target
SYSTEMD_UNIT

sudo systemctl daemon-reload
sudo systemctl enable conversational-cnc.service
sudo systemctl restart conversational-cnc.service

echo "Waiting for service to bind on :5001..."
sleep 2

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/ || echo "failed")
echo "HTTP response status on :5001: $HTTP_STATUS"
REMOTE_EXEC

  echo "======================================================================"
  echo "✅ Conversational-CNC-Controller successfully deployed to $PI_HOST!"
  echo "   Endpoint URL: http://$PI_HOST:5001"
  echo "======================================================================"
else
  echo "✅ Dry-run complete. Run './deploy.sh' without flags to deploy."
fi
