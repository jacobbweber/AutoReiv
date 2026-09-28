# [CARD-169] Training Factory Architecture Review, Nomenclature Alignment, and Location Field Clarification

> **Status**: Done
> **Created**: 2026-09-05
> **Closed**: 2026-09-07
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:docs`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Architecture`

---

## 1. Why / Intent

Across CARD-159, CARD-164, CARD-165, and CARD-166, AutoReiv developed an end-to-end capability creation system. Because it grew quickly across multiple sessions, we need to:
1. Establish clean, unified **feature nomenclature** so operators and developers use the exact same words across UI screens, code, and documentation.
2. Formally clarify what the **"Target Location" / "Project Path"** field does across the training handshake and Agent Studio, resolving operator ambiguity.

---

## 2. Feature Nomenclature Review & Alignment (Locked)

The system name is officially locked to **Agent Training Factory (ATF)**.

| Operational Facet | Technical Component | Locked Standard Name | Where Operator Sees It |
| :--- | :--- | :--- | :--- |
| **The Entire System** | `FactoryOrchestrator` & Pipeline | **Agent Training Factory** | Global feature concept across AutoReiv |
| **The Visual Drawer** | `#labMonitorDrawer` | **Lab Monitor** | Slide-out drawer in Agent Studio (`#forgeLabMonitorBtn`) |
| **The Background Engine** | `FactoryOrchestrator` | **Factory Background Worker** | Background tick worker (`orchestrator.py`) |
| **In-Flight Turn Repair** | `JitToolSynthesizer` / `CapabilityDetector` | **In-Flight Autonomous Training** | Chat Studio live progress pills & auto-resumption |
| **Queued Deficiencies** | `CapabilityGapRepository` | **Needs Training Backlog** | Card 1 in Agent Studio (`#agentTrainingBacklogCard`) |
| **Verification Gate** | `VerificationBatteryService` | **Verification Battery** | Syntax, imports, behavior, and scenario tests |

---

## 3. Understanding the "Location" Field Semantics (Locked)

### What It Is
In both the **Train Agent** modal and Agent Studio:
- **Role**: Strictly a **read-only reference pointer** for the discovery phase (`ground.py`). The factory inspects code, dependencies, and file structures using read directory tools.
- **Invariant**: The factory **never** writes files or packs into the reference location. Generated agent packs are always strictly isolated under `$DATA_DIR/packs/<agent_id>/`.
- **Optional for System/Host Agents**: For sysadmin, cloud, or system-level agents (like Hyper-V or Docker), there is no project directory. The field is left blank, and the factory grounds itself using host cmdlets and Wiki knowledge.
- **UI Label**: **"Source Code Directory (Optional)"** with helper text: *"Specify a path if you want the factory to inspect an existing codebase. Leave blank for system or host agents."*

---

## 4. Acceptance Criteria (Definition of Done)

- [x] [REQ-FACT-034] System name officially locked to **Agent Training Factory** (ATF) across all cards, UI, and documentation.
- [x] [REQ-FACT-035] Clarified location field semantics: strictly read-only reference directory, optional, never writes generated packs to source path.
- [x] [REQ-FACT-036] UI label defined as "Source Code Directory (Optional)" with helper text for system/host agents.
- [x] [REQ-FACT-037] Aligned with CARD-171, CARD-172, and CARD-175.

---

## 5. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Preserve backward compatibility with existing stored agent profile paths.
- Local commit on `qa`.
