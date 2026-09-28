# [CARD-355] Forge Platform Specialist: Conversational Intake Partner for Factory Studio

> **Status**: Complete  
> **Created**: 2026-09-18  
> **Closed**: 2026-09-18  
> **Spec Reference**: `docs/specs/agent-pack-factory/`, CARD-351  
> **Labels**: `type:feature`, `AutoReiv.Packs`, `AutoReiv.Tools`, `AutoReiv.Frontend`, `AutoReiv.Factory`  


---

## 1. Three Beats

### Beat 1: What Jacob means
Some operators find blank form inputs (Seed Intent, Starter Objectives, Reference Context) intimidating, or simply prefer talking through a capability requirement with an intelligent partner before manufacturing begins. 

Just as Education Studio provides a dedicated, Socratic companion agent (**Tutor**) grounded in topic mastery, Factory Studio should have a dedicated core platform specialist agent named **Forge (Capability Architect)**. 

Forge lives in Chat Studio and acts as an expert capability architect. Through structured Socratic inquiry, Forge helps the operator articulate what capability is missing, inspects existing tools on the target agent, determines the appropriate deliverable architecture (Native Atomic Tool, Model Context Protocol Server, or Skill Runbook), refines testable starter objectives, and drafts necessary reference context. When the operator confirms the specification, Forge programmatically dispatches the job into the deterministic 8-phase Agent Training Factory pipeline via a dedicated platform tool (`launch_factory_training`), returning the job ID and inviting the operator to monitor execution in Factory Studio.

### Beat 2: What AutoReiv does now
* Factory Studio provides an on-canvas Capability Intake Workbench (`#factoryIntakeView`, CARD-351), but all inputs (Goal, Objectives, Reference Materials, Architecture) must be authored and submitted manually by typing into textareas.
* Existing platform agents (`autoreiv`, `developer`, `direct`, `tutor`) have generalist or topic-specific system prompts. None are specialized in capability elicitation, taxonomy classification, or training job dispatch.
* No platform tool currently exists for conversational agents to inspect a target agent's current pack inventory (`inspect_agent_pack`) or programmatically queue an Agent Training Factory job (`launch_factory_training`).
* There is no direct on-canvas bridge in Factory Studio to transition smoothly to a capability design conversation in Chat Studio.

### Beat 3: What will change
1. **Core Platform Specialist Pack (`platform-packs/forge/pack.json`)**:
   - Seed a new platform agent pack: `platform-packs/forge/pack.json` (seeded into `$AUTOREIV_DATA_DIR/packs/forge/` on startup).
   - Register `forge` in `PLATFORM_PACK_IDS` in `src/application/agent_packs/schema.py` and `src/infrastructure/skills/platform_packs.py`.
   - Identity: `Forge (Capability Architect)` with avatar icon `hammer` or `anvil` and tone `pragmatic`, `collaborative`, `rigorous`.
   - System prompt tailored with explicit sections:
     - `[IDENTITY & ROLE]`: Socratic Capability Architect for AutoReiv.
     - `[DOMAIN BOUNDARIES & REFUSALS]`: Does **not** write arbitrary unverified code directly into user packs or bypass the 8-phase pipeline. Hands off all code authoring, AST analysis, and verification to the factory runner via `launch_factory_training`.
     - `[EXECUTION PROTOCOL]`:
       1. Identify target agent and inspect its current capabilities (`inspect_agent_pack`).
       2. Socratic requirement discovery: uncover host context, inputs, outputs, CLI cmdlets, and edge cases.
       3. Reference context grounding: ingest pasted API snippets, error logs, or documentation.
       4. Deliverable architecture recommendation: classify into Native Tool (`tool`), MCP Server (`mcp`), or Procedural Skill (`skill`).
       5. Draft 1–3 clear, verifiable starter objectives.
       6. Present the distilled specification to the human operator for explicit confirmation.
       7. Invoke `launch_factory_training(...)` upon human confirmation.
       8. Report the resulting `job_id` and provide clear directions to Factory Studio (`#view-factory`).
2. **Platform Tools**:
   - `inspect_agent_pack(agent_id: str)`:
     - Reads target agent's pack manifest and storage to return agent name, description, active tool names, skill IDs, and pack folder path. Allows Forge to see what the agent already knows.
   - `launch_factory_training(target_agent_id, seed_intent, objectives, deliverable_type, reference_docs, target_host, target_directory, risk_policy)`:
     - Programmatically queues a `FactoryJob` and initial `WorkPacket` in `agent_training_factory`, kicks the orchestrator tick, and returns `{ "success": True, "job_id": "...", "target_agent_id": "...", "status": "queued" }`.
3. **Factory Studio UI Bridge (`[ 💬 Talk it out with Forge ]`)**:
   - Add a secondary action button `#factoryIntakeTalkToForgeBtn` in Factory Studio (`#factoryIntakeView`).
   - Clicking the button identifies the currently selected agent in `#factoryAgentSelect`, navigates to Chat Studio (`#view-chat`), switches the active agent to `forge`, and seeds the chat input with: `I want to design a new capability for agent "${agentId}". Let's talk through what it needs.`

---

## 2. Primitives Breakdown

| Primitive | Concrete Changes |
| :--- | :--- |
| **Platform Pack** | `platform-packs/forge/pack.json` — Identity, system prompt, avatar, allowed tools (`inspect_agent_pack`, `launch_factory_training`, `lookup_agents`, `handoff_to_agent`). |
| **Platform Tools** | `launch_factory_training` and `inspect_agent_pack` registered in `src/infrastructure/agents/registry.py` and implemented in `src/application/skills/factory_dispatch_tools.py`. |
| **Platform Constants** | Add `"forge"` to `PLATFORM_PACK_IDS` in `src/application/agent_packs/schema.py` and `src/infrastructure/skills/platform_packs.py`. |
| **Studio UI** | Add `#factoryIntakeTalkToForgeBtn` in `src/web/templates/index.html` and wire click navigation in `src/web/static/modules/studios/factory.js`. |

---

## 3. Scope Boundaries & Architectural Guardrails

1. **Intake Partner, Not Execution Bypass**: Forge formulates the requirement and triggers the pipeline; Forge does **not** bypass the 8-phase factory pipeline (Intent Distill → Ground → Blueprint → Author → Scenario Verify → Code Verify → Optimize → Promote).
2. **Checkout Working-Tree Hygiene**: `platform-packs/forge/` is factory seed only. Live runtime packs live exclusively in `$AUTOREIV_DATA_DIR/packs/forge/`.
3. **Human Approval Preserved**: Factory jobs launched via `launch_factory_training` default to `risk_policy="ask"`, ensuring the human promotion gate remains fully authoritative.

---

## 4. Acceptance Criteria (Definition of Done)

- [x] **Platform Pack Seed**: `platform-packs/forge/pack.json` exists with schema 1.1, Socratic capability architect system prompt, and correct tool allowlists.
- [x] **Platform Seeding Integration**: `"forge"` is included in `PLATFORM_PACK_IDS` and seeded to user data automatically on app startup.
- [x] **Tool: `inspect_agent_pack`**: Returns agent metadata, existing tool list, and skill list for any registered agent pack.
- [x] **Tool: `launch_factory_training`**: Validates parameters, creates a `FactoryJob` and initial `WorkPacket`, triggers orchestrator tick, and returns structured job metadata.
- [x] **Factory Studio UI Bridge**: `#factoryIntakeTalkToForgeBtn` rendered on `#factoryIntakeView`, clicking navigates to Chat Studio scoped to `forge` with agent context pre-seeded.
- [x] **Frontend & Backend Tests**:
  - Unit tests for `inspect_agent_pack` and `launch_factory_training` in `tests/unit/skills/test_factory_dispatch_tools.py`.
  - Platform pack seeding test for `forge` in `tests/unit/skills/test_platform_packs.py`.
  - Frontend unit tests for `#factoryIntakeTalkToForgeBtn` click flow in `tests/unit/frontend/factory_studio.test.js`.
- [x] **Documentation & Traceability**:
  - Requirements `[REQ-FACT-060]` through `[REQ-FACT-063]` added to `docs/specs/agent-pack-factory/requirements.md` and `docs/rtm.json`.
  - `CHANGELOG.md` updated under `[Unreleased]`.
- [x] **Zero Regressions**: All existing factory tests pass, `ruff check .` clean, `npm run preflight` passes.

---

## 5. Reply Phrase
When live testing passes, reply with:
**`merge to qa`**


