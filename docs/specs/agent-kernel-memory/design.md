# Technical Design: Agent Kernel, Scoped Memory & Telemetry Engine

> **Linked Spec**: [`requirements.md`](./requirements.md)  
> **Applicable ADRs**: [`docs/adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md`](../../adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md)

---

## 1. Architectural Overview & Component Topology

```mermaid
flowchart TD
    subgraph Client["Caller (Chat API / Scheduler)"]
        Caller["AgentRunner / Session Handler"]
    end

    subgraph KernelLayer["Agent Kernel (src/application/kernel/)"]
        AK["AgentKernel (ReAct Loop)"]
        TR["ScopedToolRegistry (RBAC Filter)"]
    end

    subgraph MemoryLayer["State & Memory (src/infrastructure/memory/)"]
        DB["SQLiteStateStore (WAL Mode)"]
        SessionsTable[("sessions table")]
        MessagesTable[("messages table")]
        TelemetryTable[("telemetry_spans table")]
    end

    subgraph TelemetryLayer["Telemetry & Observability (src/application/telemetry/)"]
        TC["TelemetryCollector"]
    end

    subgraph GatewayLayer["Multi-Provider Gateway (src/application/gateway/)"]
        GW["MultiProviderGateway"]
    end

    Caller --> AK
    AK --> TR
    AK --> GW
    AK --> DB
    AK --> TC
    TC --> DB
    DB --> SessionsTable
    DB --> MessagesTable
    DB --> TelemetryTable
```

---

## 2. Sequence Flow: Agent ReAct Execution Loop

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Caller / User
    participant K as AgentKernel
    participant DB as SQLiteStateStore
    participant TR as ScopedToolRegistry
    participant GW as MultiProviderGateway
    participant T as TelemetryCollector

    Caller->>K: run_turn(agent_profile, session_id, user_message)
    K->>DB: save_message(session_id, user_message)
    K->>DB: get_messages(session_id)
    DB-->>K: history
    K->>TR: get_tools_for_agent(agent_profile)
    TR-->>K: allowed_tool_definitions

    loop ReAct Turn (up to max_turns)
        K->>GW: complete(request with allowed_tools)
        GW-->>K: CompletionResponse
        alt Response has Content Only (No Tools)
            K->>DB: save_message(session_id, assistant_message)
            K->>T: record_span(turn_telemetry)
            K-->>Caller: Final Response
        else Response has Tool Calls
            K->>DB: save_message(session_id, assistant_message_with_calls)
            loop For each ToolCall
                K->>TR: execute(tool_call, agent_profile.id)
                alt Tool is Authorized
                    TR-->>K: ToolResult(success=True, output)
                else Tool Unauthorized / Error
                    TR-->>K: ToolResult(success=False, error="Permission denied")
                end
                K->>T: record_tool_span(tool_telemetry)
                K->>DB: save_message(session_id, tool_message)
            end
        end
    end
```

---

## 3. Data Contracts & Domain Models

### 3.1 Kernel & Agent Profile Models (`src/domain/kernel/models.py`)

```python
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AgentTone(str, Enum):
    CONCISE = "concise"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    ACADEMIC = "academic"
    SOCRATIC = "socratic"
    DEFAULT = "default"


class AgentProfile(BaseModel):
    id: str = Field(description="Unique agent identifier (e.g. 'general-assistant')")
    name: str = Field(description="Human readable name")
    description: str = Field(description="Agent role summary")
    system_prompt: str = Field(description="Base persona prompt")
    tone: AgentTone = Field(default=AgentTone.DEFAULT)
    model: str = Field(default="default", description="Model override or purpose tag")
    allowed_tool_names: List[str] = Field(default_factory=list, description="Authorized tool IDs")
    max_turns: int = Field(default=10, ge=1, le=50)


class ToolResult(BaseModel):
    call_id: str
    tool_name: str
    output: Any
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0


class KernelEventType(str, Enum):
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TURN_END = "turn_end"
    ERROR = "error"


class KernelEvent(BaseModel):
    event_type: KernelEventType
    content: str = ""
    reasoning_content: str = ""
    tool_call: Optional[Dict[str, Any]] = None
    tool_result: Optional[ToolResult] = None
    is_finished: bool = False
```

### 3.2 Memory & Telemetry Models (`src/domain/memory/models.py` & `src/domain/telemetry/models.py`)

```python
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Session(BaseModel):
    id: str
    agent_id: str
    title: str = "New Conversation"
    created_at: datetime
    updated_at: datetime


class TelemetrySpan(BaseModel):
    id: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    span_type: str = "turn"  # "turn" or "tool"
    name: str
    duration_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
```

---

## 4. SQLite WAL Database Schema (`src/infrastructure/memory/schema.sql`)

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    name TEXT,
    sequence_num INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence_num);

CREATE TABLE IF NOT EXISTS telemetry_spans (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    agent_id TEXT,
    span_type TEXT NOT NULL,
    name TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT 1,
    error_message TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON telemetry_spans(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_span_type ON telemetry_spans(span_type, created_at);
```

---

## 5. Error Handling & Edge Cases

| Scenario | Detection Point | Handling | Outcome |
| :--- | :--- | :--- | :--- |
| Unauthorized Tool Call | `ScopedToolRegistry.execute()` | Check against `allowed_tool_names` | Returns `ToolResult(success=False, error="Tool ... unauthorized for agent ...")` back to LLM |
| Unknown Tool Requested | `ScopedToolRegistry.execute()` | Lookup in registry | Returns `ToolResult(success=False, error="Tool not found")` |
| Infinite Loop / Cycle | `AgentKernel._check_cycle()` | Detects identical consecutive tool arguments | Terminates turn with warning message |
| Database Locked / Busy | `SQLiteStateStore` | `PRAGMA busy_timeout=5000` + retry logic | Recovers cleanly under concurrent calls |
