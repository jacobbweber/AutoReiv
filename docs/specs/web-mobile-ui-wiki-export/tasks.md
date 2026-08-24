# Implementation Tasks: Responsive Web & Mobile Front-Door with Wiki Export

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-WEB-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Wiki Export Service & Path Jailing
- [x] **Task 1.1** `[REQ-WEB-003]`: [RED] Write failing unit tests in `tests/unit/web/test_wiki_export_service.py` verifying YAML frontmatter generation, safe filename sanitization, and path-jailed file writing.
- [x] **Task 1.2** `[REQ-WEB-003]`: [GREEN] Implement `WikiExportService` in `src/application/web/wiki_export_service.py`.

### Slice 2: REST & SSE Streaming API Gateway
- [x] **Task 2.1** `[REQ-WEB-001]`, `[REQ-WEB-004]`, `[REQ-WEB-005]`, `[REQ-WEB-006]`: [RED] Write failing integration tests in `tests/unit/web/test_web_api.py` testing agent listing, session CRUD, SSE chat streaming, wiki export, settings endpoints, KPI endpoints, and routine triggers using FastAPI `TestClient`.
- [x] **Task 2.2** `[REQ-WEB-001]`, `[REQ-WEB-004]`, `[REQ-WEB-005]`, `[REQ-WEB-006]`: [GREEN] Implement FastAPI application routes in `src/web/app.py`.

### Slice 3: Responsive Multi-View SPA Client (Desktop & Mobile)
- [x] **Task 3.1** `[REQ-WEB-002]`, `[REQ-WEB-003]`, `[REQ-WEB-004]`, `[REQ-WEB-005]`, `[REQ-WEB-006]`: Implement responsive HTML/JS/CSS client in `src/web/templates/index.html` and `src/web/static/app.js` supporting live streaming, collapsible `<think>` tags, copy/wiki buttons, settings studio, KPI dashboard, and routine controls.

### Slice 4: Verification, Traceability, & QA Gate
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
