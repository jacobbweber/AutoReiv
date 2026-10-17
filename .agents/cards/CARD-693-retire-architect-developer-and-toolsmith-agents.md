---
id: CARD-693
title: "Retire Architect, Developer, and Toolsmith agents into cohesive Agora skill folders on AutoReiv"
type: feature
status: Done
priority: P1
milestone: M28
needs_decision: none
proof:
  journeys: [card-693-retire-architect-developer-and-toolsmith-agents]
  checks: [tests/unit/architecture/test_card693_agent_skill_consolidation.py, tests/unit/frontend/card_693_agent_consolidation.test.js]
branch: feat/card-693-retire-architect-developer-and-toolsmith-agents
log: {minutes: 35, qa_runs: 2, findings: 0}
created: 2026-10-16
completed: 2026-10-16
---

# CARD-693 Retire Architect, Developer, and Toolsmith agents into cohesive Agora skill folders on AutoReiv

## Intent
Simplify the shipped agent roster to **`AutoReiv`**, **`Tutor`**, and **`Direct`** (`ADR-0066`) by retiring the separate `Toolsmith`, `Architect`, and `Developer` agents and consolidating their 17 fragmented micro-skills into 3 cohesive Agora skill folders (`capability-authoring/`, `project-cards/`, `software-development/`) with `references/*.md` guides on `AutoReiv` that mount their tools on demand via `skill_view`.

## Goal
- `platform/agents/` ships only 3 agents: `autoreiv.md`, `tutor.md`, and `direct.md`.
- `platform/skills/capability-authoring/`, `platform/skills/project-cards/`, and `platform/skills/software-development/` bundle `SKILL.md` + `references/*.md` and replace the 17 fragmented SDLC/tool micro-skills on `AutoReiv`.
- `project-cards` and `software-development` appear in `AutoReiv`'s progressive skill index and mount their tools on demand when `AutoReiv` calls `skill_view("project-cards")` or `skill_view("software-development")`, keeping normal everyday chat turns lean.
- `card_tools.py` and `card_review_tools.py` allow `AutoReiv` to plan, work, and review cards end-to-end without the artificial `architect` vs `developer` actor split while preserving every mechanical git/check guardrail.

## Change
- `docs/adr/0066-consolidate-architect-developer-and-toolsmith-into-agora-skill-folders-on-autoreiv.md`:
  - Record `ADR-0066`.
- `platform/agents/`:
  - Remove `architect.md`, `developer.md`, and `toolsmith.md`.
  - Update `autoreiv.md` to include `capability-authoring`, `project-cards`, and `software-development` (removing `agent-authoring` and specialist handoff refusals).
- `platform/skills/`:
  - Create `project-cards/` (`SKILL.md` + `references/card-rubric.md`) and `software-development/` (`SKILL.md` + `references/workflow.md`), update `capability-authoring/` (`SKILL.md` + `references/authoring-guide.md`), and remove the 17 retired micro-skill directories.
- `src/infrastructure/content/store.py`:
  - Add `CONSOLIDATED_SKILL_ALIASES` so legacy skill references map cleanly to `capability-authoring`, `project-cards`, or `software-development`.
- `src/application/agent_skills/allowed_tools.py`:
  - Add `ON_DEMAND_SHIPPED_SKILLS = frozenset({"project-cards", "software-development"})` so `pinned_skills(agent)` keeps `AutoReiv`'s default turn toolset small and mounts `project-cards` / `software-development` tools as soon as `skill_view` opens them in the session.
- `src/application/agent_skills/schema.py`, `src/web/static/modules/studios/agent_picker.js`, `src/web/static/modules/studios/projects.js`:
  - Update `CHAT_SHOWN_BY_ID` to `{"autoreiv", "direct", "tutor"}` and move `architect`, `developer`, and `toolsmith` into `CHAT_HIDDEN_BY_ID` and retired studio picker filters; route Projects Studio chat selection to `autoreiv`.
- `src/application/skills/card_tools.py` & `src/application/skills/card_review_tools.py`:
  - Allow `autoreiv` to write `Proposed`/`Ready` cards, transition cards through `In Progress -> In Review` (enforcing `_in_review_refusal`), and run `review_card` / `finish_review`.

## What dies
- `platform/agents/architect.md`, `platform/agents/developer.md`, and `platform/agents/toolsmith.md`.
- 17 fragmented micro-skill folders under `platform/skills/`: `agent-authoring`, `native-tool-engineering`, `project-orientation`, `brainstorm`, `card-intake`, `card-writing`, `plan-change`, `hand-off`, `review`, `implement-change`, `write-tests`, `debug`, `run-checks`, `git-workflow`, `code-review`, `codebase-audit`, `journey-qa`.
- Actor-only refusal split between `architect` and `developer` when `AutoReiv` drives card planning, building, and review.

## Proof
- Journey `card-693-retire-architect-developer-and-toolsmith-agents`:
  1. Open Chat and verify `/api/agents` and `#agentSelect` expose the 3-agent shipped roster (`AutoReiv`, `Tutor`, `Direct`) with `architect`, `developer`, and `toolsmith` absent.
  2. Open **Capabilities** (`#view-capabilities`) and verify the Agora skill folders `capability-authoring/`, `project-cards/`, and `software-development/` appear in the tree and none of the 17 retired micro-skills remain.
  3. In Chat on `AutoReiv`, call `skill_view(skill_id="project-cards", reference="card-rubric.md")` and verify `AutoReiv` loads the progressive reference and mounts `project-cards` tools on demand.
- Checks:
  - `tests/unit/architecture/test_card693_agent_skill_consolidation.py` (`pytest.mark.guard`)
  - `tests/unit/frontend/card_693_agent_consolidation.test.js` (Vitest)

## Plan and decisions
- **Decision D1 (Product & Architecture — Approved as Option 1)**: Retire `Toolsmith`, `Architect`, and `Developer` into 3 cohesive Agora skill folders (`capability-authoring/`, `project-cards/`, `software-development/`) on `AutoReiv`, leaving `AutoReiv`, `Tutor`, and `Direct` as the 3 shipped agents.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-693-retire-architect-developer-and-toolsmith-agents` | desktop | PASS | 3/3 steps pass; 3-agent roster (`autoreiv`, `direct`, `tutor`), consolidated Agora skill folders in `#view-capabilities`, and live on-demand `skill_view(skill_id="project-cards", reference="card-rubric.md")` verified |
| `card-693-retire-architect-developer-and-toolsmith-agents` | phone | PASS | 3/3 steps pass; 3-agent roster, consolidated Agora skill folders in `#view-capabilities`, and live on-demand `skill_view` verified |

Screenshots:
- `/tmp/autoreiv-qa/card-693/card-693-retire-architect-developer-and-toolsmith-agents-desktop-01-verify-api-and-chat-picker-expose-the-3-agent-sh.png`
- `/tmp/autoreiv-qa/card-693/card-693-retire-architect-developer-and-toolsmith-agents-desktop-02-verify-capabilities-studio-tree-shows-consolidat.png`
- `/tmp/autoreiv-qa/card-693/card-693-retire-architect-developer-and-toolsmith-agents-desktop-03-in-chat-autoreiv-opens-project-cards-card-rubric.png`

## Release note
- Simplified the shipped agent roster to `AutoReiv`, `Tutor`, and `Direct` by retiring `Architect`, `Developer`, and `Toolsmith` into cohesive Agora skill folders (`capability-authoring`, `project-cards`, `software-development`) on `AutoReiv` with on-demand `skill_view` tool mounting [CARD-693].
