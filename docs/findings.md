# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M31 Codebase Tightening, Modularization & Architectural Hygiene

## M32 Projects as user data and development skills
- 2026-10-19 | journeys | card-709 step 3 (Settings model discovery) times out: it calls `window.__autoreivSwitchTab`, which no longer exists | from CARD-728 | tests/e2e/journeys/card-709-web-and-ui-wiring-fixes.mjs
- 2026-10-19 | kernel | `system_prompt_builder` keeps an `agent.id == "developer"` special case for a retired agent | from CARD-728 | src/application/kernel/system_prompt_builder.py
- 2026-10-19 | approvals | `cli_exec` asks on every call; no "remember approved commands for this project" | from CARD-729 | src/application/safety/tool_policy_gate.py, src/application/kernel/hitl_engine.py
- 2026-10-19 | docs | AGENTS.md product lock says the model sees at most 15 tools per turn; ADR-0064 removed the per-turn cap | from CARD-729 | AGENTS.md
- 2026-10-19 | journeys | card-562 and card-563 keep their own `askAndApprove` (different signature) instead of the shared one in `lib/app.mjs` | from CARD-730 | tests/e2e/journeys/card-562-developer-one-card-to-in-review.mjs, tests/e2e/journeys/card-563-architect-plans-and-hands-off.mjs
- 2026-10-19 | mcp | GitHub MCP server (`https://api.githubcopilot.com/mcp/`) not yet exercised live; needs Jacob's token in the Credential Vault | from CARD-730 | src/infrastructure/mcp/client_adapter.py
