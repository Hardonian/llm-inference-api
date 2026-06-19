#!/usr/bin/env bash
# AI Lab Command Center - One-command installer
# Usage:  curl -fsSL https://raw.githubusercontent.com/Hardonian/ai-lab-command-center/main/install.sh | bash
# Or:     ./scripts/install.sh [--demo] [--docker] [--no-service]
set -Eeuo pipefail

REPO="${REPO:-https://github.com/Hardonian/ai-lab-command-center}"
PYTHON="${PYTHON:-python3}"
LOG_PREFIX="[ai-lab]"

DEMO=false
NO_SERVICE=false
for arg in "$@"; do
  case $arg in
    --demo) DEMO=true ;;
    --no-service) NO_SERVICE=true ;;
    *) echo "$LOG_PREFIX Unknown arg: $arg"; exit 2 ;;
  esac
done

log() { echo "$LOG_PREFIX $*"; }
fail() { echo "$LOG_PREFIX FAIL: $*" >&2; exit 1; }

# 1. Check Python >= 3.11
log "Checking Python..."
PY_OK=$($PYTHON -c 'import sys; print(int(sys.version_info >= (3,11)))' 2>/dev/null || echo 0)
if [[ "$PY_OK" != "1" ]]; then
  fail "Python 3.11+ required. Found: $($PYTHON --version 2>&1 || echo none)"
fi
log "Python OK: $($PYTHON --version)"

# 2. Clone repo if needed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"
if [[ "$SCRIPT_DIR" == "/tmp"* ]]; then
  log "Cloning repo..."
  git clone "$REPO" 2>/dev/null || curl -L "$REPO/archive/main.tar.gz" | tar xz
  cd ai-lab-command-center && REPO_DIR="$(pwd)"
fi

# 3. Create venv if needed
VENV="${REPO_DIR}/.venv"
if [[ ! -d "$VENV" ]]; then
  log "Creating venv..."
  $PYTHON -m venv "$VENV" || fail "venv creation failed"
fi

# 4. Install deps
log "Installing dependencies..."
"$VENV/bin/pip" install --quiet --upgrade pip 2>/dev/null || true
"$VENV/bin/pip" install fastapi uvicorn[standard] httpx pydantic PyJWT python-multipart jinja2 psutil prometheus-client redis aiofiles 2>/dev/null || fail "pip install failed"

# 5. Create .env if missing
if [[ ! -f "${REPO_DIR}/.env" ]]; then
  log "Creating .env..."
  cp "${REPO_DIR}/.env.example" "${REPO_DIR}/.env" 2>/dev/null || touch "${REPO_DIR}/.env"
  SECRET=$($PYTHON -c "import secrets; print(secrets.token_urlsafe(32))")
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET/" "${REPO_DIR}/.env" 2>/dev/null || echo "SECRET_KEY=$SECRET" >> "${REPO_DIR}/.env"
fi

# 6. Demo mode
if $DEMO; then
  log "Demo mode enabled"
  sed -i 's/^DEMO_MODE=.*/DEMO_MODE=true/' "${REPO_DIR}/.env" 2>/dev/null || echo "DEMO_MODE=true" >> "${REPO_DIR}/.env"
fi

# 7. Start (or show manual start)
if ! $NO_SERVICE; then
  if command -v systemctl >/dev/null && systemctl --user daemon-reload 2>/dev/null; then
    log "Installing systemd service..."
    mkdir -p ~/.config/systemd/user
    cp "${REPO_DIR}/deploy/systemd/user/"*.service ~/.config/systemd/user/ 2>/dev/null || true
    cp "${REPO_DIR}/deploy/systemd/user/"*.timer ~/.config/systemd/user/ 2>/dev/null || true
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now ai-lab-dashboard.service 2>/dev/null || true
    log "Running as systemd user service"
  else
    log "Run manually: $VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
  fi
fi

log "Install complete! Open http://127.0.0.1:8000/dashboard"