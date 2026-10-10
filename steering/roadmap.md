# AutoReiv Roadmap

> Milestones only. Cards carry `milestone:` in front matter; list them with `list_card_status.py --open --json`.
> Branches: short-lived branches from `qa`, merged to `qa` after the checks; `qa` is merged into `main` only at a release, after `preflight --release`.
> Findings for each milestone live in `docs/findings.md`. Rebuilt by CARD-561 (2026-09-27).

## Done
- [x] **M1-M8 (v0.1-v0.8)**: gateway and adapters, agent kernel, built-in agents, routines, Settings Studio, observability, web/mobile front door, packaging.
- [x] **M9-M11 (v0.9-v0.11)**: frontend modularization, quality gates, UX hardening.
- [x] **M12-M17 (v0.12-v0.17)**: cognition and memory, sandboxing and HITL, multi-agent handoff, MCP client, self-verification (M17 superseded by the job graph).
- [x] **M18 (v0.18)**: autonomic OS and mechanical governance (ADR-0054).
- [x] **M19**: primitive realignment and specialized platform agents (Studio Maker CARD-393 parked).
- [x] **M20**: architecture cleanliness, subtractive engineering, monolith decomposition.
- [x] **M21 Factory retirement** ([ADR-0060](../docs/adr/0060-retire-the-agent-training-factory.md)): Factory tables and leftovers retired.
- [x] **M22 Clean baseline and process**: green fast tier, fast tests, one findings list, housekeeping.
- [x] **M23 Education Studio and 1.0 readiness** (ADR-0059): Tutor-first education, install gates on the Windows service, systemd and Docker, the acceptance checklist.
- [x] **M24 Chat, jobs and tool reliability**: turn limits, Stop and resume, chat wiring, attachments, tool-argument robustness, guards.
- [x] **M25 Self-development** ([design note](self-development.md)): Developer builds, checks and live-tests changes on the active project; capability scoping follow-ups; journey testing.
- [x] **1.0.0 released 2026-10-09** (tag `v1.0.0`). Every card on the board is Done.

## Next
Jacob sets the next milestone after 1.0.

## Horizon
The parked ideas (Studio Maker, Help Studio, companion, video and others: CARD-146, 170, 275, 277, 280, 283-289, 331, 393, 466, 487, 493, 494, 499, 542) were closed as not pursued before 1.0. Any of them can come back as a new card.
