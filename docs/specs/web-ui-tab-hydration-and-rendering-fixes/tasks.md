# Implementation Tasks: Web UI Tab Hydration And Rendering Fixes

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-FIX-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Agent Studio & Skill Pack Grid Hydration
- [ ] **Task 1.1** `[REQ-FIX-001]`: Ensure `renderSkillsCatalog()` executes deterministically on every `loadAgentForge()` call.
- [ ] **Task 1.2** `[REQ-FIX-001]`: Verify all checkboxes match active agent's tool set.

### Slice 2: System Info & Markdown Rendering Resilience
- [ ] **Task 2.1** `[REQ-FIX-002]`: Harden `loadSystemDocsNav()` with safe error fallbacks and default topic auto-selection.
- [ ] **Task 2.2** `[REQ-FIX-002]`: Guard mermaid diagram rendering against unhandled exceptions.

### Slice 3: Wiki Studio Auto-Selection, Mobile Drawer & Mind Map / Graph
- [ ] **Task 3.1** `[REQ-FIX-003]`: Auto-load first staged/warehouse note on initial Wiki Studio load.
- [ ] **Task 3.2** `[REQ-FIX-003]`: Add visible text labels and drawer trigger buttons on mobile viewports.
- [ ] **Task 3.3** `[REQ-FIX-004]`: Harden `openMindMap()` canvas sizing and `wikiGraphViewBtn` Mermaid rendering.

### Slice 4: Tab Switching Error Isolation & Verification
- [ ] **Task 4.1** `[REQ-FIX-005]`: Wrap tab loaders in try/catch boundaries within `switchTab()`.
- [ ] **Task 4.2**: Run pre-flight verification `verify_rtm.py --pre-flight` and end-to-end testing.

