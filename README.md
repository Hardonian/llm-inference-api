# LLM Inference API

> Production-ready **local LLM inference gateway** — OpenAI-compatible endpoints,
> multi-GPU routing, load balancing, auth, and usage metering for your own
> Ollama / ComfyUI stack.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?logo=python)](https://www.python.org/)
[![Status: Active](https://img.shields.io/badge/status-active-orange)]()
[![Local-first](https://img.shields.io/badge/deployment-local--first-2ea043)]()

---

## Why

You have GPUs and models. Wiring them into a stable, authenticated,
OpenAI-compatible API for your apps and agents is the tedious part. This service
is that wiring: one endpoint, routed across your hardware, with auth, rate
limits, and per-key usage tracking.

## What it does

- **OpenAI-compatible** `/v1/chat/completions`, `/v1/completions`, `/v1/models`
- **Multi-GPU routing** — balances Ollama lanes (vision / mid / large) and ComfyUI
- **Auth** — bearer-token auth with public-path allowlist
- **Rate limiting** + **security headers** (defense-in-depth)
- **Prometheus metrics** (`/metrics`) for utilization and token throughput
- **Usage metering** — per-key token accounting for cost visibility
- **Local-first** — nothing leaves your network; runs as a systemd user service

## Quick start

```bash
# 0. Prereqs: Python 3.11+, an Ollama (and/or ComfyUI) endpoint on the LAN
git clone https://github.com/Hardonian/llm-inference-api.git
cd llm-inference-api

# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Configure
cp .env.example .env      # point OLLAMA_BASE_URL / COMFYUI at your workers

# 3. Run
uvicorn app.main:app --host 127.0.0.1 --port 8000
#  or via the bundled launcher:
python main.py

# 4. Health + first call
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/v1/models
```

### systemd (recommended for always-on)

```bash
systemctl --user status llm-inference-api.service --no-pager
# bundled helper:
./scripts/dashboardctl.sh status    # health + smoke
./scripts/dashboardctl.sh restart
```

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | public | Health check (JSON) |
| `/metrics` | GET | public | Prometheus metrics |
| `/v1/models` | GET | bearer | List routed models |
| `/v1/chat/completions` | POST | bearer | Chat completions (OpenAI-compatible) |
| `/v1/completions` | POST | bearer | Text completions |
| `/dashboard` | GET | bearer | Local operator console |

## Configuration

Key variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `OLLAMA_BASE_URL` | Upstream Ollama base URL |
| `COMFYUI_BASE_URL` | Upstream ComfyUI base URL |
| `API_TOKEN` | Bearer token for protected routes |
| `PUBLIC_PATHS` | Comma-separated paths open without auth |

## Part of the Hardonia stack

LLM Inference API is one of the [Hardonia](https://github.com/Hardonian)
local-first AI infrastructure projects — measurable value, operator-grade
control, and zero theatre.

## License

See repository LICENSE / `pyproject.toml`.
