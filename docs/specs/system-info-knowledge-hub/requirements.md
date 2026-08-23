# Requirements: System Info Conceptual Knowledge Hub and Architectural Overviews

> **Standard**: AWS Kiro EARS (Easy Approach to Requirements Syntax)  
> **Traceability Prefix**: `[REQ-SYST-xxx]`  
> **Target Components**: `AutoReiv.Web`, `AutoReiv.Docs`

---

## 1. System Context & User Stories

As an **Operator, Developer, or System Architect**,  
I want **a dedicated 'System Info' knowledge hub in the AutoReiv web UI that provides structured, educational conceptual overviews and reference definitions (such as Agents vs Workflows vs Routines vs Skill Packs vs Tools, Purpose Matrix routing, and Multi-Agent Orchestration)**,  
And I want **it to replace the raw technical specification dump with clean, digestible guides featuring Mermaid diagrams and comparison tables**,  
So that **I can quickly learn, reference, and understand how the AutoReiv agentic system works without digging through low-level engineering repository files**.

---

## 2. EARS Requirements Specification

### [REQ-SYST-001]: Curated System Info Topic Catalog & Service
- **Type**: Ubiquitous
- **Statement**: The system shall provide a `SystemInfoService` that delivers structured, high-level conceptual chapters (Core Architecture, Concept Hierarchy, Skill Packs Reference, Purpose Matrix & Hardware Sizing, Multi-Agent Orchestration, and Safety & Guardrails) with rich Markdown and interactive Mermaid diagrams.

### [REQ-SYST-002]: System Info UI Navigation & Reader Interface
- **Type**: Ubiquitous
- **Statement**: The web interface shall provide a dedicated `[ℹ️ System Info]` view with a searchable topic sidebar, interactive Mermaid Pan-Tilt-Zoom inspection, and formatted Markdown rendering.

### [REQ-SYST-003]: 5-Tier Architectural Hierarchy & Concept Definitions
- **Type**: Ubiquitous
- **Statement**: The system documentation shall clearly formalize and explain the 5 core conceptual tiers:
  1. **Agents** (Autonomous Personas, system prompts, tone, tool scoping).
  2. **Workflows & Goals** (Multi-step DAG execution plans, milestone tracking).
  3. **Routines** (Background scheduled cron jobs, recurring health checks).
  4. **Skill Packs** (Domain capability clusters, e.g. Sysadmin, Librarian, Verification, Planning, Orchestration).
  5. **Atomic Tools** (Schema-validated functions executed via JSON-RPC/ReAct).
