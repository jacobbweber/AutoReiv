---
id: CARD-566
title: "hand_off_card follows autorun like every other tool"
type: bug
status: Done
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-566-hand-off-follows-autorun]
  checks: [tests/unit/agent_packs/test_card566_hand_off_follows_autorun.py, tests/unit/skills/test_card566_git_commit_paths_string.py, tests/unit/kernel/test_card562_project_core_tools.py]
branch: fix/card-566-hand-off-follows-autorun
log: {minutes: 55, qa_runs: 3, findings: 2}
created: 2026-09-28
completed: 2026-09-28
---

# CARD-566 hand_off_card follows autorun like every other tool

## Problem
With autorun ticked (chat approval mode "run", or a routine), every tool runs without asking except `hand_off_card`:
Architect's hand-off to Developer still shows an approval card. Jacob wants one rule for all tools.

## Cause
CARD-563 D1 (A: "every hand-off is one approval click") put `hand_off_card` in `ALWAYS_CONFIRM_TOOLS`
(src/application/safety/tool_policy_gate.py), which parks it even in run mode and even when it is in the operator's safe_tools.

## Change
Decision (Jacob, 2026-09-28): reverses CARD-563 D1. `hand_off_card` follows the approval mode like every other tool:
autorun on (chat or routine) = no prompt; autorun off = it still asks once (it stays a high-risk tool).
- Drop `ALWAYS_CONFIRM_TOOLS` (hand_off_card was its only member) and its two uses in tool_policy_gate.py.
- Update the hitl_engine.py comment, card_handoff_tools.py docstring, Architect pack text and hand-off skill text.
- Update the CARD-563/564 tests that assumed always-ask.

## What dies
`ALWAYS_CONFIRM_TOOLS` and the "hand-off asks even in run mode" rule (CARD-563 D1 A).

## Proof
- Journey `card-566-hand-off-follows-autorun`: throwaway repo with a Ready CARD-3; Architect chat with autorun ticked;
  "Hand CARD-3 to Developer" runs Developer to In Review on the card branch with zero approval prompts.
- Checks: `test_card566_hand_off_follows_autorun.py`: run mode does not park hand_off_card (failing first); ask mode parks it
  once; it is still REQUIRE_CONFIRM by default (negative: never ALLOW without run mode).

## Plan and decisions
- D1 (Jacob 2026-09-28): hand_off_card obeys autorun; supersedes CARD-563 D1.
- Developer inside the hand-off already inherits the approval mode (run passes through), so autorun covers its edits too.

## Findings
- (fixed) F1 live run 1: Developer sent git_commit paths as a JSON string ('["calc.js", "calc.test.js"]'); the tool iterated
  the string and git failed with "pathspec '['". git_commit now accepts a JSON string, a comma list or one path
  (git_tools.py `_path_list`, test_card566_git_commit_paths_string.py).
- (fixed) F2 live run 2: the hand-off brief ("Work card CARD-3 to In Review ...") did not mount git_commit or git_create_branch
  within the 15-tool cap (word-overlap ranking), so Developer said it had no git_commit and stopped uncommitted.
  New CARD_WORK_TOOLS (read_card, git_create_branch, patch_project_file, run_project_checks, git_commit, set_card_status)
  stay mounted like PROJECT_CORE_TOOLS (agent_kernel.py; test in test_card562_project_core_tools.py).
- Autorun itself held in all 3 runs: 0 approval prompts, 0 parked rows.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-566-hand-off-follows-autorun | desktop | FAIL (run 1) | 0 prompts; Developer stopped at git_commit (F1) |
| card-566-hand-off-follows-autorun | desktop | FAIL (run 2) | 0 prompts; Developer said it had no git_commit (F2) |
| card-566-hand-off-follows-autorun | desktop | PASS (run 3) | 1.8 min, 0 prompts, 0 parked rows; fix + docs(card) In Review commits on card/3-divide-refuses-zero, tests pass, clean tree |

Checks: test_card566 gate (3, 2 failing first), git_commit paths (4, 3 failing first), card-work mount (2 new); full not-slow suite
2162 passed, 3 pre-existing card354 failures; fast preflight GREEN.

## Test it (Jacob)
1. Open an Architect chat on a project with a Ready card; open Options and tick Auto-run.
2. Say "Hand CARD-N to Developer." Expect no approval card: Developer works it to In Review and the outcome card shows.
3. Untick Auto-run and hand another Ready card: expect exactly one approval card for the hand-off.

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-566\...`

## Release note
CARD-566: handing a card to Developer follows autorun like every other tool (no prompt with autorun on; one prompt with it off). Reverses CARD-563 D1.
