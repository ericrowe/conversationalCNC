#!/usr/bin/env bash
# ==============================================================================
# run_tests.sh - Hermetic Test Runner for Conversational-CNC-Controller
# Automatically resolves Python virtual environment and executes pytest suite
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Resolve Python virtual environment
PYTHON_BIN=""
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/backend/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Error: No valid Python interpreter found in .venv/, backend/.venv/, or system PATH." >&2
    exit 1
fi

# 2. Execute pytest hermetically
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/backend"
echo "🧪 Running Conversational-CNC-Controller tests with: $PYTHON_BIN"
if [ $# -eq 0 ]; then
    set -- backend/tests/
fi
exec "$PYTHON_BIN" -m pytest "$@"
