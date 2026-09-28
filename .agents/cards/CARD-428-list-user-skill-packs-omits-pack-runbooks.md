---
id: CARD-428
title: "list_user_skill_packs omits pack runbooks the chat index lists"
status: Done
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:fix
  - area:developer
  - area:packs
---

# [CARD-428] list_user_skill_packs omits pack runbooks the chat index lists

> **Status**: Done  
> **Created**: 2026-09-23  
> **Found during**: CARD-427 implementation  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-427](./CARD-427-developer-chat-skill-view-does-not-open-pack-skill-runbooks.md)  
> **Review note (2026-09-23)**: `list_user_skill_packs` includes an allowlisted pack runbook from `packs/<agent>/skills/<id>/SKILL.md` when `$DATA_DIR/skills/<id>/` is absent. The row is the id, name, and description. The call does not copy the file and does not list an id that is off the agent's allowlist. A developer chat turn that names `list_user_skill_packs` can call it. Say **merge to qa** after a live test.

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-428-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

CARD-427 makes the developer chat skill index list an allowlisted pack runbook and makes `skill_view` open `packs/<agent>/skills/<id>/SKILL.md`. `list_user_skill_packs` still lists `$DATA_DIR/skills` only. An agent that has that tool sees a shorter catalog than the prompt index. Pack skills must stay in the pack folder.

---

## 2. What AutoReiv does now (Beat 2)

- `render_skill_index` includes an allowlisted id whose body lives under `packs/<agent>/skills/<id>/SKILL.md`.
- `UserSkillCatalog.list_user_skill_packs` filters `list_manifests()`, which scans `$DATA_DIR/skills` only.
- The tool text says that list is the same index already in the system prompt.
- CARD-203 still forbids copying pack runbooks into `$DATA_DIR/skills/`.

---

## 3. What will change (Beat 3)

Decide how `list_user_skill_packs` returns the same allowlisted pack runbooks the chat index already names, using the existing pack locator, without copying those files into `$DATA_DIR/skills/`.

---

## 4. What dies (Beat 4)

- The split where the chat index names a pack runbook and `list_user_skill_packs` omits that id.

---

## 5. Acceptance criteria (EARS)

- **[REQ-428-001]** WHEN an agent's allowlist includes a skill whose live body is `packs/<agent>/skills/<id>/SKILL.md` and that folder is absent from `$DATA_DIR/skills/`, THE SYSTEM SHALL include that id in `list_user_skill_packs` for that agent AND SHALL return only name and description.
- **[REQ-428-002]** THE SYSTEM SHALL NOT copy that runbook into `$DATA_DIR/skills/` AND SHALL NOT list a skill id that is not on the agent's allowlist.

---

## 6. Verification

1. On a developer whose allowlist includes `native-tool-engineering` and whose pack file is the only copy, ask that chat to call `list_user_skill_packs` by name. The id is in the result, with its name and description, and without the runbook body. `$DATA_DIR/skills/native-tool-engineering/` does not exist.
2. Call the same tool as an agent that does not have that skill ticked (AutoReiv). The id is absent.

Automated proof: `tests/integration/operator_contracts/test_oc428_list_user_skill_packs_pack_runbooks.py` (OC-428).

---

## 7. Out of scope

- Replacing a `user_modified` skill file with the seed copy.
- Changing `skill_view` body loading (CARD-427).

---

## Done

Merged to local qa on 2026-09-23.
