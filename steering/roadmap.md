# AutoReiv Roadmap

> Milestones only. Cards carry `milestone:` in front matter; list them with `list_card_status.py --open --json`.
> Branches: `feat/*` from `qa`, merged to `qa` (fast tier + journey), `qa` promoted to `main` after `preflight --release`.
> Findings for each milestone live in `docs/findings.md`. Rebuilt by CARD-561 (2026-09-27).

## Done
- [x] **M1-M8 (v0.1-v0.8)**: gateway and adapters, agent kernel, built-in agents, routines, Settings Studio, observability, web/mobile front door, packaging.
- [x] **M9-M11 (v0.9-v0.11)**: frontend modularization, quality gates, UX hardening.
- [x] **M12-M17 (v0.12-v0.17)**: cognition and memory, sandboxing and HITL, multi-agent handoff, MCP client, self-verification (M17 superseded by the job graph).
- [x] **M18 (v0.18)**: autonomic OS and mechanical governance (ADR-0054).
- [x] **M19**: primitive realignment and specialized platform agents (Studio Maker CARD-393 parked).
- [x] **M20**: architecture cleanliness, subtractive engineering, monolith decomposition.

## Open
- [ ] **M21 Factory retirement** ([ADR-0060](../docs/adr/0060-retire-the-agent-training-factory.md)): export and drop the Factory tables, retire the scaffold spine and Factory leftovers. Ready: 4 (CARD 498, 512, 514, 515).
- [ ] **M22 Clean baseline and process**: green fast tier, fast tests, one findings list, platform-pack housekeeping and debt. Ready: 7 (CARD 457, 458, 459, 468, 506, 521, 561).
- [ ] **M23 Education Studio** (ADR-0059): Tutor-first direction, legacy panel cleanup, full-screen players. Ready: 3 (CARD 435, 463, 464).
- [ ] **M24 Chat, jobs and tool reliability**: kernel repeat/turn limits, Stop and resume, chat wiring, attachments and images, tool-argument robustness, credential and path guards. Ready: 26 (CARD 460, 461, 462, 471, 473, 474, 477, 478, 479, 480, 482, 483, 484, 489, 490, 491, 492, 503, 504, 510, 519, 523, 524, 535, 551, 552).
- [ ] **M25 Self-development** ([design note](self-development.md)): Developer builds, checks and live-tests AutoReiv capabilities; ADR-0061 capability-scoping follow-ups; journey testing inside AutoReiv. Ready: 15 (CARD 516, 518, 522, 525, 527, 529, 531, 533, 540, 541, 543, 545, 546, 557, 558).

## Horizon (Parked)
Studio Maker, Help Studio, companion, video, horizon ideas (CARD-146, 170, 275, 277, 280, 283-289, 331, 393) and CARD-466, 487, 493, 494, 499, 542 (parked by CARD-561 to keep Ready P3 at or below 30).
