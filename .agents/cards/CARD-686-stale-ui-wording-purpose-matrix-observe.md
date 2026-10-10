---
id: CARD-686
title: "Settings still promises 'Purpose Matrix routing' and job links say 'Observe Studio' while the sidebar says Metrics"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/frontend/card_686_retired_names.test.js, tests/unit/web/test_card686_retired_names_server.py]
branch: fix/card-686-retired-ui-wording
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-685
  - CARD-153
---

# CARD-686 Settings still promises "Purpose Matrix routing" and job links say "Observe Studio" while the sidebar says Metrics

## Backlog
Found in the CARD-685 docs refresh on 2026-10-09. Jacob approved the build on 2026-10-09 ("Build 686 then release").

## Problem
- The Settings header (`src/web/templates/index.html`, "LLM provider endpoints, Purpose Matrix routing, live model discovery, and Hardware RAM fit estimations.") still names the Purpose Matrix, which CARD-153 retired in favour of a model per agent. There is no matrix to set in Settings.
- The job strip button title says "Open this job in Observe Studio" and the chat metrics panel says "Open Observe for full KPIs", but the sidebar names that studio **Metrics**.

## Change (proposal)
- Settings header: "Model providers, live model discovery and a hardware fit estimate. Each agent's model is set in Agents."
- Use one name for the studio everywhere ("Metrics", as in the sidebar).

## Proof
- A check that the page text no longer contains "Purpose Matrix" or "Observe Studio".

## Done
- Settings header: "Model providers, live model discovery and a hardware fit estimate. Each agent's model is set in Agents." (was "LLM provider endpoints, Purpose Matrix routing, ...").
- The telemetry studio is called Metrics everywhere, as in the sidebar: the chat job strip's View Job title ("Open this job in Metrics"), the Agents telemetry panel ("open Metrics for the full numbers" and an "Open Metrics" button) and the desktop dock label (was "Observe"). The old "observe" id still opens it.
- Server-sent text: the concepts every agent is sent say agents are edited "in the Agents studio" (was Agent Forge) and list Toolsmith among the shipped agents; the delegate tool description says "custom agents made in the Agents studio"; the parked-job refusal says "Approve it (in Chat or Agents)" (was "Forge Approve"); the deprecated `purpose` field's API description no longer names the Purpose Matrix; API docstrings say Metrics studio and Agents studio.
- Grepped the page, the UI scripts and every server string for Purpose Matrix, Observe Studio, Agent Forge, Lumina, platform packs and Docs studio: none left. Internal ids (`forge*`, `observability`) are unchanged.
- Two checks keep it that way: a vitest over `index.html` and `src/web/static`, and a pytest over every string literal under `src/`.

