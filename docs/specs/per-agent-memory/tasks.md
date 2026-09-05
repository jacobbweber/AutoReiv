# Implementation Tasks: Per-Agent Cognitive Memory System (Agent Brain)

> **Spec Reference**: docs/specs/per-agent-memory/requirements.md
> **Design Reference**: docs/specs/per-agent-memory/design.md
> **Work Card**: [CARD-116](file:///.github/cards/CARD-116-research-first-class-per-agent-memory-agent-brain.md)
> **Execution Strategy**: Strict Red-Green-Refactor TDD across 7 Sequential Vertical Slices

---

## Vertical Slice 1: Memory Path Resolver & Pack Schema Foundations
- [ ] Task 1.1: [REQ-MEM-001] Unit test `resolve_agent_memory_path` asserting path resolution to `packs/<agent_id>/<agent_slug>_memory.db` distinct from storage path.
- [ ] Task 1.2: [REQ-MEM-001] Extend `AgentProfile` and `pack.json` schema with `memory_enabled: bool = True`, `memory_retention_days: int = 30`, and `pinned_memory: str = ""`.
- [ ] Task 1.3: [REQ-MEM-001] Verify pack export/import preserves cognitive memory configuration while keeping `<agent_slug>_memory.db` distinct from domain `<agent_slug>_storage.db`.

## Vertical Slice 2: SQLite Memory Database Schema & FTS5 Repository
- [ ] Task 2.1: [REQ-MEM-002, REQ-MEM-005] Write Red integration tests for `AgentMemoryRepository` in `tests/unit/memory/test_agent_memory_repo.py`.
- [ ] Task 2.2: [REQ-MEM-002] Implement schema migration scripts initializing `pinned_memories`, `session_summaries`, `semantic_facts`, and `memory_events`.
- [ ] Task 2.3: [REQ-MEM-005] Initialize `semantic_facts_fts` virtual table with FTS5 triggers for Porter tokenization and BM25 text search.
- [ ] Task 2.4: [REQ-MEM-006] Implement half-life decay calculation formula in pure Python with unit tests verifying recency vs. access count reinforcement.

## Vertical Slice 3: Post-Turn Fact Extraction & Conflict Resolution Engine
- [ ] Task 3.1: [REQ-MEM-003] Write unit tests mocking fast extraction output and verifying candidate extraction parser.
- [ ] Task 3.2: [REQ-MEM-003] Implement `MemoryExtractorService` executing lightweight post-turn compilation pass.
- [ ] Task 3.3: [REQ-MEM-004] Implement automated conflict resolution pipeline (`ADD`, `UPDATE`, `DELETE`, `BUMP`) with deduplication against existing FTS facts.
- [ ] Task 3.4: [REQ-MEM-012] Verify extraction executes on local Ollama models with zero external vector DB dependencies.

## Vertical Slice 4: Dynamic Context Window Token Budgeting & Prompt Injection
- [ ] Task 4.1: [REQ-MEM-007] Write unit tests for `MemoryContextAssembler` verifying token budgets across small (8k), standard (16k), and large (128k) models.
- [ ] Task 4.2: [REQ-MEM-007] Implement prompt injection formatter assembling Shelf 1 (pinned), Shelf 2 (episodic), and Shelf 3 (semantic) into `AgentKernel`.
- [ ] Task 4.3: [REQ-MEM-011] Implement internal kernel memory tools: `recall_agent_memory` and `memorize_fact`.
- [ ] Task 4.4: [REQ-MEM-007] Verify prompt truncation safeguards guarantee Shelf 1 pinned directives are never dropped.

## Vertical Slice 5: Autonomous Consolidation & Maintenance Routine
- [ ] Task 5.1: [REQ-MEM-008] Write unit tests for `MemoryConsolidationRoutine` verifying duplicate merging and retention decay eviction.
- [ ] Task 5.2: [REQ-MEM-008] Implement asynchronous consolidation pass running during idle turns or background intervals.
- [ ] Task 5.3: [REQ-MEM-008] Verify background consolidation operates asynchronously without blocking active SSE chat streams.

## Vertical Slice 6: Agent Studio UI Cognitive Memory Controls & Inspector Drawer
- [ ] Task 6.1: [REQ-MEM-009] Write frontend Vitest tests for Cognitive Memory controls (`#forgeMemoryEnabled`, `#forgeMemoryRetentionDays`, `#forgePinnedMemory`).
- [ ] Task 6.2: [REQ-MEM-009] Implement UI section in `index.html` and wire event listeners in `forge.js` saving to `PUT /api/agents/{id}`.
- [ ] Task 6.3: [REQ-MEM-010] Implement Memory Inspector Drawer (`#agentBrainDrawer`) with live search table, `[ Forget Fact ]`, and `[ Purge Brain ]` buttons.
- [ ] Task 6.4: [REQ-MEM-010] Implement REST endpoints: `GET /api/agents/{id}/memory`, `DELETE /api/agents/{id}/memory/facts/{fact_id}`, and `DELETE /api/agents/{id}/memory`.

## Vertical Slice 7: End-to-End Verification, Performance Budgets & DoD Certification
- [ ] Task 7.1: [REQ-MEM-005] Execute retrieval latency benchmarks verifying FTS5 query completes in < 5ms.
- [ ] Task 7.2: Verify zero linting errors via `ruff check .` and `npm run lint:frontend`.
- [ ] Task 7.3: Run full regression test suite (748+ backend tests, 154+ frontend tests) verifying zero regressions.
- [ ] Task 7.4: Synchronize RTM matrix (`docs/rtm.json`) and certify DoD compliance.
