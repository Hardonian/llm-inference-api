#!/usr/bin/env bash
set -Eeuo pipefail

UNIT=ai-lab-dashboard.service
BASE_URL=${AI_LAB_DASHBOARD_URL:-http://127.0.0.1:8000}
ROOT=/home/scott/ai-workspace/repos/llm-inference-api

usage() {
  cat <<'EOF'
Usage: dashboardctl.sh <status|health|logs|restart|smoke|stop|start>

Commands:
  status   Show systemd user unit state, port owner, and disk snapshot
  health   Require /health JSON 200
  logs     Tail recent systemd logs
  restart  Restart the user service and verify /health
  smoke    Run syntax checks, API health, and browser smoke test
  stop     Stop service
  start    Start service and verify /health
EOF
}

health() {
  python3 - <<'PY'
import json, sys, urllib.request
url = "http://127.0.0.1:8000/health"
with urllib.request.urlopen(url, timeout=10) as r:
    data = json.load(r)
print(json.dumps({"status": data.get("status"), "checks": sorted((data.get("checks") or {}).keys())}, indent=2))
if data.get("status") != "ok":
    raise SystemExit(1)
PY
}

case "${1:-status}" in
  status)
    systemctl --user status "$UNIT" --no-pager || true
    echo
    ss -lptn | grep ':8000\b' || true
    echo
    df -hT / /mnt/ai-storage 2>/dev/null || true
    ;;
  health)
    health
    ;;
  logs)
    journalctl --user -u "$UNIT" -n "${2:-120}" --no-pager
    ;;
  restart)
    systemctl --user restart "$UNIT"
    sleep 2
    health
    ;;
  start)
    systemctl --user start "$UNIT"
    sleep 2
    health
    ;;
  stop)
    systemctl --user stop "$UNIT"
    ;;
  smoke)
    cd "$ROOT"
    .venv/bin/python -m py_compile app/main.py app/middleware/security.py app/models/schemas.py app/config/__init__.py app/services/comfyui.py
    node --check app/static/js/dashboard.js
    health
    DASHBOARD_URL="$BASE_URL/dashboard" node scripts/dashboard-smoke-playwright.js
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 2
    ;;
esac
