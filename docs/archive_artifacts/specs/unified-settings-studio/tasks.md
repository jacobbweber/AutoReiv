# Implementation Tasks: Unified Settings Studio & Model Matrix

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SET-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Provider Preset Registry & Endpoints (`[REQ-SET-001]`, `[REQ-SET-006]`)
- [ ] **Task 1.1**: [RED] Write unit tests in `tests/unit/settings/test_provider_presets.py` validating presets and model discovery endpoint.
- [ ] **Task 1.2**: [GREEN] Implement `src/application/settings/presets.py` and REST route `GET /api/settings/presets` in `src/web/app.py`.

### Slice 2: Dynamic Model Discovery & Live Hardware Fit (`[REQ-SET-002]`, `[REQ-SET-004]`)
- [ ] **Task 2.1**: [RED] Write tests in `tests/unit/settings/test_model_discovery.py` testing live discovery, model tagging, and RAM fit categorization.
- [ ] **Task 2.2**: [GREEN] Implement dynamic model discovery endpoint `GET /api/models/discover` and memory fit evaluation in `src/web/app.py`.

### Slice 3: Purpose Matrix Harmonization & Consolidated Web UI (`[REQ-SET-003]`, `[REQ-SET-005]`)
- [ ] **Task 3.1**: [RED] Write integration tests in `tests/unit/web/test_unified_settings_ui.py`.
- [ ] **Task 3.2**: [GREEN] Update `src/web/templates/index.html` and `src/web/static/app.js` with unified Provider dropdown, auto-filled URLs, dynamic Model Picker, cleaned Purpose Routing Matrix, and live Hardware Fit table.

### Slice 4: Verification, Traceability, & PR Gate
- [ ] **Task 4.1**: Run full test suite (`pytest`) and linters (`ruff check .`).
- [ ] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight` (90 requirements verified).
- [ ] **Task 4.3**: Conclude Milestone 15 and merge into `qa`.
