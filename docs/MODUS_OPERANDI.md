# AI Workstation Modus Operandi

Mission: make Scott money, save time, reduce friction, and keep the EPYC AI lab boringly reliable.

## Operating loop

1. Inventory live state before changing anything.
2. Fix the highest-risk bottleneck first: disk, service health, GPU lane ownership, repo build failure, then product polish.
3. Harden every repeated fix into one of:
   - dashboard powerup
   - script under `/home/scott/ai-lab/scripts/bin/`
   - systemd user service/timer
   - runbook under `/home/scott/ai-lab/runbooks/`
   - Hermes skill if reusable across sessions
4. Verify with real commands and browser/API smoke.
5. Snapshot in git or a timestamped release artifact.
6. Convert working internal tools into a productized service/template.

## Current command center

- Dashboard: http://127.0.0.1:8000/dashboard
- Control script: `/home/scott/ai-workspace/repos/llm-inference-api/scripts/dashboardctl.sh`
- Daily report: `/home/scott/ai-lab/scripts/bin/workstation-op.sh`
- Latest report: `/home/scott/ai-lab/reports/workstation-op-latest.md`

## Default next-best-action heuristic

Rank work by:
1. Prevents outage/data loss
2. Saves Scott repeated time
3. Makes dashboard more self-managing
4. Creates a sellable artifact
5. Improves aesthetics/polish

## Productization wedge

Offer: Private AI Lab Command Center
- $297 template
- $29/mo managed updates
- $499 setup/audit call

First customer proof checklist:
- one-command install notes
- dashboard screenshots
- 10-minute demo script
- disk/model cleanup before-after
- smoke timer proof
- service map proof
- model store manifest

## Safety rails

- No blind restarts.
- No deletion of active model stores without active path proof.
- No cloud dependencies unless explicitly requested.
- No exposing localhost services externally until auth/destructive controls are hardened.
