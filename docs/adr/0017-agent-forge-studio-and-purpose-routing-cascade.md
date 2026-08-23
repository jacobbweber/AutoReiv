# ADR-0017: Agent Forge Studio and Dynamic Purpose Routing Cascade

## Status
Accepted

## Date
2026-08-23

## Context
AutoReiv previously supported a static set of 5 built-in agents and a static purpose routing table. Operators need the ability to define, inspect, customize, and delete agents dynamically through a structured "Agent Forge" character sheet UI, with live telemetry, RBAC tool permissions, and dynamic model inheritance through a 3-tier Purpose-to-Model cascade. Furthermore, operators need an in-studio AI Co-Pilot (System Agent) equipped with meta-agent construction tooling to generate, refine, and validate production-ready agent specifications.

## Decision Drivers
- **3-Tier Model Resolution Cascade**: `Agent Model Override -> Purpose Matrix Slot -> Global Default Model`.
- **Full Custom Agent Lifecycle (CRUD)**: Persist custom agents in SQLite alongside built-in baseline profiles with safety protections.
- **Compartmentalized "Character Sheet" UI**: Represent agent components as distinct visual cards: Identity & Avatar, Persona & Tone, Operating Manual (System Prompt), Model & Purpose Binding, Skill Capabilities, and Telemetry Stats.
- **System Agent Co-Pilot Tooling**: Implement `AgentBuilderSkill` empowering `system-agent` to act as an interactive agent architect.

## Decision Outcome
Adopt `AgentForge` architecture with SQLite custom agent storage, dynamic `PurposeRouter`, `AgentBuilderSkill`, and dedicated Agent Studio UI components.

## Consequences
- **Positive**: Complete operator autonomy to create domain-specialized agents without code modifications; clean model inheritance across fleets of agents; safe and structured agent generation.
- **Negative**: Adds database migrations for custom agent profiles and requires RBAC validation on dynamically created agents.
