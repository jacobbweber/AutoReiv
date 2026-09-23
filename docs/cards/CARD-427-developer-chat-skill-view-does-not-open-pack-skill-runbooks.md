---
id: CARD-427
title: "Developer chat skill_view does not open pack skill runbooks"
status: Ready
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:fix
  - area:developer
  - area:packs
---

# [CARD-427] Developer chat skill_view does not open pack skill runbooks

> **Status**: Ready  
> **Created**: 2026-09-23  
> **Found during**: CARD-426 implementation  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-426](./CARD-426-refresh-native-tool-engineering-skill-on-user-modified.md)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-427-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

CARD-426 appends the legacy-loader warning onto `$DATA_DIR/packs/developer/skills/native-tool-engineering/SKILL.md`. Skill Studio, `GET /api/skills/user-packs/native-tool-engineering`, and job bind (`load_one_skill_body`) read that file. A developer chat turn does not. `skill_view` only opens `$DATA_DIR/skills/<id>/SKILL.md`, and the chat skill index skips an allowlisted id that is not in that store. The warning is on disk and in those readers. It is not in the chat tool result.

---

## 2. What AutoReiv does now (Beat 2)

- `UserSkillCatalog.skill_view` loads manifests from `$DATA_DIR/skills` only. For `native-tool-engineering` it returns `Unknown skill` when that folder is absent.
- `render_skill_index` omits the same id, so the developer system prompt does not list the runbook.
- `load_one_skill_body` and `read_pack` fall back to `packs/<id>/skills/<skill>/SKILL.md`, then repo `platform-packs/`.
- Pack skills stay under `packs/<id>/skills/` ([CARD-203](./CARD-203-pure-platform-skill-isolation-and-pack-boundary-guardrails.md)). They are not copied into the operator skill store.
- CARD-426 does not change this split. It only appends the warning onto the developer pack file.

---

## 3. What will change (Beat 3)

Decide how a developer chat turn opens `packs/developer/skills/native-tool-engineering/SKILL.md` so the agent receives the legacy-loader warning, without copying that file into `$DATA_DIR/skills/` and without rewriting the operator prompt.

---

## 4. What dies (Beat 4)

- The gap where the chat tool and the chat skill index cannot see a pack runbook that Skill Studio and job bind already open.

---

## 5. Acceptance criteria (EARS)

- **[REQ-427-001]** WHEN the developer allowlist includes `native-tool-engineering` and the live body is `packs/developer/skills/native-tool-engineering/SKILL.md`, THE SYSTEM SHALL return that body from the developer chat skill open path AND SHALL include the legacy-loader warning when CARD-426 has appended it.
- **[REQ-427-002]** THE SYSTEM SHALL NOT copy that runbook into `$DATA_DIR/skills/` AND SHALL NOT replace the developer prompt or unrelated skill bodies.

---

## 6. Verification

1. On a `user_modified` developer whose pack skill contains the legacy-loader warning, start a developer chat and open `native-tool-engineering`. The warning text is in the tool result. The prompt text you edited is unchanged.
2. Confirm `$DATA_DIR/skills/native-tool-engineering/SKILL.md` was not created by that open.

---

## 7. Out of scope

- Replacing a `user_modified` skill file with the seed copy.
- Migrating `packs/<id>/tools/*.py` through the CARD-423 sandbox.
