# [ADR-0061] Capability Scoping: Skills-Only Permission, Automatic Selection, One Enforcement Point

> **Status**: Accepted  
> **Date**: 2026-09-26  
> **Accepted**: 2026-09-26 (Jacob locked decisions A-J after the CARD-537 scoping investigation)  
> **Deciders**: Jacob Weber (Product Owner), coding assistant  
> **Consulted**: CARD-537 runtime investigation (branch `feat/card-532-live-qa-runner`, 2026-09-26); CARD-529 and CARD-532 live evidence  
> **Related Cards**: [CARD-539](../cards/CARD-539-capability-scoping-one-allowed-tools-function.md) (implementation), [CARD-537](../cards/CARD-537-autoreiv-ignores-newly-granted-tool.md), [CARD-529](../cards/CARD-529-developer-modify-tool-loops-and-fails.md), CARD-520, CARD-511  
> **Amends**: [ADR-0052](./0052-skill-and-tool-scoping-and-specialist-dispatch.md) section 3 (Layer 1 / Layer 2 only narrow inside ticked skills) and section 4 (dispatch routes to the covering agent); [ADR-0054](./0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) (agents specialize by domain; Rule of 7 is a selection clamp inside the allowed set); [ADR-0056](./0056-durable-runtime-registry-hybrid-c-plus.md) 4.2 item 5 (SQLite skill bindings are the only skill-to-tool source; additive grants are skill ticks); [ADR-0057](./0057-three-studios-and-developer-mediated-authoring.md) 4.2 (agent-to-skill pills and skill-to-tool bindings are the only scoping edges); [ADR-0060](./0060-retire-the-agent-training-factory.md) 4.1 (a Developer-built tool reaches an agent only as an accepted skill attachment)

> **Note (2026-09-28, CARD-570 / [ADR-0062](./0062-agents-and-skills-are-files-no-packs.md))**: skill-to-tool bindings now come from the winning `SKILL.md` `tools:` list (shipped `platform/skills` or the data-dir user copy). SQLite `skill_tool_bindings`, pack.json skill lists and seeds are gone; `resolve_allowed_tools` is still the only decider.

> **Note (2026-09-29, CARD-578 / [ADR-0064](./0064-tools-load-all-at-once.md))**: rule 4 selection is gone. There is no intent matcher, `activate_skill` or per-turn clamp; every allowed tool is sent on every call, only job/phase policy narrows, and a tool runs only if it was sent on that call.

> **Note (2026-10-01, CARD-596)**: rule 6 (Route, do not refuse) is amended: model-driven routing was unreliable on nemotron. Agents no longer hand off to other agents (except Architect/Toolsmith → Developer for coding). Instead, the user picks the agent in Chat; the generated domain line informs the model of covering agents to direct the user to open in Chat, or offers Ask Developer when none covers it.

---

## 1. Context

The CARD-537 investigation found that "which tools may this agent use" is decided in several places that disagree:

- `resolve_scoped_tools` (`agent_packs/schema.py`) mounts the tools of any active skill without checking the agent's ticked `allowed_skill`.
- `ScopedToolRegistry.get_tools_for_agent` (`kernel/tool_registry.py`) unions `allowed_tool_names` with scoped tools, except for AutoReiv, where it ignores `allowed_tool_names`. It also adds MCP, storage, memory and `read_document_file` tools from profile flags.
- `_execute_inner` (same file) and `ToolPolicyGate` (`safety/tool_policy_gate.py`, `_agent_allowed_names`) each compute a third and a fourth allowed set; for AutoReiv, execute allows every `PLATFORM_SKILL_TOOLS` tool whether ticked or not.
- Selection widens instead of narrowing: `_match_intent_skills`, `activate_skill`, and the global capability catalog match (`CapabilityCatalogResolver.resolve`, first 256 rows only) mount skills that are not ticked; `_resolve_active_tools` falls back to the full list when the catalog subset is empty; `list_available_skills_and_tools` returns the whole registry; the system prompt advertises a hard-coded list of domains and every MCP server.
- `NativeToolService._grant` writes a Developer-built tool straight into `allowed_tool_names`. Agent Studio has no tool ticks, so the grant is invisible, AutoReiv never sees it (CARD-537), and the next Studio Save rebuilds the list from skills and drops it.
- Domain text is hand-written in each prompt and tells agents to refuse.

Result: humans cannot see or control what an agent can do, the model is offered tools it may not call (CARD-529), and a granted tool is callable but never offered (CARD-537).

## 2. Why scoping exists (J)

1. Local models choose tools accurately only from a short, relevant list.
2. A confused or prompt-injected agent can only reach what its skills allow.
3. An operator can read an agent's power from its ticks in Agent Studio.

## 3. Decision (rules)

1. **Permission vs selection (A).** Permission is what an agent may ever use: coarse, human-controlled, set by skill ticks in Agent Studio. Selection is what is loaded for one turn: automatic, and only from the permitted set. Humans never curate selection.
2. **Skills only (B).** A tool reaches an agent only through a ticked skill, plus the fixed `REQUIRED_PLATFORM_TOOLS`. Every tool is bound to at least one skill with a runbook, however small. There are no loose per-agent tool grants and no "extra tools" checkboxes. *Rationale: the runbook tells the model when to use the tool, and one kind of tick keeps the UI legible.*
3. **One enforcement point (C).** One function, `resolve_allowed_tools(agent)` (created by CARD-539 in `src/application/agent_packs/allowed_tools.py`), computes the allowed set. The model's tool list, `_execute_inner` and `ToolPolicyGate` all call it. No agent id (including `autoreiv`) is special-cased. *Rationale: three copies drifted into the CARD-529 and CARD-537 bugs.*
4. **Selection only narrows (D).** The intent matcher, `activate_skill`, the capability catalog match and the per-turn tool clamp (15 since CARD-562; was 8) choose from the allowed set only. An empty intersection means no extra tools, never the full list. `activate_skill` refuses a skill that is not ticked. Catalog matching searches the agent's own ticked skills, with no scan cap. `list_available_skills_and_tools` never presents the global registry as usable.
5. **Risk tiers (E).** Inside ticked skills, read-only tools run freely; write, network and destructive tools ask for per-call confirmation through the existing `require_confirm` policy. Jacob approves changes to permission, not every action.
6. **Route, do not refuse (F).** An out-of-domain request is handed off to the agent whose skills cover it. Only if no agent can, the agent says so and offers Ask Developer (CARD-520 path). No built-in prompt tells an agent to refuse.
7. **Domain generated from ticks (G).** Each agent's domain line and its one-line routing summary are generated from its ticked skills at runtime, not hand-written.
8. **Learning is a proposal with evidence (H).** Teach and Developer draft a new skill (runbook, tools, passing test, live run) or propose attaching a tool to an existing skill of the target agent. It lands as a pending approval; when Jacob accepts, it becomes a tick visible in Agent Studio. Nothing writes an agent's tool list directly. Studio Save never silently drops accepted state. An "auto-accept low-risk read-only proposals" setting may come later, default off (recommended off; not built now).
9. **Scale (I).** No hard cap on agents; the design must work with a few dozen domain agents. Agents specialize by domain, skills by task. One shared skill library is tickable on many agents (no per-agent copies). The router sees only agent names and generated one-line summaries, never all skills. When one agent's skill index grows too large, the agent searches its own skills only.

## 4. Considered options

- **Status quo** (per-agent tool lists, skill mounts, special cases): rejected; it produced CARD-529 and CARD-537 and hides permission from the operator.
- **Skills plus "extra tools" ticks**: rejected; two kinds of ticks, tools without runbooks, and grants that bypass skill design.
- **Skills only, one resolver, narrowing selection (chosen).**

## 5. Consequences

- Positive: one place to audit and test; what Jacob ticks is exactly what an agent can reach; smaller, relevant tool lists for local models; agents grow by accepted proposals.
- Negative: every new tool needs a runbook and a skill binding; a Developer-built tool is unusable until Jacob accepts it; existing `allowed_tool_names` grants need a real migration (CARD-539); more handoffs between agents.

## 6. Compliance

- Always-on rule `.agents/rules/capability-scoping.md`.
- CARD-539 guard tests: an architecture test fails if any module other than `resolve_allowed_tools` computes an allowed-tools set; property tests that selection is always a subset of allowed; `activate_skill` on an unticked skill fails; no `autoreiv` special case; an accepted skill survives a Studio Save.
- Live QA journeys (`scripts/live_qa.py`): CARD-520 proposal, accept, then answer; out-of-domain handoff instead of refusal.
- CARD-568: the flat lists are gone everywhere (`allowed_tool_names` / `pack_tool_names` fields, the `allowed_tools_json` / `pack_tools_json` columns, the Studio API fields and `capability_migration`). The data dir was wiped instead of migrated. A pack.json that still has a flat list is rejected on import. Guard: `tests/unit/agent_skills/test_card568_no_tool_lists.py`.
