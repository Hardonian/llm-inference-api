#!/usr/bin/env bash
# AI Lab Command Center - One-command installer
# Usage:  curl -fsSL <url>/install.sh | bash
# Or:     ./scripts/install.sh [--demo] [--no-service]
set -Eeuo pipefail

REPO="${REPO:-/home/scott/ai-workspace/repos/llm-inference-api}"
PYTHON="${PYTHON:-python3}"
VENV="${REPO}/.venv"
LOG_PREFIX="[ai-lab-install]"

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

# 2. Create venv if needed
if [[ ! -d "$VENV" ]]; then
  log "Creating venv at $VENV..."
  $PYTHON -m venv "$VENV" || fail "venv creation failed"
else
  log "Venv exists at $VENV"
fi

# 3. Install deps
log "Installing dependencies..."
"$VENV/bin/pip" install --quiet --upgrade pip || fail "pip upgrade failed"
"$VENV/bin/pip" install --quiet -r "$REPO/requirements.txt" 2>/dev/null || \
  "$VENV/bin/pip" install --quiet fastapi uvicorn[standard] httpx pydantic pydantic-settings \
    PyJWT python-multipart jinja2 psutil prometheus-client redis aiofiles 2>/dev/null || \
    fail "dependency install failed"

# 4. Create .env if missing
if [[ ! -f "$REPO/.env" ]]; then
  log "Creating .env from example..."
  cp "$REPO/.env.example" "$REPO/.env"
  # Generate a random SECRET_KEY
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$REPO/.env"
fi

# 5. Demo mode toggle
if $DEMO; then
  log "Demo mode enabled (will use fake GPU/services data)"
  sed -i 's/^DEMO_MODE=.*/DEMO_MODE=true/' "$REPO/.env"
fi

# 6. Install systemd units (user-level, no sudo)
if ! $NO_SERVICE; then
  log "Installing systemd units..."
  mkdir -p ~/.config/systemd/user
  for unit in ai-lab-dashboard.service ai-lab-dashboard-smoke.service ai-lab-dashboard-smoke.timer; do
    if [[ -f "$REPO/deploy/systemd/user/$unit" ]]; then
      cp "$REPO/deploy/systemd/user/$unit" ~/.config/systemd/user/
      log "  installed $unit"
    fi
  done
  systemctl --user daemon-reload || log "WARNING: systemctl --user not available"
  if command -v systemctl >/dev/null && systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable --now ai-lab-dashboard.service 2>&1 | sed "s/^/$LOG_PREFIX  /"
    systemctl --user enable --now ai-lab-dashboard-smoke.timer 2>&1 | sed "s/^/$LOG_PREFIX  /"
    log "Service enabled and started"
  else
    log "systemctl not available; start manually: $VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
  fi
fi

log ""
log "Install complete. Open http://127.0.0.1:8000/dashboard"
