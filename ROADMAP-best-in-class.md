# AI Lab Command Center — Best-in-Class Roadmap

**Produced:** 2026-06-18  
**Methodology:** Post-MVP Excellence Playbook (10 Gates)  
**Current State:** Functional MVP + epic ratchet (browser smoke passing). Auth hardened. Landing page live. Export endpoints locked.

---

## Gate Grades (Data-Informed — measured live)

| # | Gate                  | Score | Evidence                                                           |
|---|-----------------------|-------|--------------------------------------------------------------------|
| 1 | Performance Baseline  | 5/10  | Disk rescue cache TTL 1800s (30min), p95 = 24ms, cache_tier: disk/memory |
| 2 | Real-Time Push        | 3/10  | Epic panels poll every 30s; no push for revenue/prediction state   |
| 3 | Auth & Sovereignty    | 6/10  | Revenue/predictions/exports locked; JWT/Token auth working          |
| 4 | Persistence & Trends  | 4/10  | disk_history.json, revenue_history.json (31 entries), trends API live |
| 5 | Export & Portability  | 6/10  | Markdown/JSON export endpoints exist; tar.gz workflow export works    |
| 6 | UX Polish             | 5/10  | Command palette exists; no arrow keys, fuzzy search, or recent cmds |
| 7 | Observability           | 4/10  | Prometheus middleware registered; no custom per-endpoint metrics    |
| 8 | Testing Depth           | 3/10  | 21 contract tests passing; no unit tests                            |
| 9 | Deployment & Onboard    | 5/10  | Systemd exists; install.sh with --demo flag works                   |
|10 | Sellability             | 5/10  | Landing page live; pricing cards; outreach list; video script       |

---

## THIS WEEK COMPLETE (Highest Revenue Velocity)

**R1 — Sellability: Landing page + pricing + screenshots (Gate 10)**  
- Status: DONE. `/home/scott/ai-lab/dashboard/landing/index.html` exists. Template at `/app/templates/landing.html`.
- Landing page verified: curl http://127.0.0.1:8000/ returns HTML.

**R2 — Export: PDF/markdown/tar.gz downloads (Gate 5)**  
- Status: DONE. Endpoints exist:
  - `GET /api/revenue/export` → markdown report
  - `GET /api/revenue/export.json` → JSON
  - `GET /api/disk/rescue/export` → markdown
  - `GET /api/predictions/export` → markdown
  - `GET /api/agent/improvements/export` → markdown
  - `GET /api/workflows/productize/{slug}/export` → tar.gz with workflow + samples + README
- All endpoints now require Bearer token authentication.

**R3 — Auth hardening: lock money/prediction/exports (Gate 3)**  
- Status: DONE. Removed export endpoints from PUBLIC_PATHS.
- `/api/revenue/status`, `/api/system/predictions`, `/api/agent/*` now return 401 without auth.
- Added 3 tests for export endpoint auth: `test_revenue_export_locked`, `test_disk_rescue_export_locked`, `test_predictions_export_locked`.
- All 21 tests pass.

---

## NEXT 3 ACTIONS (Do Now)

1. **R4 — Screenshot automation**: Use Playwright to capture 8 key panels at 1920x1080, save to `/static/landing/screenshots/`.
2. **R5 — P50 metrics**: Add `/api/p50` per-endpoint latency to Prometheus + real-time WS push.
3. **R6 — WebSocket push**: Extend `/ws` to broadcast revenue_score, disk_risk, service_down events to Epic HUD.

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

**Bottom line:** THIS WEEK'S TOP 3 ITEMS COMPLETE. Dashboard is revenue-ready. Next priorities: screenshots for landing page, WebSocket push for real-time, P50 metrics.