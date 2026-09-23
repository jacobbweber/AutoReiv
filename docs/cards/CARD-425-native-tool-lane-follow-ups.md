---
id: CARD-425
title: "Native tool lane follow-ups: user-modified developer allowlist and in-process pack tools"
status: Ready
created: 2026-09-23
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:fix
  - area:tools
  - area:developer
  - area:packs
---

# [CARD-425] Native tool lane follow-ups: user-modified developer allowlist and in-process pack tools

> **Status**: Ready  
> **Created**: 2026-09-23  
> **Found during**: CARD-423 implementation  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md), [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Parent**: [CARD-423](./CARD-423-custom-tool-packaging-native-and-mcp.md)

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

1. Add the new developer skill id and its two tools onto a `user_modified` developer allowlist without rewriting the rest of the profile (prompt, other tools, MCP servers).
2. Decide one fate for `packs/<id>/tools/*.py`: keep it as a documented legacy loader, or route new files through the CARD-423 native lane (sandbox + HITL + catalog label). Do not leave both as equal "native" paths.

---

## 4. What dies (Beat 4)

- The impression that a user-modified developer automatically receives `register_native_tool` just because the skill file was copied.
- Unlabeled in-process pack tool modules as a silent second native lane, once Jacob picks the fate in beat 3.

---

## 5. Acceptance criteria (EARS)

- **[REQ-425-001]** WHEN the developer profile is `user_modified` and the seed adds `native-tool-engineering`, THE SYSTEM SHALL add that skill id and `register_native_tool` / `plan_native_folder` to the developer allowlist AND SHALL leave the existing prompt and other allowlist entries in place.
- **[REQ-425-002]** THE SYSTEM SHALL have one documented fate for `packs/<id>/tools/*.py`: either an explicit legacy loader that is not labeled native custom, or registration through the CARD-423 native lane (sandbox, HITL, catalog origin **Native custom**).

---

## 6. Verification

1. Mark a developer profile `user_modified`, boot, and confirm the two new tools are callable and the previous prompt is unchanged.
2. A pack `tools/*.py` file follows the fate locked in this card, with a negative assertion against the path that was retired.

---

## 7. Out of scope

- Replacing `SandboxedSubprocessWorker` with an OS jail.
- Tools Studio code editor, folder picker, or moving MCP hosting.
