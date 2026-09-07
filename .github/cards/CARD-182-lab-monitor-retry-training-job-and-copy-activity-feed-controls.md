# [CARD-182] Lab Monitor Retry Training Job and Copy Activity Feed Controls

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Frontend`

---

## 1. Why / Intent

During capability training in the Agent Training Factory (such as testing Hyper-V or specialized skills), operators actively monitor progress in the **Lab Training Monitor** drawer. Two key usability gaps exist:
1. **Iterative Retries**: When a training attempt completes or fails (e.g. hitting a syntax nuance or environmental requirement), the operator must close the monitor, click Train again, and re-type the agent name, goal prompt, deliverable architecture, constraints, prerequisites, and reference docs from scratch. Having a **Retry** button preserves all inputs and allows launching another attempt with zero friction.
2. **Copying Activity Feed**: When reviewing execution steps or reporting an error, the operator manually highlights lines from the terminal box. A dedicated **Copy** button copies the clean, formatted execution trace (timestamps, phases, and messages) to clipboard in one click.

---

## 2. What to Build

### A. Frontend Controls in Lab Monitor (`src/web/templates/index.html`)
1. **Copy Feed Button (`#labCopyFeedBtn`)**:
   - Placed in the "Live Activity Feed" section header next to `#labPacketsCount`.
   - Small, clean action button: `<i data-lucide="copy"></i> <span>Copy</span>`.
   - Copies all formatted packet lines to clipboard and displays temporary `Copied!` feedback for 2 seconds.
2. **Retry Run Button (`#labRetryJobBtn`)**:
   - Placed in the Lab Monitor run selector row next to `#labJobStatusPill`.
   - Button: `<i data-lucide="rotate-ccw"></i> <span>Retry</span>`.
   - Visible for any selected run. When clicked, it extracts the run's original inputs and opens the **Train Agent Handshake Modal** pre-populated with:
     - Target Agent Slug (`#trainAgentNameInput`)
     - Goal / Seed Intent (`#trainAgentGoalInput`)
     - Deliverable Architecture (`#trainDeliverableType`: Auto, MCP, Native, or Skill)
     - Operational Constraints (`#trainConstraintsInput`)
     - Host Prerequisites (`#trainPrerequisitesInput`)
     - Reference Documentation (`#trainReferenceDocsInput`)
   - The operator can instantly review, tweak anything if desired, and click **Confirm & Start Training**.

### B. Frontend Logic (`src/web/static/modules/studios/forge.js` & `chat.js`)
- Wire `#labCopyFeedBtn` click event to extract all lines from `#labPacketsFeed` and copy to clipboard using `navigator.clipboard.writeText`.
- Wire `#labRetryJobBtn` click event to extract the selected job's inputs from `job.inputs` or initial `WorkPacket` payload, populate the handshake modal, expand `#trainAdvancedReqsAccordion` if any advanced fields exist, and display `#trainAgentHandshakeModal`.

### C. Backend API Endpoint (`src/web/routers/agent_training_factory.py`)
- In `GET /api/agent_training_factory/jobs/{id}`, include an `inputs` dictionary in the returned JSON response extracting:
  - `seed_intent`: original goal
  - `target_agent_id`: agent slug
  - `deliverable_type`: extracted from initial packet constraints
  - `constraints`: extracted from initial packet constraints
  - `prerequisites`: extracted from initial packet constraints
  - `reference_docs`: extracted from initial packet constraints

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-LAB-001]**: `#labCopyFeedBtn` in Lab Monitor copies clean formatted activity logs (timestamp, role, and message) to clipboard with visual feedback ("Copied!").
- [x] **[REQ-LAB-002]**: `#labRetryJobBtn` in Lab Monitor loads the selected run's inputs (target agent, seed intent, deliverable type, constraints, prerequisites, reference docs) and pre-fills the Train Agent Handshake Modal.
- [x] **[REQ-LAB-003]**: `GET /api/agent_training_factory/jobs/{job_id}` exposes structured `inputs` in the response payload.
- [x] **[REQ-LAB-004]**: Automated tests pass: Vitest for UI copy and retry button interactions, Pytest for backend job inputs extraction.

---

## 4. UI Wireframe

```text
+--------------------------------------------------------------------------+
| 🧪 Lab Training Monitor               hyperv (fjob_50ca7432c0f7)  [🔄] [✖] |
+--------------------------------------------------------------------------+
| Select Run: [ [FAILED] hyperv (fjob_50ca7432c0) v ]  [🔄 Retry] [FAILED] |
+--------------------------------------------------------------------------+
| Training Stages:                                                         |
| [1 Intent] [2 Ground] [3 Blueprint] [4 Author] [5 Scenario] [6 Code] ... |
+--------------------------------------------------------------------------+
| Live Activity Feed                                  [📋 Copy]  11 packets|
| +----------------------------------------------------------------------+ |
| | [10:11:02 AM] [ORCHESTRATOR] Train capabilities for hyperv           | |
| | [10:11:26 AM] [INTENT_DISTILL] Intent Distill completed for hyperv   | |
| | [10:12:35 AM] [BLUEPRINT] Blueprint formulated: 4 skills, 4 tools... | |
| | [10:12:41 AM] [VERIFY] Verify battery FAILED - inner rinse (1/3)...  | |
| +----------------------------------------------------------------------+ |
+--------------------------------------------------------------------------+
```

