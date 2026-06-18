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
