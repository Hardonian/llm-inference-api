# Changelog

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
