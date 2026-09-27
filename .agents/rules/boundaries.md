---
trigger: always_on
description: Where data and tooling may live, and how tools reach agents. Every line is checkable.
---
# Boundaries

## Data
- Live data (packs, `*.db`, wiki, attachments, `autoreiv.db`) lives only under the data root: `AUTOREIV_DATA_DIR`, else `%LOCALAPPDATA%\AutoReiv\`. Resolve it with `DataDirResolver().resolve()` (`src/infrastructure/data/resolver.py`); never hard-code a path.
- `ensure_live_data_root` must keep refusing a live root inside the checkout.
- `platform-packs/` is seed only; runtime reads and writes user data.
- Temporary files go only in `scratch/` (gitignored except `.gitkeep`).
- A `*.db` or live pack in the checkout outside `scratch/` is a bug: fix the writer, delete the leftover (never AppData), add a guard test.
- Check: `git status --porcelain` shows no `*.db`, `packs/` or wiki folders.

## .agents is not product
- `.agents/` is coding-agent tooling. Never seed it to user data or mount it in Chat.
- Product skills are `SKILL.md` files under `platform-packs/` and user-data `packs/<id>/skills/`. No third skill system.

## Capability scoping (ADR-0061)
- `resolve_allowed_tools(agent)` in `src/application/agent_packs/allowed_tools.py` is the only code that decides an agent's tools: `REQUIRED_PLATFORM_TOOLS` plus tools of its ticked skills. Guard: `tests/unit/architecture/test_card539_single_allowed_tools.py`.
- No side paths: no per-agent tool lists or grants, no profile flags that add tools, no `agent.id == "..."` special cases, no mounting unticked skills.
- Selection only narrows. An empty selection never falls back to the full list.
- Every tool ships bound to a skill with a `SKILL.md`.
- Code that builds or attaches tools creates a pending approval; only Jacob's acceptance widens permission.
- Prompts never tell an agent to refuse; they hand off, or offer Ask Developer.
