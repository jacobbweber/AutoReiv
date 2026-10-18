---
id: CARD-717
title: "MCP Capabilities Link and Vault Auth"
type: feature
status: In Review
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-717-mcp-capabilities-link-and-vault-auth]
  checks:
    - tests/unit/web/test_card717_mcp_vault_auth.py
    - tests/unit/frontend/card_717_mcp_capabilities_and_vault.test.js
branch: feat/card-717-mcp-capabilities-link-and-vault-auth
log: {minutes: 15, qa_runs: 1, findings: 1}
created: 2026-10-18
---

# CARD-717 MCP Capabilities Link and Vault Auth

## Intent
Jacob asked for two pre-release improvements:
1. Update the Settings (and Agents Studio) MCP Servers section button and copy from "Open in Tools Studio" to "Open in Capabilities Studio" so the UI matches the consolidated Capabilities Studio destination.
2. Allow MCP servers (starting with HTTP/SSE servers expecting a Bearer token, plus Basic Auth, custom header, or environment variable credentials) to reference an optional encrypted credential from the Credential Vault instead of storing plaintext tokens in MCP server settings.

## Cause
1. When `CARD-692` consolidated Tools Studio and Skill Studio into Capabilities Studio (`#view-capabilities`), the click handlers for `#settingsOpenToolsStudioBtn` and `#forgeOpenToolsStudioBtn` were routed to Capabilities Studio (`mcp/` node), but the button labels and empty-state copy in `src/web/templates/partials/settings_preferences.html`, `src/web/templates/partials/agents.html`, and `src/web/static/modules/studios/tools_studio_catalog.js` still read "Open in Tools Studio".
2. `MCPServerConfig` (`src/domain/settings/models.py`) only accepted static `headers` and `env` dictionaries, with no `credential_id`, `auth_type`, or `auth_header` reference to the Credential Vault (`store.get_credential(...)`), and Capabilities Studio's `#capabilitiesMcpForm` had no Vault credential picker. Additionally, startup auto-mount in `src/web/app.py` only mounted platform MCP servers with a `command` (skipping HTTP/SSE `url` servers).

## Goal
- In Settings -> Connections -> MCP Servers (and Agents Studio -> Remote MCP Servers), the button reads **Open in Capabilities Studio** and empty/helper copy refers to **Capabilities Studio**.
- When adding or editing an MCP server in Capabilities Studio (`#capabilitiesMcpForm`) or via `/api/settings/mcp` and `/api/agents/{id}/mcp`, the operator can pick an optional credential from the Credential Vault and select how it authenticates (`bearer` -> `Authorization: Bearer <secret>`, `basic` -> `Authorization: Basic <base64_or_secret>`, `header` -> `<Header-Name>: <secret>`, or `env` -> `<ENV_VAR>=<secret>`), with a quick link to manage credentials in the Vault.
- At mount time, test-probe time, and server startup, `resolve_mcp_server_auth(config, store)` decrypts the referenced Vault credential in memory and injects the resulting HTTP header or environment variable into `MCPClientAdapter` without persisting the plaintext secret in `mcp_servers` settings or agent markdown files.

## Change
- `src/domain/settings/models.py`: Add `credential_id: Optional[str] = None`, `auth_type: str = "bearer"`, and `auth_header: Optional[str] = None` to `MCPServerConfig`.
- `src/web/mcp_mount_reconcile.py`: Add `resolve_mcp_server_auth(config, store)` to resolve `credential_id` from `store.get_credential(credential_id)` into `headers` (`bearer`, `basic`, `header`) or `env` (`env`), and update `reconcile_saved_mcp_server(mcp_manager, req, store=None)` to use it.
- `src/web/routers/settings.py`, `src/web/routers/agents.py`, `src/web/app.py`: Pass `store` to `reconcile_saved_mcp_server` and `resolve_mcp_server_auth` across save, mount, test-probe, and startup auto-mount (including platform HTTP/SSE MCP servers at startup), and attach `credential_name` metadata on list endpoints.
- `src/web/templates/partials/settings_preferences.html`, `src/web/templates/partials/agents.html`, `src/web/static/modules/studios/tools_studio_catalog.js`: Update button labels and copy to **Open in Capabilities Studio** / **Capabilities Studio**, add `basic_auth` option to Credential Vault type selector, and extend `buildMcpSaveBody`, `serverToSaveBody`, and `renderMcpServerListMarkup` with Vault credential fields and badge.
- `src/web/templates/partials/tools_capabilities.html`, `src/web/static/modules/studios/capabilities_studio.js`, `src/web/static/modules/services/api.js`: Add optional Vault Credential selector (`#capabilitiesMcpCredentialSelect`), Auth Scheme selector (`#capabilitiesMcpAuthTypeSelect`: Bearer Token, Basic Auth, Custom Header, Environment Variable), optional Header / Env Var Name input (`#capabilitiesMcpAuthHeaderInput`), "Manage in Vault" shortcut button (`#capabilitiesMcpManageVaultBtn`), and Edit/Test action support in `#capabilitiesMcpList`.

## What dies
- Stale "Open in Tools Studio" / "Open Tools Studio" copy in `src/web/templates/partials/settings_preferences.html`, `src/web/templates/partials/agents.html`, and `src/web/static/modules/studios/tools_studio_catalog.js`.

## Proof
- Journey `card-717-mcp-capabilities-link-and-vault-auth`:
  1. Create a Bearer token credential in Settings -> Connections -> Credential Vault.
  2. Verify the Settings MCP section button reads "Open in Capabilities Studio" and clicking it opens Capabilities Studio on `mcp/ (MCP Servers)`.
  3. Add an HTTP/SSE MCP server in Capabilities Studio referencing the Vault credential with Bearer Token auth, verify the server row displays the Vault credential badge (`🔑 bearer · ...`), and verify the stored setting holds `credential_id` without leaking the plaintext secret.
- Checks:
  - `tests/unit/web/test_card717_mcp_vault_auth.py`
  - `tests/unit/frontend/card_717_mcp_capabilities_and_vault.test.js`

## Plan and decisions
- `needs_decision: none`. Jacob specified both the UI label update ("Capabilities Studio") and the optional Vault credential picker supporting Bearer token, Basic auth, and common credential types when adding an MCP server.

## Findings
- Fixed in-area: `src/web/app.py` startup auto-mount previously checked `if s.get("enabled", True) and s.get("name") and s.get("command"):` for platform MCP servers, skipping HTTP/SSE (`url`) servers on restart. Updated startup auto-mount to mount both command (`stdio`) and `url` (`sse`) platform MCP servers with Vault credentials resolved.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-717-mcp-capabilities-link-and-vault-auth` | desktop | PASS | Verified "Open in Capabilities Studio" label, saved Vault credential, added HTTP/SSE MCP server with Bearer auth badge, zero overflow (`1280px <= 1280px`) |
| `card-717-mcp-capabilities-link-and-vault-auth` | phone | PASS | Verified "Open in Capabilities Studio" label, saved Vault credential, added HTTP/SSE MCP server with Bearer auth badge, zero overflow (`390px <= 390px`) |

Screenshots:
- `/tmp/autoreiv-qa/card-717/card-717-mcp-capabilities-link-and-vault-auth-desktop-01-open-settings-connections-verify-open-in-capabil.png`
- `/tmp/autoreiv-qa/card-717/card-717-mcp-capabilities-link-and-vault-auth-desktop-02-click-open-in-capabilities-studio-and-add-an-htt.png`
- `/tmp/autoreiv-qa/card-717/card-717-mcp-capabilities-link-and-vault-auth-phone-02-click-open-in-capabilities-studio-and-add-an-htt.png`

## Release note
- Updated Settings and Agents Studio MCP deep-link buttons to "Open in Capabilities Studio" and added Credential Vault authentication references (Bearer Token, Basic Auth, Custom Header, Environment Variable) when configuring MCP servers.

