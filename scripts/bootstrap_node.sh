#!/usr/bin/env bash
# ==============================================================================
# Conversational CNC Controller: Turnkey Node Provisioning Standard
# ==============================================================================
# Canonical provisioning script for deploying the Conversational CNC Controller
# on a fresh Raspberry Pi host (e.g., voltron.local or barn-cnc.local).
#
# Adheres to the universal workspace bootstrap pattern established across
# Server Rack nodes.
#
# Usage:
#   sudo ./scripts/bootstrap_node.sh [OPTIONS]
#
# Options:
#   -n, --dry-run       Preview provisioning steps without modifying the system
#   --port <PORT>       Target web port (default: 80)
#   --kiosk             Force enable 7" touchscreen kiosk autostart
#   -h, --help          Show this help message
# ==============================================================================

set -euo pipefail

DRY_RUN=false
PORT=80
FORCE_KIOSK=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --kiosk)
            FORCE_KIOSK=true
            shift
            ;;
        -h|--help)
            cat << 'EOF'
Usage: sudo ./scripts/bootstrap_node.sh [OPTIONS]

Options:
  -n, --dry-run       Preview provisioning steps without modifying the system
  --port <PORT>       Target web port (default: 80)
  --kiosk             Force enable 7" touchscreen kiosk autostart
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

echo "======================================================================"
echo "🚀 Node Bootstrap: Conversational CNC Controller"
echo "======================================================================"
echo "📁 Project Root:   ${PROJECT_ROOT}"
echo "🌐 Port:           ${PORT}"
echo "🔍 Dry Run:        ${DRY_RUN}"
echo "======================================================================"

# Auto-detect display hardware (DSI or HDMI touchscreen)
DETECTED_DISPLAY=false
if [[ -e /dev/fb0 || -d /sys/class/drm/card0 ]] || xrandr &>/dev/null; then
    DETECTED_DISPLAY=true
fi

KIOSK_FLAG=""
if [[ "${FORCE_KIOSK}" == "true" || "${DETECTED_DISPLAY}" == "true" ]]; then
    echo "🖥️ Display hardware detected (/dev/fb0 / DRM). Enabling 7\" Touchscreen Kiosk."
    KIOSK_FLAG="--kiosk"
fi

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "🔍 [DRY-RUN] Would execute: ${PROJECT_ROOT}/quick_install.sh --port ${PORT} ${KIOSK_FLAG}"
    echo "🔍 [DRY-RUN] Would verify local endpoint: http://127.0.0.1:${PORT}/api/health"
    echo "🔍 [DRY-RUN] Would verify system status: http://127.0.0.1:${PORT}/api/system/status"
    echo "✅ Dry run validation complete."
    exit 0
fi

# Execute quick installer
echo "📦 Executing quick_install.sh..."
"${PROJECT_ROOT}/quick_install.sh" --port "${PORT}" ${KIOSK_FLAG}

# Post-install health verification
echo "🏥 Running post-install health verification..."
sleep 2

HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
STATUS_URL="http://127.0.0.1:${PORT}/api/system/status"

if curl -sf "${HEALTH_URL}" > /dev/null; then
    echo "✅ Health check PASSED (${HEALTH_URL})"
else
    echo "⚠️ Warning: Health check endpoint did not respond immediately on ${HEALTH_URL}"
fi

if curl -sf "${STATUS_URL}" > /dev/null; then
    echo "✅ System telemetry API PASSED (${STATUS_URL})"
fi

echo "======================================================================"
echo "🎉 Node Provisioning Complete!"
echo "======================================================================"
