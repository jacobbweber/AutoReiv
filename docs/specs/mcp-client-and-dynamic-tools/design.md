# Technical Design: MCP Standard Client Adapter & 3-Tier Dynamic Tool Resolution

> **Linked Spec**: [`requirements.md`](./requirements.md)  
> **Applicable ADRs**: `docs/adr/0001-baseline-sdlc.md`  

---

## 1. Architectural Overview & C4 Context

```mermaid
graph TD
    subgraph UI["AutoReiv Web UI (Settings Studio)"]
        MCPPanel["MCP Settings Panel (#mcpServerList)"]
    end

    subgraph Web["FastAPI Router (src/web/routers/settings.py)"]
        MCPEndpoints["/api/settings/mcp (GET, POST, DELETE)"]
    end

    subgraph Application["Application Layer (Kernel & MCP)"]
        Kernel["AgentKernel (src/application/kernel/agent_kernel.py)"]
        ToolRanker["ToolRanker (src/application/kernel/tool_ranker.py)"]
        MCPManager["MCPClientManager (src/infrastructure/mcp/client_adapter.py)"]
        SkillLoader["DynamicSkillLoader (src/application/skills/dynamic_loader.py)"]
        ToolReg["ScopedToolRegistry (src/application/kernel/tool_registry.py)"]
    end

    subgraph Infrastructure["Infrastructure & External Processes"]
        SQLite["SQLiteStateStore (mcp_servers table)"]
        MCPSubprocess["External MCP Server (stdio Subprocess: npx, uvx, python)"]
    end

    MCPPanel --> MCPEndpoints
    MCPEndpoints --> MCPManager
    MCPEndpoints --> SQLite
    MCPManager --> MCPSubprocess
    MCPManager --> ToolReg
    SkillLoader --> ToolReg

    Kernel --> ToolRanker
    ToolRanker --> ToolReg
```

---

## 2. 3-Tier Tool Resolution Flow (Context Window Preservation)

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Chat Session
    participant Kernel as AgentKernel
    participant Ranker as ToolRanker (BM25)
    participant Registry as ScopedToolRegistry
    participant Gateway as LLMGateway

    User->>Kernel: stream_turn(user_content="Check CPU load")
    Kernel->>Registry: get_tools_for_agent(agent) [Tier 1: Hard RBAC]
    Registry-->>Kernel: List of 40 Authorized ToolDefinitions
    
    alt Total Authorized Tools <= max_active_tools (6)
        Kernel->>Kernel: Mount all tools directly
    else Total Authorized Tools > max_active_tools
        Kernel->>Ranker: rank(query="Check CPU load", tools, pinned_tools, limit=6) [Tier 2 & 3]
        Ranker-->>Kernel: Top 6 ToolDefinitions (e.g. Sysadmin + Pinned)
    end

    Kernel->>Gateway: CompletionRequest(tools=Top 6 Definitions)
    Gateway-->>User: Streaming Response / Tool Execution
```

---

## 3. Data Models & API Contracts

### MCPServerConfig (Domain Model)
```python
class MCPServerConfig(BaseModel):
    name: str = Field(description="Unique identifier for the MCP server")
    command: List[str] = Field(description="Subprocess invocation command (e.g. ['npx', '-y', '@modelcontextprotocol/server-everything'])")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables passed to subprocess")
    enabled: bool = Field(default=True, description="Whether server is auto-started on boot")
```

### ToolRanker Interface (`src/application/kernel/tool_ranker.py`)
```python
class ToolRanker:
    """Fast in-memory BM25 ranker for selecting top-K relevant tool schemas."""
    
    @classmethod
    def rank_tools(
        cls,
        query: str,
        tools: List[ToolDefinition],
        pinned_tool_names: Optional[List[str]] = None,
        max_tools: int = 6,
    ) -> List[ToolDefinition]:
        ...
```

### Settings REST API Contracts
- `GET /api/settings/mcp`: Returns `List[MCPServerConfig]` with active connection status and mounted tool count.
- `POST /api/settings/mcp`: Validates command, performs test handshake, persists to SQLite, mounts tools.
- `DELETE /api/settings/mcp/{name}`: Terminates subprocess, removes from SQLite, unmounts tools.

### Public Interfaces / Ports
```python
class FeaturePort(Protocol):
    def execute(self, command: CommandDTO) -> ResultDTO: ...
```

### Data Transfer Objects / Schemas
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "status": { "type": "string" }
  },
  "required": ["id", "status"]
}
```

---

## 4. Error Handling & Edge Cases

| Error Scenario | Detection Point | Handling / Fallback | User Response |
| :--- | :--- | :--- | :--- |
| Invalid Payload | API Layer | Schema Validation | HTTP 400 with field details |
| Timeout / Downstream Error | Adapter Layer | Circuit Breaker / Retry | HTTP 503 / Friendly message |
