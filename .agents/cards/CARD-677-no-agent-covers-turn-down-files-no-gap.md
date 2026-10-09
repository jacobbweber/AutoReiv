---
id: CARD-677
title: "A 'No agent covers X' turn-down offers Ask Developer but files no capability gap"
type: bug
status: Ready
priority: P2
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
  - CARD-615
  - CARD-663
  - CARD-664
---

# CARD-677 A 'No agent covers X' turn-down offers Ask Developer but files no capability gap

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Not started; needs Jacob's build approval.

## Problem
Asked to fax or email notes, AutoReiv on Spark nemotron replied "No agent covers faxing notes ..." and "No agent covers external email functionality ...". The reply rules added "You can use Ask Developer to add this." (the CARD-615 turn-down rule), but no capability gap was filed. The Ask Developer line and the gap list disagree again, the drift CARD-663 removed for missing-tool wordings.

## Cause
`reply_rules.ask_developer_ending` treats `_NO_AGENT_COVERS` ("no agent ... covers") as a turn-down that gets the line. `CapabilityDetector.detect` only uses the shared missing-tool matcher (CARD-663), which needs a tool word.

## Change (proposal)
Move the "no agent covers X" turn-down into the shared matcher in `src/domain/capabilities/missing_tool.py` (capability = X). Then the line and the gap come from one decision, and the reply rules can drop their private `_NO_AGENT_COVERS`.

## Proof
- Check (failing first): "No agent covers faxing notes." files a gap with capability "faxing notes", and the existing CARD-615 cases still pass.
- Lean live: the fax ask files a gap.
