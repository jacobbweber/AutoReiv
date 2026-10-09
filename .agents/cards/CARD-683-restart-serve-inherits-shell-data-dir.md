---
id: CARD-683
title: "restart_serve starts :8000 with the calling shell's AUTOREIV_DATA_DIR, so the real serve can come up on a throwaway data folder"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/scripts/test_card683_restart_serve_clean_env.py]
branch: fix/card-683-restart-clean-env
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-532
  - CARD-679
---

# CARD-683 restart_serve starts :8000 with the calling shell's AUTOREIV_DATA_DIR, so the real serve can come up on a throwaway data folder

## Backlog
Found on 2026-10-09 during the serve checks after CARD-679/680/674/676. Jacob approved the build on 2026-10-09.

## Problem
`scripts/restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000` was run from a shell that still had `AUTOREIV_DATA_DIR` and `AUTOREIV_WIKI_PATH` set to a throwaway folder (`%TEMP%\ar10\data679`, left from the CARD-679 code-path check). `restart_serve.py` copies the caller's environment into the new serve, so Jacob's :8000 came up on the throwaway data folder: health 200 and `matches_index=True`, but `apply_model_plan.py --check` failed (fresh defaults: platform default ollama, Architect and Developer on default). Jacob's real data folder was not touched. Restarting from a clean shell fixed it.

Nothing in the restart output says which data folder the serve uses, so the only signal was the model-plan check.

## Change (proposal)
- `restart_serve.py` prints the data folder, database and wiki the new serve resolves (`data_dir=...`).
- When the port is 8000 (or the bind is the persisted real serve), drop `AUTOREIV_DATA_DIR`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH` and `LOCALAPPDATA` overrides that point under the temp folder or a known scratch root, or refuse and say why.

## Proof
- Check (failing first): `start_serve` for port 8000 with `AUTOREIV_DATA_DIR` under the temp folder does not pass it to the child (or refuses), and the restart output names the data folder.

## Root cause
`scripts/restart_serve.py` started the serve with a copy of the calling shell's environment (`os.environ.copy()` plus the repo .env). A shell left with `AUTOREIV_DATA_DIR` / `AUTOREIV_WIKI_PATH` pointing at a throwaway folder therefore moved Jacob's :8000 onto that folder. Nothing in the output named the data folder, so only the model-plan check caught it.

## Fix
- `serve_child_env()`: the serve gets the shell's environment without any `AUTOREIV_*` variable, then the repo .env, then explicit parameters. AutoReiv configuration comes from .env, the durable setting or the default live folder, never from whatever the shell has set. The ignored names are printed (`ignored_shell_env=[...]`).
- New parameters `--data-dir`, `--wiki-path`, `--db-path` (`-DataDir`, `-WikiPath`, `-DbPath` on `restart_serve.ps1`) for a deliberate other folder.
- The report prints `data_dir=`, `db=` and `wiki=` the serve resolves (same `DataDirResolver` as the app), also on `-DryRun` and `-Status`.
- `DetachedScriptRestarter` (in-app update restart) passes the serve's own `AUTOREIV_DATA_DIR` / `AUTOREIV_WIKI_PATH` / `AUTOREIV_DB_PATH` as those explicit parameters, so a service with a data folder on its unit comes back on the same folder.

## Checks
`tests/unit/scripts/test_card683_restart_serve_clean_env.py` failed first (8 of 8) and passes now (10 tests): shell AUTOREIV_* variables are dropped and listed; explicit parameters win; .env is applied; `start_serve` does not pass the shell data folder; the printed folder is resolved from the child env; dry-run prints the chosen folder; the .ps1 wrapper forwards the parameters; the in-app restart passes the serve's own folder on Windows and Linux.

Live on Jarvis, 2026-10-09:
- Shell with `AUTOREIV_DATA_DIR` / `AUTOREIV_WIKI_PATH` set to `%TEMP%\ar10\polluted`, `restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000 -DryRun`: printed `data_dir=C:\Users\jacob\AppData\Local\AutoReiv` and `ignored_shell_env=['AUTOREIV_DATA_DIR', 'AUTOREIV_WIKI_PATH']`; :8000 was not touched (same process, health 200).
- Same polluted shell, throwaway :8771 with `--data-dir %TEMP%\ar10\data683`: the serve came up healthy on data683 (database created there), the polluted folder was never created, `matches_index=True`. :8771 was stopped by exact command line and the shell variables were cleared.
