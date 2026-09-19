# Implementation Tasks: Skill Pack Hierarchy, Guardrails, and System Documentation Browser

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SKIL-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Skill Pack Grouping Catalog & Manifests (`[REQ-SKIL-001]`)
- [x] **Task 1.1**: [RED] Write unit test for Skill Pack catalog aggregation in `tests/unit/skills/test_skill_pack_catalog.py`.
- [x] **Task 1.2**: [GREEN] Implement Skill Pack grouping and manifest mapping in `src/application/skills/manifest.py` and enhance `GET /api/skills/catalog`.

### Slice 2: Deterministic Guardrail Engine & Invariants (`[REQ-SKIL-003]`)
- [x] **Task 2.1**: [RED] Write unit tests for agent specification guardrails in `tests/unit/agents/test_agent_guardrails.py`.
- [x] **Task 2.2**: [GREEN] Implement `AgentProfileGuardrail` in `src/domain/agents/guardrails.py` and enforce in `AgentBuilderSkill` and `src/web/app.py`.

### Slice 3: Agent Forge Skill Pack Hierarchy UI (`[REQ-SKIL-002]`)
- [x] **Task 3.1**: Enhance Card 5 (Tool Capabilities) in `src/web/templates/index.html` and `src/web/static/app.js` to render hierarchical collapsible Skill Packs with *"Select All"* bundle toggles and granular checkboxes.

### Slice 4: System Documentation Service & Browser View (`[REQ-SKIL-004]`, `[REQ-SKIL-005]`)
- [x] **Task 4.1**: [RED] Write unit test for `SystemDocumentationService` in `tests/unit/web/test_system_docs_service.py`.
- [x] **Task 4.2**: [GREEN] Implement `SystemDocumentationService` in `src/application/web/system_docs_service.py` and REST endpoints `GET /api/docs/nav` & `GET /api/docs/content`.
- [x] **Task 4.3**: Add navigation tab `[📖 System Docs]` and `#view-docs` in `src/web/templates/index.html` and `src/web/static/app.js` with tree sidebar and Markdown viewer.

### Slice 5: Verification, DoD Pre-Flight & Session Wrap-Up
- [x] **Task 5.1**: Run full test suite (`pytest`) and linters (`ruff check .`).
- [x] **Task 5.2**: Validate RTM integrity (`verify_rtm.py --pre-flight` with all 106 requirements passing).
- [x] **Task 5.3**: Live test Skill Pack bundle selection, guardrail rejections, and System Docs reader on running server.
