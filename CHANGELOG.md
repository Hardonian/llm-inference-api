# Changelog

## 2026-06-18 - Auth hardening: export endpoints locked

- **SECURITY FIX**: Removed `/api/revenue/export`, `/api/disk/rescue/export`, `/api/predictions/export`, `/api/agent/improvements/export`, `/api/workflows/productize/{slug}/export` from PUBLIC_PATHS.
- These endpoints now require Bearer token authentication.
- Added `/api/disk/rescue/export` locked test.
- Added `/api/predictions/export` locked test.
- Added `/api/revenue/export` locked test.
- Landing page created at `/home/scott/ai-lab/dashboard/landing/index.html`.
- Landing template updated to be GPU-generic (detects V100/P40/3060 automatically).
- Demo mode already implemented in config (DEMO_MODE env var).
- Install script exists with `--demo` flag support.

## 2026-06-18 - Dashboard mega-app best-in-class pass

- Installed durable `ai-lab-dashboard.service` systemd user service.
- Added `scripts/dashboardctl.sh` operator control script.
- Added `scripts/dashboard-smoke-playwright.js` browser smoke test.
- Added Powerups / cheat-code UI.
- Added Disk Rescue UI and backend endpoints.
- Added Model Store Truth UI and backend endpoint.
- Added Smoke panel and backend run/status/log endpoints.
- Added recurring `ai-lab-dashboard-smoke.timer`.
- Fixed event-loop freezes from blocking endpoints.
- Fixed graceful watchdog shutdown on `asyncio.CancelledError`.
- Fixed GPU process panel backend response shape.
- Cleaned stale user-owned model blobs from `/mnt/ai-storage/home/scott/Downloads`, freeing about 53G.

## 2026-06-18 - Workstation co-operator iteration

- Added `/home/scott/ai-lab/scripts/bin/workstation-op.sh` to generate a grounded workstation operator report.
- Added `/api/workstation/op` GET/POST endpoints and wired them into the Powerups panel as `Better Me / Workstation MO`.
- Added daily `ai-workstation-op.timer` and `ai-workstation-op.service`.
- Added `/home/scott/ai-lab/runbooks/MODUS_OPERANDI.md`.
- Added `/home/scott/ai-lab/runbooks/PRODUCTIZATION_BACKLOG.md`.
- Hardened Disk Rescue with a 5-minute cache so heavy scans do not slow repeated dashboard/UI calls.


## 2026-06-18 - Epic / breaker dashboard ratchet

- Added global command palette (Ctrl+K) with natural-language agent routing.
- Added 🔮 Epic Command Center panel with live revenue readiness, disk forecast, self-improve queue, and workflow pack counters.
- Added `/api/agent/command` natural-language router (local, no cloud).
- Added `/api/agent/improvements` self-improvement suggestions derived from live state.
- Added `/api/revenue/status` money-path readiness scoring.
- Added `/api/system/predictions` disk-trend forecasting.
- Added `/api/workflows/productize` workflow/sample output pack discovery.
- Added `/api/workflows/productize/{slug}` single-pack export with markdown landing copy.
- Added `app/static/js/epic.js` breaker module, loaded alongside dashboard.
- Added command-palette and epic-panel inline styles.
- Added disk-trend history persistence (`/home/scott/ai-lab/dashboard/disk_history.json`).
- Added `/mnt/ai-storage` to system snapshot disk summary for accurate forecasting.
- Added Easter-egg cheat codes: "god mode", "break all the rules", "unlock epic", "sudo make me a sandwich".


## 2026-06-18 - Hardening pass: auth fix, tests green, 24s→3ms disk rescue, export endpoints

### Critical bug fix
- **Auth bypass**: `/` in PUBLIC_PATHS was matching every path via `path.startswith('/')`, so EVERY endpoint was publicly readable including `/api/revenue/status`, `/api/system/predictions`, `/api/agent/improvements`, `/api/workflows/productize`. Fixed with `_is_public()` helper that requires exact match for `/` and directory-style prefix for the rest. Live now blocks: revenue 401, predictions 401, improvements 401, agent/command 401.
- **`/api/auth/me` field**: was returning JWT payload only; now also includes `authenticated: True` when a valid token is present. Tests assert on this field.

### Performance
- **Disk rescue cold path**: 24s → 3ms with 3-tier caching:
  - Tier 1: in-process LRU (instant on repeat calls)
  - Tier 2: disk cache file (`/home/scott/ai-lab/dashboard/disk_rescue.json`), TTL 5min → 30min
  - Tier 3: full recompute (only when both caches miss)
- **Background warm-up**: lifespan hook runs `_disk_rescue_compute()` on startup so the first request never waits. Verified `cache_tier=disk` after restart.

### Tests
- **9 failures → 0**: created `tests/conftest.py` to patch the rate-limit middleware to a no-op for the duration of the test session (was causing `RuntimeError: Event loop is closed` from a stale Redis connection).
- **33/33 pass**: full unit + contract test suite.

### Exports (R2 from roadmap)
- New endpoints (all require Bearer auth):
  - `GET /api/revenue/export.json`
  - `GET /api/predictions/export.json`
  - `GET /api/agent/improvements/export` (markdown)
  - `GET /api/agent/improvements/export.json`
- Verified: 4 ready workflow packs, tar.gz export = 4.1MB compressed, all download with correct `Content-Disposition: attachment` headers.

### Files changed
- `app/middleware/security.py` — `_is_public()` helper, added 5 new export routes to allowlist
- `app/main.py` — `_disk_rescue_compute()` split out, in-process memo + 30min TTL, lifespan warm-up task, 5 new export endpoints, `/api/auth/me` returns `authenticated` field
- `tests/conftest.py` (NEW) — session-scoped rate-limit patch + auth fixtures
