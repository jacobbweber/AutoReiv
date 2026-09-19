# Design: Mobile Stream Resiliency & Goal Markdown Synthesis

## 1. Architectural Overview
This design decouples HTTP SSE event streaming from underlying agent turn execution in FastAPI. 

### Component Interaction Diagram
\\mermaid
sequenceDiagram
    autonumber
    actor User as Mobile User (Phone)
    participant Browser as Chat Studio (Frontend)
    participant API as FastAPI Router (/api/chat/stream)
    participant Worker as Background Task Worker
    participant Kernel as Agent Kernel / Plan Engine
    participant Store as SQLite State Store

    User->>Browser: Send Goal Prompt
    Browser->>API: POST /api/chat/stream (SSE)
    API->>Worker: Spawn shielded asyncio.Task
    Worker->>Kernel: Run Plan Formulation & Execution
    Worker->>API: Publish SSE events (Queue)
    API-->>Browser: Stream SSE (plan_formulated, step_start, etc.)
    
    Note over User,Browser: Phone screen sleeps / app switches (TCP dropped)
    Browser-xAPI: Connection aborted
    
    Worker->>Kernel: Finish step execution & final markdown synthesis
    Worker->>Store: Save assistant deliverable to SQLite
    
    Note over User,Browser: Phone unlocks & tab regains focus
    Browser->>API: GET /api/chat/sessions/{id}/messages
    API->>Store: Fetch messages
    API-->>Browser: Return updated messages (including deliverable)
    Browser->>User: Render complete markdown report!
\
## 2. Synthesis Prompt & Fallback Formatting
The synthesis prompt explicitly instructs:
- Format as GitHub-flavored Markdown
- Include key summary, sections, action items, rollout table
- Never return raw JSON dictionaries
- Fallback JSON parser detects any valid JSON containing \goal\, \ction_plan\, \steps\, or \summary\ and converts them to formatted Markdown tables and headers.
