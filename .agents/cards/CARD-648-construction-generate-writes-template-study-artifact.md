---
id: CARD-648
title: "Construction generate route still writes a template study artifact"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/education/test_card648_construction_generate_removed.py]
branch: feat/card-648-remove-construction-generate
log: {minutes: 15, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-643
  - CARD-646
---

# CARD-648 Construction generate route still writes a template study artifact

## Intent
`POST /api/education/construction/generate` calls `construction.build_study_artifact_markdown`, which writes a study artifact note from a fixed template: the same sections for every topic, a fixed diagram and quiz prompts such as "In one sentence, what is <topic>?". It is not part of the course and nothing in the UI calls it, but anything that hits the route still gets a template note in the Wiki.

## Goal
The route writes only content grounded in Jacob's notes (via `grounded.py`, as the course steps now do) or writes nothing, or it is retired if nothing needs it.

## Plan and decisions
- Backlog card (found while building CARD-646); Jacob approved the build on 2026-10-06.
- Per Jacob's guidance the unused template route is removed, not fixed: nothing in the course or the UI called it.

## Change
- `construction.py`: `build_study_artifact_markdown` (fixed sections, a fixed Mermaid diagram and quiz prompts such as "In one sentence, what is X?"), `construct_study_artifact`, its search/read helpers and `ARTIFACT_KIND` removed. `create_study_artifact_note` (used by the grounded course labs), the allowlist guard and the Ask clause stay.
- Router: `POST /api/education/construction/generate` and `ConstructionGeneratePayload` removed.
- `education/__init__.py` exports trimmed; CARD-245 tests for the removed generator dropped (allowlist, create and Ask clause tests kept).

## What dies
The template Construction study artifact and the route that wrote it. Notes it wrote earlier are left alone.

## Proof
- Checks (failing first): the builder, generator and `ARTIFACT_KIND` are gone from the module and package; the route is not registered and returns 404/405; no source file refers to the route or the removed functions.
- Live: no UI or course path used the route; covered by the shared full-course check after CARD-653.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2658 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
Removed an unused Construction endpoint that wrote the same template study note for every topic.
