# Requirements Specification: SQLite Episodic Fact Memory Store & Agent Auto-Recall

> **Spec Status**: Approved  
> **Target Release**: Milestone 12 (v0.12.0)  
> **Card Reference**: [CARD-042](file:///.github/cards/CARD-042-sqlite-episodic-fact-memory-store-and-agent-auto-recall.md)  

> **Primary Component**: AutoReiv Memory & Agent Kernel (`src/infrastructure/memory/sqlite_store.py`, `src/application/skills/memory_skill.py`, `src/application/kernel/agent_kernel.py`, `src/web/app.py`)

---

## 1. Executive Summary & Intent

**CARD-042** introduces cross-session episodic memory factual search, dynamic auto-recall injection in `AgentKernel`, and dedicated REST API management endpoints, enabling agents to remember user preferences, system state, and environment facts across independent sessions.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-EPISODIC-001] SQLite Episodic Fact Search & Keyword Matching
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide `SQLiteStateStore.search_facts(query, entity, min_confidence, limit)` performing tokenized substring search across `entity`, `key`, and `value` fields, ordered by `confidence` descending and `updated_at` descending.

### [REQ-EPISODIC-002] Episodic Memory Auto-Recall & Context Formatting
- **EARS Pattern**: Event-Driven
- **Requirement**: When `EpisodicMemorySkill.auto_recall(prompt)` is executed, the system **shall** search relevant stored facts and render a structured `[Episodic Memory - Recalled Facts]` markdown block.

### [REQ-EPISODIC-003] Agent Kernel Automatic Fact Context Injection
- **EARS Pattern**: State-Driven
- **Requirement**: While executing turns in `AgentKernel`, the system **shall** query matching episodic facts for the user input prompt and prepend the rendered memory context to the agent's effective system prompt.

### [REQ-EPISODIC-004] Episodic Memory REST API Endpoints
- **EARS Pattern**: Ubiquitous
- **Requirement**: The FastAPI gateway **shall** expose `GET /api/memory/facts` (search and list), `POST /api/memory/facts` (upsert fact), and `DELETE /api/memory/facts/{entity}/{key}` (deletion).

### [REQ-EPISODIC-005] Comprehensive Episodic Memory Unit & Integration Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify SQLite fact search, skill auto-recall rendering, kernel auto-injection, and REST API endpoints with 100% pass rate.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `search_facts` returns relevant facts matching query tokens across entity, key, and value.
- [ ] `AC-2`: `auto_recall` formats facts into clear markdown with entity, key, value, and confidence.
- [ ] `AC-3`: `AgentKernel` automatically enriches system instructions with recalled facts without hallucinating.
- [ ] `AC-4`: REST endpoints `GET /api/memory/facts`, `POST /api/memory/facts`, and `DELETE /api/memory/facts/{entity}/{key}` return valid JSON responses.
- [ ] `AC-5`: `npm run preflight` passes all 6 quality gates cleanly.
