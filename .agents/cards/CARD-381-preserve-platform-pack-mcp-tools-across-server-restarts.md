# [CARD-381] Preserve Platform Pack MCP Tools Across Server Restarts

> **Status**: Done
> **Created**: 2026-09-19
> **ADR Reference**: ADR-0052, ADR-0054
> **Labels**: `type:bug`, `area:agents`, `area:mcp`

---

## 1. Why / Intent (Beat 1)

When an operator selects external MCP tools or custom tool grants for the primary `autoreiv` agent in Agent Studio and saves the profile, those tools must remain selected and authorized across server restarts. Currently, the boot-time platform pack reconciler clobbers operator grants by resetting `allowed_tool_names` to the minimal factory seed.

---

## 2. What AutoReiv Does Now (Beat 2)

1. In Agent Studio (`src/web/static/modules/studios/forge.js`), clicking **Save Profile** submits `PUT /api/agents/{agent_id}` with `allowed_tool_names` including ticked MCP tools.
2. In `src/web/routers/agents.py`, because `existing.is_builtin` is `False` for `autoreiv` (it has `is_platform_pack: True`), it calls `registry.register_custom_agent(profile)` which saves to SQLite `custom_agents`, but does not save an entry to `agent_overrides` and does not write to user-data `packs/autoreiv/pack.json`.
3. On every server restart, `install_platform_agent_packs()` in `src/infrastructure/skills/platform_packs.py` reads `platform-packs/autoreiv/pack.json`, calculates `merged_tools` strictly from that repo seed, and overwrites `existing.allowed_tool_names = merged_tools` in SQLite, then executes `shutil.copy2(src / "pack.json", dest / "pack.json")`.
4. As a result, all operator-selected MCP and custom tools disappear from the checked list upon server reboot.

---

## 3. What Will Change (Beat 3)

1. **Non-Destructive Boot Reconciliation**: In `src/infrastructure/skills/platform_packs.py`, update `install_platform_agent_packs()` so that `existing.allowed_tool_names` preserves any operator-added tools (such as `mcp_*` tools or custom grants). It will perform a union merge of newly added factory tools while preserving operator tool selections.
2. **Pack JSON & Override Synchronization**: When `PUT /api/agents/{agent_id}` is executed for a platform pack (`is_platform_pack: True`), ensure the operator customizations (including `allowed_tool_names`, `mcp_servers`, and credentials) are persisted to user data `packs/{agent_id}/pack.json` and mirrored in `agent_overrides` if applicable.
3. **Protected User Data**: `install_platform_agent_packs` will not unconditionally copy `platform-packs/{id}/pack.json` over `user-data/packs/{id}/pack.json` if the user pack has custom tool additions.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Unconditional Tool Overwrite**: The destructive tool clobber in `src/infrastructure/skills/platform_packs.py`:

  ```python
  # Retiring this destructive reset:
  if getattr(existing, "allowed_tool_names", None) != merged_tools:
      existing.allowed_tool_names = merged_tools
  ```

- **Unconditional Pack File Overwrite**: Retiring `shutil.copy2(src / "pack.json", dest / "pack.json")` on server boot when the destination pack contains user modifications.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL preserve operator-granted MCP and custom tools in `allowed_tool_names` for `autoreiv` and platform packs across server boot cycles.
- **Event-Driven**: WHEN an operator saves an updated profile for a platform pack via `PUT /api/agents/{agent_id}`, THE SYSTEM SHALL persist the updated `allowed_tool_names` to user data `packs/{agent_id}/pack.json`.
- **State-Driven**: WHILE `install_platform_agent_packs` reconciles platform packs on server startup, THE SYSTEM SHALL ensure all canonical platform skill tools are present without removing operator-added MCP or custom tools.
- **Complex / Unwanted**: WHEN `platform-packs/{id}/pack.json` is updated in the repo, THE SYSTEM SHALL NOT overwrite operator-configured MCP servers or tool grants in user data `packs/{id}/pack.json`.
- **Negative Assertion**: Automated tests shall explicitly assert that restarting or re-running `install_platform_agent_packs` after adding `mcp_blender_render` to `autoreiv.allowed_tool_names` keeps `mcp_blender_render` in `allowed_tool_names`.

---

## 6. Constraints & Verification Plan

- **Automated Tests**:
  - Add regression test in `tests/unit/skills/test_platform_pack_mcp_persistence.py` verifying that operator tool selections survive `install_platform_agent_packs`.
  - Add API integration test in `tests/integration/web/test_agent_mcp_tool_persistence.py` verifying `PUT /api/agents/autoreiv` persists across simulated reboot.
- **Preflight Gate**: `npm run preflight` must pass with 0 errors.

---

## 7. Human QA Verification Runbook

1. Launch AutoReiv serve (`python -m uvicorn src.web.app:app --port 8000`).
2. Open Agent Studio, select **AutoReiv**, and tick available MCP tools in the tools grid.
3. Click **Save Profile** (observe "Saved!" confirmation).
4. Restart the AutoReiv server.
5. Reopen Agent Studio on **AutoReiv** and verify that all previously selected MCP tools remain checked.
