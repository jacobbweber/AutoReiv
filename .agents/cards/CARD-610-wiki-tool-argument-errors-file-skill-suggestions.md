---
id: CARD-610
title: "Nemotron passes unsupported arguments to wiki tools, and each refusal files a skill suggestion that needs approval"
type: bug
status: In Review
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-610-wiki-args-no-approval-noise]
  checks: [tests/unit/orchestration/test_card610_ace_skips_argument_errors.py, tests/unit/kernel/test_card607_tool_not_offered.py]
branch: feat/card-607-610-tool-noise
log: {minutes: 150, qa_runs: 5, findings: 4}
created: 2026-10-03
related:
  - CARD-523
  - CARD-562
  - CARD-589
  - CARD-605
  - CARD-607
  - CARD-110
---

# CARD-610 Nemotron passes unsupported arguments to wiki tools, and each refusal files a skill suggestion that needs approval

## Problem
In both job live checks on 2026-10-03 (:8770, nemotron-3.5-lightning, "search the wiki ... then summarize" run as a job), the Execute step called a wiki tool with an argument it does not accept, for example `wiki_note_list(limit=...)`. The tool correctly refused ("Unknown: limit. Accepted parameters: category, domain, topic, status, tag, author, pinned, priority. Nothing was run"). Jacob also reported `tag` being passed where it is not accepted. Each refusal then filed a `propose_skill` approval, "Append ACE insight to wiki SOP" (source `online-ace`), on the job's step session. The chat shows an Approve/Reject card and Recent Chats marks it "Needs approval" (CARD-493/608) for what is only tool-call noise. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003c\resumed-done-desktop.png`, `...\ui1003c\recent-chats-after-resume-desktop.png`, `...\ui1003b\job-after-resume-desktop.png` (the same pattern with `wiki_overview` `tool_not_offered`).

## Cause
- The model guesses parameter names (`limit`) the wiki tools never had; the tool schemas sent to it are the source of truth, so the guess is a model or prompt issue, not a missing parameter.
- Online ACE (`record_failed_turn_delta` in `src/application/orchestration/ace_online.py`, called from `agent_kernel.py`) treats any tool error in a skill turn as a lesson and drafts a `propose_skill` HITL approval, including argument refusals ("called with arguments it does not accept", CARD-562) and `tool_not_offered`. Those are already self-correcting: the refusal text tells the model the accepted parameters, and the next call usually succeeds.

## Change
- Online ACE skips tool errors that are argument refusals or `tool_not_offered` (or at most records them as a sidecar note, never an approval). Real tool failures still draft a suggestion.
- Check the wiki skill runbook (`skills/wiki/SKILL.md`) and wiki tool descriptions for wording that invites `limit` (or `tag` where it is not accepted); remove it. Do not add a `limit` parameter just to absorb the guess.

Built (2026-10-03, with CARD-607 on `feat/card-607-610-tool-noise`):
- `is_self_correcting_refusal()` in `tool_registry.py`: a refused call that ran nothing and already told the model the fix (`tool_not_offered:`, "called with arguments it does not accept", "is not authorized for agent", "not found in system registry").
- `ace_online.is_ace_lesson_error()` = not an approval park and not such a refusal. The kernel's `_ace_note_tool` and both filters in `reflect_failed_turn` / `record_failed_turn_delta` use it, so those turns draft nothing; a real failure (timeout, tool error) in the same turn still drafts one `propose_skill`.
- `reply_rules.counts_as_failure` uses the same rule, so a refusal the model recovered from adds no "Note: ... failed" line.
- No runbook wording invited `limit`; the cause is the sibling schemas (`wiki_note_search` has `query`, `limit`, `tags` list; `wiki_note_list` has none of those and a single `tag`). The two descriptions now say so ("no query or limit parameter (use wiki_note_search ...); tag is a single string" / "tags is a list of strings"). No parameter added.

## What dies
"Append ACE insight to wiki SOP" approvals for argument mistakes the tool already corrected.

## Proof
- Journey `card-610-wiki-args-no-approval-noise`: 3 runs of the wiki-search-and-summarize job on nemotron; no `propose_skill` approval from `online-ace` for an argument refusal or `tool_not_offered`; the chat is not marked Needs approval.
- Checks: `record_failed_turn_delta` with an "arguments it does not accept" error or `tool_not_offered` drafts no approval; with a real tool failure it still drafts one (negative assertion).

## Plan and decisions
- Filter in online ACE rather than loosen the tool schemas: refusals already teach the model in-turn, and accepting unknown arguments would hide real mistakes.

## Findings
- (from docs/findings.md 2026-10-03, carded here)
- `UserSkillCatalog.save_skill("wiki", ...)` with a temp `skills_dir` wrote the repo's `platform/skills/wiki/SKILL.md` (it falls back to the platform pack for a platform id). Caught in this card's first test draft and reverted; the test uses a non-platform id. Worth a card: tests or ACE apply on a platform skill id can overwrite a shipped runbook.
- In the Formulate (plan) phase the model still calls tools not offered there (`wiki_template_list`, `system_info`, `platform-health`, a skill id): 2 per job run. They are refused with the new hint and are no longer lessons.
- Rejecting the job's `wiki_note_create` card makes the Execute step retry the create 4-5 times and end asking why it is "rejected without a clear error message"; the job is then marked done although the reply is a question.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| wiki job #1 (search + 600-word summary, Run as a job) | desktop | pass | 2 `tool_not_offered` refused, 0 online-ace approvals; job parked on a real `wiki_note_create` approval (Needs approval is correct there) |
| wiki job #2 | desktop | pass | 2 `tool_not_offered`, 0 argument refusals, 0 approvals left, job done, chat not marked Needs approval |
| wiki job #3 | desktop | pass | same as #2 |
| chat: "Call wiki_note_list(query="garden", limit=3)" | desktop | pass | 1 argument refusal (Unknown: limit, query), model retried with topic; 0 approvals, no failed note, not marked Needs approval |
| chat: "list three notes with wiki_note_list limit=3" | desktop | pass | model used the schema, no refusal |

Live on :8770, nemotron-3.5-lightning, 2026-10-03 10:00-10:10 ET. Unprompted argument refusals did not occur in 3 job runs (earlier runs on qa had `limit`), so the argument-refusal path was forced once by asking for it.

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003d\wiki-job-1..3-chat-desktop.png`, `...\ui1003d\wiki-job-1..3-recent-chats-desktop.png`, `...\ui1003d\wiki-job-5-chat-desktop.png`.

## Release note
A wiki tool call with a wrong argument name no longer files a skill suggestion that needs your approval.
