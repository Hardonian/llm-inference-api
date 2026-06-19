# AI Lab Command Center Dashboard

Local-first FastAPI dashboard for AI workstations: Ollama lanes, ComfyUI, GPU monitoring, prompt studio, disk rescue, self-heal, money paths, and operator powerups.

[![Tests](https://github.com/scott/llm-inference-api/actions/workflows/tests.yml/badge.svg)](https://github.com/scott/llm-inference-api/actions/workflows/tests.yml)
[![Deploy](https://github.com/scott/llm-inference-api/actions/workflows/deploy.yml/badge.svg)](https://github.com/scott/llm-inference-api/actions/workflows/deploy.yml)

## Run

```bash
systemctl --user status ai-lab-dashboard.service --no-pager
```

Open: http://127.0.0.1:8000/dashboard

Control:
```bash
./scripts/dashboardctl.sh status   # Service health
./scripts/dashboardctl.sh health    # HTTP smoke
./scripts/dashboardctl.sh smoke     # Browser automation
./scripts/dashboardctl.sh restart   # Restart service
./scripts/dashboardctl.sh logs 160  # Tail logs
```

## Install (60 seconds)

```bash
curl -fsSL https://raw.githubusercontent.com/scott/llm-inference-api/main/scripts/install.sh | bash
```

Demo mode (fake GPU/services data for prospects):
```bash
./scripts/install.sh --demo
```

## Product Offer

Private AI Lab Command Center

| Option | Price | What |
|--------|-------|------|
| Lifetime | $297 | Full source, unlimited use, 1hr setup call |
| Managed | $29/mo | Lifetime + weekly health checks + webhook alerts |
| Team | $997/mo | Up to 10 users + SSO/OIDC + custom integrations |

## Key Features

| Category | Feature |
|----------|---------|
| **Monitoring** | GPU temps/util/VRAM, Ollama lane health, disk pressure forecasting |
| **Generation** | Prompt Studio (8 modes), batch, upscale, variations, ComfyUI workflow runner |
| **Control** | Self-heal, disk rescue, model deduplication, process manager |
| **Revenue** | Money paths scanner, workflow pack exporter (tar.gz), export reports |
| **UX** | Ctrl+K command palette, dark/light theme, mobile responsive |

## Architecture

```
llm-inference-api/
├── app/
│   ├── main.py          # FastAPI endpoints (280+)
│   ├── middleware/      # auth, security, rate-limit
│   ├── services/        # ollama, comfyui, usage
│   └── templates/       # dashboard.html, landing.html
├── scripts/
│   ├── install.sh       # One-command install
│   ├── dashboardctl.sh  # Operator control
│   └── screenshot-gallery.js  # Landing page screenshots
└── tests/               # 36 tests passing
```

## Safety

- Binds to 127.0.0.1 (local only)
- Revenue/prediction/export endpoints require Bearer token
- Disk cleanup restricted to user-owned paths
- No cloud dependency required

## Gateways

| Gate | Score | Status |
|------|-------|--------|
| Performance Baseline | 5/10 | ✓ Cache TTL 1800s |
| Real-Time Push | 3/10 | ✓ WebSocket exists |
| Auth & Sovereignty | 6/10 | ✓ Exports locked |
| Persistence & Trends | 4/10 | ✓ History tracked |
| Export & Portability | 6/10 | ✓ 6 endpoints |
| UX Polish | 5/10 | ✓ Command palette |
| Observability | 4/10 | ✓ Prometheus ready |
| Testing Depth | 5/10 | ✓ 36 tests passing |
| Deployment & Onboard | 5/10 | ✓ systemd + install |
| Sellability | 5/10 | ✓ Landing page live |

## Docs

- `OPERATOR.md` - daily use
- `DELIVERY-dashboard-mega-app-2026-06-18.md` - delivery log
- `ROADMAP-best-in-class.md` - roadmap