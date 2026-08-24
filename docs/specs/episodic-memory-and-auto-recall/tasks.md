# Task Breakdown: SQLite Episodic Fact Memory Store & Agent Auto-Recall

> **Spec Status**: Implemented  
> **Target Release**: Milestone 12 (v0.12.0)  
> **Card Reference**: [CARD-042](file:///.github/cards/CARD-042-sqlite-episodic-fact-memory-store-and-agent-auto-recall.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/episodic-memory-and-auto-recall/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/episodic-memory-and-auto-recall/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: SQLite Fact Search & Auto-Recall Skill
- [x] **Task 1.1**: Enhance `src/infrastructure/memory/sqlite_store.py` with `search_facts` supporting tokenized keyword search and confidence filtering (`[REQ-EPISODIC-001]`).
- [x] **Task 1.2**: Enhance `src/application/skills/memory_skill.py` with `render_memory_context` and `auto_recall` (`[REQ-EPISODIC-002]`).

### Slice 2: Agent Kernel Context Auto-Injection & REST Endpoints
- [x] **Task 2.1**: Update `src/application/kernel/agent_kernel.py` to auto-inject recalled episodic facts into system instructions (`[REQ-EPISODIC-003]`).
- [x] **Task 2.2**: Expose `GET`, `POST`, `DELETE` endpoints for `/api/memory/facts` in `src/web/app.py` (`[REQ-EPISODIC-004]`).

### Slice 3: Verification, Pre-Flight & Gate Closure
- [x] **Task 3.1**: Author unit and integration tests in `tests/unit/memory/test_episodic_memory.py` (`[REQ-EPISODIC-005]`).
- [x] **Task 3.2**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-EPISODIC-005]`).
- [x] **Task 3.3**: Author ADR-0042 and sync `docs/rtm.json` with `[REQ-EPISODIC-001]` through `[REQ-EPISODIC-005]`.
- [x] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

