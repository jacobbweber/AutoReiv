# Technical Design: In-Situ Skill Distillation

> **Linked Spec**: [`requirements.md`](./requirements.md)  
> **Applicable ADRs**: `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`

---

## 1. Architectural Overview & C4 Context

```mermaid
graph TD
    UI[Chat Studio Assistant Message] -->|Click 'Teach Agent'| Modal[Teaching Guidance Modal]
    Modal -->|POST /api/skills/distill| Router[Skills Web Router]
    Router --> Service[SkillDistillationService]
    Service --> Store[SQLiteStateStore: sessions/messages/spans]
    Service --> Gateway[LLM Gateway: Distillation Prompt]
    Service --> Router
    Router -->|SkillProposal DTO| UI
    UI -->|Render| Card[Inline Skill Proposal Card]
    Card -->|POST /api/skills/adopt| Router
    Router --> Service
    Service --> PackFS[User Data: $DATA_DIR/packs/<agent>/skills/<slug>/SKILL.md]
    Service --> Registry[AgentRegistry: Sync Profile]
    Card -->|Send to Factory| Factory[Factory Studio Intake Workbench]
```

---

## 2. Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant Chat as Chat Studio UI
    participant API as /api/skills/distill & /adopt
    participant Distill as SkillDistillationService
    participant Store as SQLiteStateStore
    participant GW as LLM Gateway
    participant Pack as User Data Packs FS

    User->>Chat: Click [ 💡 Teach Agent ] on message
    Chat->>User: Open prompt modal (optional guidance)
    User->>Chat: Click "Auto-Diagnose & Draft"
    Chat->>API: POST /api/skills/distill { session_id, message_id, guidance }
    API->>Distill: distill_turn_into_skill(...)
    Distill->>Store: Fetch turn transcript (user prompt, tool calls, errors, response)
    Distill->>GW: Run structured distillation prompt
    GW-->>Distill: JSON { needs_tool, slip, remedy, skill_id, name, desc, runbook }
    Distill-->>API: SkillProposal DTO
    API-->>Chat: 200 OK with proposal
    Chat->>User: Render Inline Skill Proposal Card
    alt User clicks [ ✅ Adopt Skill ]
        User->>Chat: Click [ ✅ Adopt Skill ]
        Chat->>API: POST /api/skills/adopt { target_agent_id, skill_id, runbook_markdown }
        API->>Distill: adopt_skill(...)
        Distill->>Pack: Write $DATA_DIR/packs/<agent>/skills/<skill_id>/SKILL.md
        Distill->>Pack: Update pack.json (allowed_skill + skills)
        Distill-->>API: 200 OK { status: "adopted" }
        API-->>Chat: Skill mounted
        Chat->>User: Display "Skill mounted to <Agent>. Active for your next message."
    else Capability requires new Python tool
        User->>Chat: Click [ 🚀 Send to Factory Studio ]
        Chat->>Chat: Switch to Factory Studio with pre-filled Goal & Objectives
    end
```

---

## 3. Data Contracts & Interfaces

### Public REST Endpoints

#### 1. `POST /api/skills/distill`
**Request Payload (`DistillRequest`)**:
```json
{
  "session_id": "sess_123",
  "message_id": "msg_456",
  "guidance": "Always save templates under resources/templates/."
}
```

**Response Payload (`DistillResponse`)**:
```json
{
  "status": "ok",
  "target_agent_id": "autoreiv",
  "skill_id": "wiki-template-canonical-path",
  "name": "Wiki Template Canonical Path",
  "description": "Enforce saving wiki templates to resources/templates/.",
  "plain_summary": {
    "observed_slip": "The agent attempted to save template to notes/resources/.",
    "remedy": "Enforce canonical template paths under resources/templates/ and prohibit general note tools."
  },
  "runbook_markdown": "---\nname: wiki-template-canonical-path\ndescription: Enforce saving wiki templates to resources/templates/.\n---\n\n## When to Use\n...\n\n## Procedure\n...\n\n## Common Pitfalls & Forbidden Paths\n...\n\n## Verification\n...",
  "needs_tool": false,
  "factory_escalation": null
}
```

#### 2. `POST /api/skills/adopt`
**Request Payload (`AdoptSkillRequest`)**:
```json
{
  "target_agent_id": "autoreiv",
  "skill_id": "wiki-template-canonical-path",
  "runbook_markdown": "---\nname: wiki-template-canonical-path\n...\n"
}
```

**Response Payload (`AdoptSkillResponse`)**:
```json
{
  "status": "adopted",
  "target_agent_id": "autoreiv",
  "skill_id": "wiki-template-canonical-path",
  "file_path": "packs/autoreiv/skills/wiki-template-canonical-path/SKILL.md"
}
```

---

## 4. UI Component Architecture

1. **Assistant Message Action Bar**:
   - Add button `.msg-teach-agent-btn` (`[ 💡 Teach Agent ]`) inside `#chatStream` assistant message headers.
2. **Teach Agent Guidance Modal (`#teachAgentModal`)**:
   - Target Agent display pill.
   - Textarea `#teachAgentGuidanceInput` (placeholder: *"What should the agent have done differently? (Optional: leave blank to auto-diagnose from turn context)"*).
   - Buttons: `[ Auto-Diagnose & Draft ]` (primary) and `[ Cancel ]`.
3. **Inline Chat Skill Proposal Card (`.skill-proposal-card`)**:
   - Header with icon `💡 Skill Proposal: <Name>`.
   - Plain summary box with Observed Slip and Recommended Remedy.
   - Accordion preview: `<details><summary>View Raw Runbook (SKILL.md)</summary><pre>...</pre></details>`.
   - Primary action: `[ ✅ Adopt Skill to <Agent> ]` (or `[ 🚀 Send to Factory Studio ]` if `needs_tool` is true).
   - Secondary actions: `[ ✏️ Edit ]`, `[ ✕ Dismiss ]`.


---

## 4. Error Handling & Edge Cases

| Error Scenario | Detection Point | Handling / Fallback | User Response |
| :--- | :--- | :--- | :--- |
| Invalid Payload | API Layer | Schema Validation | HTTP 400 with field details |
| Timeout / Downstream Error | Adapter Layer | Circuit Breaker / Retry | HTTP 503 / Friendly message |
