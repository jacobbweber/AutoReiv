# [CARD-067] Allowlist-Only Tool Mount

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/allowlist-only-tool-mount/`
> **Labels**: `type:refactor`, `area:kernel`, `area:agents`

---

## 1. Why / Intent
BM25 silently dropped granted tools (`max_active_tools=6`). `list_available_skills_and_tools` looked like a JIT loader but only dumped the platform catalog. Discovery of *who* can do a job belongs on `lookup_agents`.

---

## 2. What to Build
- Turn time mounts the full RBAC allowlist. No ranking.
- Pin `lookup_agents` on the assistant (with `handoff_to_agent`).
- Remove `list_available_skills_and_tools` from builtin chat allowlists. Forge already lists tools via `GET` catalog / `list_tools()`.
- Keep `ToolRanker` as unused library (escape hatch later).

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-TOOLS-010]`: `_resolve_active_tools` returns the full allowlist.
- [x] `[REQ-TOOLS-011]`: Assistant pins `lookup_agents`.
- [x] `[REQ-TOOLS-012]`: Builtin chat profiles do not grant `list_available_skills_and_tools`.
- [x] Automated tests green via `pytest` on touched suites.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Do not invent Claude-style search-then-enable in this slice.
- Skill-pack RBAC in Forge stays.
