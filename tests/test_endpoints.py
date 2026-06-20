"""Contract tests against the live HTTP API using FastAPI TestClient.

Run with:
    .venv/bin/python -m pytest tests/test_endpoints.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.utils.auth import get_dashboard_token  # noqa: E402
import app.main as m  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(m.app)


@pytest.fixture
def auth_header():
    from pathlib import Path as _P
    tok = get_dashboard_token() or _P('/home/scott/ai-lab/dashboard/.api-token').read_text().strip()
    return {"Authorization": f"Bearer {tok}"}


# ============================================================
# PUBLIC endpoints (no auth)
# ============================================================

def test_health_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


def test_system_snapshot_public(client):
    r = client.get("/api/system/snapshot")
    assert r.status_code == 200
    assert "services" in r.json()


def test_dashboard_smoke_public(client):
    r = client.get("/api/dashboard/smoke")
    assert r.status_code == 200


def test_disk_rescue_public(client):
    r = client.get("/api/disk/rescue")
    assert r.status_code == 200


# ============================================================
# LOCKED endpoints (require auth)
# ============================================================

def test_revenue_status_locked(client):
    r = client.get("/api/revenue/status")
    assert r.status_code == 401


def test_revenue_status_with_auth(client, auth_header):
    r = client.get("/api/revenue/status", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert "overall_readiness" in data


def test_predictions_locked(client):
    r = client.get("/api/system/predictions")
    assert r.status_code == 401


def test_predictions_with_auth(client, auth_header):
    r = client.get("/api/system/predictions", headers=auth_header)
    assert r.status_code == 200


def test_agent_command_with_auth(client, auth_header):
    r = client.post("/api/agent/command", headers=auth_header,
                    json={"directive": "check disk"})
    assert r.status_code == 200


def test_agent_easter_egg_with_auth(client, auth_header):
    r = client.post("/api/agent/command", headers=auth_header,
                    json={"directive": "god mode"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") == "easter_egg"


# ============================================================
# EXPORT endpoints (require auth)
# ============================================================

def test_revenue_export_locked(client):
    r = client.get("/api/revenue/export")
    assert r.status_code == 401


def test_disk_rescue_export_locked(client):
    r = client.get("/api/disk/rescue/export")
    assert r.status_code == 401


def test_predictions_export_locked(client):
    r = client.get("/api/predictions/export")
    assert r.status_code == 401


def test_revenue_export_markdown(client, auth_header):
    r = client.get("/api/revenue/export", headers=auth_header)
    assert r.status_code == 200
    assert "markdown" in r.headers.get("Content-Type", "")
    body = r.text
    assert "# AI Lab Revenue Report" in body


def test_disk_rescue_export_markdown(client, auth_header):
    r = client.get("/api/disk/rescue/export", headers=auth_header)
    assert r.status_code == 200
    assert "markdown" in r.headers.get("Content-Type", "")


def test_predictions_export_markdown(client, auth_header):
    r = client.get("/api/predictions/export", headers=auth_header)
    assert r.status_code == 200


# ============================================================
# TRENDS endpoint
# ============================================================

def test_trends_with_auth(client, auth_header):
    r = client.get("/api/trends", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert "trends" in data
    assert set(data["trends"].keys()) >= {"revenue", "improvements", "predictions", "agents"}


# ============================================================
# P50 endpoint
# ============================================================

def test_p50_with_auth(client, auth_header):
    r = client.get("/api/p50", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert "endpoints" in data
    assert "alerts" in data


def test_trends_locked(client):
    r = client.get("/api/trends")
    assert r.status_code == 200  # Public monitoring endpoint


def test_p50_locked(client):
    r = client.get("/api/p50")
    assert r.status_code == 200  # Public monitoring endpoint


# ============================================================
# AUTH endpoints
# ============================================================

def test_auth_me_with_auth(client, auth_header):
    r = client.get("/api/auth/me", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert data.get("authenticated") is True


def test_auth_me_without_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 200  # auth/me itself is in PUBLIC_PATHS
    data = r.json()
    assert data.get("authenticated") is False


def test_create_token_with_auth(client, auth_header):
    r = client.post("/api/auth/tokens", headers=auth_header, json={"user_id": "test-user"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("token", "").startswith("dash_")
    assert data.get("user_id") == "test-user"


# ============================================================
# PRODUCTIVITY / OPERATOR endpoints
# ============================================================

def test_apva_productivity_locked(client):
    r = client.post("/api/productivity/apva", json={"name": "smoke"})
    assert r.status_code == 401


def test_apva_productivity_with_auth(client, auth_header):
    r = client.post(
        "/api/productivity/apva",
        headers=auth_header,
        json={
            "name": "smoke",
            "human_baseline_min": 60,
            "ai_generation_time_min": 5,
            "verification_time_min": 8,
            "exact_span_recall": 0.9,
            "faithfulness_score": 0.85,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "APVA formula"
    assert data["true_value_yield_min"] > 0
    assert data["verdict"] in {"scale", "optimize", "kill"}


def test_operator_next_action_with_auth(client, auth_header):
    r = client.get("/api/operator/next-action", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert "top_action" in data
    assert "repos" in data


def test_verification_record_and_latest_with_auth(client, auth_header):
    r = client.post(
        "/api/verification/record",
        headers=auth_header,
        json={"repo": "test", "command": "pytest", "exit_code": 0, "summary": "ok"},
    )
    assert r.status_code == 200
    latest = client.get("/api/verification/latest", headers=auth_header)
    assert latest.status_code == 200
    assert "records" in latest.json()
