# [CARD-225] MCP Tools Through Matched-Subset + CARD-221 Gate

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Design room after CARD-221/224; MCP transport vs authorization
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.MCP`, `AutoReiv.Safety`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **MCP is transport only**: `tools/list` discovers and mounts schemas — it is **not** authorization to run.
2. **Mounted MCP tools still face the CARD-221 gate**: Every MCP tool call must pass matched capability subset (when job-bound) **and** `ToolPolicyGate` `ALLOW` / `REQUIRE_CONFIRM` / `BLOCK` before the executor.
3. **Outside-subset / unknown MCP → BLOCK**: A tool returned by `tools/list` but absent from matched IDs (or unknown to registry) never reaches the executor.
4. **Dangerous MCP → REQUIRE_CONFIRM → existing HITL**: High-risk MCP tools park through the same HITL path as native write/shell tools — no parallel auth.
5. **Not this card**: New Studios, new MCP transports, inventing a second policy engine, CARD-226.

### Beat 2: What AutoReiv Does Now
1. `MCPClientAdapter` / `MCPClientManager` list tools via JSON-RPC `tools/list` and `ScopedToolRegistry.mount_mcp_tool` registers `mcp_<server>_<tool>` handlers (transport + mount works).
2. `ToolPolicyGate` (CARD-221) enforces allowlist + matched subset + HITL for native tools, but MCP server allow matching is incomplete (`mcp_<server>_<tool>` often fails closed on allowlist before subset can be proven), and dangerous MCP names are not defaulted to `REQUIRE_CONFIRM`.
3. Registry RBAC auto-includes tools under an agent's `mcp_servers` for listing/execute — listing can look like permission unless the gate is MCP-aware.

### Beat 3: What Will Change
1. Extend `ToolPolicyGate` so agent `mcp_servers` correctly authorize scoped `mcp_<server>_<tool>` names (prefix match), then still apply matched-subset + durable policy.
2. Outside matched IDs / unknown MCP → `BLOCK` (never executor). Dangerous MCP → `REQUIRE_CONFIRM` → existing HITL.
3. Document/enforce MCP = transport only on adapter/registry mount path (no parallel auth).
4. Proof: red "listed MCP tool outside matched IDs never runs"; green + live if feasible. Push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-MCPGATE-001]**: MCP `tools/list` / mount is transport/discovery only — listing ≠ authorization to execute.
- [x] **[REQ-MCPGATE-002]**: Mounted MCP tool calls hit matched capability subset (when job-bound) **and** `ToolPolicyGate` `ALLOW` | `REQUIRE_CONFIRM` | `BLOCK` before executor.
- [x] **[REQ-MCPGATE-003]**: Outside-subset or unknown MCP tool → `BLOCK`; handler/executor never runs.
- [x] **[REQ-MCPGATE-004]**: Dangerous MCP tools → `REQUIRE_CONFIRM` → existing HITL park/resume (no parallel HITL).
- [x] **[REQ-MCPGATE-005]**: Extends `MCPClientAdapter` / `ScopedToolRegistry` / `ToolPolicyGate` — do not invent parallel auth. Out of scope: CARD-226, new Studios.
- [x] **[REQ-MCPGATE-006]**: Automated tests red→green including listed-MCP-outside-matched-IDs never runs; ruff clean; CHANGELOG; push `feat/*` only — never qa/main. Live proof on Jarvis when feasible → In Review or Done.

---

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: listed MCP outside matched IDs must hard-BLOCK with decision log; no silent run.
- Out of scope: CARD-226, new MCP transports, UI polish beyond Obs decision log already shipped.

## 4. Modules Likely Touched

- `src/application/safety/tool_policy_gate.py` — MCP allow + subset + dangerous defaults
- `src/infrastructure/mcp/client_adapter.py` — transport-only contract notes
- `src/application/kernel/tool_registry.py` — mount ≠ auth notes
- `tests/unit/safety/test_mcp_tool_policy_gate.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- TDD: red "listed MCP tool outside matched IDs never runs" first, then green.
- Extend gate — do not fork a second MCP auth path.

## 6. Marathon Build Notes (Jarvis 2026-09-10 ET)

- Fixed ToolPolicyGate MCP server prefix allow (mcp_<server>_<tool>) so subset/dangerous paths are reachable.
- Outside matched IDs / unknown MCP -> BLOCK; dangerous MCP token heuristic -> REQUIRE_CONFIRM -> existing HITL.
- Transport-only notes on MCPClientAdapter / MCPClientManager / ScopedToolRegistry.mount_mcp_tool.
- Tests: tests/unit/safety/test_mcp_tool_policy_gate.py (6) + CARD-221 suites green.
- Status: **Done** (unit green + live smoke artifact on Jarvis).

