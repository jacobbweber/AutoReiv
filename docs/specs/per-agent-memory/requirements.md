# Requirements Specification: Per-Agent Cognitive Memory System (Agent Brain)

> **Spec Status**: Approved Specification
> **Version**: 1.0.0
> **Target Release**: v0.19.0
> **Primary Component**: AutoReiv.Kernel / AutoReiv.Memory / AutoReiv.Web (Agent Studio)
> **Card Reference**: [CARD-116](file:///.github/cards/CARD-116-research-first-class-per-agent-memory-agent-brain.md)
> **ADR Reference**: docs/adr/0047-per-agent-cognitive-memory-system.md

---

## 1. Executive Summary & Intent

Specialist agents in AutoReiv require an **independent, persistent cognitive memory system (Agent Brain)** to maintain continuity of user preferences, historical execution milestones, and operational constraints across chat sessions.

This specification synthesizes three foundational paradigms:
1. **Andrej Karpathy's Compilation Principle ("Stop retrieving, start compiling")**: Compiling conversational insights post-turn into structured memory records rather than repeatedly scanning noisy, unstructured transcripts.
2. **Mem0's Conflict-Resolved Atomic Fact Model**: Extracting granular, atomic facts with automated `ADD`, `UPDATE`, and `DELETE` logic to eliminate contradictions as knowledge changes.
3. **AutoReiv's Zero-Dependency Local Architecture**: Running entirely on Windows with pure Python standard library and SQLite FTS5, pack-scoped inside `$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`.

### Invariant Boundary: Domain Storage vs. Cognitive Memory
- **Domain Application Storage (`<agent_slug>_storage.db`, CARD-148)**: Dedicated database for agent application tables (e.g. personal finance transactions, inventory records).
- **Cognitive Agent Memory (`<agent_slug>_memory.db`, CARD-116)**: Dedicated database for the agent brain (pinned directives, rolling episodic session summaries, and semantic facts with decay curves).
- **User Knowledge Vault (`WikiStore` / Wiki Studio)**: Separate markdown knowledge base maintained by the user and the Librarian agent.

---

## 2. Requirements Matrix (EARS Notation)

### [REQ-MEM-001]: Isolated Per-Agent Database Provisioning
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL provision and resolve a dedicated SQLite database at `$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db` for each agent with cognitive memory enabled.
- **Acceptance Criteria**:
  - [ ] Memory database path is resolved via `resolve_agent_memory_path(agent_id)`.
  - [ ] An agent's cognitive memory database is completely physically separate from its domain application storage database (`<agent_slug>_storage.db`).
  - [ ] No agent brain records are ever written to or mixed into the central `database/autoreiv.db`.
  - [ ] Deleting or exporting an agent pack includes or purges `<agent_slug>_memory.db` alongside the pack.

### [REQ-MEM-002]: Three-Shelf Memory Architecture
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL organize agent memory into three distinct retrieval shelves: Pinned Memory (Shelf 1), Episodic Memory (Shelf 2), and Semantic Memory (Shelf 3).
- **Acceptance Criteria**:
  - [ ] **Shelf 1 (Pinned Directives)**: Contains fixed user instructions, hardware constraints, and persona anchors that are always injected into the agent prompt without decay.
  - [ ] **Shelf 2 (Episodic Summaries)**: Stores rolling chronological session summaries with timestamps, session identifiers, and execution status.
  - [ ] **Shelf 3 (Semantic Facts)**: Stores granular atomic facts, user traits, and environment facts indexed for relevance matching.

### [REQ-MEM-003]: Post-Turn Fact Extraction & Compilation
- **Type**: Event-Driven
- **EARS Statement**: WHEN a chat turn or autonomous job concludes, THE SYSTEM SHALL compile salient new facts and conversational discoveries into discrete candidate memory entries without re-reading raw prior transcripts.
- **Acceptance Criteria**:
  - [ ] Extraction occurs as a lightweight post-turn compilation step.
  - [ ] Extraction targets user preferences, system configuration changes, entities, and completed action outcomes.
  - [ ] The extraction prompt enforces structured output (`entity`, `attribute`, `value`, `confidence`, `operation`).

### [REQ-MEM-004]: Conflict Resolution & Deduplication Pipeline
- **Type**: Event-Driven
- **EARS Statement**: WHEN a new candidate fact is extracted, THE SYSTEM SHALL compare it against existing semantic memories and perform automated conflict resolution via ADD, UPDATE, or DELETE operations.
- **Acceptance Criteria**:
  - [ ] If a candidate fact introduces an updated value for an existing attribute (e.g. "User upgraded to Windows 11" vs existing "User OS is Windows 10"), the system shall perform an in-place `UPDATE` and refresh the timestamp.
  - [ ] If a candidate fact explicitly negates an existing fact, the system shall `DELETE` or mark the old fact as superseded.
  - [ ] If a candidate fact is genuinely new, the system shall `ADD` it with an initial relevance score and access count of 1.
  - [ ] If a candidate fact is identical to an existing fact, the system shall bump the existing fact's `access_count` and `last_accessed_at` without duplicating the row.

### [REQ-MEM-005]: Hybrid Relevance Search via SQLite FTS5
- **Type**: State-Driven
- **EARS Statement**: WHILE assembling the agent's prompt for an incoming turn, THE SYSTEM SHALL query Shelf 3 semantic memories using SQLite FTS5 BM25 text search to retrieve the most relevant facts for the current prompt.
- **Acceptance Criteria**:
  - [ ] Semantic facts table is backed by a SQLite FTS5 virtual table (`agent_memories_fts`).
  - [ ] Search calculates relevance matching based on BM25 rank combined with the fact's decayed score.
  - [ ] Query execution time for relevance retrieval is under 5 milliseconds.

### [REQ-MEM-006]: Recency & Half-Life Temperature Decay
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL calculate an effective relevance score for each semantic memory using an exponential half-life decay function based on elapsed time and access frequency.
- **Acceptance Criteria**:
  - [ ] Each fact tracks `created_at`, `updated_at`, `last_accessed_at`, `access_count`, and `decay_half_life_days`.
  - [ ] Effective score formula: S_eff = S_base * exp(-lambda * delta_t) + alpha * ln(1 + access_count).
  - [ ] Facts that are frequently accessed resist decay and remain active in retrieval.
  - [ ] Facts that have fallen below an activation threshold (S_eff < theta) are excluded from prompt injection.

### [REQ-MEM-007]: Dynamic Context Window Token Budgeting
- **Type**: State-Driven
- **EARS Statement**: WHILE assembling memory into the agent context, THE SYSTEM SHALL dynamically scale the token allocation for memory retrieval based on the active model's context window.
- **Acceptance Criteria**:
  - [ ] For small context models (<= 8,192 tokens, e.g. local Ollama 8B): Allocates a strict compact budget (max 350 tokens: Shelf 1 pinned + top 3 Shelf 3 semantic facts).
  - [ ] For medium context models (8,193 to 32,768 tokens): Allocates a standard budget (max 800 tokens: Shelf 1 pinned + top 1 Shelf 2 summary + top 6 Shelf 3 semantic facts).
  - [ ] For large context models (> 32,768 tokens): Allocates an expanded budget (max 2,000 tokens: Shelf 1 pinned + last 3 Shelf 2 summaries + top 15 Shelf 3 semantic facts).
  - [ ] Truncation strictly preserves Shelf 1 (pinned directives) first before shedding low-relevance semantic facts.

### [REQ-MEM-008]: Autonomous Background Consolidation Routine
- **Type**: Event-Driven
- **EARS Statement**: WHEN an agent is idle or a configured maintenance interval triggers, THE SYSTEM SHALL execute an autonomous memory consolidation pass on `<agent_slug>_memory.db`.
- **Acceptance Criteria**:
  - [ ] Identifies and merges near-duplicate memories created across disparate sessions.
  - [ ] Prunes or archives facts whose effective score has decayed below the cleanup threshold and exceeds the agent's configured retention period.
  - [ ] Generates higher-level rolling episodic summaries from older un-compacted session logs.
  - [ ] Runs asynchronously in the background without blocking active chat streaming turns.

### [REQ-MEM-009]: Agent Studio Cognitive Memory Controls
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL expose a dedicated "Cognitive Memory" configuration card on the Agent Studio roster sheet (`#view-forge`), completely distinct from the "Persistent Storage" card.
- **Acceptance Criteria**:
  - [ ] Includes a checkbox `#forgeMemoryEnabled` (Default: `true` for conversational assistants, `false` for pure stateless utilities).
  - [ ] Includes a bounded Retention Slider `#forgeMemoryRetentionDays` with hard bounds: minimum 7 days, maximum 90 days, default 30 days.
  - [ ] Includes a Pinned Memory multiline text area `#forgePinnedMemory` for Shelf 1 fixed directives.
  - [ ] Form values are persisted to `custom_agents` / `agent_overrides` in SQLite and loaded on edit.

### [REQ-MEM-010]: Agent Studio Memory Inspector & Purge Actions
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL provide an interactive Memory Inspector drawer in Agent Studio allowing the user to view, search, delete individual facts, or purge an agent's memory.
- **Acceptance Criteria**:
  - [ ] Opens via a `[ 🧠 Inspect Brain ]` button on the roster sheet when memory is enabled.
  - [ ] Renders stored semantic facts and episodic summaries in a table with filter search.
  - [ ] Each fact provides a `[ Forget ]` button that immediately issues `DELETE /api/agents/{id}/memory/facts/{fact_id}`.
  - [ ] Provides a high-visibility `[ ⚠️ Purge Agent Brain ]` button with a confirmation modal that executes `DELETE /api/agents/{id}/memory` and resets `<agent_slug>_memory.db`.

### [REQ-MEM-011]: Memory Kernel Tools for Agent Execution
- **Type**: State-Driven
- **EARS Statement**: WHILE an agent with cognitive memory enabled is executing a turn, THE SYSTEM SHALL provide internal tool callables to explicitly recall, verify, or memorize facts during reasoning.
- **Acceptance Criteria**:
  - [ ] `recall_agent_memory(query: str, limit: int = 5)`: Returns top matching facts from the agent's private brain.
  - [ ] `memorize_fact(category: str, fact: str, importance: float = 1.0)`: Allows the agent to explicitly store a high-conviction discovery mid-flight.
  - [ ] Tools are scoped strictly to the calling agent's `<agent_slug>_memory.db`.

### [REQ-MEM-012]: Zero External Vector Database Invariant
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL NOT require external vector database servers, cloud API keys, Docker containers, or non-standard Python dependencies to run the cognitive memory system.
- **Acceptance Criteria**:
  - [ ] System runs on Windows using Python 3.12+ standard library `sqlite3` with compiled FTS5 support.
  - [ ] Optional semantic similarity uses local Ollama `/api/embeddings` if enabled, falling back seamlessly to FTS5 BM25 text search when embeddings are unavailable.
