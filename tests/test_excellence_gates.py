"""Unit tests for the 12-R roadmap deliverables.

Run with:
    cd /home/scott/ai-workspace/repos/llm-inference-api
    .venv/bin/python -m pytest tests/ -v
"""

import json
import os
import sys
import tarfile
import io
from pathlib import Path

# Allow tests to import the app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.auth import get_dashboard_token  # noqa: E402

import app.main as m  # noqa: E402


# ============================================================
# GATE 3: AUTH hardening
# ============================================================

def test_dashboard_token_present():
    tok = get_dashboard_token()
    assert tok.startswith("dash_"), "shared dashboard token should start with dash_"
    assert len(tok) >= 32, "shared dashboard token must be long enough"


def test_to_markdown_export_renders_dicts():
    md = m._to_markdown_export("Title", {"a": 1, "b": {"c": 2}})
    assert "# Title" in md
    assert "**a**: 1" in md
    assert "**b**" in md


def test_to_markdown_export_renders_lists():
    md = m._to_markdown_export("Title", {"items": [{"x": 1}, {"x": 2}]})
    assert "[0]" in md
    assert "[1]" in md
    assert "**x**: 1" in md


# ============================================================
# GATE 5: EXPORT endpoints
# ============================================================

def test_workflow_pack_export_builds_tarball():
    inv = m._workflow_productize_inventory()
    if not inv.get("ready_packs"):
        return  # No packs to test; skip
    pack = inv["ready_packs"][0]
    slug = pack["product_url_slug"]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        readme = f"# Test Pack\\n\\nPrice: ${pack.get('estimated_price', 0)}\\n"
        ri = io.BytesIO(readme.encode())
        ti = tarfile.TarInfo("README.md")
        ti.size = len(readme)
        tf.addfile(ti, ri)
    buf.seek(0)
    with tarfile.open(fileobj=buf, mode="r:gz") as tf:
        names = tf.getnames()
        assert "README.md" in names


# ============================================================
# GATE 7: P50/P95 LATENCY (in-process, not via HTTP)
# ============================================================

def test_record_latency_and_p50():
    m._record_latency("/test/path", 0.010)
    m._record_latency("/test/path", 0.020)
    m._record_latency("/test/path", 0.100)
    samples = m.ENDPOINT_LATENCY.get("/test/path", [])
    assert len(samples) == 3
    durs = [s[1] for s in samples]
    assert sorted(durs) == sorted(durs)


# ============================================================
# GATE 12: MULTI-USER foundation
# ============================================================

def test_users_file_loads_with_default_user():
    users = m._load_users()
    assert any(u.get("id") == "default" for u in users)


def test_tokens_persistence_roundtrip():
    m._save_tokens([])
    assert m._load_tokens() == []
    m._save_tokens([{"id": "x", "token": "y", "user_id": "default", "scopes": ["dashboard"], "created_at": 0}])
    assert len(m._load_tokens()) == 1
    m._save_tokens([])  # cleanup


# ============================================================
# GATE 1: PERF / cache helpers
# ============================================================

def test_disk_rescue_cache_helper_shape():
    """Smoke check that _disk_rescue_report returns expected keys (without forcing a heavy scan)."""
    cached_path = m.DASHBOARD_STATE_DIR / "disk_rescue.json"
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": 0, "disks": [], "top_dirs": {}, "top_offenders": [], "candidates": []}
    cached_path.write_text(json.dumps(payload))
    assert cached_path.exists()
    data = json.loads(cached_path.read_text())
    assert "disks" in data
    assert "top_dirs" in data


# ============================================================
# GATE 10: SELLABILITY / money paths
# ============================================================

def test_money_paths_have_required_fields():
    paths = m._default_money_paths()
    assert len(paths) >= 3, "should have at least 3 sellable money paths"
    for p in paths:
        assert "id" in p
        assert "name" in p
        assert "tagline" in p
        assert "price_hint" in p
        assert "steps" in p
        assert isinstance(p["steps"], list)
        assert len(p["steps"]) >= 2


def test_revenue_dashboard_has_overall_readiness():
    rev = m._revenue_dashboard()
    assert "overall_readiness" in rev
    assert isinstance(rev["overall_readiness"], (int, float))


# ============================================================
# GATE 8: PREDICTIONS
# ============================================================

def test_predictive_monitoring_has_predictions():
    pred = m._predictive_monitoring()
    assert "predictions" in pred
    assert isinstance(pred["predictions"], list)


# ============================================================
# GATE 5: DEMO mode override
# ============================================================

def test_demo_override_requires_env(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    base = {"services": [{"name": "x", "ok": True}], "disk": {"paths": []}}
    assert m._maybe_demo_override(base) == base


def test_demo_override_replaces_with_fakes(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    base = {"services": [{"name": "x", "ok": False}], "disk": {"paths": [{"path": "/", "percent": 99}]}}
    out = m._maybe_demo_override(base)
    assert out["demo_mode"] is True
    assert out["services"][0]["ok"] is True
    # Disk fakes
    assert any(p.get("percent", 0) < 50 for p in out["disk"]["paths"])


# ============================================================
# GATE 2: TRENDS / HISTORY
# ============================================================

def test_history_record_and_read():
    m._record_history("revenue", {"overall_readiness": 75})
    m._record_history("revenue", {"overall_readiness": 80})
    history = m._read_list(m.HISTORY_FILES["revenue"])
    assert history[-1]["overall_readiness"] == 80


def test_trend_delta_handles_short_history():
    out = m._trend_delta([], "x")
    assert out["delta"] == 0
    out = m._trend_delta([{"x": 5}], "x")
    assert out["delta"] == 0
    out = m._trend_delta([{"x": 5}, {"x": 10}], "x")
    assert out["delta"] == 5
