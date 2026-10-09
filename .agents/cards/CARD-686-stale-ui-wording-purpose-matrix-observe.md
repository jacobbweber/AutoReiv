---
id: CARD-686
title: "Settings still promises 'Purpose Matrix routing' and job links say 'Observe Studio' while the sidebar says Metrics"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-685
  - CARD-153
---

# CARD-686 Settings still promises "Purpose Matrix routing" and job links say "Observe Studio" while the sidebar says Metrics

## Backlog
Found in the CARD-685 docs refresh on 2026-10-09. Not started; needs Jacob's build approval (it changes text in the app, which the docs-only card could not do).

## Problem
- The Settings header (`src/web/templates/index.html`, "LLM provider endpoints, Purpose Matrix routing, live model discovery, and Hardware RAM fit estimations.") still names the Purpose Matrix, which CARD-153 retired in favour of a model per agent. There is no matrix to set in Settings.
- The job strip button title says "Open this job in Observe Studio" and the chat metrics panel says "Open Observe for full KPIs", but the sidebar names that studio **Metrics**.

## Change (proposal)
- Settings header: "Model providers, live model discovery and a hardware fit estimate. Each agent's model is set in Agents."
- Use one name for the studio everywhere ("Metrics", as in the sidebar).

## Proof
- A check that the page text no longer contains "Purpose Matrix" or "Observe Studio".
