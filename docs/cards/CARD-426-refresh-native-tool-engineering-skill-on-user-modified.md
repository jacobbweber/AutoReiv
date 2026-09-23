---
id: CARD-426
title: "Refresh native-tool-engineering runbook text on a user-modified developer"
status: Ready
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:fix
  - area:developer
  - area:packs
---

# [CARD-426] Refresh native-tool-engineering runbook text on a user-modified developer

> **Status**: Ready  
> **Created**: 2026-09-23  
> **Found during**: CARD-425 implementation  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-425](./CARD-425-native-tool-lane-follow-ups.md)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-426-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

CARD-425 documents that `packs/<id>/tools/*.py` is a legacy in-process loader, not Native custom. That note lives in the seed skill `platform-packs/developer/skills/native-tool-engineering/SKILL.md`. On a live box the developer agent reads the copy under user data. ADR-0056 does not overwrite that copy when the developer profile is `user_modified`, which is the usual case after any prompt or allowlist edit.

---

## 2. What AutoReiv does now (Beat 2)

- CARD-425 appends the skill id and the two tools onto a `user_modified` developer allowlist, once.
- Pack sync still copies a missing skill folder and does not refresh a skill folder that is already there.
- A developer profile that received `native-tool-engineering` during CARD-423 keeps the older runbook text. It does not mention the legacy pack loader.
- Tools Studio still labels those modules **Legacy pack tool**. The allowlist grant does not depend on the runbook text.

---

## 3. What will change (Beat 3)

Decide how a `user_modified` developer sees the legacy-loader warning in the runbook the agent actually reads, without clobbering operator edits to that skill or to the prompt.

---

## 4. What dies (Beat 4)

- The gap where the seed runbook and the live user-data runbook disagree about `packs/<id>/tools/*.py` after CARD-425.

---

## 5. Acceptance criteria (EARS)

- **[REQ-426-001]** WHEN the developer profile is `user_modified` and the live `native-tool-engineering` skill body is missing the legacy-loader warning, THE SYSTEM SHALL surface that warning to the developer agent AND SHALL leave operator-edited prompt text and unrelated skill bodies in place.
- **[REQ-426-002]** IF the operator has edited `native-tool-engineering/SKILL.md`, THE SYSTEM SHALL NOT replace that file with the seed copy.

---

## 6. Verification

1. Copy an older `native-tool-engineering` skill into a `user_modified` developer pack, boot, and confirm the developer can see the legacy-loader warning.
2. Edit that skill file, boot again, and confirm the edit is still there.

---

## 7. Out of scope

- Rewriting every `packs/<id>/tools/*.py` module through the CARD-423 sandbox.
- OS jail for `SandboxedSubprocessWorker`.
