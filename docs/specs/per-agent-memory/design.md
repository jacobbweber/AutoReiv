# Technical Design: Per-Agent Cognitive Memory System (Agent Brain)

> **Spec Reference**: docs/specs/per-agent-memory/requirements.md
> **Architecture Level**: Component & Data Architecture
> **Primary Modules**: `src.domain.memory`, `src.infrastructure.memory.repositories`, `src.application.kernel`
> **Target Release**: v0.19.0

---

## 1. Architectural Context & Component Diagram (C4 Level 2)

The Cognitive Memory System operates as an autonomous cognitive subsystem directly alongside `AgentKernel`. It is isolated from both the primary central system database (`autoreiv.db`) and the agent's optional domain storage database (`<agent_slug>_storage.db`).

```
+-----------------------------------------------------------------------------------+
| AutoReiv Platform                                                                 |
|                                                                                   |
|  +------------------------+             +---------------------------------------+ |
|  |      Agent Studio      |             |             AgentKernel               | |
|  |  (Roster Sheet & Brain |             |       (Prompt Assembler & ReAct)      | |
|  |   Inspector Drawer)    |             +-------------------+-------------------+ |
|  +-----------+------------+                                 |                     |
|              | HTTP REST                                    | Turn Execution      |
|              v                                              v                     |
|  +------------------------+             +---------------------------------------+ |
|  |     Memory Router      |             |         Memory Pipeline Service       | |
|  |   /api/agents/{id}/    |             |  1. Pre-turn: Dynamic Shelf Assembly  | |
|  |         memory         |             |  2. Post-turn: Compile & Deduplicate  | |
|  +-----------+------------+             +-------------------+-------------------+ |
|              |                                              |                     |
|              +----------------------+-----------------------+                     |
|                                     |                                             |
|                                     v                                             |
|                     +-------------------------------+                             |
|                     |    AgentMemoryRepository      |                             |
|                     |   (SQLite WAL + FTS5 Engine)  |                             |
|                     +---------------+---------------+                             |
|                                     |                                             |
+-------------------------------------|---------------------------------------------+
                                      v
           +-----------------------------------------------------+
           | $DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db   |
           |                                                     |
           |  - pinned_memories     (Shelf 1: Fixed Directives)  |
           |  - session_summaries   (Shelf 2: Episodic History)  |
           |  - semantic_facts      (Shelf 3: Atomic Facts)      |
           |  - semantic_facts_fts  (FTS5 BM25 Index)            |
           |  - memory_events       (Audit & Consolidation Log)  |
           +-----------------------------------------------------+
```

---

## 2. Physical Database Schema (`<agent_slug>_memory.db`)

Each agent with memory enabled owns an isolated SQLite database created at:
`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`.

```sql
-- 1. Shelf 1: Pinned Memory (Fixed Directives & Non-Decaying Anchor Facts)
CREATE TABLE IF NOT EXISTS pinned_memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Shelf 2: Episodic Memory (Rolling Session & Job Summaries)
CREATE TABLE IF NOT EXISTS session_summaries (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_decisions TEXT, -- JSON array of strings
    turn_count INTEGER NOT NULL DEFAULT 1,
    outcome_status TEXT NOT NULL DEFAULT 'completed', -- 'completed', 'failed', 'parked'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_session_summaries_created ON session_summaries(created_at DESC);

-- 3. Shelf 3: Semantic Facts (Atomic Extracted Facts with Decay Dynamics)
CREATE TABLE IF NOT EXISTS semantic_facts (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL DEFAULT 'general', -- 'user_pref', 'environment', 'domain', 'constraint'
    entity TEXT NOT NULL,                     -- e.g. 'user', 'system', 'python', 'database'
    attribute TEXT NOT NULL,                  -- e.g. 'os_platform', 'preferred_format'
    value TEXT NOT NULL,                      -- e.g. 'Windows 11', 'PowerShell'
    confidence REAL NOT NULL DEFAULT 1.0,     -- 0.0 to 1.0
    access_count INTEGER NOT NULL DEFAULT 1,
    decay_half_life_days REAL NOT NULL DEFAULT 30.0,
    is_active INTEGER NOT NULL DEFAULT 1,     -- 1 = active, 0 = superseded / forgotten
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_entity_attr ON semantic_facts(entity, attribute);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_active ON semantic_facts(is_active);

-- 4. Full-Text Search Virtual Table (FTS5 BM25 Indexing)
CREATE VIRTUAL TABLE IF NOT EXISTS semantic_facts_fts USING fts5(
    id UNINDEXED,
    category,
    entity,
    attribute,
    value,
    tokenize = 'porter unicode61'
);

-- Triggers for automatic FTS synchronization
CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_ai AFTER INSERT ON semantic_facts BEGIN
    INSERT INTO semantic_facts_fts(id, category, entity, attribute, value)
    VALUES (new.id, new.category, new.entity, new.attribute, new.value);
END;

CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_au AFTER UPDATE ON semantic_facts BEGIN
    UPDATE semantic_facts_fts SET
        category = new.category,
        entity = new.entity,
        attribute = new.attribute,
        value = new.value
    WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_ad AFTER DELETE ON semantic_facts BEGIN
    DELETE FROM semantic_facts_fts WHERE id = old.id;
END;

-- 5. Audit & Maintenance Log
CREATE TABLE IF NOT EXISTS memory_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL, -- 'ADD', 'UPDATE', 'DELETE', 'CONSOLIDATE', 'EXPIRE'
    fact_id TEXT,
    details TEXT,             -- JSON payload
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. The Ingest & Compilation Sequence (Karpathy Principle)

Instead of dumping conversation logs into a raw text file or re-reading long chat history, memory compilation operates asynchronously after a turn or autonomous job:

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Client
    participant Kernel as AgentKernel
    participant Worker as Background Task Worker
    participant LLM as Fast Extraction Model
    participant Repo as AgentMemoryRepository

    User->>Kernel: Send Prompt
    Kernel->>User: Stream Response (SSE)
    Kernel->>Worker: Dispatch Post-Turn Ingest Task (SessionID, UserMsg, AgentMsg)
    Note over Kernel,User: User turn finishes with zero added latency!
    
    Worker->>LLM: Compile Facts (Structured JSON Prompt)
    LLM-->>Worker: Return Candidate Facts [ {entity, attribute, value, operation} ]
    
    loop For Each Candidate Fact
        Worker->>Repo: Query Existing by (entity, attribute)
        alt Conflict Found (e.g. Attribute Value Changed)
            Worker->>Repo: UPDATE fact (new value, refresh timestamp)
        alt Exact Match Found
            Worker->>Repo: BUMP access_count and last_accessed_at
        alt New Fact
            Worker->>Repo: INSERT new fact into semantic_facts & FTS5
        end
    end
```

---

## 4. Mathematical Temperature & Half-Life Decay Dynamics

To prevent the agent's memory from being cluttered by transient or outdated facts, each memory fact has an **Effective Relevance Score** $S_{	ext{eff}}$ calculated during retrieval:

### Decay Physics Formula:
$$S_{	ext{eff}}(t) = S_{	ext{base}} \cdot e^{-\lambda \cdot \Delta t} + lpha \cdot \ln(1 + N_{	ext{access}})$$

Where:
- $\Delta t = rac{t_{	ext{now}} - t_{	ext{last\_accessed}}}{86400}$ (Elapsed time in days since last access).
- $\lambda = rac{\ln(2)}{T_{	ext{half}}}$ (Decay rate, where $T_{	ext{half}}$ is the half-life in days, default = 30.0 days).
- $S_{	ext{base}}$ is the extraction confidence score ($0.0 \le S_{	ext{base}} \le 1.0$).
- $N_{	ext{access}}$ is the number of times this fact has been recalled or referenced.
- $lpha$ is the reinforcement coefficient (default = $0.15$), rewarding frequently referenced facts.

### Combined Search Score:
When searching for facts matching a user prompt:
$$	ext{Score}_{	ext{final}} = 	ext{BM25Rank} \cdot \left(1.0 + eta \cdot S_{	ext{eff}}ight)$$
Facts with low effective scores naturally sink below the retrieval threshold and are dropped, while reinforced facts stay warm.

---

## 5. Dynamic Context Window Token Budgeting

AutoReiv dynamically detects the active model's context capacity (configured via CARD-153/156 or global settings) and dynamically sizes the prompt injection budget:

| Context Capacity | Model Tier Example | Max Memory Budget | Shelf 1: Pinned Directives | Shelf 2: Episodic Summaries | Shelf 3: Semantic Facts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tight (<= 8k)** | Ollama 8B, Phi-3, Mistral 7B | **350 tokens** | Max 150 tokens | 0 (Omitted) | Top 3 facts (~150 tokens) |
| **Standard (8k - 32k)** | Llama 3.1 8B 16k, Gemma 2 27B | **800 tokens** | Max 250 tokens | 1 recent summary (~200 tokens) | Top 6 facts (~350 tokens) |
| **Broad (> 32k)** | Claude 3.5, GPT-4o, Gemini 1.5 | **2,000 tokens** | Max 400 tokens | Last 3 summaries (~600 tokens) | Top 15 facts (~1,000 tokens) |

### Formatted Injection Block:
The assembled block is injected as a distinct system context section directly above conversation history:

```markdown
[Agent Brain - Pinned Directives]
- Jacob's Host: Windows 11 Pro, Shell: pwsh (PowerShell).
- Never emit bash or linux shell commands.

[Agent Brain - Episodic Milestones]
- 2026-09-04 (Session #s-92a): Completed database migration to AutoReiv/database/autoreiv.db and pack-scoped storage.

[Agent Brain - Recalled Relevant Facts]
- user.preferred_language: TypeScript, Python (recency: high, confidence: 1.0)
- system.ollama_port: 11434 (recency: high, confidence: 1.0)
```

---

## 6. Autonomous Consolidation & Garbage Collection

A background routine runs during idle periods or scheduled intervals:
1. **Deduplication**: Runs pairwise FTS5 queries to identify semantically redundant facts (e.g. "User likes dark roast" and "User drinks dark roast coffee"). Merges them into the canonical record with combined access counts.
2. **TTL Eviction**: Evaluates facts against the agent's configured retention limit ($T_{	ext{retention}}$ from the Agent Studio slider). If $\Delta t > T_{	ext{retention}}$ and $S_{	ext{eff}} < 0.10$, the fact is marked inactive or permanently purged.
3. **Episodic Compression**: Consolidates multiple micro-session summaries older than 7 days into a single week milestone.

---

## 7. Agent Studio UI Specifications & Wireframes

### Roster Sheet: Distinct Storage vs. Memory Sections

```text
+------------------------------------------------------------------------+
| Agent Studio: Assistant                                                |
+------------------------------------------------------------------------+
| Name:        [ Assistant                                             ] |
| Model:       [ Use Global Default                                  v ] |
| System Prompt:                                                         |
| [ You are AutoReiv's primary orchestrator assistant...               ] |
+------------------------------------------------------------------------+
| 📦 Persistent Storage (CARD-148)                                       |
| [x] Enable Isolated Domain Storage                                      |
| Database Type: [ SQLite (Isolated File)                             v ]|
| Location: packs/assistant/assistant_storage.db                         |
| (Reserved for domain application data, e.g. finance tables & receipts) |
+------------------------------------------------------------------------+
| 🧠 Cognitive Memory (CARD-116)                                         |
| [x] Enable Agent Brain                                                 |
| Memory Retention: [====o=================] 30 Days (Bounds: 7-90 days) |
|                                                                        |
| Pinned Directives (Shelf 1 - Never Decays):                            |
| +--------------------------------------------------------------------+ |
| | - User OS: Windows 11 Pro (pwsh)                                   | |
| | - Preferred Coding Standards: KISS, strict TDD                     | |
| +--------------------------------------------------------------------+ |
| Location: packs/assistant/assistant_memory.db                          |
| [ 🧠 Inspect Brain Records ]   [ ⚠️ Purge Cognitive Brain ]             |
+------------------------------------------------------------------------+
```

### Memory Inspector Drawer (`#agentBrainDrawer`)

```text
+------------------------------------------------------------------------+
| 🧠 Cognitive Brain Inspector: Assistant                                |
+------------------------------------------------------------------------+
| Search Facts: [ filter facts...                            ] [ Search ]|
| Total Active Facts: 14   |   Episodic Summaries: 3                     |
+------------------------------------------------------------------------+
| Category   | Entity  | Attribute   | Value         | Score | Action    |
| ---------- | ------- | ----------- | ------------- | ----- | --------- |
| user_pref  | user    | shell       | pwsh          | 1.45  | [Forget]  |
| user_pref  | user    | editor      | VSCode        | 1.20  | [Forget]  |
| system     | host    | os          | Windows 11    | 1.55  | [Forget]  |
| domain     | db      | location    | database/     | 1.10  | [Forget]  |
+------------------------------------------------------------------------+
| [ Close Drawer ]                           [ ⚠️ Delete All Memories ]  |
+------------------------------------------------------------------------+
```
