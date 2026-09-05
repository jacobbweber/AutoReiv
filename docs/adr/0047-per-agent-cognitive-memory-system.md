# ADR-0047: Per-Agent Cognitive Memory System (Agent Brain)

> **Date**: 2026-09-04  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, Antigravity Agent  
> **Consulted**: AutoReiv Core Architecture  

---

## 1. Context & Problem Statement
Specialist agents in AutoReiv require an independent, persistent cognitive memory system ("Agent Brain") across chat sessions. Without persistent memory, agents lose context regarding user preferences, past project decisions, and operational constraints across turns. Existing solutions in the AI ecosystem often rely on bulky vector databases (e.g. Pinecone, ChromaDB, Qdrant, Milvus) running as external servers or Docker containers, which violates AutoReiv's core architectural principle of running cleanly and hermetically on Windows with zero external service dependencies. Furthermore, domain application data (CARD-148, e.g. finance tables) was at risk of being conflated with cognitive memory if not physically partitioned.

---

## 2. Decision Drivers
* **Strict Physical Boundary**: Domain storage (`<agent_slug>_storage.db`, CARD-148) must remain completely decoupled from cognitive memory (`<agent_slug>_memory.db`, CARD-116).
* **Zero External Dependencies**: Pure Python standard library with SQLite FTS5 (BM25 porter-stemmed text search) running locally on Windows.
* **Compilation Principle**: Post-turn fact extraction and compilation rather than costly, noisy transcript retrieval ("Stop retrieving, start compiling").
* **Mathematical Decay Physics**: Exponential half-life temperature decay coupled with logarithmic access frequency reinforcement.
* **Dynamic Budgeting**: Adaptive prompt token allocation based on active model context limits (compact for <=8k up to broad for 128k+).

---

## 3. Considered Options
* **Option 1**: Centralized vector database server (e.g. Chroma / Qdrant container).
* **Option 2**: Global SQLite table for all agents' episodic memories inside central `autoreiv.db`.
* **Option 3**: Per-agent isolated SQLite database (`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`) with three retrieval shelves (Pinned, Episodic, Semantic), SQLite FTS5 BM25 search, and decay physics (Chosen).

---

## 4. Decision Outcome
Chosen option: **Option 3**, because:
1. It delivers complete data isolation: each agent owns its private memory database file under its pack directory.
2. It enforces clear conceptual separation between domain storage (`<agent>_storage.db`) and cognitive memory (`<agent>_memory.db`).
3. It has zero external dependencies, running blisteringly fast (<5ms FTS5 queries) with zero external setup or cloud cost.
4. Exporting and importing packs can cleanly package agent configurations without leaking personal memory databases.

### Positive Consequences
* High performance, zero runtime overhead, hermetic execution on Windows.
* Clear visual and architectural distinction in Agent Studio between Persistent Storage and Cognitive Memory.
* Self-pruning memory with autonomous consolidation routine.

### Negative Consequences / Trade-offs
* Full-text search (BM25) does not perform dense semantic embeddings unless paired with local Ollama embeddings; mitigated by robust FTS5 porter stemming and category tagging.

---

## 5. Pros and Cons of Options

### Option 1: External Vector Database
* Good: Dense vector similarity search.
* Bad: Requires external services/Docker, high RAM usage, complex setup on Windows, breaks local portability.

### Option 2: Global Table in autoreiv.db
* Good: Single database file to manage.
* Bad: Cross-agent context leakage risks, no pack isolation, difficult per-agent backup/purge.

### Option 3: Per-Agent Isolated SQLite Database with 3 Shelves & FTS5
* Good: 100% portable, zero dependency, pack-scoped, strict physical separation from domain storage.
* Bad: Requires explicit schema management per agent pack database (handled cleanly by `AgentMemoryRepository`).
