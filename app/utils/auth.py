"""Shared dashboard auth helpers."""
import os
import secrets
from pathlib import Path

DASHBOARD_STATE_DIR = Path(os.environ.get("DASHBOARD_STATE_DIR", "/home/scott/ai-lab/dashboard"))
API_TOKEN_FILE = DASHBOARD_STATE_DIR / ".api-token"

def get_dashboard_token() -> str:
    """Auto-generated shared-secret for the dashboard, persisted to file."""
    tok = os.environ.get("DASHBOARD_API_TOKEN", "").strip()
    if tok:
        return tok
    if API_TOKEN_FILE.exists():
        return API_TOKEN_FILE.read_text().strip()
    tok = "dash_" + secrets.token_urlsafe(32)
    try:
        API_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        API_TOKEN_FILE.write_text(tok)
        os.chmod(API_TOKEN_FILE, 0o600)
    except Exception:
        pass
    return tok
