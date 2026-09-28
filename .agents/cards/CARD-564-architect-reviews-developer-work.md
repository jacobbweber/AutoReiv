---
id: CARD-564
title: "Architect reviews Developer's work and marks the card Done or Returned"
type: feature
status: Ready
priority: P1
milestone: M25
needs_decision: "D1 Done needs Jacob's approval click or Architect's review is enough; D2 return rounds before escalating to Jacob; D3 does Done trigger a merge request (see Plan and decisions)"
proof:
  journeys: [card-564-architect-reviews-developer-work]
  checks: [tests/unit/skills/test_card564_architect_review.py, tests/unit/skills/test_card564_returned_handoff.py]
branch: feat/card-564-architect-reviews-developer-work
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-28
---

# CARD-564 Architect reviews Developer's work and marks the card Done or Returned

## Intent
M25 slice 3 (`steering/self-development.md`). After CARD-563 Architect can write a Ready card and hand it to Developer,
but an In Review card still waits for Jacob to read the diff himself; Architect's `set_card_status` refuses Done and
Returned with "review is slice 3". Jacob wants Architect to review the work against the card, send it back with specific
notes when it falls short, and mark it Done when it is right, so Jacob's own step is only the merge (D4: Jacob approves every merge).
Lesson from CARD-562/563: every rule is enforced in a tool; skill text only explains it.

## 1. Four Beats
- **Beat 1 - What Jacob means:** Architect checks Developer's In Review work against the card and either sends it back with concrete notes or marks it Done, so Jacob only merges finished, reviewed cards.
- **Beat 2 - What AutoReiv does now:** Architect can read cards and project files and hand off a Ready card, but has no diff or check tools, `set_card_status` refuses Done/Returned for Architect, `hand_off_card` accepts only Ready cards, and Developer cannot get back onto an existing card branch (`git_create_branch` refuses to switch).
- **Beat 3 - What will change:** a `review_card` tool gives Architect the diff, Evidence and a fresh read-only check run for the card branch; Done needs a green check on the current HEAD plus a written review, Returned needs review notes and counts a round; `hand_off_card` takes a Returned card back to Developer, who resumes the card branch, addresses the notes and returns it to In Review.
- **Beat 4 - How we know:** a live journey on a throwaway repo (Architect on Spark, Developer on Nimo) shows one Return with notes, Developer fixing them, then Done with the review on the card and no merge, plus unit tests for every refusal.

## Goal
With a project selected, Jacob opens Architect on an In Review card and says "review CARD-N". Architect reads the diff
against base, the card's acceptance criteria and Evidence, re-runs the project checks read-only, and either:
- marks it **Returned** with specific review notes written on the card (`## Review` section, round number), then, on
  Jacob's word, hands it back to Developer, who resumes the card branch, addresses each note and brings it to In Review again; or
- marks it **Done** with the written review on the card. Nothing is merged or pushed; Jacob merges by hand.
Architect still never edits code, never commits except the card file, never merges or pushes.

## Change
1. **`review_card(card_id)` tool** (new, Architect only; e.g. `src/application/skills/card_review_tools.py`), read-only:
   - Refuses unless: caller is Architect, a project is selected (`selected_or_refuse`), the card is in the project and In Review,
     and the card's branch exists.
   - Returns a review packet it reads itself: card body (Goal, acceptance/Proof, Evidence, earlier `## Review` rounds),
     `git diff base...branch` (stat + patch, size-capped with a note when truncated), `git log base..branch`, working-tree state,
     and a fresh `run_project_checks` result for the branch HEAD (runs only the AGENTS.md `## Checks` commands; records the
     green check for that HEAD in the CARD-562 check record; writes nothing in the project).
   - Checks run against the branch as checked out; if the tree is not on the card branch or is dirty, refuse with what to do
     (Architect cannot switch branches; Developer's last run leaves the card branch checked out).
2. **Architect review in `set_card_status`** (`src/application/skills/card_tools.py`, actor from tool context):
   - Architect may move In Review -> Done and In Review -> Returned (replaces the "review is slice 3" refusal).
   - Both need a `review` argument (non-empty, at least one line per acceptance item is advised, not parsed). The tool writes it
     to a `## Review` section on the card as `### Round N - Done|Returned (date)`; earlier rounds are kept.
   - **Done** requires a green check record for the card branch's current HEAD (from `review_card` or Developer's last run on
     the same HEAD) and a clean tree; otherwise refused with "run review_card first". Done writes the card and commits only the
     card file on the card branch (`docs(card): CARD-N Done`), sets `completed:`, never merges, never pushes.
   - **Returned** requires review notes, increments `review_rounds` and sets `return_reason` (existing domain rules), commits only
     the card file (`docs(card): CARD-N Returned (round N)`). At `review_rounds >= max_review_rounds` (default 3) Architect cannot
     Return again: the tool refuses and tells Architect to ask Jacob (limit per D2).
   - Architect's card commit is done inside the tool, touching only `.agents/cards/`; Architect still has no `git_commit`,
     file write, patch or shell tool (pack guard).
3. **Returned card back to Developer**:
   - `hand_off_card` accepts Ready **or Returned** cards (same one approval click, CARD-563 D1). For Returned it sends
     "Address the review notes on CARD-N and bring it back to In Review." with the card id only; the card is the brief.
   - Developer: `set_card_status` Returned -> In Progress already exists (refused at max rounds). Add a card-branch resume:
     `git_create_branch` (or a small `git_switch_card_branch(card_id)`) switches to the card's recorded existing branch when the
     tree is clean; still never creates or force-moves anything else.
   - Developer's In Review gate is unchanged (card branch, clean tree, green check for HEAD); Evidence is rewritten for the new HEAD
     and the Review rounds stay on the card.
   - Developer `card-intake` / `implement-change` skill text: on a Returned card, read `## Review` and address every note.
4. **Architect skills**: new `review` skill text (read the packet, compare against Goal and Proof, write concrete notes naming
   file and behaviour, Done only when every acceptance item is met). `hand-off` skill mentions Returned cards.
5. **UI**: `review_card` and review status rows render like the CARD-563 outcome card (verdict, round, checks, branch).

## What dies
- "review is slice 3" refusal for Architect in `set_card_status` and the hand-off skill text that mentions it.
- Jacob reading every diff himself before deciding Done/Returned (he still merges by hand and can override any review).

## Proof
- Journey `card-564-architect-reviews-developer-work` (live QA; Architect on the Spark reasoning default, Developer on Nimo
  `qwen3.6:35b-a3b-65k` set only in the throwaway env) on a throwaway copy of a small git repo in the OS temp folder, selected as the active project.
  The fixture has a Ready card whose acceptance needs two things (e.g. `divide()` throws on zero **and** the README documents it):
  1. Architect hands the card to Developer (CARD-563 path); card reaches In Review.
  2. Seeded shortfall: the harness reverts the README part on the card branch with a commit before review (so a Return is deterministic).
  3. "Review CARD-N": `review_card` runs (diff, Evidence, fresh green checks). Architect marks **Returned** with notes naming the README;
     the card shows `## Review` round 1, `review_rounds: 1`, a `docs(card): ... Returned (round 1)` commit touching only the card file.
  4. `set_card_status` Done attempted before any review on a new HEAD is refused (no green check for HEAD).
  5. "Hand it back to Developer": `hand_off_card` on the Returned card; Developer resumes the card branch, fixes the README, reaches In Review again.
  6. "Review CARD-N" again: Architect marks **Done** with a written review; card `status: Done`, `## Review` round 2, commit touches only
     the card file, no merge into base, no remote, clean tree.
  Screenshots: returned review, Developer rework conversation, Done review.
- Checks: unit tests for `review_card` refusals and packet; Done refused without green HEAD / without review / dirty tree; Returned refused
  without notes and at max rounds; Architect commits touch only card files; `hand_off_card` accepts Returned and refuses other statuses;
  Developer resumes an existing card branch only when clean. Pack guard: Architect still has no code-writing, git write, shell tool.

## Plan and decisions
| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Does Architect's Done need Jacob's approval? | A: yes, one approval click on Done (and Returned), as for `hand_off_card`. B: no, Architect's review is enough; Jacob's merge is the gate. | A for now: one click keeps Jacob in the loop while the reviewer is new; slice 4 (approval level) can relax it per project. |
| D2 | How many return rounds before Jacob decides? | A: keep the existing `max_review_rounds` 3 (per card, editable in front matter). B: 1 round, then Jacob. C: no limit. | A: already in the domain rules; at the limit Architect cannot Return again and asks Jacob. |
| D3 | Does Done trigger anything (merge request, push, notification)? | A: nothing; Done only records the review, Jacob merges by hand. B: open a local merge proposal / PR draft. | A: D4 says Jacob approves every merge; a merge request can be its own card with slice 4. |

Build notes: reuse the CARD-562 check record and evidence reader, `selected_or_refuse`, the CARD-563 `hand_off_card` path and
outcome renderer, and the domain `validate_transition` rules (`return_reason`, `review_rounds`, `max_review_rounds`).
Open question for build (technical, not for Jacob): whether `review_card` checks out nothing and requires the card branch to be the
current branch (recommended, simplest and safe) or uses a temporary worktree.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
CARD-564: Architect reviews an In Review card (diff, Evidence, fresh checks) and marks it Done or Returned with notes written on the card; a Returned card goes back to Developer and returns to In Review. Nothing is merged; Jacob merges.
