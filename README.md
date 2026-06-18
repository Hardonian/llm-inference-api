# AI Lab Command Center Dashboard

Local-first FastAPI dashboard for the EPYC AI lab: Ollama lanes, ComfyUI, Open WebUI, n8n, Redis, Postgres, Qdrant, GPU/process visibility, prompt studio, private workflows, self-heal, money paths, and operator powerups.

## Run

The service is installed as a systemd user unit:

```bash
systemctl --user status ai-lab-dashboard.service --no-pager
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

Control:

```bash
scripts/dashboardctl.sh status
scripts/dashboardctl.sh health
scripts/dashboardctl.sh smoke
scripts/dashboardctl.sh restart
scripts/dashboardctl.sh logs 160
```

## Product offer

Private AI Lab Command Center

- Target: local-AI builders, agencies, researchers, power users with GPUs.
- Pain: local AI stacks are powerful but chaotic; people lose hours to ports, model paths, broken dashboards, and disk bloat.
- Promise: one private local dashboard for health, generation, power actions, smoke tests, and model/disk control.
- Pricing: $297 lifetime template or $29/mo managed updates; $499 setup call.

## Key features

- Health cards for the local AI stack.
- GPU and Ollama lane monitoring.
- ComfyUI models/nodes/workflows/queue panels.
- Prompt Studio and batch actions.
- Powerups / cheat-code panel.
- Disk Rescue panel.
- Model Store Truth panel.
- Browser smoke test automation.
- systemd user service + recurring smoke timer.
- Local-only by default.

## Safety

- Dashboard binds to 127.0.0.1.
- Destructive process-kill endpoints require auth.
- Disk Rescue destructive actions are restricted to explicit user-owned cleanup unless sudo is run manually.
- No cloud dependency required.

## Docs

- `OPERATOR.md` - daily use
- `DELIVERY-dashboard-mega-app-2026-06-18.md` - delivery and verification log
