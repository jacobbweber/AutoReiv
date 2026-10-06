---
id: CARD-638
title: "Remove Lumina Studio completely"
type: chore
status: Done
completed: 2026-10-05
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-638-lumina-removed]
  checks: [tests/unit/frontend/card_638_lumina_removed.test.js, tests/unit/education/test_card638_lumina_removed.py]
branch: feat/card-638-remove-lumina-studio
log: {minutes: 50, qa_runs: 1, findings: 2}
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
- Remove the Lumina dock icon, header tab, desktop window registration and presets entry (`agent-desktop.js`, `agent_desktop/presets.js`). `theme-engine.js` only mentions "luminance", a colour term, and is unchanged.
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
- No Lumina settings existed, and Lumina lessons were never stored, so nothing in the data directory needed cleaning. The live data check (read only) found no Lumina rows in the four agent memory databases or `database\autoreiv.db`, and no Lumina note in the wiki.
- The `/api/lumina/send-to-course` route and its button had already gone in CARD-639.
- Historical mentions stay in `docs/archive_artifacts/`, older cards and the CHANGELOG; the two ADRs and the Learning OS inventory now say Lumina was removed.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-638-lumina-removed | desktop | pass | live_qa :8770; dock has 11 launchers (Chat ... Education), no Lumina; no `#dock-lumina`, `#tab-lumina`, `#view-lumina`; a saved layout naming the Lumina window reloads with no console error and no Lumina window; the four `/api/lumina/*` routes answer 404; Education opens |
| card-638-lumina-removed | phone | pass | same |
| card-639-course-skips-amplifier-step | desktop + phone | pass | re-run on this branch: course goes environment > retention, no filler |
| tests | - | pass | education + skills 231 passed; vitest 1091 (lumina_studio suite removed, 5 new checks) |
| preflight --fast --base qa | - | GREEN | ruff, eslint, guard 188, vitest 1091 |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\lumina-removed\`
- `card-638-lumina-removed-desktop-dock.png`
- `card-638-lumina-removed-phone-dock.png`
- `card-638-lumina-removed-desktop-04-education-opens.png`

## Release note
Lumina Studio is removed: the dock icon, its window, its built-in lessons and its `/api/lumina/*` routes are gone.
