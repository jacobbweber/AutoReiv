---
id: CARD-652
title: "Knowledge artifact route returns template teaching sections"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/education/test_card652_knowledge_artifact_removed.py]
branch: feat/card-652-remove-knowledge-artifact
log: {minutes: 10, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-643
  - CARD-646
---

# CARD-652 Knowledge artifact route returns template teaching sections

## Intent
`POST /api/education/knowledge-artifact` (`knowledge_types.build_knowledge_artifact`) fills every section it is not given with fixed text such as "The core conceptual model for <topic> establishes its structural definitions ...". It only returns the artifact and writes nothing, but a caller that saves it saves a template.

## Goal
The route returns only sections it was given or that are grounded in Jacob's notes, and says when there is nothing to return.

## Plan and decisions
- Backlog card (found while checking the remaining course writers for CARD-642); Jacob approved the build on 2026-10-06.
- Per Jacob's guidance the unused template route is removed, not fixed: nothing in the UI or the course called it.
- The knowledge-type list, shapes, step resolution and GET /api/education/knowledge-types stay; the course chrome uses them.

## Change
- `knowledge_types.py`: `build_knowledge_artifact` (fixed text for every section it was not given, e.g. "The core conceptual model for X establishes its structural definitions ...") and `render_knowledge_note_markdown` removed.
- Router: `POST /api/education/knowledge-artifact` and `KnowledgeArtifactPayload` removed.
- CARD-334 test for the removed builder dropped; the inventory doc row updated.

## What dies
The template knowledge artifact and its route. It never wrote a note.

## Proof
- Checks (failing first): builder and renderer gone, knowledge types and step resolution kept; the route returns 404/405 while GET knowledge-types still lists the four types; no source file refers to the route or the removed functions.
- Live: no UI or course path used the route.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | __PYTEST__ |
| preflight --fast --base qa | GREEN | __FAST__ |

## Release note
Removed an unused endpoint that returned the same template teaching sections for every topic.
