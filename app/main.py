from contextlib import asynccontextmanager
from pathlib import Path
import time
import os
import asyncio
import json
import tarfile
import subprocess
from typing import Optional, List, Any, Dict
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, Form, File, UploadFile, Body
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from jinja2 import Environment, FileSystemLoader
import httpx

from app.config import settings
from app.core.exceptions import LLMInferenceError
from app.core.logging import configure_logging, get_logger
from app.middleware.auth import get_current_user_optional, require_permission, create_access_token, create_refresh_token, verify_refresh_token
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityMiddleware, CORSMiddleware
from app.services.ollama import ollama_manager
from app.services.usage import UsageTracker
from app.services.comfyui import comfyui_service
from app.services.security import security_service
from app.models.schemas import (
    GenerateRequest, ImprovePromptRequest, WorkflowCreate, WorkflowUpdate,
    ModelDownloadRequest, SecurityScanRequest, UpscaleRequest, VariationsRequest,
    BatchGenerateRequest, WorkflowType, PromptMode, ModelType,
)

configure_logging(debug=settings.debug)
logger = get_logger("llm-inference-api")

# Custom Jinja2Templates with fixed cache key handling
class FixedJinja2Templates(Jinja2Templates):
    def __init__(self, directory: str):
        super().__init__(directory)
        self.env = Environment(
            loader=FileSystemLoader(directory),
            autoescape=True,
            enable_async=True,
            cache_size=0,
        )

templates = FixedJinja2Templates(directory=Path(__file__).resolve().parent / "templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting app", app=settings.app_name, env=settings.environment)
    await ollama_manager.health_check_all()
    _system_snapshot()
    task = asyncio.create_task(_watchdog_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("watchdog_shutdown_failed")
    await ollama_manager.close()
    logger.info("shutting down")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(SecurityMiddleware, enable_auth=True)
app.add_middleware(CORSMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)

AGENT_ROOT = Path(os.environ.get("AI_LAB_AGENT_ROOT", "/home/scott/ai-lab/agent"))
TOOLS_FILE = AGENT_ROOT / "tools.json"
MCP_AGENTS_FILE = AGENT_ROOT / "mcp_agents.json"
MCP_RUNS_FILE = AGENT_ROOT / "mcp_runs.json"
VIEWS_FILE = AGENT_ROOT / "views.json"
WORKFLOW_ROOT = Path("/home/scott/ai-lab/image/workflows")
AI_LAB_INPUT_DIR = Path("/home/scott/ai-lab/image/inputs")
COMFYUI_ROOT = Path(os.environ.get("COMFYUI_ROOT", "/opt/ai/comfyui/ComfyUI"))
COMFYUI_INPUT_DIR = COMFYUI_ROOT / "input"
COMFYUI_MODELS_DIR = COMFYUI_ROOT / "models"
COMFYUI_OUTPUT_DIR = COMFYUI_ROOT / "output"
DASHBOARD_STATE_DIR = Path("/home/scott/ai-lab/dashboard")
JOBS_FILE = DASHBOARD_STATE_DIR / "jobs.json"
ACHIEVEMENTS_FILE = DASHBOARD_STATE_DIR / "achievements.json"


import urllib.request, shutil, socket
def _now_ts() -> float:
    return time.time()
def _default_money_paths() -> List[Dict[str, Any]]:
    return [
        {"id":"private-dashboards","name":"Private AI Lab Dashboards","tagline":"Sell the sovereign dashboard you already built.","price_hint":"$297 lifetime / $29/mo managed","lever":"llm-inference-api + ComfyUI + this dashboard","steps":["Package the repo as a private template","Record 5-min setup walkthrough","Post on X + IndieHackers + local AI communities","Offer 1 paid setup call/week"]},
        {"id":"prompt-studio","name":"Prompt Studio Service","tagline":"Tie txt2img/img2img/img2video queues to a hosted dashboard.","price_hint":"$199 lifetime","lever":"ComfyUI workflows + 8 prompt modes","steps":["Ship 3 starter workflows as paid add-on","Bundle with the dashboard","Bundle a private LoRA pack"]},
        {"id":"comfy-model-curation","name":"Comfy Model Curator","tagline":"Organize + tag local models and sell curated packs.","price_hint":"$49 per pack","lever":"comfy-model-organize.sh + organized ComfyUI dir","steps":["Pick a vertical (fashion, fitness, anime)","Curate 4-6 models + 1 LoRA per pack","Show 3 sample outputs in landing page"]},
        {"id":"video-recipes","name":"Wan 2.2 Video Recipes","tagline":"Tested txt2video / img2video recipes that actually run on RTX 3060.","price_hint":"$79 per recipe","lever":"Wan 2.2 + VHS + lightx2v LoRA","steps":["Validate one working Wan pipeline end-to-end","Record timing on each GPU","Sell recipe + sample gallery"]},
        {"id":"autonomous-ops","name":"Autonomous Operator Retainer","tagline":"Offer self-heal + watchdog + daily briefing as a service.","price_hint":"$99/mo per node","lever":"watchdog + self-heal + briefing API","steps":["Run the watchdog on one client node","Show uptime + auto-recovery log","Convert into monthly retainer"]},
        {"id":"local-llm-benchmarks","name":"Local LLM Benchmark Reports","tagline":"Automated weekly benchmark across V100/P40/3060 lanes.","price_hint":"$39/mo","lever":"Ollama lanes + 12 models each","steps":["Pick 5 prompts","Score tokens/sec + first-token latency","Send weekly PDF"]},
    ]


def _money_snapshot() -> Dict[str, Any]:
    return {"updated_at": _now_ts(), "paths": _default_money_paths()}


# ============================================================
# EPIC / BREAKER POWERUPS: agent command, self-improvement, revenue, predictions
# ============================================================

def _agent_command_router(directive: str) -> Dict[str, Any]:
    """Natural-language operator router. No LLM cloud call; deterministic local intent matching."""
    d = (directive or "").lower().strip()
    if d in {"god mode", "break all the rules", "unlock epic", "sudo make me a sandwich"}:
        return {
            "directive": directive,
            "intent": "easter_egg",
            "timestamp": _now_ts(),
            "result": {
                "message": "Breaker mode engaged. Hidden superpowers: Ctrl+K command palette, /api/agent/command, /api/revenue/status, /api/system/predictions, /api/workflows/productize.",
                "cheat_codes": ["disk rescue", "model truth", "heal", "money", "briefing", "repos", "private creations", "workflows", "improve", "predict"],
                "next_move": "Type 'money' in the command palette or click 🔮 Epic Command Center."
            }
        }
    intent = "unknown"
    args = {}
    if any(w in d for w in ["disk", "space", "full", "cleanup", "rescue"]):
        intent = "disk_rescue"
    elif any(w in d for w in ["model", "duplicate", "dedupe", "models"]):
        intent = "model_truth"
    elif any(w in d for w in ["heal", "fix", "repair", "recover", "restart"]):
        intent = "self_heal"
    elif any(w in d for w in ["money", "revenue", "monetize", "sell", "productize"]):
        intent = "revenue"
    elif any(w in d for w in ["brief", "status", "report", "sitrep"]):
        intent = "briefing"
    elif any(w in d for w in ["repos", "repository", "projects", "codebase"]):
        intent = "repos"
    elif any(w in d for w in ["creations", "private", "images", "output", "comfy output"]):
        intent = "private_creations"
    elif any(w in d for w in ["workflow", "comfy workflow", "pack"]):
        intent = "workflow_productize"
    elif any(w in d for w in ["improve", "better", "smarter", "upgrade", "optimize"]):
        intent = "self_improve"
    elif any(w in d for w in ["predict", "forecast", "will disk", "trend"]):
        intent = "predictions"
    elif any(w in d for w in ["gpu", "nvidia", "vram"]):
        intent = "gpu_status"
    elif any(w in d for w in ["logs", "journal"]):
        intent = "logs"
    else:
        args["fallback"] = True

    executed = {}
    if intent == "disk_rescue":
        executed = {"disk_rescue": _disk_rescue_report()}
    elif intent == "model_truth":
        executed = {"model_truth": _model_truth_report()}
    elif intent == "self_heal":
        executed = {"self_heal": _self_heal_actor()}
    elif intent == "revenue":
        executed = {"revenue": _revenue_dashboard(), "money_leads": _money_snapshot()}
    elif intent == "briefing":
        executed = {"briefing": _cooperator_briefing()}
    elif intent == "repos":
        executed = {"repos": _cooperator_repos_list()}
    elif intent == "private_creations":
        executed = {"private_creations": _private_creations_summary()}
    elif intent == "workflow_productize":
        executed = {"workflow_productize": _workflow_productize_inventory()}
    elif intent == "self_improve":
        executed = {"self_improve": _self_improvement_suggestions()}
    elif intent == "predictions":
        executed = {"predictions": _predictive_monitoring()}
    elif intent == "gpu_status":
        executed = {"gpu_status": _system_snapshot().get("gpu", {})}
    elif intent == "logs":
        executed = {"logs": _dashboard_logs(80)}
    else:
        executed = {"help": "Try: disk rescue, model truth, heal, money, briefing, repos, private creations, workflows, improve, predict"}

    return {
        "directive": directive,
        "intent": intent,
        "timestamp": _now_ts(),
        "result": executed,
    }


def _cooperator_repos_list() -> Dict[str, Any]:
    base = Path("/home/scott/ai-workspace/repos")
    repos = []
    if base.exists():
        for p in sorted(base.iterdir()):
            if p.is_dir():
                git = p / ".git"
                meta = {"name": p.name, "path": str(p), "is_git": git.exists()}
                if git.exists():
                    try:
                        head = (git / "HEAD").read_text().strip()
                        meta["head_ref"] = head.split("/")[-1]
                    except Exception:
                        pass
                repos.append(meta)
    return {"repos": repos, "base": str(base)}


def _revenue_dashboard() -> Dict[str, Any]:
    """Track active money opportunities + add sales-ready scoring."""
    paths = _default_money_paths()
    report = _system_snapshot()
    services = report.get("services", []) or []
    svc_ok = {s["name"]: s.get("ok", False) for s in services}
    total_score = 0
    for p in paths:
        score = 50
        if "dashboard" in p["lever"].lower(): score += 15
        if "ComfyUI" in p["lever"]: score += 15 if svc_ok.get("comfyui") else 0
        if "Ollama" in p["lever"]: score += 15 if svc_ok.get("ollama") else 0
        p["readiness_score"] = min(score, 100)
        total_score += p["readiness_score"]
    avg = total_score // len(paths) if paths else 0
    return {
        "updated_at": _now_ts(),
        "overall_readiness": avg,
        "paths": sorted(paths, key=lambda x: x["readiness_score"], reverse=True),
        "next_action": "Ship Private AI Lab Dashboards (highest readiness)" if avg >= 70 else "Stabilize GPU lanes and model stores first",
    }


def _self_improvement_suggestions() -> Dict[str, Any]:
    """Dashboard looks at its own logs and state and suggests concrete improvements."""
    snap = _system_snapshot()
    suggestions = []
    disk_high = [d for d in snap.get("disk", {}).get("paths", []) if d.get("percent", 0) >= 80]
    if disk_high:
        suggestions.append({"area": "disk", "impact": "high", "title": "Add automatic disk pressure prediction", "why": "Path(s) >=80% full; trend-based alerts prevent outages.", "action": "Implement /api/system/predictions with daily growth rate.", "estimated_hours": 2})
    services_down = [s["name"] for s in snap.get("services", []) if not s.get("ok")]
    if services_down:
        suggestions.append({"area": "reliability", "impact": "high", "title": "Tighten watchdog restart thresholds", "why": f"Services currently down: {services_down}", "action": "Add per-service restart policy + backoff in _self_heal_actor.", "estimated_hours": 3})
    if not _read_json_file(DASHBOARD_STATE_DIR / "smoke.json", {}).get("last_ok"):
        suggestions.append({"area": "quality", "impact": "med", "title": "Surface last smoke result in dashboard header", "why": "Operators need at-a-glance confidence.", "action": "Read smoke.json in /api/system/watchdog and badge the UI.", "estimated_hours": 1})
    # Always give at least one product suggestion
    suggestions.append({"area": "money", "impact": "high", "title": "Auto-generate workflow product pages", "why": "ComfyUI outputs exist; packaging them is manual friction.", "action": "Build /api/workflows/productize to export packs.", "estimated_hours": 4})
    suggestions.append({"area": "ux", "impact": "med", "title": "Add command palette (Ctrl+K)", "why": "Power users need sub-1-second access to every action.", "action": "Implement global keyboard-driven command palette.", "estimated_hours": 2})
    suggestions.append({"area": "ux", "impact": "med", "title": "Make particle background react to GPU load", "why": "Visual feedback makes the lab feel alive.", "action": "Pass GPU load to canvas renderer via WebSocket.", "estimated_hours": 1})
    return {"updated_at": _now_ts(), "suggestions": suggestions}


def _predictive_monitoring() -> Dict[str, Any]:
    """Predict disk and service trouble before it happens."""
    snap = _system_snapshot()
    predictions = []
    history = _read_json_file(DASHBOARD_STATE_DIR / "disk_history.json", [])
    for path in ["/", "/mnt/ai-storage"]:
        usage = next((d for d in snap.get("disk", {}).get("paths", []) if d.get("path") == path), None)
        if not usage:
            continue
        hist = [h for h in history if h.get("path") == path]
        pct = usage.get("percent", 0)
        trend = 0
        days_to_full = None
        if len(hist) >= 2:
            first, last = hist[0], hist[-1]
            dt = last.get("ts", _now_ts()) - first.get("ts", _now_ts())
            dp = last.get("percent", pct) - first.get("percent", pct)
            if dt > 0:
                trend = dp / (dt / 86400)  # percent per day
                if trend > 0 and pct < 100:
                    days_to_full = (100 - pct) / trend
        predictions.append({
            "path": path,
            "percent": pct,
            "trend_pct_per_day": round(trend, 3),
            "days_to_full": round(days_to_full, 1) if days_to_full else None,
            "risk": "critical" if (days_to_full and days_to_full < 7) else "high" if pct >= 85 else "med" if pct >= 75 else "low",
        })
    # Persist history
    try:
        for path in ["/", "/mnt/ai-storage"]:
            usage = next((d for d in snap.get("disk", {}).get("paths", []) if d.get("path") == path), None)
            if usage:
                history.append({"ts": _now_ts(), "path": path, "percent": usage.get("percent", 0)})
        # keep last 90 days
        history = history[-2000:]
        _write_json_file(DASHBOARD_STATE_DIR / "disk_history.json", history)
    except Exception:
        pass
    return {"updated_at": _now_ts(), "predictions": predictions}


def _workflow_productize_inventory() -> Dict[str, Any]:
    """Find ComfyUI workflows and output galleries ready to become products."""
    workflows = []
    sample_outputs = []
    if WORKFLOW_ROOT.exists():
        for fp in sorted(WORKFLOW_ROOT.rglob("*.json")):
            try:
                data = json.loads(fp.read_text())
                nodes = len(data) if isinstance(data, dict) else 0
                workflows.append({"name": fp.stem, "path": str(fp), "nodes": nodes, "size": fp.stat().st_size})
            except Exception:
                workflows.append({"name": fp.stem, "path": str(fp), "nodes": 0, "size": fp.stat().st_size})
    if COMFYUI_OUTPUT_DIR.exists():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            for fp in sorted(COMFYUI_OUTPUT_DIR.rglob(ext)):
                try:
                    stat = fp.stat()
                    sample_outputs.append({"path": str(fp), "size": stat.st_size, "mtime": stat.st_mtime})
                except Exception:
                    pass
    sample_outputs.sort(key=lambda x: x["mtime"], reverse=True)
    packs = []
    for w in workflows[:10]:
        packs.append({
            "workflow": w["name"],
            "samples": [s["path"] for s in sample_outputs[:6]],
            "estimated_price": 49 if w["nodes"] < 20 else 79,
            "tagline": f"{w['name']} - ready-to-run ComfyUI workflow",
            "product_url_slug": w["name"].lower().replace(" ", "-").replace("_", "-"),
        })
    return {
        "updated_at": _now_ts(),
        "workflow_count": len(workflows),
        "sample_count": len(sample_outputs),
        "top_workflows": workflows[:10],
        "ready_packs": packs[:5],
        "next_step": "Export first pack with /api/workflows/productize/{slug}",
    }



def _cooperator_briefing() -> Dict[str, Any]:
    snap = _system_snapshot()
    services_down = [s["name"] for s in snap.get("services", []) if not s.get("ok")]
    disk_high = [d for d in snap.get("disk", {}).get("paths", []) if d.get("percent", 0) >= 80]
    actions = []
    if services_down:
        actions.append({"priority": "high", "title": "Restart failed services", "detail": f"Down: {', '.join(services_down)}", "endpoint": "/api/system/self-heal"})
    if disk_high:
        actions.append({"priority": "med", "title": "Free disk space", "detail": f"Paths >=80% full: {[d['path'] for d in disk_high]}", "endpoint": "/api/system/self-heal"})
    actions.append({"priority": "low", "title": "Run prompt optimization", "detail": "Try Optimize+Queue on a real prompt to add a job", "endpoint": "/api/generate"})
    actions.append({"priority": "low", "title": "Review money paths", "detail": "Pick one path and run the first step today", "endpoint": "/api/money/leads"})
    return {
        "timestamp": _now_ts(),
        "headline": "Sovereign workstation ready" if not services_down else f"{len(services_down)} service(s) need attention",
        "actions": actions,
        "snapshot": snap,
    }


def _cooperator_run(directive: str, max_steps: int = 5) -> Dict[str, Any]:
    directive = (directive or "").strip()[:2000]
    steps: List[Dict[str, Any]] = []
    lower = directive.lower()
    if not directive:
        steps.append({"step": 1, "kind": "noop", "detail": "Empty directive; nothing to do."})
    if any(w in lower for w in ["heal", "self-heal", "fix", "recover"]):
        steps.append({"step": len(steps)+1, "kind": "self_heal", "detail": "Triggered /api/system/self-heal", "endpoint": "/api/system/self-heal", "result": _self_heal_actor()})
    if any(w in lower for w in ["money", "sell", "revenue", "income", "pitch"]):
        steps.append({"step": len(steps)+1, "kind": "money_paths", "detail": "Loaded money paths", "endpoint": "/api/money/leads", "result": _money_snapshot()})
    if any(w in lower for w in ["briefing", "morning", "today", "status"]):
        steps.append({"step": len(steps)+1, "kind": "briefing", "detail": "Generated briefing", "endpoint": "/api/cooperator/briefing", "result": _cooperator_briefing()})
    if any(w in lower for w in ["repo", "repos", "workspace", "code"]):
        try:
            repos = sorted([p.parent.name for p in Path("/home/scott/ai-workspace/repos").glob("*/.git")]) or [p.name for p in Path("/home/scott/ai-workspace/repos").iterdir() if p.is_dir()]
            steps.append({"step": len(steps)+1, "kind": "repos", "detail": f"Found {len(repos)} repos", "endpoint": "/api/cooperator/repos", "result": {"repos": repos}})
        except Exception as exc:
            steps.append({"step": len(steps)+1, "kind": "repos", "detail": f"Failed: {exc}"})
    if any(w in lower for w in ["private", "creation", "art", "story", "image", "video"]):
        snap = {"comfy_output_gb": _comfy_output_size_gb(), "models": _local_model_count(), "workflows": _local_workflow_count()}
        steps.append({"step": len(steps)+1, "kind": "private_creations", "detail": "Current private-creation footprint", "result": snap})
    if any(w in lower for w in ["dashboard", "tab", "ui"]):
        steps.append({"step": len(steps)+1, "kind": "dashboard_summary", "detail": "Open the dashboard at /dashboard", "endpoint": "/dashboard"})
    if not steps:
        steps.append({"step": 1, "kind": "fallback", "detail": "No recognized verb; defaulting to briefing", "result": _cooperator_briefing()})
    plan = {"timestamp": _now_ts(), "directive": directive, "steps": steps[:max_steps]}
    log = _read_list(COOP_FILE)
    log.append(plan)
    _write_list(COOP_FILE, log[-100:])
    return plan


def _private_creations_summary() -> Dict[str, Any]:
    creations = []
    for d in (Path("/home/scott/ai-lab/creations"), Path("/home/scott/ai-lab/private"), Path("/home/scott/Pictures")):
        if d.exists():
            for ext in ("*.png","*.jpg","*.jpeg","*.webp","*.mp4","*.gif","*.json","*.md"):
                for p in d.rglob(ext):
                    try:
                        creations.append({"path": str(p), "size": p.stat().st_size, "modified": p.stat().st_mtime})
                    except Exception: pass
    creations.sort(key=lambda c: c["modified"], reverse=True)
    return {"count": len(creations), "latest": creations[:20]}
SYSTEM_SNAPSHOT_FILE = DASHBOARD_STATE_DIR / "system_snapshot.json"
SELF_HEAL_LOG = DASHBOARD_STATE_DIR / "self_heal_log.json"
WATCHDOG_FILE = DASHBOARD_STATE_DIR / "watchdog.json"
MONEY_FILE = DASHBOARD_STATE_DIR / "money.json"
COOP_FILE = DASHBOARD_STATE_DIR / "cooperator.json"
PRIVATE_CREATIONS_FILE = DASHBOARD_STATE_DIR / "private_creations.json"
WATCHDOG_INTERVAL_SECONDS = 60


def _system_service_check(name: str, url: str, timeout: float = 1.5, ok_alive: bool = True) -> Dict[str, Any]:
    start = _now_ts()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"name": name, "ok": ok_alive and r.status < 500, "status": r.status, "latency_ms": int((_now_ts()-start)*1000)}
    except Exception as exc:
        return {"name": name, "ok": False, "status": None, "latency_ms": int((_now_ts()-start)*1000), "error": str(exc)[:120]}


def _redis_ping(port: int = 6380) -> Dict[str, Any]:
    start = _now_ts()
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1.5)
        s.sendall(b"PING\r\n")
        data = s.recv(64)
        s.close()
        ok = b"PONG" in data
        return {"name": "redis", "ok": ok, "status": 200 if ok else None, "latency_ms": int((_now_ts()-start)*1000), "error": None if ok else f"got {data!r}"}
    except Exception as exc:
        return {"name": "redis", "ok": False, "status": None, "latency_ms": int((_now_ts()-start)*1000), "error": str(exc)[:120]}


def _self_alive() -> Dict[str, Any]:
    # Don't recurse into HTTP from the same process; use a file heartbeat instead
    hb = _read_json_file(WATCHDOG_FILE, {})
    last = float(hb.get("timestamp", _now_ts()))
    age = _now_ts() - last
    return {"name": "llm-inference-api", "ok": age < 180, "status": 200, "latency_ms": 0, "watchdog_age_s": round(age, 1)}


def _disk_summary() -> Dict[str, Any]:
    out = []
    for p in [Path("/"), Path("/mnt/ai-storage"), Path("/home"), Path("/opt"), COMFYUI_OUTPUT_DIR, Path("/home/scott/ai-lab")]:
        try:
            usage = shutil.disk_usage(str(p))
            out.append({"path": str(p), "used_gb": round(usage.used/1024**3, 1), "free_gb": round(usage.free/1024**3, 1), "percent": int(usage.used/usage.total*100)})
        except Exception:
            pass
    return {"paths": out}


def _memory_summary() -> Dict[str, Any]:
    try:
        with open("/proc/meminfo") as f:
            lines = {l.split(":")[0]: int(l.split(":")[1].strip().split()[0]) for l in f if ":" in l}
        total = lines.get("MemTotal", 0)
        avail = lines.get("MemAvailable", 0)
        used = max(0, total - avail)
        return {"total_gb": round(total/1024/1024, 1), "used_gb": round(used/1024/1024, 1), "percent": int(used/total*100) if total else 0}
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "percent": 0}


def _load_summary() -> Dict[str, Any]:
    try:
        one, five, fifteen = os.getloadavg()
        return {"one": one, "five": five, "fifteen": fifteen, "cpu_count": os.cpu_count() or 1}
    except Exception:
        return {"one": 0, "five": 0, "fifteen": 0, "cpu_count": 0}


def _comfy_output_size_gb() -> float:
    total = 0
    if COMFYUI_OUTPUT_DIR.exists():
        for p in COMFYUI_OUTPUT_DIR.rglob("*"):
            if p.is_file():
                try: total += p.stat().st_size
                except Exception: pass
    return round(total/1024**3, 2)


def _prune_old_comfy_outputs(days: int = 30) -> Dict[str, Any]:
    if not COMFYUI_OUTPUT_DIR.exists():
        return {"pruned": 0, "freed_mb": 0, "skipped": True}
    cutoff = _now_ts() - days*86400
    pruned = 0
    freed = 0
    for p in COMFYUI_OUTPUT_DIR.rglob("*"):
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                freed += p.stat().st_size
                p.unlink()
                pruned += 1
        except Exception: pass
    # remove empty dirs
    for d in sorted([x for x in COMFYUI_OUTPUT_DIR.rglob("*") if x.is_dir()], reverse=True):
        try:
            d.rmdir()
        except Exception: pass
    return {"pruned": pruned, "freed_mb": round(freed/1024**2, 1), "skipped": False}


def _system_snapshot() -> Dict[str, Any]:
    snap = {
        "timestamp": _now_ts(),
        "memory": _memory_summary(),
        "load": _load_summary(),
        "disk": _disk_summary(),
        "comfy_output_gb": _comfy_output_size_gb(),
        "services": [
            _self_alive(),
            _system_service_check("comfyui", "http://127.0.0.1:8188/system_stats"),
            _system_service_check("ollama-default", "http://127.0.0.1:11434/api/tags"),
            _system_service_check("ollama-v100", "http://127.0.0.1:11437/api/tags"),
            _system_service_check("ollama-p40", "http://127.0.0.1:11435/api/tags"),
            _system_service_check("ollama-3060", "http://127.0.0.1:11436/api/tags"),
            _system_service_check("open-webui", "http://127.0.0.1:3002/api/health"),
            _system_service_check("n8n", "http://127.0.0.1:5678/healthz"),
            _system_service_check("qdrant", "http://127.0.0.1:6333/"),
            _redis_ping(6380),
        ],
    }
    _write_json_file(SYSTEM_SNAPSHOT_FILE, snap)
    return snap


def _self_heal_actor() -> Dict[str, Any]:
    snap = _system_snapshot()
    actions: List[Dict[str, Any]] = []
    for svc in snap.get("services", []):
        if svc["name"] in ("comfyui",) and not svc["ok"]:
            actions.append({"target": "comfyui.service", "action": "systemctl-restart", "status": _try_restart("comfyui.service"), "reason": "ComfyUI down"})
    # Disk pressure prune
    for d in snap.get("disk", {}).get("paths", []):
        if d.get("percent", 0) >= 85 and d.get("path") in ("/", "/home"):
            actions.append({"target": d["path"], "action": "prune-old-comfy-outputs", "status": _prune_old_comfy_outputs(30)})
            break
    # stale jobs prune
    stale = 0
    jobs = _read_list(JOBS_FILE)
    cutoff = _now_ts() - 7*86400
    for j in jobs:
        if j.get("created_at", 0) < cutoff and j.get("status") in ("success", "error"):
            stale += 1
    if stale:
        keep = [j for j in jobs if not (j.get("created_at", 0) < cutoff and j.get("status") in ("success", "error"))]
        _write_list(JOBS_FILE, keep)
    if stale:
        actions.append({"target": "jobs.json", "action": "prune-stale", "status": {"removed": stale}})
    log = _read_list(SELF_HEAL_LOG)
    log.append({"timestamp": _now_ts(), "actions": actions})
    _write_list(SELF_HEAL_LOG, log[-200:])
    return {"actions": actions, "snapshot": snap}


def _try_restart(unit: str) -> Dict[str, Any]:
    try:
        proc = subprocess.run(["systemctl", "--user", "restart", unit], capture_output=True, text=True, timeout=15)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout[-200:], "stderr": proc.stderr[-200:]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _watchdog_loop() -> None:
    while True:
        try:
            result = _self_heal_actor()
            _write_json_file(WATCHDOG_FILE, {"timestamp": _now_ts(), "actions": result.get("actions", []), "services_ok": sum(1 for s in result.get("snapshot", {}).get("services", []) if s.get("ok"))})
        except Exception as exc:
            _write_json_file(WATCHDOG_FILE, {"timestamp": _now_ts(), "error": str(exc)})
        await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)


def _safe_job_id(prompt_id: str) -> str:
    return "".join(ch for ch in str(prompt_id) if ch.isalnum() or ch in "-_")[:96]


def _read_list(path: Path) -> List[Dict[str, Any]]:
    data = _read_json_file(path, [])
    return data if isinstance(data, list) else []


def _write_list(path: Path, data: List[Dict[str, Any]]) -> None:
    _write_json_file(path, data[-300:])


def _workflow_estimate_seconds(workflow: str, request: Optional[Any] = None) -> int:
    steps = int(getattr(request, "steps", 20) or 20) if request is not None else 20
    width = int(getattr(request, "width", 1024) or 1024) if request is not None else 1024
    height = int(getattr(request, "height", 1024) or 1024) if request is not None else 1024
    megapixels = max(0.25, (width * height) / 1_000_000)
    base = {"txt2img": 12, "img2img": 14, "upscale": 8, "variations": 14, "txt2video": 45, "img2video": 55, "video": 55}.get(workflow, 18)
    return int(max(5, base + (steps * 1.6 * megapixels)))


def _optimization_hints(workflow: str, request: Optional[Any] = None) -> List[str]:
    steps = int(getattr(request, "steps", 20) or 20) if request is not None else 20
    width = int(getattr(request, "width", 1024) or 1024) if request is not None else 1024
    height = int(getattr(request, "height", 1024) or 1024) if request is not None else 1024
    hints = []
    if workflow in {"txt2video", "img2video", "video"}:
        hints.append("Video is the slow path: use shorter clips/low frame count first, then upscale/refine only keepers.")
    if width * height > 1024 * 1024:
        hints.append("Resolution drives time/VRAM quadratically; draft at 768-1024px, upscale final winners.")
    if steps > 25:
        hints.append("Steps above ~25 often give diminishing returns; test 12-18 steps before long runs.")
    if workflow in {"img2img", "img2video"}:
        hints.append("Denoise controls faithfulness: lower preserves source, higher changes composition more.")
    hints.append("Keep prompts specific: subject + style + lighting + camera + constraints beats long vague text.")
    return hints


def _register_job(prompt_id: str, workflow: str, prompt: str = "", source: Optional[str] = None, request: Optional[Any] = None) -> Dict[str, Any]:
    DASHBOARD_STATE_DIR.mkdir(parents=True, exist_ok=True)
    job = {
        "prompt_id": prompt_id,
        "workflow": workflow,
        "prompt": prompt[:500],
        "source": source,
        "created_at": _now_ts(),
        "status": "queued",
        "estimate_seconds": _workflow_estimate_seconds(workflow, request),
        "progress_percent": 2,
        "outputs": [],
        "hints": _optimization_hints(workflow, request),
    }
    jobs = [j for j in _read_list(JOBS_FILE) if j.get("prompt_id") != prompt_id]
    jobs.append(job)
    _write_list(JOBS_FILE, jobs)
    return job


async def _comfy_job_status(prompt_id: str) -> Dict[str, Any]:
    prompt_id = _safe_job_id(prompt_id)
    jobs = _read_list(JOBS_FILE)
    job = next((j for j in jobs if j.get("prompt_id") == prompt_id), {"prompt_id": prompt_id, "created_at": _now_ts(), "workflow": "unknown", "estimate_seconds": 30, "hints": []})
    elapsed = max(0.0, _now_ts() - float(job.get("created_at", _now_ts())))
    estimate = max(1, int(job.get("estimate_seconds") or 30))
    status = "running"
    outputs: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            hist = await client.get(f"http://localhost:8188/history/{prompt_id}")
            if hist.status_code == 200:
                item = hist.json().get(prompt_id)
                if item:
                    st = item.get("status", {})
                    status = st.get("status_str") or ("success" if st.get("completed") else "running")
                    for msg in st.get("messages", []) or []:
                        if isinstance(msg, list) and len(msg) > 1 and msg[0] == "execution_error":
                            errors.append(str(msg[1].get("exception_message", "execution error")))
                    for node_out in (item.get("outputs") or {}).values():
                        for key in ("images", "gifs", "videos"):
                            for out in node_out.get(key, []) or []:
                                filename = out.get("filename")
                                if filename:
                                    subfolder = out.get("subfolder", "") or ""
                                    typ = out.get("type", "output") or "output"
                                    url = f"/api/comfy/view?filename={filename}&subfolder={subfolder}&type={typ}"
                                    outputs.append({"filename": filename, "subfolder": subfolder, "type": typ, "url": url, "kind": key.rstrip('s')})
    except Exception as exc:
        errors.append(str(exc))
    if status == "success":
        progress = 100
    elif status == "error":
        progress = min(100, max(1, int((elapsed / estimate) * 100)))
    else:
        progress = min(95, max(2, int((elapsed / estimate) * 100)))
    job.update({"status": status, "elapsed_seconds": round(elapsed, 1), "progress_percent": progress, "outputs": outputs, "errors": errors, "updated_at": _now_ts()})
    jobs = [j for j in jobs if j.get("prompt_id") != prompt_id]
    jobs.append(job)
    _write_list(JOBS_FILE, jobs)
    return job


async def _all_jobs_enriched(limit: int = 25) -> List[Dict[str, Any]]:
    jobs = sorted(_read_list(JOBS_FILE), key=lambda j: j.get("created_at", 0), reverse=True)[:limit]
    enriched = []
    for job in jobs:
        pid = job.get("prompt_id")
        if pid:
            enriched.append(await _comfy_job_status(pid))
    return sorted(enriched, key=lambda j: j.get("created_at", 0), reverse=True)


def _local_model_count() -> int:
    if not COMFYUI_MODELS_DIR.exists():
        return 0
    return sum(1 for p in COMFYUI_MODELS_DIR.rglob("*") if p.is_file() and p.suffix.lower() in {".safetensors", ".ckpt", ".pt", ".pth", ".gguf"})


def _local_workflow_count() -> int:
    return len(list(WORKFLOW_ROOT.glob("*.json"))) if WORKFLOW_ROOT.exists() else 0


async def _dashboard_achievements() -> Dict[str, Any]:
    jobs = await _all_jobs_enriched(75)
    completed = [j for j in jobs if j.get("status") == "success"]
    workflows = {j.get("workflow") for j in completed}
    generated = len(completed)
    upscales = len([j for j in completed if j.get("workflow") == "upscale"])
    video_jobs = len([j for j in completed if "video" in str(j.get("workflow"))])
    models = _local_model_count()
    workflow_files = _local_workflow_count()
    gpus_online = 0
    try:
        import pynvml
        pynvml.nvmlInit(); gpus_online = pynvml.nvmlDeviceGetCount(); pynvml.nvmlShutdown()
    except Exception:
        gpus_online = 0
    defs = [
        ("first-gen", "First Blood", "Generated one completed ComfyUI job", "🎨", generated, 1),
        ("centurion", "Centurion", "Complete 100 ComfyUI jobs", "💯", generated, 100),
        ("gpu-master", "GPU Master", "Three real NVIDIA GPUs visible to NVML", "🎮", gpus_online, 3),
        ("architect", "Architect", "Four saved executable workflow templates", "⚙️", workflow_files, 4),
        ("wordsmith", "Wordsmith", "Use the local LLM prompt improver 25 times", "🔮", len([j for j in jobs if j.get("workflow") == "prompt-improve"]), 25),
        ("resolution-king", "Resolution King", "Complete 10 real upscales", "🔍", upscales, 10),
        ("video-pilot", "Video Pilot", "Queue a video/image-video workflow", "🎞️", video_jobs, 1),
        ("curator", "Curator", "Organize 15 real ComfyUI model files", "📚", models, 15),
        ("workflow-range", "Range Finder", "Complete txt2img + img2img + upscale", "🧭", len(workflows & {"txt2img", "img2img", "upscale"}), 3),
    ]
    achievements = []
    for aid, name, desc, icon, current, target in defs:
        pct = min(100, int((current / target) * 100)) if target else 0
        achievements.append({"id": aid, "name": name, "description": desc, "icon": icon, "current": current, "target": target, "percent": pct, "unlocked": current >= target})
    _write_json_file(ACHIEVEMENTS_FILE, {"updated_at": _now_ts(), "achievements": achievements})
    return {"achievements": achievements, "metrics": {"completed_jobs": generated, "models": models, "workflows": workflow_files, "gpus_online": gpus_online}}


def _default_tools() -> List[Dict[str, Any]]:
    return [
        {
            "id": "service-health",
            "name": "Service Health",
            "kind": "builtin",
            "description": "Check llm-inference-api, Ollama lanes, ComfyUI, Open WebUI, n8n, Redis, Qdrant, and Postgres availability.",
        },
        {
            "id": "list-workflows",
            "name": "List Workflows",
            "kind": "builtin",
            "description": "List saved ComfyUI workflows from /home/scott/ai-lab/image/workflows.",
        },
        {
            "id": "list-ollama-models",
            "name": "List Ollama Models",
            "kind": "builtin",
            "description": "List models from the local V100, P40, and RTX 3060 Ollama lanes.",
        },
        {
            "id": "daily-report",
            "name": "Daily Report",
            "kind": "script",
            "description": "Run the local AI lab daily report generator without exposing secrets.",
            "script": "/home/scott/ai-lab/scripts/bin/ai-lab-report.sh",
        },
    ]


def _default_agents() -> List[Dict[str, Any]]:
    return [
        {
            "id": "workflow-optimizer",
            "name": "Workflow Optimizer",
            "kind": "builtin",
            "description": "Local planner that returns workflow, cleanup, and dashboard action suggestions.",
            "model": "local-planner",
        },
        {
            "id": "p40-agent",
            "name": "P40 Agent",
            "kind": "ollama",
            "description": "Ollama agent on the P40 lane (port 11435).",
            "endpoint": "http://localhost:11435",
            "model": "llama3.1:8b",
        },
        {
            "id": "3060-agent",
            "name": "3060 Agent",
            "kind": "ollama",
            "description": "Ollama agent on the RTX 3060 lane (port 11436).",
            "endpoint": "http://localhost:11436",
            "model": "qwen2.5-coder:7b",
        },
    ]


def _default_views() -> List[Dict[str, Any]]:
    return [
        {
            "id": "overview",
            "name": "Overview",
            "type": "dashboard",
            "url": "/dashboard",
            "scope": "local",
            "description": "Main AI lab dashboard.",
        },
        {
            "id": "gpu-lanes",
            "name": "GPU + Ollama Lanes",
            "type": "status",
            "url": "/dashboard#gpu",
            "scope": "local",
            "description": "GPU and lane health view.",
        },
        {
            "id": "workflows",
            "name": "Workflows",
            "type": "workflow",
            "url": "/dashboard#workflows",
            "scope": "local",
            "description": "Saved ComfyUI workflows.",
        },
        {
            "id": "tools",
            "name": "Custom Tools",
            "type": "tools",
            "url": "/dashboard#tools",
            "scope": "local",
            "description": "Local helper tools.",
        },
        {
            "id": "mcp-agents",
            "name": "MCP Agents",
            "type": "agent",
            "url": "/dashboard#mcp",
            "scope": "local",
            "description": "Local MCP-style agents.",
        },
    ]


def _read_json_file(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        logger.warning("failed to read %s: %s", path, exc)
    return default


def _write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _ensure_agent_files() -> None:
    AGENT_ROOT.mkdir(parents=True, exist_ok=True)
    if not TOOLS_FILE.exists():
        _write_json_file(TOOLS_FILE, _default_tools())
    if not MCP_AGENTS_FILE.exists():
        _write_json_file(MCP_AGENTS_FILE, _default_agents())
    if not VIEWS_FILE.exists():
        _write_json_file(VIEWS_FILE, _default_views())
    if not MCP_RUNS_FILE.exists():
        _write_json_file(MCP_RUNS_FILE, [])


def _workflow_summary(path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
    nodes = data.get("nodes") if isinstance(data, dict) else []
    return {
        "id": path.stem,
        "name": data.get("name") or path.stem,
        "description": data.get("description") or f"{path.name} from {path.parent}",
        "path": str(path),
        "updated": path.stat().st_mtime,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
        "nodes": nodes if isinstance(nodes, list) else [],
        "raw": data,
    }


async def _health_checks() -> Dict[str, Any]:
    health = await ollama_manager.health_check_all()
    checks: Dict[str, Any] = {
        "llm-inference-api": {"status": "ok"},
        "ollama": health,
    }
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in {
            "comfyui": "http://localhost:8188/system_stats",
            "open-webui": "http://localhost:3002/api/health",
            "n8n": "http://localhost:5678/healthz",
            "qdrant": "http://localhost:6333/",
        }.items():
            try:
                response = await client.get(url)
                checks[name] = {"status": "ok" if response.status_code < 500 else "error", "http_status": response.status_code}
            except Exception as exc:
                checks[name] = {"status": "error", "error": str(exc)}
    checks["redis"] = {"status": "configured", "host": settings.redis_host, "port": settings.redis_port}
    checks["postgres"] = {"status": "configured", "host": settings.postgres_host, "port": settings.postgres_port}
    return checks


async def _run_builtin_tool(tool_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if tool_id == "service-health":
        return {"checks": await _health_checks()}
    if tool_id == "list-workflows":
        WORKFLOW_ROOT.mkdir(parents=True, exist_ok=True)
        workflows = [_workflow_summary(path) for path in sorted(WORKFLOW_ROOT.glob("*.json"))]
        return {"workflows": workflows, "count": len(workflows), "root": str(WORKFLOW_ROOT)}
    if tool_id == "list-ollama-models":
        lanes = []
        async with httpx.AsyncClient(timeout=4.0) as client:
            for lane in settings.ollama_instances.values():
                try:
                    response = await client.get(f"http://localhost:{lane.port}/api/tags")
                    lanes.append({"lane": lane.gpu_type, "port": lane.port, "ok": response.status_code < 500, "models": response.json().get("models", []) if response.status_code == 200 else []})
                except Exception as exc:
                    lanes.append({"lane": lane.gpu_type, "port": lane.port, "ok": False, "error": str(exc)})
        return {"lanes": lanes}
    raise HTTPException(status_code=400, detail=f"Unknown built-in tool: {tool_id}")


async def _run_tool(tool: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    tool_id = tool.get("id")
    kind = tool.get("kind")
    if kind == "builtin":
        return await _run_builtin_tool(tool_id, payload)
    if kind == "script":
        script = tool.get("script")
        if not script or not Path(script).exists():
            return {"ok": False, "message": f"Script not found: {script}"}
        proc = await asyncio.create_subprocess_exec(
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }
    raise HTTPException(status_code=400, detail=f"Unsupported tool kind: {kind}")


async def _run_mcp_agent(agent: Dict[str, Any], prompt: str, model: Optional[str]) -> Dict[str, Any]:
    kind = agent.get("kind")
    if kind == "builtin":
        return {
            "agent_id": agent.get("id"),
            "agent_name": agent.get("name"),
            "prompt": prompt,
            "response": "Local workflow optimizer: keep dashboard actions wired to /api/comfy/workflows, /api/tools/custom, /api/mcp/run, and /api/views. Prefer local-only execution and verify with /health and /api/comfy/queue before claiming success.",
        }
    if kind == "ollama":
        endpoint = agent.get("endpoint", "http://localhost:11435").rstrip("/")
        model_name = model or agent.get("model") or "llama3.1:8b"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{endpoint}/api/generate", json={
                "model": model_name,
                "prompt": f"You are a local MCP-style dashboard agent. Keep the answer concise and actionable.\n\nUser: {prompt}",
                "stream": False,
                "options": {"num_predict": 700},
            })
            response.raise_for_status()
            return response.json()
    raise HTTPException(status_code=400, detail=f"Unsupported agent kind: {kind}")

app.mount(
    "/admin",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "admin", html=True),
    name="admin",
)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Path("app/static/favicon.svg"), media_type="image/svg+xml")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    template = templates.env.get_template("dashboard.html")
    content = await template.render_async({"request": request, "data": {}})
    return HTMLResponse(content=content)


@app.get("/gpu-status")
async def gpu_status():
    health = await ollama_manager.health_check_all()
    gpus: list[dict[str, object]] = []
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for idx in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            name = pynvml.nvmlDeviceGetName(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpus.append({
                "index": idx,
                "name": name,
                "memory": f"{mem.used // (1024 * 1024)}/{mem.total // (1024 * 1024)} MB",
                "utilization": util.gpu,
            })
        pynvml.nvmlShutdown()
    except Exception as exc:
        gpus = [{"index": -1, "name": "unavailable", "memory": "0/0 MB", "utilization": 0, "error": str(exc)}]
    return {"driver": "580.159.03", "gpus": gpus}


@app.get("/ollama-status")
async def ollama_status():
    health = await ollama_manager.health_check_all()
    lanes = [
        {"name": "default", "port": 11434, "healthy": bool(health.get("default")), "memory": "16 GB"},
        {"name": "v100", "port": 11437, "healthy": bool(health.get("v100")), "memory": "16 GB"},
        {"name": "p40", "port": 11435, "healthy": bool(health.get("p40")), "memory": "24 GB"},
        {"name": "3060", "port": 11436, "healthy": bool(health.get("3060")), "memory": "12 GB"},
    ]
    instances = []
    for lane in lanes:
        models = 0
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{lane['port']}", timeout=10) as client:
                r = await client.get("/api/tags")
                if r.status_code == 200:
                    models = len(r.json().get("models", []))
        except Exception:
            pass
        instances.append({**lane, "models": models})
    return {"instances": instances}


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    return response


@app.get("/health")
async def health():
    checks = await _health_checks()
    ollama = checks.get("ollama", {})
    return {"status": "ok", "checks": checks, "ollama_instances": {name: bool(status) for name, status in ollama.items()}}


@app.get("/v1/models")
async def list_models(user=None):
    return []


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, user=None):
    return JSONResponse(status_code=501, content={"detail": "not implemented yet"})


@app.post("/v1/completions")
async def completions(request: Request, user=None):
    return JSONResponse(status_code=501, content={"detail": "not implemented yet"})


@app.post("/v1/embeddings")
async def embeddings(request: Request, user=None):
    return JSONResponse(status_code=501, content={"detail": "not implemented yet"})


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Queue a generation job to ComfyUI"""
    try:
        prompt = request.prompt
        workflow = request.workflow.value
        mode = request.mode.value

        # Forward to ComfyUI
        async with httpx.AsyncClient(timeout=30) as client:
            comfy_prompt = build_comfyui_prompt(prompt, workflow, mode, request)
            response = await client.post(
                "http://localhost:8188/prompt",
                json={"prompt": comfy_prompt}
            )

            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id")
                job = _register_job(prompt_id, workflow, prompt, getattr(request, "image_path", None), request) if prompt_id else None
                return {
                    "success": True,
                    "prompt_id": prompt_id,
                    "message": "Queued to ComfyUI",
                    "job": job,
                }
            else:
                return JSONResponse(
                    status_code=502,
                    content={"detail": f"ComfyUI error: {response.text}"}
                )
    except Exception as e:
        logger.error("generate_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/comfy/view")
async def comfy_view(filename: str, subfolder: str = "", type: str = "output"):
    base = {"output": COMFYUI_OUTPUT_DIR, "input": COMFYUI_INPUT_DIR}.get(type, COMFYUI_OUTPUT_DIR)
    target = (base / subfolder / filename).resolve()
    base_resolved = base.resolve()
    if not str(target).startswith(str(base_resolved)) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="ComfyUI file not found")
    media = "image/png"
    suffix = target.suffix.lower()
    if suffix in {".jpg", ".jpeg"}: media = "image/jpeg"
    elif suffix == ".webp": media = "image/webp"
    elif suffix == ".gif": media = "image/gif"
    elif suffix == ".mp4": media = "video/mp4"
    elif suffix == ".webm": media = "video/webm"
    return FileResponse(target, media_type=media)


@app.get("/api/system/snapshot")
async def api_system_snapshot():
    return await asyncio.to_thread(_system_snapshot)


@app.get("/api/system/watchdog")
async def api_system_watchdog():
    if WATCHDOG_FILE.exists():
        return _read_json_file(WATCHDOG_FILE, {})
    return {"timestamp": _now_ts(), "actions": []}


@app.post("/api/system/self-heal")
async def api_system_self_heal():
    return await asyncio.to_thread(_self_heal_actor)


@app.get("/api/money/leads")
async def api_money_leads():
    return _money_snapshot()


@app.get("/api/cooperator/briefing")
async def api_cooperator_briefing():
    return await asyncio.to_thread(_cooperator_briefing)


@app.post("/api/cooperator/run")
async def api_cooperator_run(request: Request):
    body = {}
    try: body = await request.json()
    except Exception: pass
    directive = body.get("directive") or body.get("text") or ""
    return await asyncio.to_thread(_cooperator_run, directive)


@app.get("/api/cooperator/repos")
async def api_cooperator_repos():
    base = Path("/home/scott/ai-workspace/repos")
    repos = []
    if base.exists():
        for p in sorted(base.iterdir()):
            if p.is_dir():
                git = p/".git"
                meta = {"name": p.name, "path": str(p), "is_git": git.exists()}
                if git.exists():
                    try:
                        head = (git/"HEAD").read_text().strip()
                        meta["head_ref"] = head.split("/")[-1]
                    except Exception: pass
                repos.append(meta)
    return {"repos": repos, "base": str(base)}


@app.get("/api/private-creations")
async def api_private_creations():
    return await asyncio.to_thread(_private_creations_summary)


# Epic / breaker API surface
@app.post("/api/agent/command")
async def api_agent_command(request: Request):
    body = {}
    try: body = await request.json()
    except Exception: pass
    directive = body.get("directive") or body.get("text") or ""
    return await asyncio.to_thread(_agent_command_router, directive)


@app.get("/api/agent/improvements")
async def api_agent_improvements():
    return await asyncio.to_thread(_self_improvement_suggestions)


@app.get("/api/revenue/status")
async def api_revenue_status():
    return await asyncio.to_thread(_revenue_dashboard)


@app.get("/api/system/predictions")
async def api_system_predictions():
    return await asyncio.to_thread(_predictive_monitoring)


@app.get("/api/workflows/productize")
async def api_workflows_productize():
    return await asyncio.to_thread(_workflow_productize_inventory)


@app.get("/api/workflows/productize/{slug}")
async def api_workflows_productize_slug(slug: str):
    inv = _workflow_productize_inventory()
    pack = next((p for p in inv.get("ready_packs", []) if p.get("product_url_slug") == slug), None)
    if not pack:
        raise HTTPException(status_code=404, detail="workflow pack not found")
    return {"pack": pack, "markdown": _workflow_pack_markdown(pack)}


def _workflow_pack_markdown(pack: Dict[str, Any]) -> str:
    lines = [
        f"# {pack['workflow']} Workflow Pack",
        "",
        f"**Price:** ${pack['estimated_price']}",
        f"**Tagline:** {pack['tagline']}",
        "",
        "## Includes",
        "- Ready-to-load ComfyUI workflow JSON",
        "- Model manifest (generate with Model Truth)",
        "- Sample outputs",
        "",
        "## Setup",
        "1. Copy workflow JSON into ComfyUI workflow manager.",
        "2. Install required models from the manifest.",
        "3. Hit Generate.",
        "",
        "## Notes",
        "This pack was auto-generated from a working local AI lab configuration.",
    ]
    return "\n".join(lines)


@app.get("/api/jobs")
async def dashboard_jobs(limit: int = 25):
    jobs = await _all_jobs_enriched(limit=max(1, min(limit, 100)))
    return {"jobs": jobs}


@app.get("/api/jobs/{prompt_id}")
async def dashboard_job(prompt_id: str):
    return await _comfy_job_status(prompt_id)


@app.get("/api/achievements")
async def dashboard_achievements():
    return await _dashboard_achievements()


@app.post("/api/improve-prompt")
async def improve_prompt(request: ImprovePromptRequest):
    """Use LLM to improve a prompt"""
    try:
        prompt = request.prompt
        mode = request.mode.value

        if not prompt:
            return JSONResponse(status_code=400, content={"detail": "Prompt required"})

        system_prompts = {
            "cinematic": "You are a cinematic prompt engineer. Enhance the prompt with camera angles, lighting, composition, color grading, and technical details. Return ONLY the improved prompt.",
            "realistic-photo": "You are a photography prompt engineer. Enhance with camera settings, lens, lighting, film stock, and photorealistic details. Return ONLY the improved prompt.",
            "private-adult-fiction": "You are an adult fiction prompt writer. Enhance with sensory details, atmosphere, and narrative depth. Return ONLY the improved prompt.",
            "fashion": "You are a fashion photography prompt engineer. Enhance with styling, runway/editorial context, lighting, and composition. Return ONLY the improved prompt.",
            "fitness": "You are a fitness photography prompt engineer. Enhance with athletic form, gym/studio lighting, dynamic poses, and motivational atmosphere. Return ONLY the improved prompt.",
            "office-professional": "You are a corporate photography prompt engineer. Enhance with professional lighting, clean composition, modern office aesthetics. Return ONLY the improved prompt.",
            "anime": "You are an anime art prompt engineer. Enhance with style references, character design, cel shading, and studio references. Return ONLY the improved prompt.",
            "product-shot": "You are a product photography prompt engineer. Enhance with studio lighting, background, materials, and commercial appeal. Return ONLY the improved prompt."
        }

        system = system_prompts.get(mode, system_prompts["cinematic"])

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "http://localhost:11436/api/chat",
                json={
                    "model": "hermes3",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                }
            )

            if response.status_code == 200:
                data = response.json()
                improved = data.get("message", {}).get("content", "").strip()
                return {"improved_prompt": improved or prompt}
            else:
                return {"improved_prompt": prompt}
    except Exception as e:
        logger.error("improve_prompt_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/upscale")
async def upscale_latest(request: UpscaleRequest = Body(default_factory=UpscaleRequest)):
    """Upscale an image"""
    try:
        import os
        if not request.image_path:
            return {"success": False, "message": "No image selected. Upload an image or open ComfyUI directly.", "comfyui": "http://localhost:8188"}
        image_path = request.image_path
        candidate = Path(image_path) if os.path.isabs(image_path) else COMFYUI_INPUT_DIR / os.path.basename(image_path)
        if not candidate.exists():
            return JSONResponse(status_code=404, content={"detail": "Image not found in ComfyUI input folder; upload it first"})

        async with httpx.AsyncClient(timeout=30) as client:
            upscale_prompt = build_upscale_prompt(request.image_path)
            response = await client.post(
                "http://localhost:8188/prompt",
                json={"prompt": upscale_prompt}
            )

            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id")
                job = _register_job(prompt_id, "upscale", "upscale image", request.image_path, request) if prompt_id else None
                return {"success": True, "prompt_id": prompt_id, "source": request.image_path, "job": job}
            else:
                return JSONResponse(status_code=502, content={"detail": "ComfyUI upscale failed"})
    except Exception as e:
        logger.error("upscale_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/variations")
async def generate_variations(request: VariationsRequest = Body(default_factory=VariationsRequest)):
    """Generate variations of an image"""
    try:
        import os
        if not request.image_path:
            return {"success": False, "message": "No image selected. Upload an image or open ComfyUI directly.", "comfyui": "http://localhost:8188"}
        image_path = request.image_path
        candidate = Path(image_path) if os.path.isabs(image_path) else COMFYUI_INPUT_DIR / os.path.basename(image_path)
        if not candidate.exists():
            return JSONResponse(status_code=404, content={"detail": "Image not found in ComfyUI input folder; upload it first"})

        async with httpx.AsyncClient(timeout=30) as client:
            var_prompt = build_variations_prompt(request.image_path)
            response = await client.post(
                "http://localhost:8188/prompt",
                json={"prompt": var_prompt}
            )

            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id")
                job = _register_job(prompt_id, "variations", "image variations", request.image_path, request) if prompt_id else None
                return {"success": True, "prompt_id": prompt_id, "source": request.image_path, "job": job}
            else:
                return JSONResponse(status_code=502, content={"detail": "ComfyUI variations failed"})
    except Exception as e:
        logger.error("variations_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/cleanup")
async def cleanup_outputs(days: int = 30):
    """Clean outputs older than specified days"""
    try:
        def _cleanup() -> Dict[str, Any]:
            import os, glob, time
            output_dir = str(COMFYUI_OUTPUT_DIR)
            cutoff = time.time() - (days * 86400)
            files = glob.glob(os.path.join(output_dir, "*"))
            removed = 0
            for f in files:
                if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                    os.remove(f)
                    removed += 1
            return {"removed": removed}

        result = await asyncio.to_thread(_cleanup)
        removed = result["removed"]
        return {"success": True, "removed": removed, "message": f"Cleaned {removed} files older than {days} days"}
    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/backup")
async def backup_workflows():
    """Backup ComfyUI workflows"""
    try:
        def _backup() -> Path:
            WORKFLOW_ROOT.mkdir(parents=True, exist_ok=True)
            backup_dir = Path("/home/scott/ai-lab/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_file = backup_dir / f"workflows-{timestamp}.tar.gz"
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(WORKFLOW_ROOT, arcname="image/workflows")
            return backup_file

        backup_file = await asyncio.to_thread(_backup)
        return {"success": True, "file": str(backup_file), "size": backup_file.stat().st_size}
    except Exception as e:
        logger.error("backup_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/report")
async def daily_report():
    """Generate daily workstation report"""
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["/home/scott/ai-lab/scripts/bin/ai-lab-report.sh", "today"],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout or "Report generation produced no output"
    except Exception as e:
        logger.error("report_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/heal")
async def self_heal():
    """Run self-heal checks"""
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["/home/scott/ai-lab/scripts/bin/ai-heal.sh"],
            capture_output=True, text=True, timeout=60,
        )
        return {"success": True, "output": result.stdout, "stderr": result.stderr}
    except Exception as e:
        logger.error("heal_failed", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})



# Best-in-class operator powerups: disk rescue, model truth, smoke, logs, release.
def _run_command(command: List[str], timeout: int = 30) -> Dict[str, Any]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-4000:]}
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def _bytes_fmt(size: int) -> str:
    n = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def _disk_usage_path(path: str) -> Dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": path,
        "total_gb": round(usage.total / 1024**3, 1),
        "used_gb": round(usage.used / 1024**3, 1),
        "free_gb": round(usage.free / 1024**3, 1),
        "percent": int(usage.used / usage.total * 100),
    }


def _find_large_files(root: str, min_size_mb: int = 512, limit: int = 80) -> List[Dict[str, Any]]:
    cmd = ["find", root, "-xdev", "-type", "f", "-size", f"+{min_size_mb}M", "-printf", "%s\t%p\n"]
    result = _run_command(cmd, timeout=120)
    rows = []
    if result["stdout"]:
        for line in result["stdout"].splitlines():
            try:
                size, path = line.split("\t", 1)
                size_i = int(size)
                rows.append({"size": size_i, "size_h": _bytes_fmt(size_i), "path": path})
            except Exception:
                pass
    rows.sort(key=lambda r: r["size"], reverse=True)
    return rows[:limit]


def _du_children(path: str, depth: int = 1, limit: int = 30) -> List[Dict[str, Any]]:
    result = _run_command(["du", "-xhd", str(depth), path], timeout=120)
    rows = []
    for line in result.get("stdout", "").splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            rows.append({"size_h": parts[0], "path": parts[1]})
    return rows[-limit:]


def _disk_rescue_report() -> Dict[str, Any]:
    cache = DASHBOARD_STATE_DIR / "disk_rescue.json"
    try:
        if cache.exists() and time.time() - cache.stat().st_mtime < 300:
            cached = _read_json_file(cache, {})
            if cached:
                cached["cached"] = True
                cached["cache_age_sec"] = round(time.time() - cache.stat().st_mtime, 1)
                return cached
    except Exception:
        pass
    paths = [p for p in ["/", "/mnt/ai-storage", "/home", "/opt", "/tmp"] if Path(p).exists()]
    disks = [_disk_usage_path(p) for p in paths]
    inactive_swap = []
    active_swaps = _run_command(["swapon", "--show=NAME", "--noheadings"], timeout=10).get("stdout", "")
    for f in ("/mnt/ai-storage/swapfile64", "/mnt/ai-storage/swapfile-ai"):
        fp = Path(f)
        if fp.exists():
            inactive_swap.append({"path": f, "size": fp.stat().st_size, "size_h": _bytes_fmt(fp.stat().st_size), "active": f in active_swaps})
    stale_download_models = []
    downloads = Path("/mnt/ai-storage/home/scott/Downloads")
    if downloads.exists():
        for ext in ("*.safetensors", "*.gguf", "*.ckpt", "*.bin"):
            for fp in downloads.glob(ext):
                try:
                    stale_download_models.append({"path": str(fp), "size": fp.stat().st_size, "size_h": _bytes_fmt(fp.stat().st_size)})
                except Exception:
                    pass
    stale_download_models.sort(key=lambda r: r["size"], reverse=True)
    snap_chunks = []
    snap_dir = Path("/mnt/ai-storage/var/lib/snapd/snaps")
    if snap_dir.exists():
        for pat in ("nemotron-3-super*", "cuda-samples_*", "cuda-uc_*"):
            for fp in snap_dir.glob(pat):
                try:
                    snap_chunks.append({"path": str(fp), "size": fp.stat().st_size, "size_h": _bytes_fmt(fp.stat().st_size), "requires_sudo": not os.access(fp, os.W_OK)})
                except Exception:
                    pass
    snap_chunks.sort(key=lambda r: r["size"], reverse=True)
    candidates = {
        "inactive_swapfiles": inactive_swap,
        "stale_download_models": stale_download_models,
        "stale_snap_model_chunks": snap_chunks[:80],
        "snap_ollama_store": _du_children("/mnt/ai-storage/var/snap/ollama/common/models", 1, 10) if Path("/mnt/ai-storage/var/snap/ollama/common/models").exists() else [],
    }
    reclaim = sum(x["size"] for x in inactive_swap if not x.get("active")) + sum(x["size"] for x in stale_download_models) + sum(x["size"] for x in snap_chunks)
    payload = {
        "timestamp": _now_ts(),
        "disks": disks,
        "top_dirs": {p: _du_children(p, 1, 20) for p in ("/mnt/ai-storage", "/home/scott", "/opt", "/var") if Path(p).exists()},
        "large_files": _find_large_files("/mnt/ai-storage", 5 * 1024, 60) if Path("/mnt/ai-storage").exists() else [],
        "candidates": candidates,
        "estimated_reclaim_bytes": reclaim,
        "estimated_reclaim_h": _bytes_fmt(reclaim),
        "sudo_needed": ["/mnt/ai-storage/swapfile64", "/mnt/ai-storage/swapfile-ai", "/mnt/ai-storage/var/lib/snapd/snaps/*"],
    }
    try:
        _write_json_file(cache, payload)
    except Exception:
        pass
    return payload


def _disk_rescue_execute(action: str) -> Dict[str, Any]:
    action = (action or "").strip()
    deleted = []
    errors = []
    if action in {"downloads", "safe-user"}:
        downloads = Path("/mnt/ai-storage/home/scott/Downloads")
        if downloads.exists():
            for ext in ("*.safetensors", "*.gguf", "*.ckpt", "*.bin"):
                for fp in downloads.glob(ext):
                    try:
                        size = fp.stat().st_size
                        fp.unlink()
                        deleted.append({"path": str(fp), "size": size, "size_h": _bytes_fmt(size)})
                    except Exception as exc:
                        errors.append({"path": str(fp), "error": str(exc)})
    elif action == "tmp-dashboard":
        for f in ("/tmp/dashboard-smoke.js", "/tmp/dashboard-one.js", "/tmp/heal-one.js", "/tmp/dashboard-401.js"):
            fp = Path(f)
            if fp.exists():
                try:
                    size = fp.stat().st_size
                    fp.unlink()
                    deleted.append({"path": str(fp), "size": size, "size_h": _bytes_fmt(size)})
                except Exception as exc:
                    errors.append({"path": f, "error": str(exc)})
    else:
        return {"ok": False, "error": "unknown action", "allowed_actions": ["downloads", "safe-user", "tmp-dashboard"]}
    return {"ok": not errors, "action": action, "deleted": deleted, "errors": errors, "disk": _disk_usage_path("/mnt/ai-storage") if Path("/mnt/ai-storage").exists() else None}


def _model_truth_report() -> Dict[str, Any]:
    roots = [
        "/opt/ai/comfyui/ComfyUI/models",
        "/mnt/ai-storage/opt/ai/ComfyUI/models",
        "/mnt/ai-storage/home/scott/PrivateImageAI/models",
        "/mnt/ai-storage/home/scott/Desktop/PrivateImageAI/models",
        "/mnt/ai-storage/ollama-models",
        "/mnt/ai-storage/opt/ai/ollama/models",
        "/mnt/ai-storage/var/snap/ollama/common/models",
        "/home/scott/.ollama/models",
    ]
    files = []
    for root in roots:
        if not Path(root).exists():
            continue
        for pattern in ("*.safetensors", "*.ckpt", "*.gguf", "*.bin"):
            try:
                for fp in Path(root).rglob(pattern):
                    if fp.is_file():
                        st = fp.stat()
                        files.append({"name": fp.name, "path": str(fp), "size": st.st_size, "size_h": _bytes_fmt(st.st_size), "root": root})
            except Exception:
                pass
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for item in files:
        by_key.setdefault(f"{item['name']}::{item['size']}", []).append(item)
    duplicates = [v for v in by_key.values() if len(v) > 1]
    duplicates.sort(key=lambda group: group[0]["size"] * len(group), reverse=True)
    active = {
        "comfyui_models": "/opt/ai/comfyui/ComfyUI/models",
        "service_comfyui_root": str(COMFYUI_ROOT),
        "service_comfyui_models": str(COMFYUI_MODELS_DIR),
    }
    return {
        "timestamp": _now_ts(),
        "active_paths": active,
        "roots_scanned": [r for r in roots if Path(r).exists()],
        "file_count": len(files),
        "total_bytes": sum(i["size"] for i in files),
        "total_h": _bytes_fmt(sum(i["size"] for i in files)),
        "largest": sorted(files, key=lambda i: i["size"], reverse=True)[:80],
        "duplicates_by_name_size": duplicates[:50],
        "recommendation": "Treat /opt/ai/comfyui/ComfyUI/models as active ComfyUI. Verify Ollama systemd OLLAMA_MODELS before deleting duplicated Ollama blob stores.",
    }


def _dashboard_smoke_status() -> Dict[str, Any]:
    script = Path("/home/scott/ai-workspace/repos/llm-inference-api/scripts/dashboard-smoke-playwright.js")
    result_file = DASHBOARD_STATE_DIR / "smoke.json"
    if result_file.exists():
        last = _read_json_file(result_file, {})
    else:
        last = {}
    return {"script": str(script), "script_exists": script.exists(), "last": last}


def _run_dashboard_smoke() -> Dict[str, Any]:
    script = "/home/scott/ai-workspace/repos/llm-inference-api/scripts/dashboard-smoke-playwright.js"
    result = _run_command(["node", script], timeout=240)
    payload = {"timestamp": _now_ts(), "ok": result["ok"], "returncode": result["returncode"], "stdout": result["stdout"], "stderr": result["stderr"]}
    _write_json_file(DASHBOARD_STATE_DIR / "smoke.json", payload)
    return payload


def _dashboard_logs(lines: int = 120) -> Dict[str, Any]:
    lines = max(20, min(int(lines or 120), 500))
    result = _run_command(["journalctl", "--user", "-u", "ai-lab-dashboard.service", "-n", str(lines), "--no-pager"], timeout=20)
    return {"ok": result["ok"], "logs": result["stdout"], "stderr": result["stderr"]}


@app.get("/api/disk/rescue")
async def api_disk_rescue():
    return await asyncio.to_thread(_disk_rescue_report)


@app.post("/api/disk/rescue")
async def api_disk_rescue_execute(request: Request):
    body = {}
    try: body = await request.json()
    except Exception: pass
    return await asyncio.to_thread(_disk_rescue_execute, body.get("action", ""))


@app.get("/api/models/truth")
async def api_model_truth():
    return await asyncio.to_thread(_model_truth_report)


@app.get("/api/dashboard/smoke")
async def api_dashboard_smoke_status():
    return _dashboard_smoke_status()


@app.post("/api/dashboard/smoke")
async def api_dashboard_smoke_run():
    return await asyncio.to_thread(_run_dashboard_smoke)


@app.get("/api/dashboard/logs")
async def api_dashboard_logs(lines: int = 120):
    return await asyncio.to_thread(_dashboard_logs, lines)


def _workstation_op_report() -> Dict[str, Any]:
    script = "/home/scott/ai-lab/scripts/bin/workstation-op.sh"
    latest = Path("/home/scott/ai-lab/reports/workstation-op-latest.md")
    result = _run_command([script], timeout=240) if Path(script).exists() else {"ok": False, "stdout": "", "stderr": f"missing {script}", "returncode": 127}
    report_path = result.get("stdout", "").strip().splitlines()[-1] if result.get("stdout") else str(latest)
    content = ""
    target = Path(report_path)
    if target.exists():
        content = target.read_text(errors="ignore")[-24000:]
    elif latest.exists():
        content = latest.read_text(errors="ignore")[-24000:]
    return {
        "ok": result.get("ok", False),
        "report": report_path,
        "latest": str(latest),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "content": content,
    }


@app.get("/api/workstation/op")
async def api_workstation_op_status():
    latest = Path("/home/scott/ai-lab/reports/workstation-op-latest.md")
    return {"exists": latest.exists(), "latest": str(latest), "content": latest.read_text(errors="ignore")[-24000:] if latest.exists() else ""}


@app.post("/api/workstation/op")
async def api_workstation_op_run():
    return await asyncio.to_thread(_workstation_op_report)

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            health = await ollama_manager.health_check_all()
            gpu_data = []
            try:
                import pynvml
                pynvml.nvmlInit()
                count = pynvml.nvmlDeviceGetCount()
                for idx in range(count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                    name = pynvml.nvmlDeviceGetName(handle)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_data.append({
                        "index": idx,
                        "name": name,
                        "memory": f"{mem.used // (1024*1024)}/{mem.total // (1024*1024)} MB",
                        "utilization": util.gpu
                    })
                pynvml.nvmlShutdown()
            except:
                pass

            await websocket.send_json({
                "type": "status",
                "services": {k: v for k, v in health.items()},
                "gpu": gpu_data,
                "ollama": health,
                "timestamp": time.time()
            })

            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("ws_error", error=str(e))


def _first_model(folder: str, preferred: Optional[List[str]] = None) -> str:
    path = COMFYUI_MODELS_DIR / folder
    files = sorted([p.name for p in path.glob("*") if p.is_file() and p.suffix.lower() in {".safetensors", ".ckpt", ".pt", ".pth"}]) if path.exists() else []
    for name in preferred or []:
        if name in files:
            return name
    if not files:
        raise HTTPException(status_code=503, detail=f"No ComfyUI model found in models/{folder}")
    return files[0]


def _comfy_image_name(image_path: Optional[str]) -> str:
    if not image_path:
        raise HTTPException(status_code=400, detail="Upload/select an image first for this workflow")
    return os.path.basename(image_path)


def build_txt2img_prompt(prompt: str, request: GenerateRequest) -> dict:
    ckpt = _first_model("checkpoints", ["sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly-fp16.safetensors"])
    return {
        "3": {"inputs": {"seed": request.seed or int(time.time() * 1000) % 4294967295, "steps": request.steps or 20, "cfg": request.cfg or 7, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}, "class_type": "KSampler"},
        "4": {"inputs": {"ckpt_name": ckpt}, "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": request.width or 1024, "height": request.height or 1024, "batch_size": request.batch_size or 1}, "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": "low quality, blurry, distorted, watermark, text", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": "ai_lab/txt2img", "images": ["8", 0]}, "class_type": "SaveImage"}
    }


def build_img2img_prompt(prompt: str, request: GenerateRequest) -> dict:
    ckpt = _first_model("checkpoints", ["sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly-fp16.safetensors"])
    image_name = _comfy_image_name(request.image_path)
    return {
        "1": {"inputs": {"image": image_name}, "class_type": "LoadImage"},
        "2": {"inputs": {"ckpt_name": ckpt}, "class_type": "CheckpointLoaderSimple"},
        "3": {"inputs": {"text": prompt, "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "4": {"inputs": {"text": "low quality, blurry, distorted, watermark, text", "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "5": {"inputs": {"pixels": ["1", 0], "vae": ["2", 2]}, "class_type": "VAEEncode"},
        "6": {"inputs": {"seed": request.seed or int(time.time() * 1000) % 4294967295, "steps": request.steps or 18, "cfg": request.cfg or 7, "sampler_name": "euler", "scheduler": "normal", "denoise": request.denoise or 0.55, "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}, "class_type": "KSampler"},
        "7": {"inputs": {"samples": ["6", 0], "vae": ["2", 2]}, "class_type": "VAEDecode"},
        "8": {"inputs": {"filename_prefix": "ai_lab/img2img", "images": ["7", 0]}, "class_type": "SaveImage"}
    }


def build_video_placeholder_prompt(prompt: str, request: GenerateRequest) -> dict:
    return build_txt2img_prompt(f"video storyboard keyframe, {prompt}", request)


def build_comfyui_prompt(prompt: str, workflow: str, mode: str, request: GenerateRequest) -> dict:
    if workflow in {"img2img", "inpaint", "controlnet"}:
        return build_img2img_prompt(prompt, request)
    if workflow in {"video", "txt2video", "img2video"}:
        return build_video_placeholder_prompt(prompt, request)
    return build_txt2img_prompt(prompt, request)


def build_upscale_prompt(image_path: str) -> dict:
    image_name = _comfy_image_name(image_path)
    return {
        "1": {"inputs": {"image": image_name}, "class_type": "LoadImage"},
        "2": {"inputs": {"image": ["1", 0], "upscale_method": "lanczos", "scale_by": 2.0}, "class_type": "ImageScaleBy"},
        "3": {"inputs": {"filename_prefix": "ai_lab/upscale", "images": ["2", 0]}, "class_type": "SaveImage"}
    }


def build_variations_prompt(image_path: str, prompt: str = "creative high quality variation") -> dict:
    request = GenerateRequest(prompt=prompt, workflow=WorkflowType.IMG2IMG, image_path=image_path, denoise=0.45, steps=16, cfg=7)
    return build_img2img_prompt(prompt, request)


# ========================================
# COMFYUI MANAGEMENT ENDPOINTS
# ========================================

@app.get("/api/comfy/models")
async def list_comfy_models():
    models = await comfyui_service.scan_model_directories()
    return {"models": models}


@app.get("/api/comfy/nodes")
async def list_comfy_nodes():
    nodes = await comfyui_service.list_custom_nodes()
    return {"nodes": nodes}


@app.post("/api/comfy/download")
async def download_model(request: ModelDownloadRequest):
    result = await comfyui_service.download_model(str(request.url), request.type.value, request.target_folder)
    return {"success": True, "model": result}


@app.post("/api/comfy/install-node")
async def install_custom_node(repo: str):
    result = await comfyui_service.install_custom_node(repo)
    return result


@app.get("/api/comfy/workflows")
async def list_workflows():
    workflows = await comfyui_service.list_workflows()
    return {"workflows": workflows}


@app.get("/api/comfy/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    workflow = await comfyui_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.post("/api/comfy/workflows")
async def create_workflow(workflow: WorkflowCreate):
    workflow_id = await comfyui_service.save_workflow(workflow.dict())
    return {"success": True, "workflow_id": workflow_id}


@app.put("/api/comfy/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: WorkflowUpdate):
    existing = await comfyui_service.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")
    update_data = workflow.dict(exclude_unset=True)
    existing.update(update_data)
    existing["updated"] = int(time.time())
    await comfyui_service.save_workflow(existing)
    return {"success": True}


@app.delete("/api/comfy/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    success = await comfyui_service.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True}


@app.post("/api/comfy/workflows/{workflow_id}/queue")
async def queue_workflow(workflow_id: str):
    workflow = await comfyui_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    result = await comfyui_service.queue_workflow(workflow)
    return {"success": True, "prompt_id": result.get("prompt_id")}


@app.get("/api/comfy/queue")
async def get_comfy_queue():
    queue = await comfyui_service.get_queue()
    return queue


@app.get("/api/tools/custom")
async def list_custom_tools():
    _ensure_agent_files()
    return {"tools": _read_json_file(TOOLS_FILE, _default_tools())}


@app.post("/api/tools/custom")
async def run_custom_tool(payload: Dict[str, Any] = Body(default_factory=dict)):
    _ensure_agent_files()
    tools = _read_json_file(TOOLS_FILE, _default_tools())
    tool_id = payload.get("tool_id") or payload.get("id")
    tool = next((item for item in tools if item.get("id") == tool_id), None)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    result = await _run_tool(tool, payload.get("payload") or {})
    return {"success": True, "tool": tool, "result": result}


@app.get("/api/mcp/agents")
async def list_mcp_agents():
    _ensure_agent_files()
    return {"agents": _read_json_file(MCP_AGENTS_FILE, _default_agents())}


@app.post("/api/mcp/run")
async def run_mcp_agent(payload: Dict[str, Any] = Body(default_factory=dict)):
    _ensure_agent_files()
    agents = _read_json_file(MCP_AGENTS_FILE, _default_agents())
    agent_id = payload.get("agent_id") or payload.get("id")
    prompt = payload.get("prompt") or payload.get("input") or ""
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    agent = next((item for item in agents if item.get("id") == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    response = await _run_mcp_agent(agent, prompt, payload.get("model"))
    runs = _read_json_file(MCP_RUNS_FILE, [])
    runs.append({
        "id": f"run-{int(time.time() * 1000)}",
        "agent_id": agent_id,
        "prompt": prompt,
        "created": int(time.time()),
        "response": response,
    })
    _write_json_file(MCP_RUNS_FILE, runs[-100:])
    return {"success": True, "agent": agent, "response": response}


@app.get("/api/views")
async def list_views():
    _ensure_agent_files()
    return {"views": _read_json_file(VIEWS_FILE, _default_views())}


@app.post("/api/views")
async def save_view(payload: Dict[str, Any] = Body(default_factory=dict)):
    _ensure_agent_files()
    views = _read_json_file(VIEWS_FILE, _default_views())
    view = {
        "id": payload.get("id") or f"view-{int(time.time() * 1000)}",
        "name": payload.get("name") or "Untitled View",
        "type": payload.get("type") or "custom",
        "url": payload.get("url") or "/dashboard",
        "scope": payload.get("scope") or "local",
        "description": payload.get("description") or "",
        "updated": int(time.time()),
    }
    views = [item for item in views if item.get("id") != view["id"]]
    views.append(view)
    _write_json_file(VIEWS_FILE, views)
    return {"success": True, "view": view}


@app.delete("/api/views/{view_id}")
async def delete_view(view_id: str):
    _ensure_agent_files()
    views = _read_json_file(VIEWS_FILE, _default_views())
    views = [item for item in views if item.get("id") != view_id]
    _write_json_file(VIEWS_FILE, views)
    return {"success": True}


@app.get("/api/gpu/{gpu_index}/processes")
async def get_gpu_processes(gpu_index: int):
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        compute_procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)

        processes = []
        for proc in compute_procs:
            try:
                import psutil
                p = psutil.Process(proc.pid)
                processes.append({
                    "pid": proc.pid,
                    "name": p.name(),
                    "vram": proc.usedGpuMemory // (1024 * 1024),
                    "type": "compute",
                })
            except:
                processes.append({
                    "pid": proc.pid,
                    "name": "unknown",
                    "vram": proc.usedGpuMemory // (1024 * 1024),
                    "type": "compute",
                })

        pynvml.nvmlShutdown()
        return {"processes": processes}
    except Exception as e:
        logger.error(f"Failed to get GPU processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gpu/{gpu_index}/kill-all")
async def kill_gpu_processes(gpu_index: int):
    try:
        import pynvml
        import psutil
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

        for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle):
            try:
                psutil.Process(proc.pid).terminate()
            except:
                pass

        for proc in pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle):
            try:
                psutil.Process(proc.pid).terminate()
            except:
                pass

        pynvml.nvmlShutdown()
        return {"success": True, "message": f"All processes on GPU {gpu_index} terminated"}
    except Exception as e:
        logger.error(f"Failed to kill GPU processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process/{pid}/kill")
async def kill_process(pid: int):
    try:
        import psutil
        psutil.Process(pid).terminate()
        return {"success": True, "message": f"Process {pid} terminated"}
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="Process not found")
    except Exception as e:
        logger.error(f"Failed to kill process: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# SECURITY ENDPOINTS
@app.post("/api/security/scan")
async def security_scan(request: SecurityScanRequest):
    threats = security_service.scan_text(request.text, source="api_scan")
    return {"threats": threats, "count": len(threats)}


@app.post("/api/security/scan-prompt")
async def scan_prompt(request: ImprovePromptRequest):
    threats = security_service.scan_prompt(request.prompt, "prompt-improve")
    return {"threats": threats, "count": len(threats), "safe": len(threats) == 0}


@app.get("/api/security/stats")
async def security_stats():
    return security_service.get_threat_stats()


@app.get("/api/security/threats")
async def get_threats(limit: int = 100, since: Optional[int] = None):
    threats = security_service.get_threats(limit=limit, since=since)
    return {"threats": threats}


@app.get("/api/security/audit")
async def get_audit_logs(limit: int = 100, since: Optional[int] = None, level: Optional[str] = None):
    logs = security_service.get_audit_logs(limit=limit, since=since, level=level)
    return {"logs": logs}


@app.post("/api/security/block-ip")
async def block_ip(ip: str, reason: str = "Security threat"):
    security_service.block_ip(ip, reason)
    return {"success": True, "message": f"IP {ip} blocked"}


@app.post("/api/security/unblock-ip")
async def unblock_ip(ip: str):
    security_service.unblock_ip(ip)
    return {"success": True, "message": f"IP {ip} unblocked"}


@app.post("/api/security/rotate-keys")
async def rotate_api_keys():
    new_key = security_service.generate_api_key()
    return {"success": True, "new_key": new_key}


# OLLAMA MODEL MANAGEMENT
@app.get("/api/ollama/{port}/models")
async def list_ollama_models(port: int):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"http://localhost:{port}/api/tags")
        resp.raise_for_status()
        return {"models": resp.json().get("models", [])}


@app.post("/api/ollama/{port}/pull")
async def pull_ollama_model(port: int, model: str):
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(f"http://localhost:{port}/api/pull", json={"name": model})
        resp.raise_for_status()
        return {"success": True}


@app.delete("/api/ollama/{port}/models/{model_name}")
async def delete_ollama_model(port: int, model_name: str):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.request("DELETE", f"http://localhost:{port}/api/delete", json={"name": model_name})
        resp.raise_for_status()
        return {"success": True}


# BATCH GENERATION
@app.post("/api/batch-generate")
async def batch_generate(request: BatchGenerateRequest):
    prompt_ids = []
    for i in range(request.count):
        varied_prompt = f"{request.base_prompt} --variation {i+1} --strength {request.variation_strength}"
        try:
            result = await generate(GenerateRequest(
                prompt=varied_prompt,
                workflow=request.workflow,
                mode=request.mode
            ))
            if isinstance(result, dict) and result.get("prompt_id"):
                prompt_ids.append(result["prompt_id"])
        except Exception as e:
            logger.error(f"Batch generation failed for item {i}: {e}")
        await asyncio.sleep(0.5)

    return {"success": True, "prompt_ids": prompt_ids, "count": len(prompt_ids)}


# FILE UPLOAD
@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded = []
    AI_LAB_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMFYUI_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORKFLOW_ROOT.mkdir(parents=True, exist_ok=True)
    COMFYUI_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model_exts = {".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".onnx", ".bin"}
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    doc_exts = {".json", ".txt", ".md"}
    allowed_ext = image_exts | doc_exts | model_exts

    def route_model_folder(filename: str) -> str:
        lower = filename.lower()
        if "vae" in lower:
            return "vae"
        if "lora" in lower or "lightx2v" in lower:
            return "loras"
        if "umt5" in lower or "t5" in lower or "clip" in lower or "text_encoder" in lower:
            return "text_encoders"
        if any(token in lower for token in ["wan", "flux", "hunyuan", "ltxv"]):
            return "diffusion_models"
        if any(token in lower for token in ["control", "canny", "depth", "openpose"]):
            return "controlnet"
        if any(token in lower for token in ["upscale", "esrgan", "realesrgan"]):
            return "upscale_models"
        return "checkpoints"

    for file in files:
        original = Path(file.filename or "upload.bin").name
        ext = Path(original).suffix.lower()
        if ext not in allowed_ext:
            uploaded.append({"original_name": original, "skipped": True, "reason": "unsupported extension"})
            continue

        sanitized_original = original.replace("/", "_").replace("\\", "_")
        safe_name = f"{int(time.time())}_{sanitized_original}"
        if ext in model_exts:
            folder = route_model_folder(safe_name)
            target_dir = COMFYUI_MODELS_DIR / folder
            kind = "model"
        elif ext == ".json":
            target_dir = WORKFLOW_ROOT
            kind = "workflow"
        else:
            target_dir = AI_LAB_INPUT_DIR
            kind = "image" if ext in image_exts else "document"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name

        size = 0
        with open(target_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                f.write(chunk)

        item = {
            "filename": safe_name,
            "original_name": original,
            "kind": kind,
            "size": size,
            "path": str(target_path),
        }

        if ext in image_exts:
            comfy_path = COMFYUI_INPUT_DIR / safe_name
            comfy_path.write_bytes(target_path.read_bytes())
            item["comfy_name"] = safe_name
            item["comfy_path"] = str(comfy_path)
        elif ext in model_exts:
            item["model_folder"] = folder
            item["comfy_path"] = str(target_path)
        elif ext == ".json":
            item["workflow_id"] = Path(safe_name).stem

        uploaded.append(item)

    return {"uploaded": uploaded, "count": len([item for item in uploaded if not item.get("skipped")])}


# AUTH ENDPOINTS
from app.middleware.auth import create_access_token, create_refresh_token, verify_refresh_token

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    access_token = create_access_token({"sub": username, "permissions": ["read", "write", "admin"]})
    refresh_token = create_refresh_token({"sub": username})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@app.post("/api/auth/refresh")
async def refresh_token(refresh_token: str = Form(...)):
    try:
        payload = verify_refresh_token(refresh_token)
        access_token = create_access_token({"sub": payload["sub"], "permissions": ["read", "write", "admin"]})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.get("/api/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user_optional)):
    return user or {"authenticated": False}


# HEALTH/READINESS
@app.get("/ready")
async def readiness():
    checks = {
        "ollama_v100": False,
        "ollama_p40": False,
        "ollama_3060": False,
        "comfyui": False,
    }

    try:
        health = await ollama_manager.health_check_all()
        checks["ollama_v100"] = health.get("v100", False)
        checks["ollama_p40"] = health.get("p40", False)
        checks["ollama_3060"] = health.get("3060", False)
    except:
        pass

    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get("http://localhost:8188/system_stats")
            checks["comfyui"] = resp.status_code == 200
    except:
        pass

    healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"ready": healthy, "checks": checks}
    )


@app.get("/live")
async def liveness():
    return {"alive": True, "timestamp": time.time()}


# METRICS/ADMIN
@app.get("/admin/metrics")
async def admin_metrics():
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "uptime": time.time() - psutil.boot_time(),
        "processes": len(psutil.pids()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
