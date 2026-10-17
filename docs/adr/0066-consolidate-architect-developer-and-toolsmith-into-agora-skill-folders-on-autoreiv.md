# ADR-0066: Consolidate Architect, Developer, and Toolsmith into Agora Skill Folders on AutoReiv

> **Date**: 2026-10-16  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, AutoReiv Agent  
> **Guard Test**: `tests/unit/architecture/test_card693_agent_skill_consolidation.py`

---

## 1. Context & Problem Statement
Before Agora skill folders (`ADR-0065`) and progressive on-demand session tool mounting (`CARD-688`, `CARD-691`), AutoReiv split tool building and project development across three separate specialist agents (`Toolsmith`, `Architect`, and `Developer`) and 16 granular micro-skills:
1. **`Toolsmith` (`platform/agents/toolsmith.md`)** existed solely to call `register_native_tool` via `native-tool-engineering`. Now that `AutoReiv` writes `skills/<id>/SKILL.md`, `references/*.md`, and `tools/*.py` inline and auto-discovers user skills via `user:*`, switching to a separate `Toolsmith` chat session is redundant.
2. **`Architect` + `Developer` (`platform/agents/architect.md`, `platform/agents/developer.md`)** split a single software-development workflow across two agents connected by `hand_off_card` and actor-ID refusals in `card_tools.py` (`actor == "architect"` vs `actor == "developer"`). In practice, one assistant plans, builds, and verifies changes on the active project, and progressive `skill_view` mounting means `AutoReiv` can carry project-planning and coding skills without bloating normal chat turns.

---

## 2. Decision Drivers
* Eliminate multi-agent ping-pong (`Architect <-> Developer` and `AutoReiv -> Toolsmith`) in Chat.
* Keep the shipped agent roster focused on distinct operator modes (`AutoReiv`, `Tutor`, `Direct`).
* Group the fragmented SDLC and capability-authoring micro-skills into cohesive Agora skill folders (`SKILL.md` + `references/*.md`) that mount on demand when `AutoReiv` calls `skill_view`.
* Preserve every mechanical safety gate in `card_tools.py`, `card_review_tools.py`, and `git_tools.py` (active Projects Studio repo jail, branch-first rule, protected-branch commit refusal, and green `run_project_checks` required before `In Review`).

---

## 3. Considered Options
* **Option 1 (Chosen)**: Retire `Toolsmith`, `Architect`, and `Developer` from the shipped agent roster (leaving `AutoReiv`, `Tutor`, `Direct`) and consolidate their capabilities into 3 Agora skill folders on `AutoReiv` (`capability-authoring/`, `project-cards/`, `software-development/`) with `references/*.md` guides and on-demand session tool mounting.
* **Option 2**: Retire `Toolsmith`, `Architect`, and `Developer`, but keep all ~16 granular SDLC micro-skills in `platform/skills/`.
* **Option 3**: Keep a 4-agent roster (`AutoReiv`, `Developer`, `Tutor`, `Direct`), merging `Architect` into `Developer` and retiring only `Toolsmith`.

---

## 4. Decision Outcome
Chosen option: **Option 1**, because:
1. **3-Agent Shipped Roster (`AutoReiv`, `Tutor`, `Direct`)**:
   - `platform/agents/` ships only `autoreiv.md`, `tutor.md`, and `direct.md`.
   - `CHAT_SHOWN_BY_ID` is `frozenset({"autoreiv", "direct", "tutor"})`; `architect`, `developer`, and `toolsmith` are retired into `CHAT_HIDDEN_BY_ID`.
2. **3 Cohesive Agora Skill Folders on `AutoReiv`**:
   - **`platform/skills/capability-authoring/`** (`SKILL.md` + `references/authoring-guide.md`): `write_skill_file`, `skill_view`, `list_available_skills_and_tools` (consolidates `agent-authoring` and `capability-authoring`, retiring `native-tool-engineering`).
   - **`platform/skills/project-cards/`** (`SKILL.md` + `references/card-rubric.md`): `active_project_info`, `list_cards`, `read_card`, `write_card`, `set_card_status`, `review_card`, `finish_review` (consolidates `project-orientation`, `brainstorm`, `card-intake`, `card-writing`, `plan-change`, `review`, `hand-off`).
   - **`platform/skills/software-development/`** (`SKILL.md` + `references/workflow.md`): `read_project_file`, `write_project_file`, `patch_project_file`, `list_project_dir`, `search_project`, `run_project_checks`, `git_status`, `git_diff`, `git_branch`, `git_create_branch`, `git_commit`, `run_journey` (consolidates `implement-change`, `write-tests`, `debug`, `run-checks`, `git-workflow`, `code-review`, `codebase-audit`, `journey-qa`).
3. **Progressive On-Demand Mounting (`ON_DEMAND_SHIPPED_SKILLS`)**:
   - `project-cards` and `software-development` are declared in `platform/agents/autoreiv.md` (`skills:`) and listed in `AutoReiv`'s progressive skill index (`render_skill_index`), while their tools stay unmounted on ordinary chat turns until `AutoReiv` opens `skill_view("project-cards")` or `skill_view("software-development")` in the session.
4. **Tool-Enforced Mechanical Guardrails Without Actor Split**:
   - `card_tools.py` and `card_review_tools.py` allow `AutoReiv` to plan, transition, and review cards end-to-end while enforcing the exact same mechanical checks (`set_card_status("In Review")` requires a card branch, clean git tree, and green `run_project_checks` for `HEAD`).
