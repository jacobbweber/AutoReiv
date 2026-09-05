# [CARD-169] Training Factory Architecture Review, Nomenclature Alignment, and Location Field Clarification

> **Status**: Ready
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:docs`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Architecture`

---

## 1. Why / Intent

Across CARD-159, CARD-164, CARD-165, and CARD-166, AutoReiv developed an end-to-end capability creation system. Because it grew quickly across multiple sessions, we need to:
1. Establish clean, unified **feature nomenclature** so operators and developers use the exact same words across UI screens, code, and documentation.
2. Formally clarify what the **"Target Location" / "Project Path"** field does across the training handshake and Agent Studio, resolving operator ambiguity.

---

## 2. Feature Nomenclature Review & Alignment

The system encompasses four distinct operational facets. We propose standardizing on the following terminology:

| Operational Facet | Technical Component | Proposed Standard UI Name | Where Operator Sees It |
| :--- | :--- | :--- | :--- |
| **The Entire System** | `AgentPackFactory` & Graph Orchestrator | **The Training Lab** (or **Agent Factory**) | Global feature concept across AutoReiv |
| **The Visual Drawer** | `#labMonitorDrawer` | **Lab Monitor** | Slide-out drawer in Agent Studio (`#forgeLabMonitorBtn`) |
| **The Background Engine** | `FactoryRunner` | **Autonomous Factory Runner** | Server background worker (`factory_runner.py`) |
| **In-Flight Turn Repair** | `JitToolSynthesizer` / `CapabilityDetector` | **In-Flight Autonomous Training** | Chat Studio live progress pills & auto-resumption |
| **Queued Deficiencies** | `CapabilityGapRepository` | **Needs Training Backlog** | Card 1 in Agent Studio (`#agentTrainingBacklogCard`) |
| **Verification Gate** | `VerificationBattery` | **4-Stage Sandbox Battery** | 4-step quality gate (Syntax, Safety, Behavior, SRE) |

---

## 3. Understanding the "Location" Field Semantics

### What It Is
In both the **Train Agent** modal (`#trainLocationInput`) and Agent Studio (`#forgeAgentPath`):
- **Name**: "Target Location" or "Project Path"
- **Internal Role**: The reference path passed into the discovery phase (`_step_discovery_probe`).

### Why It Was Confusing
- If an operator creates a coding agent (e.g. for a Python repo), the location is a real folder like `D:\Projects\Active\AutoReiv`. The agent inspects `git log`, dependencies, and tests.
- But if an operator creates a sysadmin or virtualization agent (e.g. `Hyper-V` or `Docker`), there is **no project folder**. The agent operates directly against host cmdlets and OS services.
- Furthermore, newly trained agent artifacts are **never** stored in the user's project location. Generated agent packs, skills, and tools are always strictly isolated under `$DATA_DIR/packs/<agent_id>/`.

### Unified Clarification & UI Polish
1. **Mark as Explicitly Optional**: Clarify that leaving the location blank instructs the Lab to ground the agent in host-level execution and pure intent.
2. **Rename Label in UI**:
   - Change label from ambiguous "Target Location" &rarr; **"Target Codebase / Directory (Optional)"**.
   - Helper text: *"Leave blank for host sysadmin, cloud, or system-level agents. Specify a path only if the agent is dedicated to a specific software project directory."*
3. **Validation Invariant**: Ensure factory runners never fail or stall if location is empty; fallback seamlessly to host-environment probing (CARD-166).

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-FACT-034] Update UI text in `index.html` and `handshake.js` to label the location input as "Target Codebase / Directory (Optional)" with contextual helper text.
- [ ] [REQ-FACT-035] Synchronize product documentation and architecture overviews in `docs/` with the unified nomenclature table (Training Lab, Lab Monitor, Factory Runner, In-Flight Training, Needs Training Backlog).
- [ ] Automated frontend smoke tests verify modal input labels and placeholders.
- [ ] Zero lint errors via `ruff check .` and `npm run test:unit:frontend`.

---

## 5. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Preserve backward compatibility with existing stored agent profile paths.

