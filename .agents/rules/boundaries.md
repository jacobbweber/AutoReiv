---
trigger: always_on
description: Where data and tooling may live, and how tools reach agents. Every line is checkable.
---
# Boundaries

## Data
- Live data (user agent/skill copies, `*.db`, wiki, attachments, `autoreiv.db`) lives only under the data root: `AUTOREIV_DATA_DIR`, else `%LOCALAPPDATA%\AutoReiv\`. Resolve it with `DataDirResolver().resolve()` (`src/infrastructure/data/resolver.py`); never hard-code a path.
- `ensure_live_data_root` must keep refusing a live root inside the checkout.
- `platform/` (shipped agents and skills) is read in place and never written at runtime; Studio saves write user copies to the data dir (ADR-0062).
- Temporary files go only in `scratch/` (gitignored except `.gitkeep`).
- A `*.db` or live pack in the checkout outside `scratch/` is a bug: fix the writer, delete the leftover (never AppData), add a guard test.
- Check: `git status --porcelain` shows no `*.db`, data `agents/`/`skills/` or wiki folders.

## .agents is not product
- `.agents/` is coding-agent tooling. Never seed it to user data or mount it in Chat.
- Product skills are `SKILL.md` files under `platform/skills/` and user-data `skills/<id>/`. Agents are `platform/agents/<id>.md` and user-data `agents/<id>.md`. No third system, no packs (guard: `tests/unit/agents/test_card570_no_packs.py`).

## Formats and skills (ADR-0062)
- No old-format readers before 1.0: a format change ships with a data wipe or Use shipped version; code never reads the previous layout.
- A skill is a job that groups several tools, not one skill per tool. Short instructions are fine for obvious tools. The skill's `tools:` list shapes what the model sees; the permission check and the tools themselves are the safety.

## Capability scoping (ADR-0061)
- `resolve_allowed_tools(agent)` in `src/application/agent_skills/allowed_tools.py` is the only code that decides an agent's tools: `REQUIRED_PLATFORM_TOOLS` plus the `tools:` of its ticked skills (winning SKILL.md). Guard: `tests/unit/architecture/test_card539_single_allowed_tools.py`.
- No side paths: no per-agent tool lists or grants, no profile flags that add tools, no `agent.id == "..."` special cases, no mounting unticked skills.
- Selection only narrows. An empty selection never falls back to the full list.
- Every tool ships bound to a skill with a `SKILL.md`.
- Code that builds or attaches tools creates a pending approval; only Jacob's acceptance widens permission.
- Prompts never tell an agent to refuse; they hand off, or offer Ask Developer.
