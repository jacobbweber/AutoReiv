---
id: CARD-510
title: "An Agent Studio Save rewrites the agent's tool list from pills (AutoReiv loses wiki_graph and read_document_file; memory tools get added)"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-438
  - CARD-449
  - CARD-509
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-510] An Agent Studio Save rewrites the agent's tool list from pills

> **Status**: Ready (found in the CARD-509 build repro, 2026-09-25 ~10:50 PM ET; existed before CARD-509). Not next: queue is CARD-509, Factory retirement CARD-495..498, then Education Studio.
> **Related**: CARD-438 (grandfathered tools on Save), CARD-449 (content lock), CARD-509 (skill list on Save)
> **Labels**: `type:bug`, `area:agents`, `P2`

## What was seen (scratch only, never Jacob's AppData)

A fresh install, then one Max-Turns-only Save in Agent Studio, on both qa `375945f7` and the CARD-509 branch:
- AutoReiv `allowed_tool_names` lost `wiki_graph` and `read_document_file`, and gained `recall_agent_memory` and `memorize_fact`.
- Developer gained `recall_agent_memory` and `memorize_fact`.

Nothing else changed in the form. Script: `scratch/c509_ui.cjs <agent> <maxTurns>` against the scratch server on port 8767.

## Suspected cause (to confirm)

`src/web/static/modules/studios/forge.js` L419-453 rebuilds `allowed_tool_names` on every Save from the tools of the checked skills (catalog and `pack_skills` rows), plus the storage and memory checkbox tools. Tools that come from somewhere else (the seed `pack_tool_names`, platform grants, or a skill whose row has no tools, such as the CARD-509 extra pills) are dropped. The Memory checkbox adds the memory tools even when the agent did not have them.

For an unlocked platform agent the next restart puts the seed tools back, so it self-heals. For a locked agent (Developer after a real prompt edit) the change sticks.

## Direction

- Decide the rule first: a Save should change tools only when the operator changed something that owns tools (a skill pill, the Storage or Memory checkbox). Otherwise send the loaded tool list unchanged, or have the server keep tools it did not show.
- Tests first: Vitest for the payload (a scalar-only Save sends the loaded tools); unit test that a scalar PUT leaves `allowed_tool_names` unchanged; smoke desktop and phone.
