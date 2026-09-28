---
id: CARD-425
title: "Native tool lane follow-ups: user-modified developer allowlist and in-process pack tools"
status: Done
created: 2026-09-23
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:fix
  - area:tools
  - area:developer
  - area:packs
---

# [CARD-425] Native tool lane follow-ups: user-modified developer allowlist and in-process pack tools

> **Status**: Done  
> **Created**: 2026-09-23  
> **Found during**: CARD-423 implementation  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md), [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-423](./CARD-423-custom-tool-packaging-native-and-mcp.md)  
> **Review note (2026-09-23)**: Beat 3 fate is locked. `packs/<id>/tools/*.py` stays an explicit legacy in-process loader (`origin=legacy_pack_tool`, catalog label **Legacy pack tool**). It is not Native custom. A `user_modified` developer gets `native-tool-engineering` plus `register_native_tool` / `plan_native_folder` appended once. Prompt, other allowlist entries, and MCP servers stay. After the grant is recorded in `platform_user_modified_skill_grants`, a later removal stays removed. Say **merge to qa** after a live test.

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-425-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

CARD-423 shipped a sandboxed native lane and developer skills. Two leftovers can make that lane look incomplete on a live box, or leave a second native path that skips the new gates.

---

## 2. What AutoReiv does now (Beat 2)

- Fresh developer installs pick up `native-tool-engineering` from `platform-packs/developer/pack.json`.
- When the live developer profile is `user_modified`, pack sync copies a missing skill folder and does **not** add the new skill id or `register_native_tool` / `plan_native_folder` to the allowlist (ADR-0056).
- `BuiltinAgentRegistry.bootstrap` still imports `packs/<id>/tools/*.py` and registers those callables in-process. That path does not use `native_custom_tools`, the sandbox worker, or ToolPolicyGate HITL.

---

## 3. What will change (Beat 3)

Locked 2026-09-23:

1. Add the new developer skill id and its two tools onto a `user_modified` developer allowlist without rewriting the rest of the profile (prompt, other tools, MCP servers). The grant is recorded once in `platform_user_modified_skill_grants`. A later removal stays removed.
2. `packs/<id>/tools/*.py` stays an explicit legacy in-process loader. Origin `legacy_pack_tool`. Catalog label **Legacy pack tool**. It is not labeled Native custom and it is not rewritten through the CARD-423 sandbox in this card.

---

## 4. What dies (Beat 4)

- The impression that a user-modified developer automatically receives `register_native_tool` just because the skill file was copied, with no allowlist change.
- Unlabeled in-process pack tool modules as a silent second native lane equal to CARD-423.

---

## 5. Acceptance criteria (EARS)

- **[REQ-425-001]** WHEN the developer profile is `user_modified` and the seed adds `native-tool-engineering`, THE SYSTEM SHALL add that skill id and `register_native_tool` / `plan_native_folder` to the developer allowlist AND SHALL leave the existing prompt and other allowlist entries in place.
- **[REQ-425-002]** THE SYSTEM SHALL have one documented fate for `packs/<id>/tools/*.py`: either an explicit legacy loader that is not labeled native custom, or registration through the CARD-423 native lane (sandbox, HITL, catalog origin **Native custom**).

---

## 6. Verification

1. Mark a developer profile `user_modified`, boot, and confirm the two new tools are callable and the previous prompt is unchanged.
2. A pack `tools/*.py` file follows the fate locked in this card, with a negative assertion against the path that was retired.

### Live test

1. On a developer profile that is already `user_modified` and missing `native-tool-engineering`, restart serve.
2. Open the developer agent. The prompt you edited is still there. `native-tool-engineering` is on the skill list. `register_native_tool` and `plan_native_folder` are on the tool allowlist. Other tools and MCP servers you already had are still there.
3. Remove `native-tool-engineering` and restart serve again. It stays off.
4. Put a `packs/<some-id>/tools/widget_ping.py` module in user data and restart serve. Tools Studio shows **Legacy pack tool**, not **Native custom**. `GET /api/tools/native` does not list `widget_ping`.

Automated proof: `tests/integration/operator_contracts/test_oc425_native_tool_lane_followups.py` and `tests/unit/frontend/card_425_legacy_pack_tool.test.js`.

Follow-up: [CARD-426](./CARD-426-refresh-native-tool-engineering-skill-on-user-modified.md). A `user_modified` copy of the skill folder is not refreshed, so a box that already had `native-tool-engineering` keeps the older runbook text. The catalog label does not depend on that file.

---

## 7. Out of scope

- Replacing `SandboxedSubprocessWorker` with an OS jail.
- Tools Studio code editor, folder picker, or moving MCP hosting.

---

## Done

Merged to local qa on 2026-09-23. [CARD-426](./CARD-426-refresh-native-tool-engineering-skill-on-user-modified.md) is In Review: append the legacy-loader warning onto a user-modified native-tool-engineering skill without replacing the file. Draft GitHub PR was a side-effect only.
