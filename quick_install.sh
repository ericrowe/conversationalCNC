#!/usr/bin/env bash
# ==============================================================================
# Conversational CNC Controller: Open-Source Standalone Turnkey Installer
# ==============================================================================
# Self-contained installer for Raspberry Pi OS, Debian, Ubuntu, and Linux hosts.
# Sets up Python virtual environment, systemd service on port 80, optional
# 7" touchscreen kiosk display, and local atomic backup rotation.
#
# Usage:
#   sudo ./quick_install.sh [OPTIONS]
#
# Options:
#   --port <PORT>       Custom web port (default: 80, or 5000 in dev)
#   --kiosk             Enable Chromium fullscreen kiosk autostart for 7" touchscreen
#   --no-service        Install dependencies and virtualenv only without systemd service
#   --dry-run, -n       Preview install actions without modifying system
#   --help, -h          Show this help message
# ==============================================================================

set -euo pipefail

TARGET_PORT=80
ENABLE_KIOSK=false
INSTALL_SERVICE=true
DRY_RUN=false
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="${SUDO_USER:-$(whoami)}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            TARGET_PORT="$2"
            shift 2
            ;;
        --kiosk)
            ENABLE_KIOSK=true
            shift
            ;;
        --no-service)
            INSTALL_SERVICE=false
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            cat << 'EOF'
Conversational CNC Controller Installer

Usage:
  sudo ./quick_install.sh [OPTIONS]

Options:
  --port <PORT>       Custom web port (default: 80)
  --kiosk             Enable 7" touchscreen kiosk autostart
  --no-service        Setup venv only without creating systemd service
  --dry-run, -n       Preview install actions without making changes
  --help, -h          Show help message
EOF
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Run ./quick_install.sh --help for options"
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo "⚡ Conversational CNC Controller: Standalone Installation"
echo "======================================================================"
echo "📁 Install Directory: ${INSTALL_DIR}"
echo "👤 App User:          ${APP_USER}"
echo "🌐 Web Port:          ${TARGET_PORT}"
echo "🖥️ Touchscreen Kiosk: ${ENABLE_KIOSK}"
echo "🔍 Dry Run:           ${DRY_RUN}"
echo "======================================================================"

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "🔍 [DRY-RUN] System packages to install: python3 python3-venv sqlite3 libcap2-bin curl rsync"
    echo "🔍 [DRY-RUN] Virtual environment will be built at ${INSTALL_DIR}/.venv"
    if [[ "${INSTALL_SERVICE}" == "true" ]]; then
        echo "🔍 [DRY-RUN] Systemd service will be configured: /etc/systemd/system/conversational-cnc.service"
    fi
    if [[ "${ENABLE_KIOSK}" == "true" ]]; then
        echo "🔍 [DRY-RUN] Kiosk autostart will be configured at /etc/xdg/autostart/cnc-kiosk.desktop"
    fi
    echo "✅ Dry run preview complete. No modifications made."
    exit 0
fi

# Ensure root privileges for system packages and systemd
if [[ $EUID -ne 0 && "${INSTALL_SERVICE}" == "true" ]]; then
    echo "⚠️ System service installation requires root privileges. Please run with sudo:"
    echo "   sudo ./quick_install.sh"
    exit 1
fi

echo "📦 Step 1: Installing system dependencies..."
if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip sqlite3 libcap2-bin curl rsync
    if [[ "${ENABLE_KIOSK}" == "true" ]]; then
        apt-get install -y -qq chromium-browser || apt-get install -y -qq chromium || true
    fi
elif command -v dnf &>/dev/null; then
    dnf install -y python3 sqlite curl rsync
fi

echo "🐍 Step 2: Building Python virtual environment..."
VENV_DIR="${INSTALL_DIR}/.venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip -q
if [[ -f "${INSTALL_DIR}/requirements.txt" ]]; then
    "${VENV_DIR}/bin/python" -m pip install -r "${INSTALL_DIR}/requirements.txt" -q
fi

# Ensure python binary can bind to port 80 without full root
if command -v setcap &>/dev/null && [[ -f "${VENV_DIR}/bin/python" ]]; then
    setcap 'cap_net_bind_service=+ep' "${VENV_DIR}/bin/python" || true
fi

# Create instance directory with proper permissions
mkdir -p "${INSTALL_DIR}/instance"
mkdir -p "${INSTALL_DIR}/backend/instance"
mkdir -p /var/backups/conversational_cnc
chown -R "${APP_USER}:${APP_USER}" "${INSTALL_DIR}" /var/backups/conversational_cnc || true

if [[ "${INSTALL_SERVICE}" == "true" ]]; then
    echo "⚙️ Step 3: Installing systemd service (port ${TARGET_PORT})..."
    cat > /etc/systemd/system/conversational-cnc.service << EOF
[Unit]
Description=Conversational CNC Controller Web & Generation Engine
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PORT=${TARGET_PORT}"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_DIR}/bin/python run.py
Restart=always
RestartSec=3
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable conversational-cnc.service
    systemctl restart conversational-cnc.service

    echo "⏳ Waiting for service startup..."
    sleep 2

    if systemctl is-active --quiet conversational-cnc.service; then
        echo "✅ Service is active and running!"
    else
        echo "⚠️ Service did not start cleanly. Check logs: journalctl -u conversational-cnc.service -n 20"
    fi
fi

if [[ "${ENABLE_KIOSK}" == "true" ]]; then
    echo "🖥️ Step 4: Configuring 7\" Touchscreen Kiosk Display..."
    mkdir -p /etc/xdg/autostart
    cat > /etc/xdg/autostart/cnc-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=Conversational CNC Status Kiosk
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 http://127.0.0.1:${TARGET_PORT}/status
X-GNOME-Autostart-enabled=true
EOF
    echo "✅ Kiosk autostart configured for display session."
fi

# Daily Backup Cron
echo "💾 Step 5: Configuring automated daily backup snapshot..."
if [[ -f "${INSTALL_DIR}/scripts/backup_cnc.sh" ]]; then
    chmod +x "${INSTALL_DIR}/scripts/backup_cnc.sh"
    cat > /etc/cron.d/conversational-cnc-backup << EOF
# Daily atomic SQLite snapshot for Conversational CNC Controller
30 2 * * * ${APP_USER} ${INSTALL_DIR}/scripts/backup_cnc.sh > /var/log/cnc_backup.log 2>&1
EOF
    chmod 644 /etc/cron.d/conversational-cnc-backup
fi

# Discover Primary Local IP
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "======================================================================"
echo "🎉 Installation Complete!"
echo "======================================================================"
echo "🌐 Web Interface:      http://${HOST_IP}:${TARGET_PORT}/"
echo "📊 Server Status HUD:  http://${HOST_IP}:${TARGET_PORT}/status"
echo "🔧 Systemd Service:    systemctl status conversational-cnc.service"
echo "📜 View Service Logs:  journalctl -u conversational-cnc.service -f"
echo "======================================================================"
