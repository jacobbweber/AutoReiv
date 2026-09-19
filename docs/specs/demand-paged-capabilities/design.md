# Technical Design: Demand-Paged Capability Engine & Progressive Tool Mounting

> **Spec Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/demand-paged-capabilities/requirements.md)  
> **Card Reference**: [CARD-362](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-362-demand-paged-capability-engine-progressive-tool-mounting.md)  
> **Grounding**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)

---

## 1. Architecture Overview & Component Interactions

The Demand-Paged Capability Engine replaces static tool allowlists with dynamic, intent- and phase-driven progressive disclosure:

```
[ Operator Intent / Job Phase ]
                │
                ▼
[ Capability Intent & Phase Resolver ]
                │
                ▼ (Maps to Active Skill IDs)
[ Demand-Paged Capability Engine ] ──► Clamps to MAX_ACTIVE_TOOLS_PER_TURN = 8
                │
                ▼
[ Dynamic Tool Scoper ] ──► System Prompt: Lean Baseline Primitives (3 tools)
                │                         + 1-Line Compact Capability Index
                ▼
[ Completion Request ] ──► Total Tools <= 8 (Schema tax slashed from 16k to <500 tokens)
```

---

## 2. Core Constants & Data Structures

```python
MAX_ACTIVE_TOOLS_PER_TURN = 8

BASELINE_PLATFORM_TOOLS = (
    "activate_skill",
    "ask_clarification",
    "handoff_to_agent",
    "get_session_info",
)
```

### Dynamic Tool Resolution Strategy (`AgentKernel._resolve_active_tools`)
1. If `agent_id == 'direct'`, return `[]` (`tools=None`).
2. If `active_skills` is present or derived from intent matching, mount tools declared by those active skills.
3. If `matched_capability_ids` is present (from Job/Phase context), map capability IDs to corresponding tool names.
4. Merge baseline platform tools with skill-bound tools:
   - Primary: Active skill tools for the active turn or phase.
   - Secondary: Baseline platform coordination tools (`activate_skill`, `ask_clarification`, `handoff_to_agent`).
5. Enforce **Rule of 7 Cap**: `clamped_tools = resolved_tools[:MAX_ACTIVE_TOOLS_PER_TURN]`.

---

## 3. Compact Capability Index

Instead of serializing 40 tool schemas into JSON schemas in the API request, the system prompt includes a compact capability index:
```markdown
## Available Capabilities & Skills (Demand-Paged)
Use `activate_skill` to load full tool schemas for any domain:
- `wiki`: Local-first knowledge base notes, markdown documents, and PARA vault search.
- `coding`: File reading, writing, editing, and terminal script execution in the active project.
- `diagnostics`: System health checks, hardware metrics, and background service diagnostics.
- `tasks`: Routine automation, cron schedule management, and standing background jobs.
```

---

## 4. Telemetry Attribution

Turn spans record:
- `active_tool_count`: Number of tools mounted for the turn.
- `tool_schema_chars`: Character length of JSON serialized tool definitions.
- `tool_entropy_capped`: Boolean indicating if clamping was triggered.
