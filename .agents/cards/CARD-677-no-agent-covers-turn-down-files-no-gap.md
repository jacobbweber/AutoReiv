---
id: CARD-677
title: "A 'No agent covers X' turn-down offers Ask Developer but files no capability gap"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card677_no_agent_covers_gap.py, tests/unit/orchestration/test_card663_missing_tool_phrasings.py, tests/unit/kernel/test_card615_ask_developer_line.py]
branch: fix/card-677-no-agent-covers-files-gap
log: {minutes: 35, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-615
  - CARD-663
  - CARD-664
---

# CARD-677 A 'No agent covers X' turn-down offers Ask Developer but files no capability gap

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Jacob approved the build on 2026-10-09.

## Problem
Asked to fax or email notes, AutoReiv on Spark nemotron replied "No agent covers faxing notes ..." and "No agent covers external email functionality ...". The reply rules added "You can use Ask Developer to add this." (the CARD-615 turn-down rule), but no capability gap was filed. The Ask Developer line and the gap list disagree again, the drift CARD-663 removed for missing-tool wordings.

## Cause
`reply_rules.ask_developer_ending` treats `_NO_AGENT_COVERS` ("no agent ... covers") as a turn-down that gets the line. `CapabilityDetector.detect` only uses the shared missing-tool matcher (CARD-663), which needs a tool word.

## Change (proposal)
Move the "no agent covers X" turn-down into the shared matcher in `src/domain/capabilities/missing_tool.py` (capability = X). Then the line and the gap come from one decision, and the reply rules can drop their private `_NO_AGENT_COVERS`.

## Proof
- Check (failing first): "No agent covers faxing notes." files a gap with capability "faxing notes", and the existing CARD-615 cases still pass.
- Lean live: the fax ask files a gap.

## Root cause
The Ask Developer line treated "No agent covers X" as a turn-down through a private pattern in `reply_rules` (`_NO_AGENT_COVERS`), but `CapabilityDetector` only used the shared missing-tool matcher, which needs a tool word. So the line was offered and no gap was filed.

## Fix
- "No (other) agent ... covers X" is now a pattern in the shared matcher (`src/domain/capabilities/missing_tool.py`), with X as the capability. A pronoun ("no agent covers that") leaves the capability to the prompt.
- `reply_rules` dropped `_NO_AGENT_COVERS`; the line and the gap now come from one decision.
- One CARD-663 "not a gap" example ("I can't book flights; no agent covers that.") moved: it is a turn-down and now files a gap, by this card's decision.

## Checks
`tests/unit/orchestration/test_card677_no_agent_covers_gap.py` failed first (6 failed) and passes now: "No agent covers faxing notes." files a gap with capability "faxing notes"; questions, conditionals and "the Tutor agent covers that" do not. The CARD-615 Ask Developer tests and the CARD-663 phrasing tests pass.

## Live check (2026-10-09, about 12:45 ET)
Throwaway serve on 127.0.0.1:8770 from a fresh clone of qa ae4b4884, new data folder, Spark vLLM :8006 nemotron-3.5-lightning only (every agent on the default model). Stopped afterwards by exact command line.
- "Print my meeting notes on the office printer." got "No agent covers printing physical documents to an office printer." plus the Ask Developer line, and a gap was filed (capability "printing physical documents to an office printer"). PASS: the line and the gap now agree. (A printer prompt was used instead of fax so the check never looked like an outbound message.)
