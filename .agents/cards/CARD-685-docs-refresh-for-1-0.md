---
id: CARD-685
title: "Docs refresh for 1.0: a friendly README, a user guide and accurate install docs"
type: docs
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card668_install_docs.py, tests/unit/deploy/test_deploy_suite.py, tests/unit/deploy/test_card673_no_packs_dir.py, tests/unit/system/test_card662_update_rollback_keeps_data.py, tests/unit/test_card661_acceptance_checklist.py]
branch: docs/card-685-docs-refresh
log: {minutes: 90, qa_runs: 1, findings: 2}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-661
  - CARD-668
---

# CARD-685 Docs refresh for 1.0: a friendly README, a user guide and accurate install docs

## Backlog
Requested by Jacob after the 1.0.0 release (2026-10-09). Jacob asked for it on 2026-10-09.

## Problem
The README still described eight studios including a Docs studio and Agent Forge, a "purpose matrix", `data/autoreiv.db` and `data/wiki` as the default data paths, and mixed developer detail into the user's front door. The install doc named card numbers, called the Docker wiki host folder required while the compose file falls back to a volume, and pointed at "Settings > Software Updates" (the panel is "System & Software Updates"). About 230 relative links across the docs pointed at the old `docs/cards/` folder or at `file:///d:/...` paths on one machine.

## Change
- Docs only, no code behavior changes.
- README becomes a short, friendly front door: what AutoReiv is, a quick start per install path, a first-steps tour, where your data lives and how it is kept safe, and links to deeper docs.
- New `docs/user-guide.md` (studios, agents, skills and tools, jobs and approvals, routines, models, updates and backups), `docs/developer.md` (developer detail moved out of the README) and `docs/README.md` (docs index).
- Install and deploy docs checked against the real scripts and compose file; card-era jargon removed.
- Dead relative links repointed to `.agents/cards/`, `docs/adr/` and `docs/archive_artifacts/specs/`.

## Proof
- The existing doc tests pass, every relative link in the tracked markdown resolves, and every command shown matches the script flags.

## Done
- `README.md` rewritten as a short front door with Jacob's intro (Hermes Agent and OpenClaw linked to their official GitHub repositories, checked by web search), a quick start per install path, first steps, the data table and links.
- New `docs/user-guide.md`, `docs/developer.md` and `docs/README.md`.
- `docs/install-and-uninstall.md`: a "From a terminal" section, the Windows service needs the clone's `.venv` first, the Docker wiki host folder is optional (the compose file falls back to the `autoreiv-wiki` volume), the update panel is "System & Software Updates", rollback is a `git checkout` of the previous release tag (there are no release branches), and a systemd install updates by pulling in the clone and running the installer again (the installed copy has no git). Card numbers removed.
- `deploy/README.md`: one table per script with every real option (`-HostIP`, `-DbPath`, `-WikiPath`, `-Reload` on `run_autoreiv.ps1`, `--print-unit`, `--dry-run`); ADR and card jargon and the stale "no suggested default" wiki note removed.
- `.env.example`, `AGENTS.md`, `steering/product.md` and `steering/roadmap.md`: stale `packs/` paths, studio names, a dead `docs/architecture` link and the pre-1.0 open milestones fixed.
- 233 dead relative links repointed (old `docs/cards/` and `docs/specs/` paths and `file:///d:/...` links) across `CHANGELOG.md`, `docs/adr`, `docs/design`, `docs/education` and `docs/archive_artifacts`. Every relative link in tracked markdown now resolves.

## Findings
- CARD-686 (backlog, Ready): the Settings header still says "Purpose Matrix routing", and job links say "Observe Studio" while the sidebar says Metrics. These are code (page text) fixes, so they are not in this card.
- A systemd install has no in-app update (the installed copy has no git); the docs now say to update from the clone. Changing that is a product decision, not a bug.

