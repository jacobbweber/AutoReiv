# [CARD-116] Research & Design First-Class Per-Agent Memory (Agent Brain)

> **Status**: Done
> **Created**: 2026-08-30
> **Updated**: 2026-09-05
> **Spec Reference**: docs/specs/per-agent-memory/
> **Labels**: `type:research`, `type:spec`, `AutoReiv.Kernel`, `AutoReiv.Memory`, `AutoReiv.Agents`

---

## 1. Why / Intent

Every specialist agent in AutoReiv needs an **independent, persistent cognitive brain**—not a single markdown file shared across all agents, not an opaque cloud vector store, and not raw chat history.

Following the completion of core foundations (per-agent persistent storage in `CARD-148`, per-agent LLM routing in `CARD-153`/`CARD-156`, and background execution resilience in `CARD-154`), we are designing a **tier-1 autonomous agent memory system** that is:
1. **Lightweight and 100% Local**: Runs entirely on Windows with pure Python and SQLite FTS5. Zero heavy third-party vector database daemons (no Chroma, Qdrant, Milvus, or Docker requirements).
2. **Pack-Scoped**: Lives directly inside the agent's isolated pack storage (`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`), ensuring full lifecycle alignment during backup, export, and deletion.
3. **Context-Adaptive**: Smoothly scales across small local context windows (e.g. 4k–8k Ollama models) and large frontier models (128k+ tokens) using dynamic token budgeting.
4. **Self-Compounding & Low Maintenance**: Adopts Andrej Karpathy's compilation principle ("Stop retrieving, start compiling") combined with Mem0's conflict-resolved atomic facts, avoiding brittle markdown linting loops while keeping facts accurate and fresh.

---

## 2. Core Architectural Synthesis

### Persistent Storage vs. Cognitive Memory (Critical Separation)
- **Domain Application Storage (<agent_slug>_storage.db, CARD-148)**: Optional domain database reserved for specialist agents to store application records (e.g., a Finance agent storing bank transactions and receipts, or an Inventory agent storing product catalogs).
- **Cognitive Memory (<agent_slug>_memory.db, CARD-116)**: The agent's independent brain storing pinned directives, session summaries, and semantic facts with decay curves. Kept in its own dedicated database so cognitive memory is never entangled with application data.

### User Knowledge vs. Agent Brain (The Essential Separation)
- **User Knowledge (Wiki Studio)**: Your personal notes, research, and project documentation. Already lives in AutoReiv's Wiki Studio (`#view-wiki`), managed and cross-linked by the built-in **Librarian** agent.
- **Agent Brain (CARD-116)**: The private cognitive memory of an individual agent (e.g. user preferences, past execution summaries, domain facts, and operational constraints).

### Synthesizing Three Paradigms
1. **From Andrej Karpathy's `llm-wiki.md` ("Stop retrieving, start compiling")**:
   - Never repeatedly search noisy, raw chat transcripts.
   - At the conclusion of turns or sessions, **compile** salient discoveries into structured, durable memory entries.
2. **From Mem0**:
   - Store **atomic, discrete facts** rather than monolithic essay files.
   - Automated conflict resolution: when a new fact contradicts an existing one (e.g. "Jacob upgraded to Windows 11" vs "Jacob is on Windows 10"), the agent performs an in-place `UPDATE` or `DELETE`, preventing hallucinated contradictions.
3. **From AutoReiv's Native SQLite Three-Shelf Brain (The Implementation Engine)**:
   - Built directly on SQLite + FTS5 full-text BM25 search (with optional local Ollama embeddings).
   - Fast (<1ms query latency), zero foreign dependencies, zero Windows install headaches.

---

## 3. The Four Memory Tiers & Dynamics

### A. Memory Taxonomy
1. **Working / Pinned Memory (Shelf 1)**:
   - Permanent directives, critical machine/user context, and active constraints.
   - Always injected into the prompt. Directly viewable and editable on the agent sheet in Agent Studio.
2. **Episodic Memory (Shelf 2 - Recent Work Summaries)**:
   - Rolling chronological milestones and past session summaries ("On Tuesday we migrated database paths").
   - Anchored with timestamps, session IDs, and outcome status.
3. **Semantic Memory (Shelf 3 - Atomic Fact Archive)**:
   - Granular facts, user preferences, and domain knowledge decoupled from specific sessions.
   - Indexed via SQLite FTS5 for instant keyword/BM25 relevance scoring upon user prompt arrival.
4. **Procedural Memory**:
   - Operational runbooks and tools (handled natively via AutoReiv's `SKILL.md` runbooks and registered tool callables).

### B. Memory Dynamics & Decay
- **Recency & Temperature (Half-Life Decay)**: Facts track `created_at`, `last_accessed_at`, and `access_count`. Unused facts decay in relevance score over time.
- **Dynamic Context Token Budgeting**: 
  - For small local models (4k–8k tokens): Allocates a strict, compact budget (e.g., 200–400 tokens: pinned facts + top 3 relevance-scored facts).
  - For large models (32k+ tokens): Dynamically widens the retrieval budget to top 10–15 facts and recent session summaries.
- **Routine Maintenance & Consolidation**:
  - Background consolidation pass (running on routine or post-session idle).
  - Merges near-duplicate facts, resolves lingering contradictions, and purges expired facts that have decayed past the retention threshold.

---

## 4. Agent Studio Levers & UI Controls

On the Agent Studio roster sheet (`#view-forge`), each agent receives dedicated memory controls:
- **Memory Toggle**: Enable/disable cognitive memory for that specific agent.
- **Retention Slider**: Hard bounded (e.g. `7` to `90` days, default `30` days).
- **Pinned Facts Editor**: Multiline text area for fixed directives that never decay.
- **Memory Inspector & Purge**: Slide-out drawer or table showing all currently stored facts with an instant `[ Forget Fact ]` or `[ Purge Brain ]` action.

---

## 5. Goal Mode Research & Planning Scope

Before writing production code, deep research and planning will deliver:
1. **Formal Specification (`docs/specs/per-agent-memory/`)**:
   - `requirements.md`: EARS requirements covering ingest, conflict resolution, decay, retrieval, and UI levers.
   - `design.md`: SQLite schema (`agent_memories`, `memory_fts`, `session_summaries`), prompt assembly sequence, scoring formulas, and background consolidation mechanics.
   - `tasks.md`: Vertical slices implementing domain models, SQLite repositories, kernel prompt injection, consolidation routines, and Agent Studio UI.
2. **Local Model Invariant Proof**:
   - Verification that extraction and conflict-resolution prompts execute reliably on small local Ollama models (e.g. Llama 3.1 8B, Qwen 2.5 7B) within latency and token constraints.

---

## 6. Acceptance Criteria (Definition of Done)

- [x] `[REQ-MEM-001]`: Specification documents (`requirements.md`, `design.md`, `tasks.md`) authored and verified in `docs/specs/per-agent-memory/`.
- [ ] `[REQ-MEM-002]`: Isolated SQLite brain schema implemented in `$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`.
- [ ] `[REQ-MEM-003]`: Ingestion and conflict resolution pipeline (ADD, UPDATE, DELETE) operational with zero external vector DB dependencies.
- [ ] `[REQ-MEM-004]`: Three-shelf prompt injection active in `AgentKernel` with dynamic context window token budgeting.
- [ ] `[REQ-MEM-005]`: Background consolidation and decay routine implemented with retention slider support in Agent Studio.
- [ ] `[REQ-MEM-006]`: Automated unit and integration tests pass cleanly via `pytest` and `vitest`.
- [ ] `[REQ-MEM-007]`: Zero linting errors via `ruff check .` and frontend static analysis.

---

## 7. Constraints & Honor Flags

- Zero external vector DB dependencies (no Chroma, Qdrant, Milvus, or cloud SaaS).
- 100% pure Python standard library + SQLite FTS5 running locally on Windows.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
