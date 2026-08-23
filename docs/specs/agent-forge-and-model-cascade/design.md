# Technical Design: Agent Forge Studio & Purpose Routing Cascade

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`tasks.md`](./tasks.md)  
> **Applicable ADRs**: `docs/adr/0017-agent-forge-studio-and-purpose-routing-cascade.md`

---

## 1. System Architecture & Model Resolution Cascade Flow

```mermaid
flowchart TD
    Prompt[User Input / Subagent Call] --> Kernel[AgentKernel.run_turn]
    Kernel --> CheckOverride{Agent has explicit model override?}
    CheckOverride -- Yes (e.g. qwen2.5-coder:7b) --> ExecModel[Execute on Explicit Model]
    CheckOverride -- No / 'default' --> CheckPurpose{Agent has Purpose Slot?}
    CheckPurpose -- Yes (e.g. TASK_EXECUTION) --> MatrixLookup[Lookup Purpose in ModelPurposeMatrix]
    MatrixLookup --> PurposeModel[Execute on Matrix Model (e.g. qwen2.5-coder:7b)]
    CheckPurpose -- No --> DefaultLookup[Execute on Global Default Model]
```

---

## 2. Domain Models & Database Schemas

### 2.1. Enhanced `AgentProfile` Domain Model (`src/domain/kernel/models.py`)
```python
class AgentProfile(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    purpose: ModelPurpose = ModelPurpose.GENERAL
    tone: Optional[str] = "Professional, helpful, and concise"
    avatar_icon: str = "bot"
    model: str = "default"
    allowed_tool_names: Optional[List[str]] = None
    max_turns: int = 15
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

### 2.2. SQLite Custom Agents Table Schema
```sql
CREATE TABLE IF NOT EXISTS custom_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'general',
    tone TEXT,
    avatar_icon TEXT DEFAULT 'bot',
    model TEXT DEFAULT 'default',
    allowed_tool_names TEXT, -- JSON array
    max_turns INTEGER DEFAULT 15,
    is_builtin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2.3. `AgentBuilderSkill` Tooling (`src/application/skills/agent_builder_skill.py`)
- `list_available_skills_and_tools()`: Returns metadata on all installed system skills and tools.
- `propose_agent_specification(role, objective, domain)`: Generates validated agent configs.
- `save_agent_specification(agent_spec)`: Persists agent profile in registry.
