# Technical Architecture & Design: Session Artifact Store and Context-Isolated Batch Worker Skill

## 1. System Architecture Overview

```
                                 ┌────────────────────────────────────────────────────────┐
                                 │ Primary Agent (Assistant / AutoReiv in Chat Session)   │
                                 │ - Context: ~5k tokens (conversational, fast)           │
                                 └───────────────────────────┬────────────────────────────┘
                                                             │ 1. Calls `batch_worker_scan`
                                                             ▼
                                 ┌────────────────────────────────────────────────────────┐
                                 │ BatchWorkerSkill Engine (Map-Reduce Coordinator)       │
                                 │ - Discovers N files / paths                            │
                                 │ - Chunks into M batches (e.g., 5 files per worker)     │
                                 └───────┬───────────────┬────────────────┬───────────────┘
                                         │               │                │
                        ┌────────────────┘               ▼                └────────────────┐
                        ▼                        ┌───────────────┐                         ▼
                 ┌───────────────┐               │ Worker Task 2 │                  ┌───────────────┐
                 │ Worker Task 1 │               │ (Isolated RAM)│                  │ Worker Task M │
                 │ (Isolated RAM)│               └───────┬───────┘                  │ (Isolated RAM)│
                 └───────┬───────┘                       │                          └───────┬───────┘
                         │ 2. Extracts structured JSON   │                                  │
                         └───────────────────────────────┼──────────────────────────────────┘
                                                         │ 3. Master consolidation
                                                         ▼
                                 ┌────────────────────────────────────────────────────────┐
                                 │ SessionArtifactRepository (SQLite `session_artifacts`) │
                                 │ - id: `art_<uuid>`                                     │
                                 │ - session_id: `ses_<id>` (ON DELETE CASCADE)           │
                                 │ - summary: "Audited 30 files, found 3 key findings..." │
                                 │ - content: Complete structured markdown report         │
                                 │ - expires_at: NOW() + 7 days                           │
                                 └───────────────────────┬────────────────────────────────┘
                                                         │ 4. Returns summary + `artifact://` link
                                                         ▼
                                 ┌────────────────────────────────────────────────────────┐
                                 │ Chat Studio UI                                         │
                                 │ - Interactive Artifact Pill in Chat Bubble             │
                                 │ - Click -> Opens Artifact Modal / Slide-Over           │
                                 │ - [ ⭐ Promote to Wiki Vault ] -> Creates Wiki Note    │
                                 └────────────────────────────────────────────────────────┘
```

---

## 2. Component Design & Contracts

### 2.1 Domain Models (`src/domain/memory/models.py` or `src/domain/artifacts/models.py`)
```python
class SessionArtifact(BaseModel):
    id: str
    session_id: str
    title: str
    content_type: str = "text/markdown"  # "text/markdown", "application/json"
    content: str
    summary: str
    item_count: int = 0
    is_pinned: bool = False
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
```

### 2.2 SQLite DDL (`src/infrastructure/memory/schema.py`)
```sql
CREATE TABLE IF NOT EXISTS session_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text/markdown',
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    item_count INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON session_artifacts(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_expires ON session_artifacts(expires_at, is_pinned);
```

### 2.3 Skill Definition (`src/application/skills/worker_skill.py`)
- Tool 1: `batch_worker_scan(session_id: str, paths: List[str], objective: str) -> Dict[str, Any]`
- Tool 2: `get_session_artifact(artifact_id: str) -> Dict[str, Any]`
- Tool 3: `promote_artifact_to_wiki(artifact_id: str, wiki_slug: str, title: Optional[str]) -> Dict[str, Any]`

---

## 3. UI Markdown & Slide-Over Wireframe

```text
+-------------------------------------------------------------------------------+
| Assistant:                                                                    |
| I have completed an exhaustive security scan across 42 router files.         |
|                                                                               |
| +---------------------------------------------------------------------------+ |
| | 📄 Artifact: Backend Security Audit Report (42 files scanned)             | |
| | Summary: 2 endpoints missing rate limits, 1 unvalidated query parameter.  | |
| | [ 👁️ View Full Report ]                   [ ⭐ Promote to Wiki Vault ]    | |
| +---------------------------------------------------------------------------+ |
+-------------------------------------------------------------------------------+
```
