---
id: CARD-562
title: "Developer works one card to In Review on the active project"
type: feature
status: Ready
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-562-developer-one-card-to-in-review]
  checks: [tests/unit/skills/test_card_tools.py, tests/unit/skills/test_git_tools.py, tests/unit/agent_packs, cards-folder guard, ADR-0061 binding guard]
branch: feat/card-562-developer-one-card-to-in-review
absorbs: [CARD-558, CARD-540, CARD-541, CARD-557 (scratch-file half)]
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-27
---

# CARD-562 Developer works one card to In Review on the active project

## Intent
M25 slice 1 (design: `scratch/m25-design/design-note.md`, `skill-map.md`, `template-review.md`).
Jacob wants a general Developer agent that works on any repo he sets as the active project,
with AutoReiv (a separate clone with its own dev port) as the first one. This slice makes the
Developer able to take one Ready card through branch → plan → edit → checks → commit → In Review
by itself, and to file gaps it finds as Proposed cards. Decisions settled 2026-09-27:
D1 cards live in `.agents/cards/` for every project; D2 Developer files Proposed cards;
D3 the Developer model is pinned via Agent Studio override (Ollama coder model on Nimo), with no new purpose;
D4 Jacob approves every merge; D5 self-extension skills are parked.

## Goal
With a git repo selected as the active project, Jacob tells Developer "work CARD-N".
Developer creates the card branch, writes its plan into the card, edits files, runs the
project's `AGENTS.md ## Checks` commands until green, commits, writes evidence and sets the card
to In Review. Push and merge are never done by Developer.

## Change
1. **Cards folder move (D1).**
   - `git mv docs/cards/*.md .agents/cards/` in AutoReiv.
   - Card tools (`src/application/skills/card_tools.py`) default to `.agents/cards`, with `docs/cards` and `.github/cards` kept as read-only fallbacks.
   - Update `.agents/skills/card` (SKILL.md, `new_card.py`, `list_card_status.py`), `AGENTS.md`, `.agents/rules`, `.agents/skills/adr-manager`, `.github/PULL_REQUEST_TEMPLATE.md`, `src/application/sdlc/paths.py` (checkout detection), `src/application/orchestration/repo_code_grounding.py`, live-qa/preflight card lookups, steering and roadmap links, the tutor flashcard-turn link and the guard tests.
   - Leave `CHANGELOG.md`, `docs/archive_artifacts/` and ADR history text as they are (historical).
2. **Templates.** Rewrite `templates/sdlc-project/` per `template-review.md`:
   - New short `AGENTS.md` contract with `## Project/Run/Checks/Branches/Cards/Rules/Don't touch` headings.
   - One `.agents/cards/`, `docs/adr/` and a new card template.
   - Cut the steering placeholders, the SDD trio, `.github/cards`, CONTRIBUTING, and the Conductor/Coding/"Jacob"/"AutoReiv" wording.
   - Update the manifest.
3. **Tools (each registered and bound to exactly one skill, ADR-0061; ≤8 tools per skill).**
   - `git_create_branch` (from the `## Branches` base; refuses a dirty tree; no force).
   - `run_project_checks` (runs only `AGENTS.md ## Checks` commands in the active project; timeout; exit code + output tail).
   - `search_project` (grep).
   - `patch_project_file` (exact-string replace).
   - `active_project_info` (read-only).
   - Bind the orphaned `git_status/git_diff/git_branch/git_commit` and `list_cards/read_card/write_card/set_card_status`.
4. **Skills (platform, one SKILL.md each, no project facts):** project-orientation, card-intake, card-writing (Developer files `status: Proposed` only), plan-change, implement-change, write-tests, debug, run-checks, git-workflow, code-review (self-review use), codebase-audit.
5. **Developer pack.**
   - `allowed_skill` = the skills above.
   - Remove `coding`, `sdlc-engineering`, `capability-authoring`, `mcp-engineering`, `native-tool-engineering`, `build-agent-pack` and `proposals`.
   - Clean up pack fields (CARD-540/541).
   - Sync the AppData pack.
6. **No active project (CARD-558):** project/git/card/check tools return a clear "select a project in Projects Studio" error instead of defaulting to the AutoReiv checkout.
7. **Scratch files (CARD-557 scratch half):** agent scratch scripts go to the OS temp dir, never the project checkout.

## What dies
- `sdlc-engineering` and `coding` skills.
- The Developer ticks on the self-extension skills (parked, not deleted).
- `docs/cards/` as the card home.
- The template's SDD trio and steering placeholders.
- The stale `--nightly` / self-copy text in `steering/self-development.md` (points to the design note).
- `status: Proposed` is added to the status list in the card skill for agent-filed cards.

## Proof
- Journey `card-562-developer-one-card-to-in-review`:
  1. Create a throwaway git fixture repo from the new template (with a one-line `## Checks` fast command) and set it as the active project.
  2. Write a tiny Ready card in its `.agents/cards/`.
  3. Ask Developer to work the card.
  4. Assert: the branch exists, the card has Plan + Evidence, the checks ran green, there is exactly one new commit, the card status is In Review, and nothing was pushed.
  5. Ask Developer for a quick audit and assert that one `status: Proposed` card was filed.
  6. With no active project, a tool call returns the clear error.
- Checks:
  - Guard: no tracked `docs/cards/*.md` remain and card tools write to `.agents/cards`.
  - Guard: every tool bound to a Developer skill is registered, and no skill has more than 8 tools.
  - Guard: the template manifest matches the files.
  - Fast tier green.

## Plan and decisions
- Order: folder move first (its own commit, paths only), then templates, tools, skills and pack, then the journey.
- Developer model pin is an Agent Studio setting done by Jacob; the journey can run on any configured model.
- Approval level (unattended) is slice 4; this card still asks on edits in `ask` mode.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Changed: cards now live in `.agents/cards/`. Added: the Developer agent can take a card to In Review on the active project (branch, plan, edit, checks, commit) and file Proposed cards.
