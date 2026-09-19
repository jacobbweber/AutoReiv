# [CARD-362] Demand-Paged Capability Engine & Progressive Tool Mounting

> **Status**: Ready  
> **Created**: 2026-09-19  
> **Spec Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [docs/specs/demand-paged-capabilities/](file:///d:/Projects/Active/AutoReiv/docs/specs/demand-paged-capabilities/)  
> **Labels**: `type:feature`, `domain:kernel`, `domain:capabilities`, `architecture:autonomic-os`

---

## 1. Why / Intent

As established in **ADR-0054**, static agent tool allowlists loading 30–40 tools incur an enormous ~16,000 prompt token schema tax. On local dense models (such as Qwen 2.5 14B/32B/72B), this bloat degrades KV-cache pre-fill latency and dramatically increases tool-choice entropy, resulting in tool hallucinations and misrouted actions.

AutoReiv requires a **Demand-Paged Capability Engine** that enforces the **Rule of 7** (no more than 8 tools visible to the LLM per turn) and mounts tool schemas only when their corresponding skill or phase is actively bound.

---

## 2. What to Build

1. **Hard Tool Entropy Budget Cap (`MAX_ACTIVE_TOOLS_PER_TURN = 8`)**:
   - Update `AgentKernel._resolve_active_tools()` and `ScopedToolRegistry.get_tools_for_agent()` to enforce an upper limit of at most 8 tool definitions exposed to the model.
   - Deterministic priority ordering: Active skill/phase tools take precedence, supplemented by core coordination primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `get_session_info`).

2. **Compact 1-Line Capability Index**:
   - Instead of injecting large tool schemas into baseline turns, inject a concise markdown capability index (<500 tokens) in the system prompt summarizing available skills and activation keywords.

3. **Progressive Skill-Bound Tool Mounting & Dynamic Eviction**:
   - When a skill is activated (via intent, `activate_skill`, or `JobPhaseOrchestrator` phase binding), mount strictly the tools required for that skill.
   - Moving across turn or phase boundaries unmounts stale tools and pages in the active phase's tools, keeping the total count <= 8.

4. **Telemetry Attribution**:
   - Record `active_tool_count`, `tool_schema_chars`, and `tool_entropy_capped` in turn telemetry spans.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] **[REQ-CAP-PAGE-001]**: `AgentKernel._resolve_active_tools()` enforces a strict upper bound of at most 8 tools per turn across all agent profiles.
- [ ] **[REQ-CAP-PAGE-002]**: Default turns for `autoreiv` expose only the lean platform baseline tools (<= 4 tools) with a compact 1-line capability index in the system message.
- [ ] **[REQ-CAP-PAGE-003]**: Activating a skill dynamically mounts that skill's tools and evicts unneeded tools to maintain the 8-tool ceiling.
- [ ] **[REQ-CAP-PAGE-004]**: Orchestrator phase execution resolves and mounts tools filtered strictly to the active phase's matched capability IDs.
- [ ] **[REQ-CAP-PAGE-005]**: Turn telemetry spans record `active_tool_count` and `tool_schema_chars`.
- [ ] Automated tests green via `pytest tests/unit/kernel/test_demand_paged_tools.py`.
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Invariants

- Grounded in **ADR-0054** (Rule of 7 and Demand-Paged Capabilities).
- Zero breaking changes to Direct Mode (`direct`), which retains `tools=None`.
- Follow strict Red-Green-Refactor TDD on branch `feat/card-362-demand-paged-capabilities`.
- Wait for Jacob's explicit **build** before implementing code.
