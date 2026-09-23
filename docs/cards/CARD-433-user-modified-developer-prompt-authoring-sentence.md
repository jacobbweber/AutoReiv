---
id: CARD-433
title: "Append an authoring sentence to a user-modified developer prompt"
status: Ready
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:cleanup
  - area:developer
  - area:packs
---

# [CARD-433] Append an authoring sentence to a user-modified developer prompt

> **Status**: Ready
> **Created**: 2026-09-23
> **Found during**: [CARD-429](./CARD-429-classification-simplification.md)
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md), [ADR-0058](../adr/0058-retire-agent-builder-into-developer.md)
> **Parent**: [CARD-429](./CARD-429-classification-simplification.md)

Optional later slice. Planning only. Say **continue** to change this card. Say **build** before any product code. Say **merge to qa** only after In Review and a live look.

---

## Gate language

| Jacob reply | Meaning |
| --- | --- |
| **`continue`** | Refine this card. No product code. |
| **`build`** | Implement on `feat/card-433-*` from `qa`. |
| **`merge to qa`** | After In Review and a live test. |

---

## 1. Why / Intent (Beat 1)

A developer pack Jacob already edited does not get the new system-prompt sentence from the seed. CARD-429 adds the authoring skills and tools with the additive grant, and the skill file tells Developer how to propose, commit, and scaffold. The prompt he wrote stays. This card adds one sentence to that prompt so the chat instructions match the tools, without replacing his text.

---

## 2. What AutoReiv does now (Beat 2)

ADR-0056 does not overwrite a pack marked `user_modified`. `apply_user_modified_additive_skill_grants` in `src/infrastructure/skills/platform_packs.py` appends skill ids and tool names once and records them in `platform_user_modified_skill_grants`. It does not change `system_prompt`. The seed prompt in `platform-packs/developer/pack.json` already tells a fresh developer to use `propose_skill`, `commit_skill_pack`, and `scaffold_agent_pack`, and not to use `save_agent_specification`. A `user_modified` prompt never receives that sentence.

---

## 3. What will change (Beat 3)

When developer is `user_modified` and the prompt does not already mention the authoring tools, append one short paragraph. Do not replace the existing prompt. Record the append once, the same way CARD-425 records a skill grant, so a later deletion of that paragraph stays deleted.

Recommended paragraph: Developer can propose and commit skills, propose tools, and scaffold agent packs with the capability-authoring tools. `scaffold_agent_pack` writes the pack. Do not use `save_agent_specification`.

A developer that is not `user_modified` already has the seed prompt. This card does not touch that file again.

---

## 4. What dies today (Beat 4)

- The gap where a `user_modified` developer prompt never mentions the authoring tools that the allowlist already has.

Kept: the operator’s existing prompt text, the additive skill grant, seed-hash overwrite rules for every other field, and `save_agent_specification` staying off the allowlist.

---

## 5. Acceptance criteria (EARS)

- **[REQ-433-001]** WHEN the developer profile is `user_modified` AND the system prompt does not mention `scaffold_agent_pack` THE SYSTEM SHALL append one authoring paragraph AND SHALL leave the existing prompt text in place.
- **[REQ-433-002]** WHEN that paragraph was already appended AND the operator removed it THE SYSTEM SHALL NOT append it again.
- **[REQ-433-003]** WHEN the developer profile is not `user_modified` THE SYSTEM SHALL leave the seed prompt path unchanged by this card.
- **[REQ-433-004]** THE SYSTEM SHALL NOT add `save_agent_specification` to the developer allowlist.

---

## 6. Human verification runbook

After **build**:

1. On a developer profile you already edited, restart serve.
2. Open Agent Studio. Your old prompt is still there, with one added paragraph about propose, commit, and scaffold.
3. Delete that paragraph, save, restart serve. It does not come back.
4. Tools still include `propose_skill` and `scaffold_agent_pack`. `save_agent_specification` is still not on the allowlist.

---

## 7. Out of scope

- Replacing a `user_modified` prompt with the seed prompt.
- Changing `user_modified` rules for tools, MCP servers, or other packs.
- Unregistering `save_agent_specification` ([CARD-431](./CARD-431-unregister-save-agent-specification.md)).
- Merging `$DATA_DIR/skills/` with `packs/<id>/skills/`. Blocked by [CARD-203](./CARD-203-pure-platform-skill-isolation-and-pack-boundary-guardrails.md) and [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md).
