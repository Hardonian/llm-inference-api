#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
LOG_DIR="${LOG_DIR:-/tmp/ai-lab-dashboard-verify}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/verify-$(date +%Y%m%d_%H%M%S).log"
exec > >(tee "$LOG") 2>&1

echo "=== AI Lab dashboard verify ==="
echo "repo=$(pwd)"
python_bin="${PYTHON:-.venv/bin/python}"
node_bin="${NODE:-node}"

echo "--- syntax ---"
"$python_bin" -m py_compile app/main.py app/models/schemas.py app/config/__init__.py app/middleware/security.py
"$node_bin" --check app/static/js/dashboard.js
"$node_bin" --check app/static/js/epic.js
"$node_bin" --check app/static/js/operator.js
"$node_bin" --check app/static/js/apva.js

echo "--- unit/contract tests ---"
"$python_bin" -m pytest -q

echo "--- live service checks (if running) ---"
if curl -fsS -m 3 http://127.0.0.1:8000/health >/tmp/dashboard-health.json; then
  python3 -m json.tool /tmp/dashboard-health.json >/dev/null
  token="$($python_bin - <<'PY'
from app.utils.auth import get_dashboard_token
print(get_dashboard_token())
PY
)"
  auth_header="$(printf '%s: %s %s' Authorization Bearer "$token")"
  curl -fsS -m 5 http://127.0.0.1:8000/api/productivity/apva \
    -H "$auth_header" \
    -H 'Content-Type: application/json' \
    -d '{"name":"verify","human_baseline_min":60,"ai_generation_time_min":5,"verification_time_min":8}' \
    | python3 -m json.tool >/tmp/dashboard-apva.json
  curl -fsS -m 5 http://127.0.0.1:8000/api/operator/next-action \
    -H "$auth_header" \
    | python3 -m json.tool >/tmp/dashboard-next-action.json
  echo "live checks ok"
else
  echo "live dashboard not running on 127.0.0.1:8000; skipped live checks"
fi

echo "VERIFY_LOG=$LOG"
