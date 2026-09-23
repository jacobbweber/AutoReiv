---
id: CARD-426
title: "Refresh native-tool-engineering runbook text on a user-modified developer"
status: Done
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:fix
  - area:developer
  - area:packs
---

# [CARD-426] Refresh native-tool-engineering runbook text on a user-modified developer

> **Status**: Done  
> **Created**: 2026-09-23  
> **Found during**: CARD-425 implementation  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-425](./CARD-425-native-tool-lane-follow-ups.md)  
> **Review note (2026-09-23)**: Beat 3 is locked. On boot, a `user_modified` developer whose live `native-tool-engineering/SKILL.md` lacks both the marker `<!-- autoreiv:native-tool-legacy-loader -->` and the heading `## Not the legacy pack loader` gets only that seed warning section appended. The rest of the file, the prompt, and other skill bodies stay. If the marker or the heading is already present, the file is not rewritten. Say **merge to qa** after a live test.

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

Locked 2026-09-23:

1. The seed warning section in `platform-packs/developer/skills/native-tool-engineering/SKILL.md` carries the stable marker `<!-- autoreiv:native-tool-legacy-loader -->` under the heading `## Not the legacy pack loader`.
2. On boot, for a `user_modified` developer only: if the live `packs/developer/skills/native-tool-engineering/SKILL.md` is missing both that marker and that heading, append the seed warning section. Do not replace the file.
3. If the marker or the heading is already present, leave that file byte-for-byte alone.
4. Do not rewrite the developer prompt or any other skill body.
5. Tools Studio catalog labels stay on `catalog_origin_label` / `origin=legacy_pack_tool`. They do not read this skill file.

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

### Live test

1. On a developer profile that is already `user_modified`, open `$DATA_DIR/packs/developer/skills/native-tool-engineering/SKILL.md`. If it has no `<!-- autoreiv:native-tool-legacy-loader -->` and no heading `## Not the legacy pack loader`, leave a sentence only you wrote in that file. Leave the developer prompt as you edited it.
2. Restart serve.
3. Open that same file. Your sentence is still there. The legacy-loader section is at the end, including the marker and the words Legacy pack tool. The file is not a copy of `platform-packs/developer/skills/native-tool-engineering/SKILL.md`.
4. Open native-tool-engineering in Skill Studio for the developer. The same warning and your sentence are both there. The developer prompt is unchanged. Another skill file is unchanged.
5. Edit the skill, keep the marker, add a new sentence, and restart serve. The new sentence is still there. The file was not replaced with the seed.
6. Put a `packs/<some-id>/tools/widget_ping.py` module in user data and restart serve. Tools Studio still shows **Legacy pack tool**. That label does not come from this skill file.

Automated proof: `tests/integration/operator_contracts/test_oc426_native_tool_skill_warning.py`.

A profile that is first marked `user_modified` on this same boot (no stored seed hash, live profile already diverged) gets the warning on the following boot. That matches the CARD-425 allowlist grant.

Chat `skill_view` still opens `$DATA_DIR/skills/<id>/SKILL.md` only, and the chat skill index skips a pack runbook that is not in that store. Job bind (`load_one_skill_body`), `GET /api/skills/user-packs/native-tool-engineering`, and Skill Studio read the pack copy. Follow-up: [CARD-427](./CARD-427-developer-chat-skill-view-does-not-open-pack-skill-runbooks.md).

---

## 7. Out of scope

- Rewriting every `packs/<id>/tools/*.py` module through the CARD-423 sandbox.
- OS jail for `SandboxedSubprocessWorker`.

---

## Done

Merged to local qa on 2026-09-23. Follow-up [CARD-427](./CARD-427-developer-chat-skill-view-does-not-open-pack-skill-runbooks.md) remains open for chat skill_view pack runbooks. Draft GitHub PR was a side-effect only.
