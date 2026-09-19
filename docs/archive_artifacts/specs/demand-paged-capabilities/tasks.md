# Vertical Slice Tasks: Demand-Paged Capability Engine & Progressive Tool Mounting

> **Spec Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/demand-paged-capabilities/requirements.md)  
> **Card Reference**: [CARD-362](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-362-demand-paged-capability-engine-progressive-tool-mounting.md)

---

## Slice 1: Rule of 7 Entropy Cap & Dynamic Paging (`[REQ-CAP-PAGE-001]`, `[REQ-CAP-PAGE-002]`, `[REQ-CAP-PAGE-003]`)

- [x] **Task 1.1** `[REQ-CAP-PAGE-001]`: [RED] Write unit test in `tests/unit/kernel/test_demand_paged_tools.py` asserting that `AgentKernel._resolve_active_tools()` never returns more than 8 tools under any profile or skill combination, and verifies clamping order.
- [x] **Task 1.2** `[REQ-CAP-PAGE-001]`, `[REQ-CAP-PAGE-002]`: [GREEN] Implement `MAX_ACTIVE_TOOLS_PER_TURN = 8` and lean baseline platform tool resolution in `AgentKernel` and `ScopedToolRegistry`.
- [x] **Task 1.3** `[REQ-CAP-PAGE-003]`: [GREEN] Verify that activating skills (e.g. `wiki`, `coding`, `diagnostics`) pages in skill-specific tools while evicting unneeded tools to remain within the 8-tool ceiling.
- [x] **Task 1.4**: [REFACTOR] Ensure system prompt builder appends the compact 1-line capability index when skills are not pre-mounted.

---

## Slice 2: Orchestrator Phase-Bound Scoping & Telemetry (`[REQ-CAP-PAGE-004]`, `[REQ-CAP-PAGE-005]`)

- [x] **Task 2.1** `[REQ-CAP-PAGE-004]`: [RED] Write unit test verifying that phase transitions in `JobPhaseOrchestrator` dynamically scope tools to the active phase's matched capabilities.
- [x] **Task 2.2** `[REQ-CAP-PAGE-004]`: [GREEN] Wire phase-level capability resolution to kernel streaming turn options in `chat.py`.
- [x] **Task 2.3** `[REQ-CAP-PAGE-005]`: [GREEN] Record `active_tool_count` and `tool_schema_chars` in telemetry turn spans.
- [x] **Task 2.4**: [REFACTOR] Clean up legacy unused tool allowlists and verify zero schema bloat.

---

## Slice 3: Verification & Preflight Gates

- [x] **Task 3.1**: Run `pytest tests/unit/kernel/test_demand_paged_tools.py` and full kernel test suite.
- [x] **Task 3.2**: Run `ruff check src/ tests/` and `npm run lint:frontend`.
- [x] **Task 3.3**: Sync `docs/rtm.json` with requirements `[REQ-CAP-PAGE-001]` through `[REQ-CAP-PAGE-005]`.
- [x] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]`.
