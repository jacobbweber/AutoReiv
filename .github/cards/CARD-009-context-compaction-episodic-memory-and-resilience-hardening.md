# [CARD-009] Context Compaction Episodic Memory and Resilience Hardening

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/context-compaction-and-resilience/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Prevent context overflow with sliding window summarization, persist episodic facts across sessions, and add exponential backoff retry jitter with connection pooling

---

## 2. What to Build
ContextCompactor, episodic_facts SQLite table, EpisodicMemorySkill, gateway retry loop with backoff and jitter, client connection pooling, and cycle detector in streaming

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
