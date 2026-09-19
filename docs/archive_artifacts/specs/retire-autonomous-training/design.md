# Technical Design: Retire Autonomous Training Checkbox & JIT Synthesis

> **Spec Status**: Approved  
> **Linked Requirements**: [`requirements.md`](./requirements.md)  
> **Traceability Key**: All components reference corresponding `[REQ-PRUNE-AUTO-xxx]` tags.  

---

## 1. Architecture Overview & Component Boundaries

```
[Chat Turn Execution] 
         │
         ▼
[CapabilityDetector.detect()] 
         │
         ├───[ Gap Detected ]────────────────────────┐
         │                                           ▼
         │                          [CapabilityGapRepository.create_gap()]
         │                                           │
         │                                           ▼
         │                              [SQLite capability_gaps Table]
         │                                           │
         │                                           ▼
         ▼                              [Factory Studio: Backlog Tab]
[Assistant Message Returned]             (Human Operator Reviews & Trains)
```

1. **Frontend Surface (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`)**:
   - Strip `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput` from the HTML template.
   - Remove JavaScript selectors and event handlers in `forge.js`.
2. **Backend Kernel Execution (`src/application/kernel/agent_kernel.py`)**:
   - Remove the `if getattr(agent, "allow_autonomous_training", False):` fork.
   - Unconditionally route any detected gap to `self.capability_gap_repo.create_gap()`.
3. **Data Model Integrity (`src/domain/kernel/models.py`, `src/domain/settings/models.py`)**:
   - Keep `allow_autonomous_training: bool = False` and `max_training_retries: int = 2` on `AgentProfile` and `AgentCustomization` as default backward-compatible fields so existing rows in SQLite don't fail schema validation.

---

## 2. Interface Specifications & Contracts

### Agent Studio Template (`src/web/templates/index.html`)
The container for Autonomous Training Controls (lines 2622–2636) is deleted. The following `#forgeScaffoldQueueCard` (Agent Training Optimization) remains as the primary capability review surface in Agent Studio.

### Kernel Event Stream (`src/application/kernel/agent_kernel.py`)
In `run_stream` and `run_turn`, when `CapabilityDetector.detect` discovers a gap:
```python
gap = CapabilityDetector.detect(user_prompt=user_req_text, assistant_response=full_content)
if gap:
    try:
        self.capability_gap_repo.create_gap(
            agent_id=agent.id,
            user_prompt=gap.user_prompt,
            missing_capability=gap.missing_capability,
            context_summary=gap.context_summary,
            suggested_tool_name=gap.suggested_tool_name,
        )
    except Exception as ge:
        logger.debug("Failed to record capability gap: %s", ge)
```
No `jit_synthesizer.synthesize_and_deploy` call is made during live chat.

---

## 3. Backward Compatibility & Migration
No schema migration is needed. The SQLite columns `allow_autonomous_training` and `max_training_retries` remain intact with their default values. Existing custom agents stored in the DB continue to load cleanly without error.
