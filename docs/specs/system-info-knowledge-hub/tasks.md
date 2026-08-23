# Implementation Tasks: System Info Conceptual Knowledge Hub and Architectural Overviews

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SYST-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: System Info Topic Catalog & Service (`[REQ-SYST-001]`, `[REQ-SYST-003]`)
- [ ] **Task 1.1**: [RED] Write unit tests for `SystemInfoService` in `tests/unit/web/test_system_info_service.py`.
- [ ] **Task 1.2**: [GREEN] Implement `SystemInfoService` in `src/application/web/system_info_service.py` with comprehensive, rich markdown chapters on Architecture, Concept Hierarchy, Skill Packs, Purpose Matrix, Multi-Agent Orchestration, and Safety Guardrails.

### Slice 2: REST API Endpoints & Web UI Transformation (`[REQ-SYST-001]`, `[REQ-SYST-002]`)
- [ ] **Task 2.1**: Update `src/web/app.py` with `GET /api/system-info/topics` and `GET /api/system-info/topic/{id}`.
- [ ] **Task 2.2**: Update `src/web/templates/index.html` and `src/web/static/app.js` to rename sidebar item to `[ℹ️ System Info]`, populate topic list, and render clean markdown with Mermaid PTZ support.

### Slice 3: Verification, Pre-Flight Gates & Session Wrap-Up
- [ ] **Task 3.1**: Run full test suite (`pytest`) and linting (`ruff check .`).
- [ ] **Task 3.2**: Verify RTM integrity (`verify_rtm.py --pre-flight` with all 117 requirements passing).
- [ ] **Task 3.3**: Live test System Info page in browser.
