---
id: CARD-431
title: "Unregister save_agent_specification"
status: Done
created: 2026-09-23
adr: docs/adr/0058-retire-agent-builder-into-developer.md
labels:
  - type:cleanup
  - area:tools
  - area:agents
---

# [CARD-431] Unregister save_agent_specification

> **Status**: Done
> **Created**: 2026-09-23
> **Found during**: [CARD-429](./CARD-429-classification-simplification.md)
> **ADR Reference**: [ADR-0058](../adr/0058-retire-agent-builder-into-developer.md)
> **Parent**: [CARD-429](./CARD-429-classification-simplification.md)
> **Operator contract**: `tests/integration/operator_contracts/test_oc431_unregister_save_agent_specification.py`

Say **merge to qa** after a live look. Do not merge from this card alone.

---

## Gate language

| Jacob reply | Meaning |
| --- | --- |
| **`continue`** | Refine this card. No product code. |
| **`build`** | Implement on `feat/card-431-*` from `qa`. |
| **`merge to qa`** | After In Review and a live test. |

---

## 1. Why / Intent (Beat 1)

`scaffold_agent_pack` is the pack write. `save_agent_specification` is the old Agent Builder write. CARD-429 left the handler registered and off the developer allowlist so a model would not call it. If nothing still needs that registration, it should leave the tool catalog.

---

## 2. What AutoReiv does now (Beat 2)

`AgentBuilderTools` in `src/application/skills/agent_builder_tools.py` still registers `save_agent_specification`. The description tells the model not to use it. Developer’s allowlist, the `capability-authoring` tool group, and the additive grant do not include it. `scaffold_agent_pack` in `src/application/skills/agent_pack_tools.py` writes the pack. The name still appears on the tool policy gate (`src/application/safety/tool_policy_gate.py`) and the HITL engine (`src/application/kernel/hitl_engine.py`).

---

## 3. What will change (Beat 3)

Before code, confirm no live caller needs the registered tool (chat, jobs, HITL resume of an in-flight proposal). Recommended: unregister the tool and drop it from the policy-gate and HITL name lists. Keep `scaffold_agent_pack`. Delete the Python method only when a scavenger pass shows zero callers. If a parked HITL row still names the tool, leave the handler registered and stop this card.

---

## 4. What dies today (Beat 4)

- The `registry.register_tool` entry for `save_agent_specification`, if the check in Beat 3 says nothing needs it.
- Catalog, policy-gate, and HITL name-list entries for that tool.

Kept until the scavenger pass is clean: the method body, `propose_agent_specification`, and `scaffold_agent_pack`.

---

## 5. Acceptance criteria (EARS)

- **[REQ-431-001]** WHEN boot finishes THE SYSTEM SHALL NOT list `save_agent_specification` as a callable tool.
- **[REQ-431-002]** THE SYSTEM SHALL still register `scaffold_agent_pack` AND SHALL still let Developer call it when the turn asks to scaffold an agent pack.
- **[REQ-431-003]** WHEN an in-flight HITL record still names `save_agent_specification` THE SYSTEM SHALL NOT unregister the handler in this slice.
- **[REQ-431-004]** THE SYSTEM SHALL NOT register `agent-builder` again.

---

## 6. Human verification runbook

1. Open Tools Studio. `save_agent_specification` is not in the catalog.
2. Ask Developer to scaffold an agent pack. It can still call `scaffold_agent_pack`.
3. Chat has no Agent Builder.

Beat 3 on this checkout: no `*.db` under the workspace or this machine, no `AUTOREIV_DATA_DIR`, and no pack allowlist, job, or routine calls the tool. A fresh boot database has no `pending_approvals` row for it, so REQ-431-003 did not block unregister. The handler method is deleted because nothing calls it.

If a parked approval on a machine this checkout cannot see still names the tool, Approve will not run that handler. Say so before **merge to qa** if that row exists.

---

## 7. Out of scope

- Rewriting historical session text that mentions the old tool.
- Removing `propose_skill`, `propose_tool`, or `propose_agent_specification`.
- Merging skill disk homes.
