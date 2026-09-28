---
id: CARD-563
title: "Architect plans cards with Jacob and hands a Ready card to Developer"
type: feature
status: Ready
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-563-architect-plans-and-hands-off]
  checks: [tests/unit/skills/test_card563_hand_off_card.py, tests/unit/skills/test_card563_architect_card_powers.py, tests/unit/agent_packs/test_card563_architect_pack.py]
branch: feat/card-563-architect-plans-and-hands-off
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-28
---

# CARD-563 Architect plans cards with Jacob and hands a Ready card to Developer

## Intent
M25 slice 2 (design: `scratch/m25-design/design-note.md` sections 2, 3 and 6; `steering/self-development.md`).
Jacob wants to think a change through with a strong reasoning model, have it write the card, and then say "go"
so Developer does the card in the active project without Jacob pasting prompts. Slice 1 (CARD-562) made Developer
able to take a Ready card to In Review; this slice adds the Architect that writes Ready cards and starts Developer on one.
Lesson from CARD-562: every rule below is enforced in a tool, and skill text only explains it.

## Goal
With a git repo selected in Projects Studio, Jacob opens Architect, talks through an idea, and Architect writes a
card with status Ready. Jacob says "hand it to Developer"; Architect calls one tool, Developer runs
"Work card CARD-N to In Review" in the active project (Jacob approves Developer's prompts as today), and when it
finishes Architect's chat shows the outcome read from git and the card file: branch, commits, card status, green checks.
Architect never edits code, runs checks or commits, and never sets Done or Returned (review is slice 3).

## Change
1. **Architect platform pack** `platform-packs/architect/pack.json` (+ skills under `platform-packs/architect/skills/`).
   - `"model": "default"`: runs on the global reasoning default (Spark vLLM). No new purpose, no override.
   - Skills: `project-orientation` (shared, read-only), `brainstorm` (ask one question at a time, 2-3 options with a
     recommendation, stop when the change fits one card), `card-writing` (shared with Developer), `hand-off` (new).
   - Tools: read-only project tools (`active_project_info`, `read_project_file`, `search_project`, `list_project_dir`,
     `read_steering`), card tools (`list_cards`, `read_card`, `write_card`, `set_card_status`), and `hand_off_card`.
     No `write_project_file`, `patch_project_file`, `run_project_checks`, `git_*` writes, shell or code runner,
     and no generic `handoff_to_agent`/`lookup_agents` for card work.
   - Seed/migration so an existing install gets the Architect once (same pattern as the CARD-562 migrations), visible in chat.
2. **Architect card powers, enforced in `CardTools`** (`src/application/skills/card_tools.py`, actor from tool context):
   - `write_card`: Architect may create cards as Proposed or Ready and edit any card that is not In Progress / In Review.
     Developer stays Proposed-only (CARD-562). New cards still get the next CARD-N id.
   - `set_card_status` for Architect: Discuss/Proposed -> Ready and Ready -> Proposed only. Done and Returned are refused
     with "review is slice 3" until CARD-564 (slice 3) lands.
3. **`hand_off_card(card_id)` tool** (new, e.g. `src/application/skills/card_handoff_tools.py`), the only way Architect starts Developer:
   - Refuses when: no project is selected (same `selected_or_refuse` guard); the card is not in the active project;
     its status is not Ready; the caller is not Architect; another card is already In Progress in this project;
     Developer is missing or disabled. Each refusal says what to do next.
   - Starts Developer with the fixed directive "Work card CARD-N to In Review in the active project." and the card id only
     (the card is the brief; no Architect transcript), reusing `HandoffEngine` / `handoff_to_agent` plumbing with a
     turn budget large enough for a card (slice-1 runs needed about 15 tool calls).
   - Developer's HITL prompts reach Jacob as they do for a direct Developer chat (existing approval_required path).
   - When Developer stops, the tool returns an outcome it reads itself, not the model's claim: card status from the
     file, branch, `git log base..HEAD`, the card's tool-written Evidence block, and a link/id to the Developer conversation.
4. **Result visible to Jacob**: the Developer run is a normal Developer conversation Jacob can open (not a hidden child
   session), and Architect's chat shows the outcome block. Exact shape per D2.
5. Tools Studio / Ask Developer stay paused (no change here).

## What dies
- Jacob hand-starting Developer with a pasted "Work card CARD-N" prompt for Architect-planned cards (still possible by hand).
- Nothing is deleted. Generic `handoff_to_agent` stays for other agents; Architect is simply not granted it.

## Proof
- Journey `card-563-architect-plans-and-hands-off` (live QA, Nimo for Developer, Spark reasoning default for Architect)
  on a throwaway copy of a small git repo in the OS temp folder (same fixture style as card-562), selected as the active project:
  1. Architect's tools are the planning set: no write/patch/check/commit/shell tools (API check).
  2. Jacob: "divide() should refuse division by zero; write a card". Architect asks at most one question, then files
     `CARD-<next>-...md` with status Ready; no code or git change.
  3. Architect tries `set_card_status` Done on CARD-1 and is refused (review is slice 3).
  4. Jacob: "hand it to Developer". `hand_off_card` starts Developer; the harness approves Developer's prompts.
     Asserts: a card branch, a fix commit plus `docs(card): CARD-N In Review`, card In Review with the tool-written
     Evidence, clean tree, no remote; Architect's chat shows the outcome block with that branch and status;
     the Developer conversation is listed in Developer's chats.
  5. `hand_off_card` on a Proposed card is refused; with the project cleared it is refused with the no-project message.
  Tool call order is logged in the summary (as in card-562).
- Checks: unit tests for every `hand_off_card` refusal and the success path (fake Developer run), Architect card powers
  (Ready allowed, Done/Returned refused, Developer still Proposed-only), and a pack guard (Architect has no code-writing,
  check, commit, shell or generic handoff tool; model is `default`).

## Plan and decisions
| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Does every hand-off need Jacob's approval? | A: yes, `hand_off_card` is an approval prompt each time. B: no, Jacob's "hand it to Developer" is enough. | A for now: one click, and Developer's own edits already ask. Slice 4 (approval level) can relax it per project. |
| D2 | Where does Developer's work run and show? | A: Architect waits; Developer runs as a nested hand-off and Architect's chat shows the outcome, with the Developer conversation openable. B: Developer runs in its own background job; Architect's chat gets a notice when done. | A: reuses the existing handoff and approval path, smallest to build; B can follow if long cards block the chat. |
| D3 | Tool building (Ask Developer, Tools Studio): here, or a separate Toolsmith agent? | A: restore on Developer in this card. B: separate follow-up card with a Toolsmith agent after slice 3. C: leave parked. | B: keeps this card small and Developer's toolset clean (design D5: revisit after slice 3). Not in this card. |

**Decided by Jacob 2026-09-28 ("build"): D1 A, D2 A, D3 B.** Every `hand_off_card` is one approval click; Architect's
chat waits while Developer runs inside the hand-off and the Developer conversation can be opened; tool building is a
separate card after slice 3 (logged in `docs/findings.md`).

Build notes: reuse `HandoffEngine` (child max turns via `bound_child_max_turns`), `selected_or_refuse`, the CARD-562
green-check record and evidence reader; the argument-mismatch error from CARD-562 covers new tools automatically.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
CARD-563: new Architect agent (reasoning model) brainstorms with Jacob, writes Ready cards and hands one to Developer with `hand_off_card`; the outcome (branch, commits, card status) shows back in Architect's chat.
