# [CARD-376] Audit and Clean Platform Skills and Tools

> **Status**: Done  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:refactor`, `skills`, `tools`, `hygiene`, `architecture`

---

## 1. Why / Intent
Systematically audit all platform skills (`platform-packs/autoreiv/skills/` and bundled seeds) and tool definitions (`src/application/skills/`, `src/infrastructure/agents/registry.py`). Determine which tools and skills are actively utilized, verify their compliance with the Single-Brain / Autonomic OS model (ADR-0054) and the Rule of 7 tool entropy ceiling, and clean up vestigial, dead, or unhooked tools and runbooks left behind by architectural evolutions.

---

## 2. Three Beats

### Beat 1: What Jacob Means
Jacob wants to know if the skills and tools currently installed in AutoReiv actually make sense for the system today, whether they are hooked up and functional, and whether obsolete, leftover, or unvalidated tools (e.g., retired fleet or mock tools) are cluttering the codebase and prompt context. Anything unnecessary or disconnected should be pruned or cleanly consolidated.

### Beat 2: What AutoReiv Does Now
- `src/infrastructure/agents/registry.py` bootstraps dozens of tool groups into `ScopedToolRegistry`.
- `platform-packs/autoreiv/skills/` contains 11 skill runbooks, and `src/infrastructure/skills/seeds/` contains bundled skill seeds.
- Some tools in `src/application/skills/` (such as `opentofu_tools.py` from the deprecated Homelab fleet) may linger unhooked or partially wired, consuming maintenance overhead and potential context tax if referenced.
- There has not been an audit verifying that every tool registered on `master_tool_registry` has active tests, valid schema parameters, and attribution to an active skill.

### Beat 3: What Will Change
- Build an automated tool and skill inventory test/script that inspects every registered tool in `ScopedToolRegistry` and every `SKILL.md`.
- Cross-reference every tool against:
  1. Active agent and skill runbook bindings.
  2. Test suite coverage.
  3. Deprecated architecture references (e.g. `opentofu`, retired personas).
- Identify unhooked, dead, or vestigial tools and skills.
- Prune unreferenced or deprecated tools, update registrations in `registry.py`, and ensure all remaining tools have valid docstrings, typed parameter schemas, and $\le 7$ tools per skill runbook.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Comprehensive inventory generated of all registered tools and platform skills.
- [x] Every active tool is verified to be hooked up, callable, and tested.
- [x] Dead, vestigial, or unhooked tools (e.g. deprecated `opentofu_tools.py`, `check_port`, `delegate_to_fleet_agent`, `lookup_homelab_docs`) are pruned or cleanly retired.
- [x] All active skill runbooks under `platform-packs/autoreiv/skills/` and seeds comply with the Matt Pocock progressive disclosure standard and $\le 7$ tools ceiling (`autoreiv lint-skills`).
- [x] Automated regression test suite validates the active tool roster and prevents accidental re-registration of pruned tools (`test_tool_and_skill_audit.py`).
- [x] Zero lint errors via `ruff check src tests` and `npm run lint:frontend`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to core platform capabilities (wiki, shell, projects, git, factory, diagnostics).
- Single isolated `feat/card-376-audit-clean-skills-tools` branch cut from `qa` upon Jacob's `build` approval.
