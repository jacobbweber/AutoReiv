# Requirements Specification: In-Situ Skill Distillation

> **Spec Status**: Approved  
> **Target Release**: v0.34.0  
> **Primary Component**: AutoReiv.Chat / AutoReiv.Skills  
> **Card Reference**: CARD-352  

---

## 1. Executive Summary & Intent

Most day-to-day agent capability gaps do not require compiling new Python tools in an 8-phase code factory. When an agent makes a procedural mistake during a chat (such as saving a file to the wrong path, misformatting a tool input, or forgetting a mandatory verification step), the operator must be able to correct and teach the agent in-situ. AutoReiv provides a fast, one-click learning loop that analyzes the conversation turn, distills the transcript and correction into a standardized `SKILL.md` runbook in seconds, presents a plain-language proposal card directly in the chat stream, and immediately mounts the adopted skill to the target agent for the very next turn. If the distillation detects that the capability requires a new native Python tool rather than procedural guidance, it seamlessly escalates to Factory Studio with pre-filled inputs.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-SKIL-010]: In-Situ Turn Distillation & Capability Analysis API
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a client submits POST /api/skills/distill with session_id, message_id, and optional guidance, THE SYSTEM SHALL extract the turn trajectory, diagnose procedural friction, and return a structured skill proposal.`
- **Acceptance Criteria**:
  - [ ] Given a valid `session_id` and `message_id`, the system extracts the target agent, previous user prompt, assistant response, tool calls, and tool results.
  - [ ] The system evaluates whether existing tools can satisfy the requirement or if a new native code tool is needed (`needs_tool: bool`).
  - [ ] When `needs_tool` is false, the system synthesizes a standardized `SKILL.md` runbook featuring YAML frontmatter (`name`, `description` < 60 chars), `## When to Use`, `## Procedure`, `## Common Pitfalls & Forbidden Paths`, and `## Verification`.
  - [ ] The response payload returns `{ "status": "ok", "skill_id": str, "name": str, "description": str, "runbook_markdown": str, "plain_summary": { "observed_slip": str, "remedy": str }, "needs_tool": bool, "target_agent_id": str, "factory_escalation": Optional[dict] }`.
  - [ ] Given an invalid or missing `session_id`, the endpoint returns HTTP 404 or 422 with a structured error message.

### [REQ-SKIL-011]: Chat Assistant Turn `[ 💡 Teach Agent ]` Trigger & Guidance Modal
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator views an assistant message in Chat Studio, THE SYSTEM SHALL render a [ 💡 Teach Agent ] action button on the message header.`
- **Acceptance Criteria**:
  - [ ] Clicking `[ 💡 Teach Agent ]` on an assistant turn opens a lightweight teaching modal displaying the target agent's identity.
  - [ ] The modal presents an optional input: *"What should the agent have done differently? (Optional: leave blank to auto-diagnose from turn context)"*.
  - [ ] Submitting the modal dispatches `POST /api/skills/distill` while disabling the submit button and displaying a loading spinner.
  - [ ] Entering `/learn <guidance>` in the chat composer also triggers the distillation flow for the latest turn.

### [REQ-SKIL-012]: Inline Chat Skill Proposal Card with Plain-Language Summary
- **Type**: Event-Driven
- **EARS Statement**: `WHEN POST /api/skills/distill completes successfully, THE SYSTEM SHALL render an interactive Skill Proposal Card directly in the active chat stream.`
- **Acceptance Criteria**:
  - [ ] The card displays a plain-language summary header: *"Observed Slip"* and *"What this teaches"*, avoiding dense code clutter up front.
  - [ ] The card provides a collapsible accordion: *"View Raw Runbook (SKILL.md)"* rendering the full synthesized Markdown with YAML frontmatter.
  - [ ] The card includes three primary actions: `[ ✅ Adopt Skill to <Agent> ]`, `[ ✏️ Quick Tweak ]`, and `[ ✕ Dismiss ]`.
  - [ ] The card reflects state transitions (e.g. "Adopting...", "Adopted ✓", "Dismissed").

### [REQ-SKIL-013]: One-Click Skill Adoption & Immediate Runtime Mounting
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator clicks [ ✅ Adopt Skill ], THE SYSTEM SHALL write the runbook to the target agent's user-data pack and mount it for subsequent chat turns.`
- **Acceptance Criteria**:
  - [ ] `POST /api/skills/adopt` writes `SKILL.md` to `$DATA_DIR/packs/<target_agent_id>/skills/<skill_slug>/SKILL.md`.
  - [ ] The skill is registered in the target agent's pack manifest (`pack.json`) and added to `allowed_skill`.
  - [ ] The runtime agent registry synchronizes the agent profile immediately without requiring a server reboot.
  - [ ] The card transitions to a success state displaying: *"Skill mounted to <Agent>. Active for your next message."*

### [REQ-SKIL-014]: Factory Studio Escalation Bridge for Missing Native Tools
- **Type**: Event-Driven
- **EARS Statement**: `WHEN distillation indicates needs_tool is true OR the operator chooses to escalate, THE SYSTEM SHALL provide a one-click bridge to Factory Studio.`
- **Acceptance Criteria**:
  - [ ] When `needs_tool` is true, the card displays: *"This capability requires writing new host code or an API tool, which needs sandbox verification in Factory Studio."*
  - [ ] The card renders a prominent button: `[ 🚀 Send to Factory Studio ]`.
  - [ ] Clicking the button navigates to Factory Studio (`#view-factory`), switches to the Intake sub-view, selects the target agent, and populates the Training Goal and Starter Objectives from the distillation analysis.

---

## 3. Non-Functional & Boundary Constraints
- **Response Latency**: Distillation pass completes within 5 seconds on local/cloud models.
- **Hygiene**: Runbooks are saved strictly under `$DATA_DIR/packs/<agent_id>/skills/`, never under the git checkout.
- **Fail-Safe**: If distillation LLM is unavailable or times out, the user receives a helpful toast and the conversation stream remains undisturbed.

---

## 4. Out of Scope
- Direct AST generation of arbitrary `.py` files inside Chat Studio (owned exclusively by Factory Studio).
- Modifying hardcoded platform seed files under `platform-packs/` directly from Chat.

