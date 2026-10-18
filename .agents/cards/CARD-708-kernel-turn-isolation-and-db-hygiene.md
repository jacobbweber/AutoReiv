---
id: CARD-708
title: "Isolate AgentKernel per-turn state across subagent handoffs, eliminate per-step DDL/full-scan overhead, and make SQLite message sequencing & chat search bounded"
type: bug
status: In Review
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-708-kernel-turn-isolation-and-db-hygiene]
  checks: [tests/unit/kernel/test_card708_turn_isolation_and_db_hygiene.py]
branch: feat/card-708-kernel-turn-isolation-and-db-hygiene
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-708 Isolate AgentKernel per-turn state across subagent handoffs, eliminate per-step DDL/full-scan overhead, and make SQLite message sequencing & chat search bounded

## Problem
1. **`AgentKernel` shared mutable per-turn state clobbered on subagent handoffs**: `AgentKernel` (`src/application/kernel/agent_kernel.py`) stores per-turn execution state as attributes on the singleton `self` (`self.react_state`, `self._ace_tool_errors`, `self._turn_matched_capability_ids`, `self._turn_planning_phase`, `self._last_turn_tool_stats`, `self._last_progressive_skills`, `self._last_episodic_memory`). When a parent turn executes a subagent handoff (`HandoffIsolationEngine.execute_handoff` or `resume_nested_child`), the child turn runs on the same `AgentKernel` instance while the parent is suspended inside `await self.execute_and_scrub_tool()`. The child overwrites `_turn_matched_capability_ids`, `_turn_planning_phase`, `_ace_tool_errors`, and `react_state`; when control returns to the parent loop (`agent_kernel.py:1821`), the parent's subsequent steps run with the child's clobbered state.
2. **Multi-table DDL + full-table regex scan executed on every ReAct step and education tool call**: `_build_effective_system_message()` (`agent_kernel.py:652-653`) runs on every step (`turn_idx`) of `run_turn()` and `stream_turn()`, and `EducationTools._resolve_repo()` (`education_tools.py:50-56`) runs on every education tool call. Both instantiate a new `AgentMemoryRepository` and call `initialize_schema()`, which executes multi-table DDL (`executescript`), `ALTER TABLE` statements, and `deactivate_short_lived_facts()` (which queries every active row from `semantic_facts` and regex-scans them in Python).
3. **Non-atomic `sequence_num` calculation in `save_message()`**: `SessionRepositoryMixin.save_message()` (`src/infrastructure/memory/repositories/sessions.py:252-259`) queries `SELECT COALESCE(MAX(sequence_num), 0) + 1` in a separate statement before `INSERT` on a default deferred SQLite connection, allowing concurrent writes to the same session to race and produce duplicate sequence numbers.
4. **Unbounded full-table scan of all messages in `past_chat_search.py`**: `_fetch_store_rows()` and `_fetch_cold_sqlite_rows()` in `src/application/chat/past_chat_search.py:284-379` execute `SELECT ... FROM messages` with no `WHERE` filter and no `LIMIT`, loading every message across every session in `autoreiv.db` (and every cold backup DB) into Python memory.

## Cause
- Turn-scoped state was stored on `self` without snapshotting/restoring outer state when `run_turn()` / `stream_turn()` is re-entered by a nested turn.
- `AgentMemoryRepository.initialize_schema()` was not cached per `(resolved_path, (st_ino, st_dev))` in-process and ran `deactivate_short_lived_facts()` unconditionally on every call.
- `save_message()` did not use an atomic `INSERT INTO messages (...) VALUES (..., (SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM messages WHERE session_id = ?), ...)` inside an immediate transaction.
- `past_chat_search.py` fetched all rows before filtering in Python instead of pushing SQL `WHERE` token/session filters and a safety row bound down to SQLite.

## Change
- Encapsulate per-turn mutable state on `AgentKernel` via `_turn_depth`, `_snapshot_turn_state()`, and `_restore_turn_state()` around nested `run_turn()` / `stream_turn()` invocations so nested subagent handoffs preserve the parent turn's `_turn_matched_capability_ids`, `_turn_planning_phase`, `_ace_tool_errors`, and `react_state`, and make `HandoffIsolationEngine.resume_nested_child()` respect `self.kernel_factory`.
- Cache schema initialization per resolved database path and `(st_ino, st_dev)` in `AgentMemoryRepository` (`_INITIALIZED_DB_SIGNATURES`) so `initialize_schema()` and `deactivate_short_lived_facts()` run once per DB path (re-initializing only if the DB file was recreated), removing redundant DDL and full-table scans from every ReAct step and education tool call.
- Make `save_message()` in `src/infrastructure/memory/repositories/sessions.py` compute `sequence_num` atomically via an inline subquery inside `BEGIN IMMEDIATE`.
- Push SQL `LIKE` token filtering, `agent_id` / `exclude_session_id` predicates, and a bounded `LIMIT` down into `_fetch_store_rows()` and `_fetch_cold_sqlite_rows()` in `src/application/chat/past_chat_search.py`, and open cold backup SQLite files in read-only mode with a timeout.

## What dies
- Repeated per-step DDL execution and full-table `semantic_facts` scans on already-initialized `memory.db` files.
- Unbounded `SELECT * FROM messages` table scans in `past_chat_search.py`.
- Separate non-atomic `SELECT COALESCE(MAX(sequence_num), 0) + 1` query in `save_message()`.

## Proof
- Journey `card-708-kernel-turn-isolation-and-db-hygiene`:
  1. Execute a turn and search past chats (`search_past_chats`), verifying fast, accurate retrieval and unbroken chat turn execution on desktop and phone.
- Checks:
  - `tests/unit/kernel/test_card708_turn_isolation_and_db_hygiene.py`

## Plan and decisions
- Technical concurrency and DB hygiene fixes under Phase 1 (Option 1 approved by Jacob).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-708-kernel-turn-isolation-and-db-hygiene` | desktop | PASS | Seeded session `0944fc3f-4609-4080-9ffe-461d627d5c48` with `sequence_num=[1, 2]`; verified bounded `search_past_chats` SQL pushdown (`[Recent]` hit, active session excluded) and assistant recall on desktop |
| `card-708-kernel-turn-isolation-and-db-hygiene` | phone | PASS | Seeded session `fb14c566-938f-4254-8dd6-93020c8f30d8` with `sequence_num=[1, 2]`; verified bounded `search_past_chats` SQL pushdown (`[Recent]` hit, active session excluded) and assistant recall on phone |

Screenshots:
- `/tmp/autoreiv-qa/card-708/card-708-kernel-turn-isolation-and-db-hygiene-desktop-02-open-a-fresh-autoreiv-session-and-recall-project.png`
- `/tmp/autoreiv-qa/card-708/card-708-kernel-turn-isolation-and-db-hygiene-desktop-03-verify-bounded-search-past-chats-hit-self-sessio.png`
- `/tmp/autoreiv-qa/card-708/card-708-kernel-turn-isolation-and-db-hygiene-phone-03-verify-bounded-search-past-chats-hit-self-sessio.png`

## Release note
- Isolated per-turn `AgentKernel` state across nested subagent handoffs, cached `AgentMemoryRepository` schema initialization so ReAct steps no longer re-run DDL and full-table scans, made `save_message` sequence numbering atomic, and bounded `search_past_chats` SQL queries [CARD-708].
