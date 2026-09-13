# [CARD-221] Tool Policy Gate (ALLOW / REQUIRE_CONFIRM / BLOCK)

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-220; extends HITL / DangerousCommandFilter / kernel `_gate_tool_call`
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Safety`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Every tool call is judged**: After model intent and **before** the executor, policy returns `ALLOW` | `REQUIRE_CONFIRM` | `BLOCK`.
2. **Registry listing ≠ authorization**: A tool can be registered / listed to the model and still be `BLOCK`ed at the gate. Listing is not permission.
3. **Defaults (fail-closed)**:
   - read / safe → `ALLOW`
   - dangerous / write / shell → `REQUIRE_CONFIRM` → existing HITL park/resume (no parallel HITL)
   - unknown / not in agent allowlist / not in matched capability subset (when job-bound) / out-of-scope → `BLOCK`
4. **Durable config, not prompt text**: Policy lives in durable settings (Agent Forge surfaces agent allowlists; global defaults in settings). Observability gets a **decision log** of gate verdicts.
5. **Not this card**: New Studios, UI polish beyond Forge/Obs hooks, new parallel approval UX.

### Beat 2: What AutoReiv Does Now
1. Kernel `_gate_tool_call` parks high-risk via `HITLApprovalEngine.requires_approval` and hard-denies `DangerousCommandFilter` patterns on `cli_exec` — but there is no explicit ALLOW/REQUIRE_CONFIRM/BLOCK verdict object or decision log.
2. Tool registry RBAC denies unauthorized tools inside `execute`, after the gate sometimes skips non-allowlisted tools (`return None` → execute path).
3. High-risk set is hardcoded in `HITLApprovalEngine`; not durable Agent Forge / settings config.
4. Observability shows tool reliability KPIs, not per-call policy decisions.

### Beat 3: What Will Change
1. `ToolPolicyGate` (application) evaluates verdict from durable policy + agent allowlist + optional matched capability subset + DangerousCommandFilter + high-risk defaults.
2. Kernel `_gate_tool_call` uses the gate: ALLOW → execute; REQUIRE_CONFIRM → existing HITL park; BLOCK → fail-closed ToolResult (never runs).
3. Durable `tool_policy` settings key + decision log rows queryable via Observability API.
4. Proof: red "listed but BLOCKED never runs"; red "dangerous without approve stays parked"; green. Extend existing HITL — do not invent parallel HITL.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-TOOLPOL-001]**: Every tool call receives an explicit verdict `ALLOW` | `REQUIRE_CONFIRM` | `BLOCK` after model intent, before executor.
- [x] **[REQ-TOOLPOL-002]**: Registry listing ≠ authorization — a registered/listed tool can still be `BLOCK`ed and never executes.
- [x] **[REQ-TOOLPOL-003]**: Defaults: read/safe → ALLOW; dangerous/write/shell → REQUIRE_CONFIRM → existing HITL park/resume; unknown / not in agent allowlist / not in matched capability subset (when provided) / out-of-scope → BLOCK fail-closed.
- [x] **[REQ-TOOLPOL-004]**: Policy stored in durable config (`tool_policy` settings + agent allowlists via Agent Forge paths); Observability decision log records verdicts. Not prompt-only.
- [x] **[REQ-TOOLPOL-005]**: Extends `_gate_tool_call` / `HITLApprovalEngine` / `DangerousCommandFilter` — no parallel HITL. Out of scope: new Studios.
- [x] **[REQ-TOOLPOL-006]**: Automated tests red→green including: listed-but-BLOCKED never runs; dangerous without approve stays parked. Ruff clean; CHANGELOG; push `feat/*` only — never qa/main.

---

## 3. Constraints & Honor Flags

- Status: **Done** (unit gate green + live QA on Jarvis serve 2026-09-10 ET).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Out of scope: new Studios, ATF/Lab rewrite, Homelab domain outcomes.
- Anti-theatre: durable policy + decision log + gate before execute; failure = BLOCK / park (never silent run).

---

## 4. Modules Likely Touched

- `src/application/safety/tool_policy_gate.py` (new)
- `src/application/kernel/agent_kernel.py` — `_gate_tool_call`
- `src/application/kernel/hitl_engine.py` — reuse park path
- `src/application/skills/command_filter.py` — reuse
- `src/infrastructure/memory/schema.py` + settings / decision-log repo
- `src/web/routers/observability.py` — decision log read
- `tests/unit/safety/test_tool_policy_gate.py`

---

## 5. Marathon Notes

- Build lock: verdict enum + gate before executor + durable config + decision log + extend HITL.
- TDD: red listed-BLOCKED + dangerous-parked first, then green.

## 6. Marathon Build Notes (Jarvis)

- `ToolPolicyGate` evaluates ALLOW / REQUIRE_CONFIRM / BLOCK before executor; durable `tool_policy` settings + decision log table `tool_policy_decisions`.
- Kernel `_gate_tool_call` routes through the gate; REQUIRE_CONFIRM uses existing HITL park/resume; BLOCK fail-closed; DangerousCommandFilter hard-BLOCK for prohibited patterns.
- Observability: `GET /api/observability/tool-policy-decisions`.
- Tests: `tests/unit/safety/test_tool_policy_gate.py` (7) + `test_tool_policy_kernel_gate.py` (2) green; related HITL 33 passed; ruff clean.
- Agent Forge continues to own agent `allowed_tool_names` (authorization input); listing ≠ run permission.
- Out of scope: new Studios.

## 7. Live QA (Jarvis 2026-09-10 ET)

- Restarted `deploy/windows/run_autoreiv.ps1 -HostIP 127.0.0.1 -Port 8000` after killing stale :8000 listeners.
- `GET /api/observability/tool-policy-decisions` -> **200** (not 404).
- REQUIRE_CONFIRM: developer `cli_exec` `echo CARD221-LIVE-CONFIRM` -> decision `tpd_625a75b101bc` verdict REQUIRE_CONFIRM + pending HITL `appr_bd4f13f82bfa` (tool not executed).
- BLOCK: durable `tool_policy.block_tools=["cli_exec"]` + restart -> `tpd_0a9860eaaec1` verdict BLOCK (`settings.block_tools`); no pending approval for that session; tool never ran.
- CARD-220 path (same serve): multi-step Chat created `job_c8ace807fec1` `template_id=catalog_resolve_rhe` with matched `["tool.wiki_note_search","skill.platform-health","agent.assistant","routine.sre-pulse"]` on checkpoint (Research/Handoff/Execute).
- Restored empty `tool_policy` block list after BLOCK probe.

