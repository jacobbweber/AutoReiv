---
id: CARD-427
title: "Developer chat skill_view does not open pack skill runbooks"
status: Done
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:fix
  - area:developer
  - area:packs
---

# [CARD-427] Developer chat skill_view does not open pack skill runbooks

> **Status**: Done  
> **Created**: 2026-09-23  
> **Found during**: CARD-426 implementation  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-426](./CARD-426-refresh-native-tool-engineering-skill-on-user-modified.md)  
> **Review note (2026-09-23)**: Developer chat `skill_view` reads `packs/developer/skills/native-tool-engineering/SKILL.md` through the same locator Skill Studio uses. The chat skill index lists that runbook. The open does not copy the file into `$DATA_DIR/skills/` and does not rewrite the developer prompt. Say **merge to qa** after a live test.

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

`skill_view` and the chat skill index resolve an allowlisted runbook with `locate_skill_markdown` (operator skill store, then that agent's pack, then any pack). The body returned to the chat turn is the pack file, including the CARD-426 warning when that file has it. `skill_view` is callable on a chat turn when the agent has an allowlist. It is not written onto the stored tool allowlist. The operator prompt text stays the prompt text.

---

## 4. What dies (Beat 4)

- The gap where the chat tool and the chat skill index cannot see a pack runbook that Skill Studio and job bind already open.

---

## 5. Acceptance criteria (EARS)

- **[REQ-427-001]** WHEN the developer allowlist includes `native-tool-engineering` and the live body is `packs/developer/skills/native-tool-engineering/SKILL.md`, THE SYSTEM SHALL return that body from the developer chat skill open path AND SHALL include the legacy-loader warning when CARD-426 has appended it.
- **[REQ-427-002]** THE SYSTEM SHALL NOT copy that runbook into `$DATA_DIR/skills/` AND SHALL NOT replace the developer prompt or unrelated skill bodies.

---

## 6. Verification

1. On a `user_modified` developer whose pack skill contains the legacy-loader warning, start a developer chat and ask it to open `native-tool-engineering` with `skill_view`. The tool result includes your sentence and the legacy-loader warning (`<!-- autoreiv:native-tool-legacy-loader -->`, `## Not the legacy pack loader`, Legacy pack tool). The prompt text you edited is unchanged.
2. Confirm `$DATA_DIR/skills/native-tool-engineering/SKILL.md` was not created by that open.
3. Confirm another skill file under `packs/developer/skills/` is unchanged.

Automated proof: `tests/integration/operator_contracts/test_oc427_developer_chat_pack_skill_view.py` (OC-427).

Follow-up: [CARD-428](./CARD-428-list-user-skill-packs-omits-pack-runbooks.md). `list_user_skill_packs` still lists `$DATA_DIR/skills` only. The chat index now also lists allowlisted pack runbooks.

---

## 7. Out of scope

- Replacing a `user_modified` skill file with the seed copy.
- Migrating `packs/<id>/tools/*.py` through the CARD-423 sandbox.

---

## Done

Merged to local qa on 2026-09-23.
