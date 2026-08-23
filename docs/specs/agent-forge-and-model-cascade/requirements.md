# Requirements Specification: Agent Forge Studio & Purpose Routing Cascade

> **Spec Status**: Ready for Implementation  
> **Target Release**: Milestone 16 (v1.4.0)  
> **Primary Component**: `AutoReiv.Agents`, `AutoReiv.Kernel`, & `AutoReiv.Web`  
> **Applicable ADRs**: `docs/adr/0017-agent-forge-studio-and-purpose-routing-cascade.md`  
> **Linked Work Card**: `.github/cards/CARD-016-agent-forge-studio-and-purpose-routing-cascade.md`

---

## 1. Executive Summary & User Story
As an AutoReiv operator and systems architect,  
I want a dedicated Agent Forge Studio where I can inspect, create, customize, and delete agents using an RPG character sheet interface, bind agents to purpose matrix slots or explicit models, configure granular skill scopes, view live agent telemetry, and collaborate with an in-studio System Agent AI Co-Pilot,  
So that agent lifecycle management is intuitive, repeatable, deterministic, and fully compliant with AI engineering standards.

---

## 2. EARS Functional Requirements

### `[REQ-FORGE-001]` 3-Tier Purpose-to-Model Resolution Cascade
- **Ubiquitous**: WHEN executing an agent turn or routine, THE `AgentKernel` SHALL resolve the execution model through a hierarchical cascade: (1) Agent explicit model override, (2) Purpose Matrix slot corresponding to `agent.purpose`, (3) Gateway global default model.

### `[REQ-FORGE-002]` Agent Purpose Classification Contract
- **Ubiquitous**: EVERY `AgentProfile` SHALL define a `purpose` attribute of type `ModelPurpose` (`GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, `FAST`), enabling automatic model inheritance from the Purpose Matrix.

### `[REQ-FORGE-003]` SQLite Custom Agent Persistence & Lifecycle Management
- **State-driven**: THE `SQLiteStateStore` and `BuiltinAgentRegistry` SHALL persist custom agent profiles with full CRUD operations (`create`, `read`, `update`, `delete`), while strictly protecting built-in agent baseline profiles from deletion.

### `[REQ-FORGE-004]` Granular Skill Tool Scoping (RBAC)
- **Ubiquitous**: WHEN an agent is customized with an `allowed_tool_names` list, THE `ScopedToolRegistry` SHALL strictly filter and enforce authorized tool execution boundaries at runtime.

### `[REQ-FORGE-005]` System Agent Meta-Builder Tooling (`AgentBuilderSkill`)
- **Ubiquitous**: THE `AgentBuilderSkill` SHALL equip `system-agent` with tools (`list_available_skills_and_tools`, `propose_agent_specification`, `save_agent_specification`) allowing it to assist operators in authoring valid, deterministic agent configurations.

### `[REQ-FORGE-006]` "Agent Forge" Studio SPA & Real-Time Co-Pilot Chat
- **Ubiquitous**: THE Web UI SHALL provide a dedicated Agent Studio view featuring a compartmentalized Character Sheet (Identity, Avatar, Tone, Operating Manual, Purpose/Model, Skill Scopes, Lifetime Telemetry) and an embedded interactive System Agent chat panel.
