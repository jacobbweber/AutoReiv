# Requirements Specification: Skill Pack Taxonomy Realignment & AutoReiv Dedicated Diagnostics

> **Card ID**: [`CARD-056`](file:///d:/Projects/Active/AutoReiv/.github/cards/CARD-056-skill-pack-taxonomy-realignment-and-autoreiv-dedicated-diagnostics.md)  
> **Milestone**: 20  
> **Status**: Approved

---

## 1. User Story

As an **AutoReiv user and agent developer configuring custom agents in Agent Forge**,  
I want **skill packs organized into clear, intuitive functional tiers with AutoReiv's core diagnostics distinctly marked**,  
so that **I can easily assign the right tool capabilities without naming confusion, duplicate tools, or conceptual ambiguity.**

---

## 2. EARS Requirements

### `[REQ-TAX-001]`: 3-Tier Skill Pack Taxonomy Schema
- **Type**: Ubiquitous
- **Requirement**: The `SkillPackManifest` domain model SHALL support a `tier` property categorizing every skill pack into one of three standard tiers:
  1. `productivity`: User Knowledge & Productivity (Wiki, Tasks, Batch Worker).
  2. `system`: System Operations & Platform (Sysadmin, AutoReiv Core Diagnostics).
  3. `cognition`: Agent Cognition & Runtime (Goal Planning, Multi-Agent Delegation, Logic Verification, Agent Builder).

### `[REQ-TAX-002]`: AutoReiv Dedicated Branding & Verification Naming Realignment
- **Type**: Ubiquitous
- **Requirement**: The system SHALL brand the internal platform diagnostics pack as `"AutoReiv Core Platform SRE & Diagnostics"` with a dedicated tag (`is_core: true`), and SHALL rename the self-reflection validation pack to `"Agent Logic Verification (Critic)"` to eliminate naming collisions.

### `[REQ-TAX-003]`: Redundant Micro-Helper Tool Pruning
- **Type**: Event-Driven
- **Requirement**: When tools are registered or listed, the system SHALL prune `yaml_frontmatter_parse` from the active tool registry, relying on `wiki_note_read`'s native frontmatter parsing to eliminate redundant tool schemas.

### `[REQ-TAX-004]`: Agent Forge Studio 3-Tier Grouped Rendering
- **Type**: Ubiquitous
- **Requirement**: The Agent Forge Studio UI SHALL render skill packs categorized into 3 distinct visual sections with section headers, Lucide icons, tool counters, and a visible `"Core AutoReiv Dedicated"` badge on the platform diagnostics pack.

### `[REQ-TAX-005]`: Comprehensive Verification Gate
- **Type**: Ubiquitous
- **Requirement**: All unit tests, API integration tests, and Playwright smoke tests SHALL pass 100% green with zero regressions across tool resolution, agent bootstrapping, and catalog APIs.
