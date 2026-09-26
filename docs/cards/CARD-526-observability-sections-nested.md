---
id: CARD-526
title: "Observability sections are nested by two missing </details> tags: the friction recommendations are three collapsed levels deep"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-311
  - CARD-354
  - CARD-428
labels:
  - type:bug
  - area:observability
  - area:ui
  - P3
---

# [CARD-526] Observability sections nested inside Live System Logs

> **Status**: Ready (found in the CARD-520 reproduction, 2026-09-26 ~1:00 PM ET, qa `0f5cf9da`). CARD-520 decision D10 recommends folding this into CARD-520; if accepted, it closes with CARD-520.
> **Related**: CARD-520, CARD-311 (logs, journey, capability sections), CARD-354 (friction section), CARD-428 (journey canvas)
> **Labels**: `type:bug`, `area:observability`, `area:ui`, `P3`

## Evidence

- `src/web/templates/index.html`: the `<details class="obs-section" data-obs-section="logs">` at L928 has no closing tag before the next section (L966), and `data-obs-section="capability"` at L1143 has none before `friction` (L1185).
- In the browser (scratch server, desktop 1280x900 and phone 390x844, `scratch\c520_dbg2.cjs`): top-level sections are Metrics, Per-Agent KPIs, Tool Reliability and Live System Logs. **Journey Canvas, Standing Journey Timeline and Capability Catalog are inside Live System Logs, and Skill Friction & Runbook Recommendations is inside Capability Catalog** (depth 2). All collapsed by default.
- Effect: to see friction recommendations the operator must open Live System Logs, then Capability Catalog, then the friction section. Opening the logs section to reach anything below also starts the log view. `expandObsSection('friction')` opens only the innermost `details`, so code that jumps to the section shows nothing.

## Change

Close the two sections where they end, so every `details.obs-section` is top level. Keep each section's current default (Journey Canvas is `open`).

## Done when

A Vitest DOMParser check finds no `details.obs-section` inside another; the friction section opens with one click on desktop and phone; smoke reaches the friction list without opening Logs or Capability Catalog.
