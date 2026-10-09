---
id: CARD-683
title: "restart_serve starts :8000 with the calling shell's AUTOREIV_DATA_DIR, so the real serve can come up on a throwaway data folder"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-532
  - CARD-679
---

# CARD-683 restart_serve starts :8000 with the calling shell's AUTOREIV_DATA_DIR, so the real serve can come up on a throwaway data folder

## Backlog
Found on 2026-10-09 during the serve checks after CARD-679/680/674/676. Not started; needs Jacob's build approval.

## Problem
`scripts/restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000` was run from a shell that still had `AUTOREIV_DATA_DIR` and `AUTOREIV_WIKI_PATH` set to a throwaway folder (`%TEMP%\ar10\data679`, left from the CARD-679 code-path check). `restart_serve.py` copies the caller's environment into the new serve, so Jacob's :8000 came up on the throwaway data folder: health 200 and `matches_index=True`, but `apply_model_plan.py --check` failed (fresh defaults: platform default ollama, Architect and Developer on default). Jacob's real data folder was not touched. Restarting from a clean shell fixed it.

Nothing in the restart output says which data folder the serve uses, so the only signal was the model-plan check.

## Change (proposal)
- `restart_serve.py` prints the data folder, database and wiki the new serve resolves (`data_dir=...`).
- When the port is 8000 (or the bind is the persisted real serve), drop `AUTOREIV_DATA_DIR`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH` and `LOCALAPPDATA` overrides that point under the temp folder or a known scratch root, or refuse and say why.

## Proof
- Check (failing first): `start_serve` for port 8000 with `AUTOREIV_DATA_DIR` under the temp folder does not pass it to the child (or refuses), and the restart output names the data folder.
