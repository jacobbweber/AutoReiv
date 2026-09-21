---
id: CARD-405
title: "Agent Memory System Verification, Stress Audit, and Live Walkthrough"
status: Ready
created: 2026-09-21
adr: none
labels:
  - type:test
  - area:memory
  - domain:agents
---

# [CARD-405] Agent Memory System Verification, Stress Audit, and Live Walkthrough

> **Status**: Ready  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:test`, `area:memory`, `domain:agents`  

---

## 1. Why / Intent (Beat 1)

AutoReiv provides a cognitive memory architecture (Three-Shelf Cognitive Brain) allowing agents to retain persistent facts, episodic milestones, and user preferences across turns and sessions.

Jacob needs a thorough, transparent walkthrough and automated stress audit of the entire memory subsystem to:
1. Verify that memory features (extraction, storage, decay physics, FTS5 search, prompt context assembly, and Forge Brain Drawer UI) are working fundamentally and literally as designed.
2. Ensure there are zero cross-agent memory leaks (e.g. Developer agent knowing Tutor agent facts).
3. Validate that memory survives server restarts and correctly handles post-turn conflict resolution (`ADD`, `UPDATE`, `DELETE`, `BUMP`).
4. Provide a clear, step-by-step human verification runbook to test memory in live chat.

---

## 2. What AutoReiv Does Now (Beat 2)

1. **Storage**: Every agent has a dedicated SQLite database `<agent_id>_memory.db` under `$DATA_DIR/packs/<agent_id>/` managed by `AgentMemoryRepository` (`src/infrastructure/memory/repositories/agent_memory.py`).
2. **Three Shelves**:
   - **Shelf 1 (Pinned Directives)**: Non-decaying directives in `pinned_memories` table.
   - **Shelf 2 (Episodic Memory)**: Session summaries, key decisions, and outcomes in `session_summaries` table.
   - **Shelf 3 (Semantic Facts)**: Atomic facts with FTS5 BM25 search and exponential decay in `semantic_facts` and `semantic_facts_fts`.
3. **Extraction & Conflict Resolution**: `MemoryExtractorService` (`src/application/memory/extractor.py`) parses turns for candidate facts and executes atomic conflict resolution.
4. **Context Assembly**: `MemoryContextAssembler` (`src/application/memory/assembler.py`) dynamically injects memories according to context window tier (tight, standard, broad).
5. **Agent Tools**: `AgentMemoryTools` (`recall_agent_memory`, `memorize_fact`).
6. **UI**: Brain Drawer in Agent Forge Studio (`src/web/static/modules/studios/forge/`).

---

## 3. What Will Change (Beat 3)

### 3.1 Comprehensive Memory Verification Test Suite
- Author `tests/integration/test_agent_memory_lifecycle_walkthrough.py`:
  - **End-to-End Extraction Loop**: Sends chat turns, executes extraction, verifies atomic fact creation and conflict resolution (`ADD` new, `UPDATE` revised, `BUMP` reinforced).
  - **Half-Life Decay & Reinforcement Physics**: Audits $S_{\text{eff}} = S_{\text{base}} \cdot e^{-\lambda \Delta t} + \alpha \ln(1 + N_{\text{access}})$, verifying that stale facts decay while touched facts remain elevated.
  - **Context Tier Token Budgeting**: Verifies assembler behavior across tight ($\le 8\text{k}$), standard ($8\text{k}-32\text{k}$), and broad ($>32\text{k}$) context limits.
  - **Cross-Agent Isolation**: Verifies that two distinct agents (`developer` vs `autoreiv`) never share or leak memory rows.
  - **Server Reboot & Reopen Persistence**: Closes SQLite connections, reopens on fresh instances, and verifies schema and virtual table integrity.
  - **REST API Endpoints**: Tests `GET /api/agents/{id}/memory`, `DELETE /api/agents/{id}/memory/facts/{fact_id}`, and `DELETE /api/agents/{id}/memory`.

### 3.2 Human Live Walkthrough Guide
- Provide Jacob with an observable 2-minute runbook:
  1. Open Chat Studio with an agent.
  2. State an explicit preference (e.g. "I prefer Python for backend scripts and Vitest for frontend").
  3. Open Agent Forge Studio $\rightarrow$ Click agent $\rightarrow$ Open **Brain Drawer**.
  4. Verify the semantic fact appears with category `user_pref`, confidence `1.0`, and access count `1`.
  5. In a new conversation session, ask a question and observe the agent recalling the preference seamlessly via prompt assembly.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Eliminate unverified edge cases in memory token budgeting and small-talk filtering.
- Prune obsolete mock fixtures or orphaned memory test utilities.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-405-001] Strict Per-Agent Isolation**:
  - *The System Shall* enforce that all cognitive memory operations are strictly partitioned by agent ID into `<agent_id>_memory.db`, guaranteeing zero cross-agent fact contamination.

- **[REQ-405-002] Multi-Tier Memory Context Assembly**:
  - *When* assembling prompt memory blocks for an active model,
  - *The System Shall* adhere to token budget tiers (tight: ~350 tokens, standard: ~800 tokens, broad: ~2000 tokens), prioritizing Pinned Directives and top-ranked Semantic Facts.

- **[REQ-405-003] Atomic Conflict Resolution**:
  - *When* candidate facts are extracted post-turn,
  - *The System Shall* execute conflict resolution (`ADD`, `UPDATE`, `BUMP`) preserving existing high-confidence knowledge without duplicate entry bloat.

- **[REQ-405-004] FTS5 BM25 Relevance with Decay Physics**:
  - *When* querying semantic facts,
  - *The System Shall* combine FTS5 BM25 match scores with exponential half-life decay and logarithmic access counts to rank relevant facts accurately.

- **[REQ-405-005] Small-Talk Trivial Turn Bypass (Negative Assertion)**:
  - *The System Shall* bypass post-turn memory extraction on trivial utterances ("ok", "thanks", "hello"), asserting that no unnecessary LLM extraction cycles or spurious facts are generated.

---

## 6. Constraints & Verification Plan

- Isolated feature branch `feat/CARD-405-agent-memory-walkthrough` cut from `qa`.
- Integration tests in `tests/integration/test_agent_memory_lifecycle_walkthrough.py`.
- Frontend Vitest tests in `tests/unit/frontend/agent_memory_ui.test.js`.
- All linters and boundary audits pass cleanly.
