# Implementation Tasks: [Feature Name]

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Core Domain Logic & Port Interfaces
- [ ] **Task 1.1** `[REQ-DOMAIN-001]`: [RED] Write failing unit test for core domain entity validation in `tests/unit/test_domain.py`.
- [ ] **Task 1.2** `[REQ-DOMAIN-001]`: [GREEN] Implement domain entity and value objects in `src/domain/entity.py`.
- [ ] **Task 1.3** `[REQ-DOMAIN-001]`: [REFACTOR] Apply KISS/Rule of Three to domain logic.

### Slice 2: Application Service & Port Adapter
- [ ] **Task 2.1** `[REQ-DOMAIN-002]`: [RED] Write failing integration test for application service in `tests/integration/test_service.py`.
- [ ] **Task 2.2** `[REQ-DOMAIN-002]`: [GREEN] Implement service use-case handler in `src/application/service.py`.
- [ ] **Task 2.3** `[REQ-DOMAIN-002]`: [GREEN] Implement infrastructure adapter in `src/infrastructure/adapter.py`.
- [ ] **Task 2.4**: [REFACTOR] Ensure DIP/LSP compliance across application ports.

### Slice 3: Verification, Traceability, & QA Handoff
- [ ] **Task 3.1**: Run complete test suite and linters (`pytest`, `ruff`).
- [ ] **Task 3.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 3.3**: Prepare step-by-step verification instructions for Human QA tester.
