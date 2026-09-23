---
id: CARD-424
title: "MCP disable must unmount (Tools Studio enable/disable honesty)"
status: In Review
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:fix
  - area:mcp
  - area:tools
  - area:studios
---

# [CARD-424] MCP disable must unmount (Tools Studio enable/disable honesty)

> **Status**: In Review  
> **Review note**: 2026-09-23 — Platform and agent MCP save unmount when `enabled` is false and mount when true. Save `mounted` and list `is_mounted` follow the live manager. Tools Studio shows plain Disabled after a successful disable, and a warning plus still-mounted wording only when unmount fails.  
> **Created**: 2026-09-22  
> **Found during**: CARD-421 live test (Harness Engineer + Jacob) on `feat/card-421-tools-studio-v1-catalog-and-mcp-attach`  
> **Parent**: [CARD-421](./CARD-421-tools-studio-v1-catalog-and-mcp-attach.md)  
> **Related**: [CARD-422](./CARD-422-tools-studio-form-and-developer-mediation.md), [CARD-423](./CARD-423-custom-tool-packaging-native-and-mcp.md) (do not fold this fix into those)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC — **no product code** |
| **`build`** | Implement on `feat/card-424-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

During CARD-421 live test, Disable in Tools Studio only persisted `enabled: false` on the existing MCP attach save API. The process stayed mounted, so the UI correctly showed **Disabled (still mounted, N tools)**. Delete already unmounts. Operators expect Disable to stop the plug-in box from staying live, not only flip a durable flag.

This card closes that honesty gap: disable unmounts, enable remounts, list status matches reality. Standing practice: findings like this become Ready follow-up cards automatically, not chat-only notes.

---

## 2. What AutoReiv does now (Beat 2)

- Tools Studio Disable/Enable re-saves the server via `POST /api/settings/mcp` or `POST /api/agents/{id}/mcp` with `enabled` flipped (`serverToSaveBody` in `tools_studio_catalog.js`).
- `save_mcp_server` in `src/web/routers/settings.py` mounts when `req.enabled` is true; when `enabled` is false it saves config and **does not** call `mcp_manager.unmount_server`.
- Delete path does call `unmount_server`.
- Save response currently reports `"mounted": True` even when disabling (misleading).
- UI badge path already distinguishes Disabled vs Disabled (still mounted).

---

## 3. What will change (Beat 3)

1. Platform MCP save: when `enabled` is false, unmount that server after durable save; when true, mount as today.
2. Agent-scoped MCP save: same unmount-on-disable / mount-on-enable behavior on `/api/agents/{id}/mcp*`.
3. Save/list responses: `mounted` / `is_mounted` and tool lists reflect post-action reality (disabled and unmounted shows not mounted, tool_count 0 unless another path remounts).
4. Tools Studio badges: after disable, prefer plain **Disabled** once unmounted; keep still-mounted wording only if a race or failure leaves it mounted, and surface that failure to the operator.
5. Tests: API + frontend coverage for disable unmounts, enable remounts, and no still-mounted lie on happy path.
6. Proof: live disable of a real SSE or stdio server (for example HyperV MCP) leaves it unmounted until Enable.

**Out of scope:** CARD-422 form/developer; CARD-423 dual packaging; MCP hosting UI; deleting servers (already unmounts).

---

## 4. What dies (Beat 4)

- Expectation that Disable is only a durable preference bit while the process keeps serving tools.
- Happy-path **Disabled (still mounted)** as the normal Disable outcome.

---

## 5. Acceptance criteria (EARS)

- **[REQ-424-001]** WHEN the operator disables a platform MCP server from Tools Studio (or the same save API), THE SYSTEM SHALL persist `enabled: false` AND unmount that server so it is not left mounted on the happy path.
- **[REQ-424-002]** WHEN the operator enables a previously disabled MCP server, THE SYSTEM SHALL persist `enabled: true` AND mount it (or return a clear mount failure while keeping durable enabled state honest).
- **[REQ-424-003]** WHEN the operator disables an agent-scoped MCP server, THE SYSTEM SHALL apply the same unmount-on-disable behavior for that agent only.
- **[REQ-424-004]** WHEN listing MCP servers after a successful disable, THE SYSTEM SHALL report `is_mounted` false (or equivalent) and SHALL NOT claim tools are mounted for that disabled server on the happy path.
- **[REQ-424-005]** THE SYSTEM SHALL NOT leave Delete as the only operator path that unmounts a server the operator intended to disable.

---

## 6. Verification

Automated:

- Pytest: save with `enabled: false` calls unmount (or integration equivalent); save with `enabled: true` mounts; list reflects mount state.
- Vitest: toggle helpers / badge copy for disabled-unmounted vs failure still-mounted.

Manual live test:

1. With HyperV (or any) MCP attached and mounted, Disable in Tools Studio.
2. Confirm list shows Disabled and not still mounted; tools from that server are gone from the live catalog grouping for that server.
3. Enable again; tools return.
4. Repeat once for an agent-scoped server.
5. Delete still unmounts and removes config.

---

## 7. Honest scope note

This is a small MCP lifecycle fix discovered in CARD-421 review. It is Ready so it cannot be forgotten after CARD-421 merges Done. Do not ship theatre badges that hide a missing unmount.
