---
id: CARD-539
title: "Capability scoping: one allowed-tools function, skills-only permission, selection only narrows, route not refuse"
status: In Progress
created: 2026-09-26
branch: qa
adr: ADR-0061
related:
  - CARD-537
  - CARD-529
  - CARD-520
  - CARD-511
  - CARD-532
labels:
  - type:architecture
  - area:agents
  - area:tools
  - P1
---

# [CARD-539] Capability scoping: one allowed-tools function

> **Status**: In Progress on `feat/card-539-capability-scoping` (from qa `2cfae4bb`). **Build approved** by Jacob 2026-09-26 ~9:23 PM ET: D1-D7 as recommended, D8-D11 as recommended, and the AGENTS.md lock rewording.  
> **ADR**: [ADR-0061](../adr/0061-capability-scoping-skills-only-permission-one-enforcement-point.md) (locked decisions A-J, Jacob 2026-09-26)  
> **Folds in**: CARD-529 items 2 and 4 (tools offered outside the allowlist; keyword-family catalog routing). CARD-529 keeps items 1 and 3.  
> **Unblocks**: CARD-537.

---

## 1. Why / Intent (Beat 1)

Jacob ticks skills per agent in Agent Studio and expects that to be the whole story: an agent can use exactly the tools of its ticked skills, nothing else, and it grows only when he accepts a proposal. Each turn the system picks a few relevant tools from that set on its own. When a request belongs to another agent, it goes there instead of being refused. Why scoping matters: local-model tool-choice accuracy, limiting damage from confusion or injected instructions, and legibility (ADR-0061 section 2).

## 2. What AutoReiv Does Now (Beat 2)

Four places compute "allowed", and several paths widen it:

| Where | What it does today |
|---|---|
| `agent_packs/schema.py` `resolve_scoped_tools` | With `active_skills`, mounts those skills' tools (code tables `PLATFORM_SKILL_TOOLS` / `DYNAMIC_SKILL_TOOLS`, SQLite bindings, pack.json `skills[].tools`) without checking `allowed_skill`. |
| `kernel/tool_registry.py` `get_tools_for_agent` | `allowed_tool_names` ∪ scoped, except AutoReiv (scoped only, `allowed_tool_names` ignored). Adds MCP servers, storage, memory, `read_document_file` from profile flags. |
| `kernel/tool_registry.py` `_execute_inner` | Own RBAC set; AutoReiv may call every `PLATFORM_SKILL_TOOLS` tool, ticked or not. |
| `safety/tool_policy_gate.py` `_agent_allowed_names`, `_capability_tool_names` | Third set (static scoped ∪ `allowed_tool_names`) plus the job's matched-capability subset. |
| `kernel/agent_kernel.py` `_match_intent_skills` | Regex keywords mount wiki, diagnostics, coding, MCP domains for AutoReiv, not limited to ticks. |
| `skills/platform_primitives.py` `activate_skill` | Mounts any skill in the code tables or any MCP family; no tick check. |
| `capabilities/resolver.py` `CapabilityCatalogResolver.resolve` | Keyword-scores the global catalog (first 256 rows, `scan_limit`); `skill.*` hits become active skills. |
| `agent_kernel.py` `_resolve_active_tools` | Narrows to the catalog subset but falls back to the full list when the intersection is empty (`or tools`); then the 8-tool clamp. |
| `agent_kernel.py` `_build_effective_system_message` | Hard-coded "Available Capabilities & Skills (Demand-Paged)" block advertising wiki/coding/diagnostics/tasks/mcp-engineering and every MCP server, for every agent. |
| `skills/agent_builder_tools.py` `list_available_skills_and_tools` | Returns the whole tool registry. |
| `tools/native_packaging.py` `NativeToolService._grant` | Appends a Developer-built tool to the target agent's `allowed_tool_names`, invisible in Studio. `_sync_policy` sets its HITL tier. |
| `tools/developer_mediation.py` `format_developer_prompt` | Tells Developer "Register with grant_agent_ids [...]". |
| `web/static/modules/studios/forge.js` Save | Rebuilds `allowed_tool_names` from ticked skills; drops any grant. |
| `web/routers/agents.py` `update_agent` | Stores whatever `allowed_tool_names` the payload sends. |
| `platform-packs/autoreiv/pack.json`, `domain/agents/good_agent_instructions.py` `render_good_agent_instructions` | Hand-written domain plus "Refuse requests outside your authorized domain". |
| `orchestration/directory_service.py` `_to_compact_card`, `orchestration_tools.lookup_agents` | Router summary = first sentence of the prompt + first 4 tools. |

Symptoms: CARD-537 (granted `get_weather` callable but never offered to AutoReiv, which refuses); CARD-529 (Developer offered `repo_file_read` via a catalog `skill.coding` match, then blocked by the gate).

## 3. What Will Change (Beat 3)

1. **New `src/application/agent_packs/allowed_tools.py`**: `resolve_allowed_tools(agent) -> AllowedTools` = `REQUIRED_PLATFORM_TOOLS` ∪ tools bound to the agent's ticked skills (D1 source), with provenance (tool -> skill) for errors and UI. Cached per agent revision. The only function that decides allowed tools.
2. **Callers use it**: `get_tools_for_agent`, `_execute_inner` and `ToolPolicyGate._agent_allowed_names` call `resolve_allowed_tools`; all `autoreiv` branches go. `resolve_scoped_tools` becomes seed/selection helper only or is removed.
3. **Selection narrows** (one `select_turn_tools(agent, allowed, ...)` in the kernel): `_match_intent_skills` (all agents, keywords from ticked skills' frontmatter), `activate_skill` (refuses unticked skills with a plain message), catalog subset and the 8-tool clamp all intersect with `allowed`. Empty intersection -> required tools only. `_capability_tool_names` only narrows.
4. **Catalog**: `CapabilityCatalogResolver.resolve` takes the agent's ticked skill ids and filters in the store query; `scan_limit` goes. Multi-phase jobs route a phase to the agent whose skills cover it (handoff), never mount foreign skills.
5. **Prompt**: the hard-coded capability block goes; `render_skill_index` (ticked skills only) stays; when the index is large (D6), a `skill_search` over the agent's own skills replaces it. The domain line is generated from ticked skills at runtime (D5).
6. **Route, do not refuse**: `pack.json` and `render_good_agent_instructions` replace the refusal sentence with a handoff instruction; when no agent covers the request, reply that none can and offer Ask Developer. Router summaries (`_to_compact_card`, `lookup_agents`) come from ticked skills; no tool lists.
7. **Proposals, not grants**: `_grant` and `grant_agent_ids` go. Developer (and Teach) produce a pending proposal: new skill (runbook + tools + passing test + live-run evidence) or "attach tool T to skill S of agent A". Accepting writes the SQLite skill binding (and the tick for a new skill). `_sync_policy` stays (risk tier). `format_developer_prompt` asks for a proposal, not a grant.
8. **Studio and API**: forge.js Save sends skill ticks only; `update_agent` ignores `allowed_tool_names` / `pack_tool_names` in payloads and rejects a stale save (version check) so accepted ticks are never silently dropped. Pending proposals show in Agent Studio.
9. **`list_available_skills_and_tools`**: returns skills and tools as a catalog for authoring, clearly marked "not callable by you"; never merged into a tool list.
10. **Migration** (section 6) and seeds: platform pack.json files drop `allowed_tool_names` / `pack_tool_names`; tools come from skills.

## 4. What Dies Today (Beat 4)

- `autoreiv` special cases in `get_tools_for_agent`, `_execute_inner`, `_agent_allowed_names`, `_match_intent_skills`, chat context tool listing (`routers/chat.py`).
- `allowed_tool_names` and `pack_tool_names` as permission inputs (read path; column kept one release as derived, read-only).
- Profile-flag tool paths in `get_tools_for_agent`: storage, memory, `read_document_file`, per-agent `mcp_servers` (replaced per D2, D3).
- `activate_skill` for unticked skills and raw MCP families; the `tasks` alias with no runbook.
- `_resolve_active_tools` fallback `or tools`; `CapabilityCatalogResolver` `scan_limit` and global matching for turns.
- The hard-coded "Available Capabilities & Skills (Demand-Paged)" prompt block.
- `NativeToolService._grant`, `grant_agent_ids` (validate, API, `native_tool_engineering.py`, `routers/native_tools.py`), the `developer_mediation` grant sentence.
- forge.js `derivedTools` / `packTools` payload; hand-written "Refuse requests outside your authorized domain" text; router `skills=tools[:4]`.
- Tests that lock any of the above.

## 5. Decisions

| # | Kind | Question | Recommendation | Needs Jacob |
|---|---|---|---|---|
| D1 | architecture | Canonical skill-to-tool source | SQLite skill bindings (ADR-0056); `PLATFORM_SKILL_TOOLS`, `DYNAMIC_SKILL_TOOLS` and pack.json `skills[].tools` become seed input reconciled into bindings at boot | yes |
| D2 | architecture | MCP tools | An attached MCP server reaches an agent only through a skill that binds its tools (attach creates a small runbook skill, tickable); per-agent `mcp_servers` no longer grants tools | yes |
| D3 | product | Profile flags | Storage checkbox = tick of `sqlite-storage`; memory tools stay in REQUIRED (flag only controls the memory DB); `read_document_file` joins REQUIRED (read-only, operator attachments); `allow_wiki_access` retires (untick wiki skills instead) | yes |
| D4 | product | Proposal flow | Reuse `skill_proposals` pending approvals with an "attach tool to skill" kind; accept from the chat card or an Agent Studio "Pending" list; accepted = binding + visible tick | yes |
| D5 | product | Generated domain text | Store no domain section; inject at runtime: "Your domain: <ticked skill blurbs>"; routing summary = name + top skill names, max 160 chars | yes |
| D6 | product | Out-of-domain UX | Hand off without asking (a handoff is not a permission change), one-line notice in chat; if no agent covers it, say so with an Ask Developer button | yes |
| D7 | product | Auto-accept low-risk read-only proposals | Record only; default off; not built | yes (confirm off) |
| D8 | technical | Function name/location | `resolve_allowed_tools` in `agent_packs/allowed_tools.py`, returns set + provenance | no |
| D9 | technical | Skill index threshold | Switch to own-skill search above 20 ticked skills or ~1.5K index tokens | no |
| D10 | technical | Stale Studio save | `updated_at` version check, 409 with reload message | no |
| D11 | technical | Risk tier source | Tool registration carries `risk` (read_only / write / network / destructive); non-read-only defaults to `require_confirm`; operator `tool_policy` still overrides | no |

**Decision record (2026-09-26 ~9:23 PM ET):** Jacob approved D1-D7 exactly as recommended above and delegated D8-D11 (taken as recommended). Implementation notes:
- D1: SQLite `skill_tool_bindings` rows win for a skill; the seeds (pack.json `skills[].tools`, `PLATFORM_SKILL_TOOLS`, `DYNAMIC_SKILL_TOOLS`) are read only when a skill has no binding row. This is reconcile-on-read: same result as copying seeds at boot, without marking platform skills as operator-saved (which would freeze seed updates).
- AGENTS.md runtime lock reworded (Jacob): the chat panel shows the tools of the agent's ticked skills; the model sees at most 8 selected from those per turn.

## 6. Migration (real, idempotent, runs once at startup)

1. Export every agent's `allowed_tool_names`, `pack_tool_names`, `allowed_skill` and `mcp_servers` to `{data}/migrations/card-539-allowlists.json` before any change.
2. For each agent compute `extra = allowed_tool_names - resolve_allowed_tools(agent)`.
3. For each extra tool: if an existing skill binds it, create a pending proposal "tick skill S on agent A"; if none does (native custom tools such as the CARD-520 grant), create a pending proposal "new skill with runbook for T on agent A" with a drafted minimal runbook. Nothing is auto-granted; until accepted the tool is not allowed.
4. Per-agent MCP servers and flags convert per D2/D3.
5. Record a marker setting and a `capability_migration` event per agent; a second run changes nothing. Tests cover fresh install and upgrade from a DB with grants.
6. Pre-build audit: diff each seeded platform agent's current effective set against the new derived set and list any loss in this card before building (for example AutoReiv currently reaching all `PLATFORM_SKILL_TOOLS` at execute).

## 7. Acceptance Criteria (EARS)

- **REQ-539-001**: THE SYSTEM SHALL compute an agent's allowed tools only in `resolve_allowed_tools`, as `REQUIRED_PLATFORM_TOOLS` ∪ tools bound to its ticked skills.
- **REQ-539-002**: THE SYSTEM SHALL use that set for the model's tool list, `_execute_inner` and `ToolPolicyGate`, with no agent-id special cases.
- **REQ-539-003**: WHEN any selection step runs (intent, `activate_skill`, catalog, clamp) THE SYSTEM SHALL output a subset of the allowed set; WHEN the intersection is empty THE SYSTEM SHALL mount no extra tools.
- **REQ-539-004**: WHEN `activate_skill` names a skill not ticked for the agent THE SYSTEM SHALL refuse it with a plain message and mount nothing.
- **REQ-539-005**: THE SYSTEM SHALL match capabilities only within the agent's ticked skills, with no scan cap.
- **REQ-539-006**: THE SYSTEM SHALL NOT offer the model any tool it may not call (closes CARD-529 item 2).
- **REQ-539-007**: WHEN Developer or Teach builds or attaches a tool for an agent THE SYSTEM SHALL create a pending proposal and SHALL NOT change the agent's permission until Jacob accepts.
- **REQ-539-008**: WHEN a proposal is accepted THE SYSTEM SHALL show the skill as ticked in Agent Studio and a later Studio Save SHALL keep it.
- **REQ-539-009**: WHEN a request is outside an agent's ticked skills and another agent's skills cover it THE agent SHALL hand off; WHEN no agent covers it THE agent SHALL say so and offer Ask Developer.
- **REQ-539-010**: THE SYSTEM SHALL generate each agent's domain line and routing summary from its ticked skills.
- **REQ-539-011**: WHILE a tool is not read-only THE SYSTEM SHALL require per-call confirmation unless operator policy says otherwise.
- **REQ-539-012**: WHEN the migration runs THE SYSTEM SHALL back up old allowlists, create proposals for extra tools, and change nothing on a second run.

## 8. Tests (write first, confirm red)

- **Architecture guard**: fails if any module other than `agent_packs/allowed_tools.py` builds an allowed-tools set (AST scan for reads of `allowed_tool_names` / `pack_tool_names` / `PLATFORM_SKILL_TOOLS` used as permission, and for `== "autoreiv"` in kernel, registry, gate, schema).
- **Property tests** (hypothesis): for random agents, ticks, intents, catalog hits and `activate_skill` calls, selected tools ⊆ allowed; empty intersection -> required only.
- `activate_skill` on an unticked skill fails; on a ticked skill mounts only its tools.
- AutoReiv special case gone: AutoReiv and a custom agent with the same ticks get identical tool lists and RBAC.
- Grant -> accept -> Studio Save round-trip keeps the skill ticked and the tool allowed; a stale Save gets 409.
- Migration: fresh install and upgrade with an `allowed_tool_names` grant produce a backup, one proposal, no permission change, idempotent second run.
- Tool list, `_execute_inner` and gate agree for every seeded agent.

## 9. Live QA (`scripts/live_qa.py`, desktop and phone)

1. **card-520 journey, updated**: Teach "needs a tool" -> Ask Developer builds `get_weather` -> a pending proposal to attach it to a skill of AutoReiv appears (no silent grant) -> accept -> the skill shows ticked in Agent Studio -> AutoReiv answers the Boston weather question in the same chat and a new chat.
2. **New routing journey**: ask AutoReiv for a shell/code change -> it hands off to Developer (no refusal text); ask for something no agent covers -> reply says so with Ask Developer.

## 10. Failure Modes

- Platform agents lose tools they relied on through side paths -> pre-build audit (6.6) and the per-agent agreement test.
- Migration silently removes a working grant -> backup JSON, pending proposals listed in Agent Studio, event per agent.
- Stale Studio tab overwrites an accepted tick -> version check (D10).
- The 8-tool clamp hides a needed tool -> model pages it in with `activate_skill` for a ticked skill; never beyond ticks.
- Handoff loops between agents -> jobs already cap handoffs (`budget_max_handoffs`); add the same cap for chat handoffs if missing, and never hand back to the origin agent in the same turn.
- Resumed jobs carry checkpoint capability ids from before the change -> intersected with allowed; fail closed with a plain fact.
- Prompt injection asks for an unticked skill -> refused and logged.
- Proposal fatigue -> D7 later, default off.

## 11. Human Verification Runbook (under 2 minutes)

1. Agent Studio -> AutoReiv: note the ticked skills; no tool checkboxes exist.
2. Chat with AutoReiv: "What is the weather in Boston?" -> it offers Ask Developer or hands off; no refusal wording.
3. After the Developer proposal, accept it; the new skill shows ticked; ask again -> weather answer.
4. Save AutoReiv in Agent Studio; ask again -> still works.
