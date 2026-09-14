#!/usr/bin/env bash
# ==============================================================================
# install_sudoers.sh - Install Scoped Sudoers Drop-in for Conversational CNC
# Run on voltron: sudo ./scripts/install_sudoers.sh
# ==============================================================================
set -euo pipefail

TARGET_FILE="/etc/sudoers.d/020_conversational_cnc"
APP_USER="${1:-detour}"

echo "======================================================================"
echo "🔒 Installing Scoped Least-Privilege Sudoers for Conversational CNC"
echo "======================================================================"
echo "Target User: ${APP_USER}"
echo "Target File: ${TARGET_FILE}"

if [[ $EUID -ne 0 ]]; then
    echo "⚠️ Root privileges required. Re-running with sudo..."
    exec sudo "$0" "$APP_USER"
fi

cat > "${TARGET_FILE}" << EOF
# Least-privilege scoped permissions for Conversational CNC Controller
${APP_USER} ALL=(ALL) NOPASSWD: /sbin/poweroff, /usr/sbin/poweroff, /sbin/reboot, /usr/sbin/reboot, /bin/systemctl poweroff, /usr/bin/systemctl poweroff, /bin/systemctl reboot, /usr/bin/systemctl reboot, /bin/systemctl restart conversational-cnc.service, /usr/bin/systemctl restart conversational-cnc.service
EOF

chmod 0440 "${TARGET_FILE}"

if command -v visudo &>/dev/null; then
    visudo -c -f "${TARGET_FILE}"
    echo "✅ Sudoers syntax verified successfully by visudo."
fi

echo "======================================================================"
echo "🎉 Scoped sudoers permissions installed for ${APP_USER}!"
echo "======================================================================"
