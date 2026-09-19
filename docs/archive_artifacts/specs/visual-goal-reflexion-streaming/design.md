# Technical Design: Visual Goal Mode & Reflexion Streaming

## Architecture Context & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as Chat Studio UI (chat.js)
    participant Router as /api/chat/stream (FastAPI)
    participant PlanEng as PlanAndExecuteEngine
    participant RefEng as ReflexionLoopEngine
    participant Kernel as AgentKernel

    User->>Browser: Types goal + toggles [x] Goal [x] Verify
    Browser->>Router: POST /api/chat/stream { agent_id, session_id, content, goal_mode: true, self_verify: true }
    
    alt goal_mode == true
        Router->>PlanEng: formulate_plan(agent, goal)
        PlanEng-->>Router: ExecutionPlan(steps=[S1, S2, S3])
        Router-->>Browser: SSE event: plan_formulated { steps: [...] }
        
        loop For Each Step in Plan
            Router-->>Browser: SSE event: step_start { step_index: i, title: "..." }
            alt self_verify == true
                Router->>RefEng: run_reflexion_turn(agent, step_prompt)
                RefEng->>Kernel: stream_turn / run_turn
                Router-->>Browser: SSE event: reflexion_attempt { attempt: 1 }
                RefEng-->>Router: Step Result (verified)
            else standard step
                Router->>Kernel: run_turn(agent, step_prompt)
                Kernel-->>Router: Step Result
            end
            Router-->>Browser: SSE event: step_complete { step_index: i, status: "completed" }
        end
        Router->>PlanEng: synthesize_plan_results(...)
        Router-->>Browser: SSE event: token / turn_done
    else standard / single-turn
        Router->>Kernel: stream_turn(agent, content)
        Kernel-->>Router: Event Stream
        Router-->>Browser: SSE stream events
    end
```

---

## Component Modifications

1. **`src/web/routers/chat.py`**:
   - Update `ChatStreamRequest` to include `goal_mode: bool = False` and `self_verify: bool = False`.
   - Update `chat_stream` generator to dispatch through `PlanAndExecuteEngine` and `ReflexionLoopEngine` when flags are set.
2. **`src/web/static/modules/studios/chat.js`**:
   - Include `goal_mode: state.goalEnabled` and `self_verify: state.verifyEnabled` in `/api/chat/stream` payload.
   - Add SSE listeners for `plan_formulated`, `step_start`, `step_complete`, `reflexion_attempt`, `reflexion_critique`, and `reflexion_verified`.
   - Render the dynamic milestone DAG card and reflexion badge inside `streamBubble`.
