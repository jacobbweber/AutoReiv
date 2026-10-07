---
id: CARD-668
title: "Short install and uninstall docs for Windows service, Linux systemd, and Docker"
type: feature
status: Ready
priority: P1
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
---

# CARD-668 Short install and uninstall docs for Windows service, Linux systemd, and Docker

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Operators need a short, plain-language place that says how to install and uninstall AutoReiv on Windows (service), Linux (systemd), and Docker, where user data lives on each, and that uninstall must not delete that data.

## Goal
A short doc (or one short page per target) covers install, uninstall, the expected data path, and the rule that uninstall leaves data alone. It matches what CARD-658, CARD-659, and CARD-660 prove.

## Acceptance
- Docs exist for Windows service, Linux systemd, and Docker.
- Each names the expected user data path (and how to override it if supported).
- Each states clearly that uninstall / remove-container must not delete the data folder or volume unless the operator runs a separate, clearly named wipe step.
- Cross-links from README or the existing packaging ADR so the doc is findable.
- Paths and steps agree with the results of CARD-658, CARD-659, and CARD-660 (update this card if those find a different real path).

## Plan and decisions
Needs Jacob's build approval before any work starts. Prefer one short doc under `docs/` with three sections over three long guides. Can land after or with the install gate cards so the paths are the ones that were actually verified.
