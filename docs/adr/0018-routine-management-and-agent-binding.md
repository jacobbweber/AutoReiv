# ADR-0018: Routine Management, Dual Cron Humanization, and Agent Forge Binding

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Decision Makers**: Jacob Weber, Principal Agent Engineer  
> **Linked Issue / Card**: CARD-017

---

## 1. Context and Problem Statement

AutoReiv supports background autonomous routines, but operators needed full CRUD and lifecycle management from the Control Plane SPA, including:
1. Bidirectional human-readable translations for cron schedules and precise next execution ETA countdowns.
2. Direct REST endpoints to create, edit, pause/resume, delete custom routines, and run out-of-band executions while protecting baseline system routines.
3. At-a-glance visibility into which standing routines are tethered to each agent directly within their Agent Forge character sheet.

---

## 2. Considered Options

- **Option A: Declarative Lead-Agent Routines with Autonomous Delegation (Chosen)**:
  Each routine assigns a single Lead Agent and a mission directive. If the mission requires multi-agent interaction, the lead agent uses its existing `delegate_task` or verification capabilities at runtime. Dual cron translation is performed cleanly with lightweight parsing.
- **Option B: Heavy Drag-and-Drop Canvas Graph (LangGraph/Dify UI)**:
  Connecting visual nodes for routines. Rejected due to extreme cognitive friction, brittle visual state, and loss of agent autonomy.

---

## 3. Decision Outcome

**Chosen Option**: **Option A**.

### Positive Consequences
- **Zero Heavy Dependencies**: Lightweight Python and JS regex humanizer converts standard 5-part cron syntax to clean English.
- **Full Control Plane CRUD**: Operators can create, edit, pause, and delete routines effortlessly.
- **Unified Agent Sheet**: Operators see all standing background duties directly on the agent's character sheet.
- **DoD Compliance**: Verified by automated unit and integration tests.
