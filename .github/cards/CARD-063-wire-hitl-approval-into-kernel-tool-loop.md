# [CARD-063] Wire HITL Approval Into Kernel Tool Loop

> **Status**: In Progress
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/hitl-kernel-tool-loop/`
> **Labels**: `type:feature`, `area:kernel`, `area:safety`, `area:web`
> **Depends on**: CARD-046 (scaffold), CARD-045 (command filter)

---

## 1. Why / Intent
HITL types, SQLite `pending_approvals`, and `/api/approvals` exist, but `AgentKernel` never parks. `cli_exec` is `subprocess.run(..., shell=True)` with an unused denylist. That is theater. Mutating tools must stop for a human decision before they run.

---

## 2. What to Build
- Wire park/resume into `run_turn` / `stream_turn` for high-risk tools.
- Point the high-risk list at real tools: `cli_exec`, wiki writes, `save_agent_specification`, `execute_code`.
- Run `DangerousCommandFilter` on `cli_exec` (hard deny, no park).
- Emit an approval-required SSE event; resume via existing decision endpoints.
- Tests for park, approve, reject, and dangerous deny.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-HITL-010]`: High-risk tools do not execute until approved.
- [ ] `[REQ-HITL-011]`: High-risk names match registered tools.
- [ ] `[REQ-HITL-012]`: Prohibited `cli_exec` commands are rejected without parking.
- [ ] `[REQ-HITL-013]`: Stream emits approval-required; decision route resumes.
- [ ] `[REQ-HITL-014]`: Automated tests cover park / approve / reject / deny-dangerous.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Do not invent a second approval stack; reuse CARD-046 tables and routes.
- Reads stay auto. Do not HITL `system_info` or wiki reads.
- Single isolated slice on `qa`.
