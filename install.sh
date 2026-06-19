#!/usr/bin/env bash
set -Eeuo pipefail

# AI Lab Command Center — One-command installer
# Usage: bash install.sh [--demo]
# Installs deps, creates venv, installs systemd service, starts dashboard.

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
SERVICE_NAME="ai-lab-dashboard"
DEMO_MODE="false"
LOG_DIR="$REPO_DIR/logs"

echo "╔══════════════════════════════════════════════╗"
echo "║   AI Lab Command Center — Installer v1.0     ║"
echo "╚══════════════════════════════════════════════╝"

# Parse flags
for arg in "$@"; do
    case "$arg" in
        --demo) DEMO_MODE="true"; echo "  → Demo mode enabled (fake GPU/system data)" ;;
    esac
done

echo ""
echo "[1/6] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PYVER ✓"

echo ""
echo "[2/6] Creating virtualenv..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  Created $VENV_DIR"
else
    echo "  Already exists, skipping"
fi

echo ""
echo "[3/6] Installing dependencies..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$REPO_DIR/requirements.txt" 2>/dev/null || \
    "$VENV_DIR/bin/pip" install -q fastapi uvicorn[standard] httpx redis prometheus-client pyjwt python-multipart
echo "  Dependencies installed ✓"

echo ""
echo "[4/6] Creating log directory..."
mkdir -p "$LOG_DIR"
echo "  $LOG_DIR ✓"

echo ""
echo "[5/6] Installing systemd user service..."
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$SYSTEMD_DIR"
cat > "$SYSTEMD_DIR/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=AI Lab Command Center Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR
Environment=DEMO_MODE=$DEMO_MODE
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/dashboard.log
StandardError=append:$LOG_DIR/dashboard-error.log

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
echo "  Service installed and enabled ✓"

echo ""
echo "[6/6] Starting service..."
systemctl --user start "$SERVICE_NAME"
sleep 2

# Health check
if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "  Dashboard is UP ✓"
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  Dashboard: http://127.0.0.1:8000/dashboard"
    echo "  Health:    http://127.0.0.1:8000/health"
    echo "  API docs:  http://127.0.0.1:8000/docs"
    if [ "$DEMO_MODE" = "true" ]; then
        echo "  Mode:      DEMO (fake GPU/service data)"
    fi
    echo "═══════════════════════════════════════════════"
else
    echo "  WARNING: Health check failed. Check logs:"
    echo "    journalctl --user -u $SERVICE_NAME -n 20"
    exit 1
fi
