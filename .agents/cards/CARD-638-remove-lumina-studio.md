---
id: CARD-638
title: "Remove Lumina Studio completely"
type: chore
status: In Progress
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-638-lumina-removed]
  checks: [tests/unit/frontend/card_638_lumina_removed.test.js, tests/unit/education/test_card638_lumina_removed.py]
branch: feat/card-638-remove-lumina-studio
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-328
  - CARD-639
  - CARD-281
---

# CARD-638 Remove Lumina Studio completely

## Intent
Jacob reviewed the Lumina assessment and chose to abandon Lumina Studio. Its explainers were poor in quality and accuracy, and the compose endpoint never reached a model (it called a gateway method that does not exist and silently returned a generic three-scene filler lesson).

## Goal
AutoReiv has no Lumina Studio: no dock icon, no window or tab, no Lumina front-end files, no `/api/lumina/*` routes, no built-in Lumina lessons, no Lumina styles, settings, docs references or tests. This is a development-only clean removal with no migration.

## Change
- Remove the Lumina dock icon, desktop window registration, presets entry and theme entries (`agent-desktop.js`, `agent_desktop/presets.js`, `theme-engine.js`).
- Remove the Lumina view markup in `index.html`, the Lumina wiring in `app.js`, and `src/web/static/modules/lumina/` plus `src/web/static/modules/studios/lumina.js`.
- Remove the Lumina rules in `desktop.css` and `studios.css`.
- Remove `/api/lumina/starters`, `/api/lumina/lesson/{id}`, `/api/lumina/compose` and `/api/lumina/send-to-course` from `routers/education.py`, and `src/application/education/lumina.py` with its built-in lessons.
- Remove the leftover `lumina_film: False` flags and Lumina guard text from the visual amplifier responses (`visual_amplifiers.py`, `routers/education.py`), and Lumina mentions in current docs.
- Remove the Lumina tests (`test_card328_lumina_amplifiers.py`, `lumina_studio.test.js`) and Lumina references in other tests.
- Stored data: Lumina lessons were never persisted, so there is nothing to read or delete in the data directory. A saved desktop layout that still lists the Lumina window must load cleanly without it.

## What dies
Lumina Studio, its four built-in lessons (photosynthesis, black holes, neural networks, entropy), the 14-archetype SVG engine, the browser-voice concept player, and the four `/api/lumina/*` routes.

## Proof
- Journey `card-638-lumina-removed`: on a throwaway server the app loads with no Lumina dock icon or window, no console errors, `/api/lumina/starters` returns 404, and a saved desktop layout that still names the Lumina window opens without errors (screenshot of the dock).
- Checks: no `lumina` reference remains in `src/` or the template; the Lumina routes return 404; the desktop restores a stale Lumina window entry without throwing.

## Plan and decisions
- Built after CARD-639, which removes the only other user of `lumina.py` (the course amplifier step), so each merge leaves a working system.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Lumina Studio is removed: the dock icon, its window, its built-in lessons and its `/api/lumina/*` routes are gone.
