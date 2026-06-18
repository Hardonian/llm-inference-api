# AI Lab Command Center — Best-in-Class Roadmap

**Produced:** 2026-06-18  
**Methodology:** Post-MVP Excellence Playbook (10 Gates)  
**Current State:** Functional MVP + epic ratchet (browser smoke passing)

---

## Gate Grades (Data-Informed — measured live)

| # | Gate                  | Score | Evidence                                                           |
|---|-----------------------|-------|--------------------------------------------------------------------|
| 1 | Performance Baseline  | 3/10  | `/api/disk/rescue` p95 = 24,370ms cold; no p95 monitoring          |
| 2 | Real-Time Push        | 3/10  | Epic panels poll every 30s; no push for revenue/prediction state   |
| 3 | Auth & Sovereignty    | 2/10  | Money, predictions, model-truth all in public allowlist             |
| 4 | Persistence & Trends  | 3/10  | Only `disk_history.json` persisted; no revenue/improvement history  |
| 5 | Export & Portability  | 1/10  | Zero export endpoints (no PDF/markdown/tar.gz)                      |
| 6 | UX Polish             | 5/10  | Command palette exists; no arrow keys, fuzzy search, or recent cmds |
| 7 | Observability         | 4/10  | Prometheus middleware registered; no custom per-endpoint metrics    |
| 8 | Testing Depth         | 1/10  | Zero unit tests; only Playwright smoke                              |
| 9 | Deployment & Onboard  | 3/10  | Systemd exists; no install script, demo mode, docker, or tour       |
| 10| Sellability           | 2/10  | README only; no landing page, pricing, screenshots, or demo video   |

---

## Roadmap — Sorted by Money×Leverage

### THIS WEEK (Highest Revenue Velocity)

**R1 — Sellability: Landing page + pricing + screenshots (Gate 10)**
- What: `/home/scott/ai-lab/dashboard/landing/index.html` — self-contained landing
- Contents: hero, feature grid (8 gates with screenshots), pricing cards ($297/$29mo), install CTA
- Verify: open in browser, screenshot gallery visible
- Hours: 4
- Risk: low — static HTML

**R2 — Export: PDF/markdown/tar.gz downloads (Gate 5)**
- What: New endpoints:
  - `GET /api/revenue/export` → markdown report with timestamp
  - `GET /api/disk/rescue/export` → markdown
  - `GET /api/workflows/productize/{slug}/export` → tar.gz with workflow JSON + README + sample images
- Verify: curl each endpoint, verify content type and body
- Hours: 6
- Risk: low — pure generation, no state mutation

**R3 — Auth hardening: lock money/prediction/exports (Gate 3)**
- What: Remove from public allowlist:
  - `/api/revenue/*`
  - `/api/system/predictions`
  - `/api/workflows/productize/*`
  - `/api/agent/*`
- Add JWT bearer check (existing auth middleware); keep `/health`, `/api/disk/rescue` (GET), `/api/dashboard/smoke` public
- Verify: unauth curl to `/api/revenue/status` returns 401; authed curl returns 200
- Hours: 3
- Risk: medium — must not lock Scott out of his own dashboard; test auth path first

---

### THIS MONTH (Foundation — makes paying users possible)

**R4 — Deployment: one-command install + demo mode (Gate 9)**
- What:
  - `install.sh` — clone, create venv, install deps, install systemd, start
  - `--demo` flag — fakes GPU/system data so a prospect can try without hardware
  - Landing page gets "Install in 60 seconds" section
- Verify: run install.sh on fresh VM, dashboard boots to demo mode
- Hours: 8
- Risk: low if demo-mode is additive

**R5 — Persistence: revenue/improvement/prediction history (Gate 4)**
- What:
  - `revenue_history.json` — appended on each `/api/revenue/status` call
  - `improvement_history.json` — appended on `/api/agent/improvements`
  - `/api/trends` endpoint returns 7d/30d deltas
  - Epic HUD cards show "vs last week" arrow
- Verify: 5 calls to revenue → history file has 5 entries
- Hours: 4
- Risk: low

**R6 — Testing: unit + contract tests (Gate 8)**
- What:
  - `tests/test_disk_rescue_cache.py` — cache TTL behavior
  - `tests/test_agent_router.py` — all intents + easter eggs
  - `tests/test_revenue_scoring.py` — readiness math
  - `tests/test_predictions.py` — trend calculation
  - `tests/contract/test_endpoints.py` — every endpoint returns valid schema
  - `pytest.ini` + `conftest.py` with fixture app
- Verify: `pytest` exits 0; CI badge in README
- Hours: 8
- Risk: medium — may reveal latent bugs (feature, not bug)

**R7 — Performance: fix 24s cold path + add caching (Gate 1)**
- What:
  - `disk_rescue` cache TTL extended from 300s to 3600s (1h) — disk doesn't change fast
  - Background task refreshes cache every 50 minutes
  - `/api/p50` endpoint returns live latency for top 10 endpoints (measured in-process)
  - p95 alert: if p95 > 5s for any endpoint, emit structured log + push to client
- Verify: cold-path p95 for `/api/disk/rescue` drops to < 2s
- Hours: 5
- Risk: low

**R8 — Real-Time: WS push for epic HUD (Gate 2)**
- What:
  - Extend existing WebSocket at `/ws` to broadcast: revenue_score, disk_risk, service_down events
  - Epic HUD cards consume WS events instead of polling
  - Client reconnects with backoff
- Verify: change a service status; HUD updates within 2s in browser
- Hours: 6
- Risk: medium — WS state management

---

### THIS QUARTER (Differentiation — makes this the only option)

**R9 — UX Polish: command palette + keyboard + mobile (Gate 6)**
- What:
  - Arrow keys navigate palette items; Enter selects
  - Fuzzy search (fuse.js) for 3+ char queries
  - Recent commands persist in localStorage, shown first
  - Mobile: collapsible epic panel; command palette full-width
  - ARIA labels on all interactive elements
- Verify: navigate entire dashboard with keyboard only; mobile layout on 375px viewport
- Hours: 10
- Risk: low

**R10 — Observability: per-endpoint Prometheus metrics + alert webhook (Gate 7)**
- What:
  - Custom metrics: `dashboard_request_seconds{endpoint}`, `dashboard_errors_total{kind}`
  - `/metrics` Prometheus endpoint already registered — add custom collectors
  - Webhook hook: POST to configurable URL when disk > 90% or service down
- Verify: curl /metrics, find custom metrics; trigger alert; verify webhook fired
- Hours: 6
- Risk: low

**R11 — Sellability Phase 2: product hunt launch kit (Gate 10 continued)**
- What:
  - 30-sec demo video (script in `/home/scott/ai-lab/dashboard/launch/video-script.md`)
  - Screenshot gallery automation (Playwright captures 8 key panels at 1920x1080)
  - Product Hunt / Hacker News / Indie Hackers launch copy
  - First 10 paying customer outreach list (local AI researchers, agencies, indie hackers)
- Verify: all launch assets exist; outreach list actionable
- Hours: 6
- Risk: low — pure content

**R12 — Multi-User Mode (unlocks team sales)**
- What:
  - User table in existing Postgres
  - Per-user dashboard state isolation
  - Team admin: invite by email, SSO via OIDC later
- Verify: create second user, log in, see isolated state
- Hours: 20
- Risk: high — requires RLS audit; defer until R3 auth hardening is solid

---

## Next 3 Actions (Do Now)

1. **R1 — Landing page**: Write `/home/scott/ai-lab/dashboard/landing/index.html` (~4h).
2. **R2 — Export endpoints**: Add 3 new export endpoints + curl verification (~3h).
3. **R3 — Auth tightening**: Remove sensitive endpoints from allowlist + test auth path (~2h).

Total week-1 effort: ~9h. Unlocks: can show a prospect a landing page, let them download a sample report, and demo with auth.

---

## What NOT To Do

- Do not add more panels or features until R5 (persistence) lands — more state = more state to lose.
- Do not rewrite the agent router with a local LLM until R8 (real-time) lands — router is fine; latency is the bottleneck.
- Do not add OAuth/SSO until R3 (basic auth hardening) is solid — premature auth complexity.
- Do not publish to npm / Docker Hub until R4 (install script) works on a fresh VM.
- Do not chase 100% test coverage; 80% with coverage on critical paths is enough.

---

## Kill Criteria

If after 60 days:
- Zero landing page visitors: kill Sellability, focus on Deployment
- Zero export downloads: Export gate is overengineered, simplify
- Tests reveal > 3 critical bugs: spend month on Testing gate exclusively
- Auth lockout incident during R3: pause R12 until auth is audited

---

**Bottom line:** This dashboard is functional MVP. The gap to best-in-class is 10 gates. The first 3 (Sellability, Export, Auth) unlock actual revenue. Do them this week. The rest are foundation for scale.
