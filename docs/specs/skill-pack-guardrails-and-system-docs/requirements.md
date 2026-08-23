# Requirements: Skill Pack Hierarchy, Guardrails, and System Documentation Browser

> **Standard**: AWS Kiro EARS (Easy Approach to Requirements Syntax)  
> **Traceability Prefix**: `[REQ-SKIL-xxx]`  
> **Target Components**: `AutoReiv.Skills`, `AutoReiv.Agents`, `AutoReiv.Web`

---

## 1. System Context & User Stories

As an **Operator & System Architect**,  
I want to **view and toggle agent tool authorization organized by logical Skill Packs with granular expanders**,  
And I want **strict guardrail validation that deterministically rejects hallucinated tools, invalid slugs, or malformed agent profiles**,  
And I want **a dedicated System Documentation & Specs Browser in the Control Plane to read specs, ADRs, and architecture notes**,  
So that **our agents and skills are strictly compliant with platform invariants and all system documentation is accessible directly in the UI**.

---

## 2. EARS Requirements Specification

### [REQ-SKIL-001]: Hierarchical Skill Pack Catalog API
- **Type**: Ubiquitous
- **Statement**: The system shall expose a structured endpoint `GET /api/skills/catalog` that groups tools under their respective parent **Skill Packs** (e.g. `SysadminSkill`, `LibrarianSkill`, `VerificationSkill`, `PlanningSkill`, `AgentBuilderSkill`, `DelegateSkill`, `MCPSkill`), detailing each pack's display name, icon, description, and atomic tool list.

### [REQ-SKIL-002]: Agent Forge Hierarchical Skill Pack UI & Bundle Selection
- **Type**: Event-Driven
- **Statement**: When an operator views the Character Sheet in Agent Forge Studio, the UI shall render tool authorizations grouped by Skill Pack cards, allowing one-click *"Select Pack"* bundle toggles while preserving expandable individual tool checkboxes.

### [REQ-SKIL-003]: Deterministic Agent Specification Guardrail Engine
- **Type**: Ubiquitous / Defensive
- **Statement**: When an agent profile is proposed by `AgentBuilderSkill` or submitted to `POST /api/agents` or `PUT /api/agents/{id}`, the system shall validate the payload against platform invariants: ensuring kebab-case regex ID slugs, validating that all `allowed_tool_names` exist in the real tool registry (rejecting hallucinated tools), verifying valid `ModelPurpose` and `AgentTone`, and bounding `max_turns` between 1 and 50.

### [REQ-SKIL-004]: System Documentation & Specs Navigation REST API
- **Type**: Ubiquitous
- **Statement**: The system shall expose safe documentation indexing and retrieval endpoints `GET /api/docs/nav` and `GET /api/docs/content?path={rel_path}` that traverse `docs/specs/`, `docs/adr/`, and architecture documents without directory traversal vulnerabilities.

### [REQ-SKIL-005]: Control Plane System & Specs Documentation Browser UI
- **Type**: Ubiquitous
- **Statement**: The system shall provide a dedicated navigation tab `[📖 System Docs]` in the Control Plane SPA featuring a searchable document tree (Specs, ADRs, Invariants, RTM Summary) and a responsive Markdown reader with syntax highlighting, GitHub alerts, and Mermaid diagram rendering.
