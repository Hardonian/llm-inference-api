# AI Lab Dashboard Operator Guide

Open: http://127.0.0.1:8000/dashboard

## Daily commands

```bash
cd /home/scott/ai-workspace/repos/llm-inference-api
scripts/dashboardctl.sh status
scripts/dashboardctl.sh health
scripts/dashboardctl.sh smoke
scripts/dashboardctl.sh logs 160
scripts/dashboardctl.sh restart
```

## Dashboard superpowers

- Powerups: briefing, money paths, self-heal, repo radar, private creations, daily report, free-form directive.
- Disk Rescue: disk pressure, large files, inactive swapfiles, stale downloads, stale snap chunks, cleanup output.
- Models: active model paths, largest models, duplicate same-name/same-size model candidates.
- Smoke: last smoke result, run browser smoke, view service logs.

## Safety rules

- The dashboard is local-first and runs on localhost.
- Destructive process-kill endpoints remain auth-protected.
- Disk cleanup actions are dry-run/read-heavy except explicit user-owned downloads/temp cleanup.
- Root-owned cleanup under /mnt/ai-storage still requires sudo in a terminal.

## Service

```bash
systemctl --user status ai-lab-dashboard.service --no-pager
systemctl --user restart ai-lab-dashboard.service
journalctl --user -u ai-lab-dashboard.service -n 160 --no-pager
```

## Recurring smoke timer

```bash
systemctl --user status ai-lab-dashboard-smoke.timer --no-pager
journalctl --user -u ai-lab-dashboard-smoke.service -n 160 --no-pager
```
