# Requirements Specification: First-class per-agent memory (agent brain)

> **Spec Status**: Stub (research backlog)
> **Target Release**: undecided (research first)
> **Primary Component**: AutoReiv.Memory / AutoReiv.Agents / AutoReiv.Web (Agent Studio)
> **Card Reference**: [CARD-116](file:///.github/cards/CARD-116-research-first-class-per-agent-memory-agent-brain.md)

---

## 1. Executive Summary & Intent

Research stub only. Jacob (2026-08-30): each agent needs an **independent, first-class brain**. Not one markdown file for every agent. Not Chat session history alone.

Do **not** pick a vendor here. Do **not** implement product code. Study Hermes `MEMORY.md` / `USER.md` as prior art, not a design to copy. Related: CARD-114 findings on memory; alignment talks; CARD-042 episodic facts; session history retention (chat prune is not the brain).

---

## 2. Research constraints (not a chosen design)

### [REQ-BRAIN-001]: Independent brain per agent
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL give each agent its own first-class memory (brain), not a single shared markdown file for all agents.
- **Acceptance Criteria**:
  - [ ] A Coding agent's brain is not the same store as a Sysadmin agent's brain.
  - [ ] Chat session transcripts alone do not satisfy this requirement.

### [REQ-BRAIN-002]: Not session history
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL treat Chat session history (`history_retention_days`, session/message rows) as distinct from the agent brain.
- **Acceptance Criteria**:
  - [ ] Pruning chat sessions does not, by itself, define brain lifetime.
  - [ ] Existing specs `agent-session-history-retention` and `episodic-memory-and-auto-recall` are inputs, not the answer.

### [REQ-BRAIN-003]: Agent Studio levers with hard bounds
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL expose per-agent fine-tune controls in Agent Studio (including how long facts live and other memory levers) AND SHALL enforce hard minimum and maximum values.
- **Acceptance Criteria**:
  - [ ] Controls are per agent, not a single global slider.
  - [ ] Hard min/max exist; the UI cannot save outside those bounds.

### [REQ-BRAIN-004]: Research before vendor
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL NOT treat a vendor, hosted memory product, or a copied Hermes layout as the CARD-116 design.
- **Acceptance Criteria**:
  - [ ] Hermes MEMORY.md/USER.md is cited as prior art to study.
  - [ ] This stub names no vendor as the solution.

---

## 3. Out of Scope (this stub)
- Product Python/JS, schema migrations, or Agent Studio UI work.
- Picking a vendor or copying Hermes blindly.
- Setting the card In Progress.
- Pushing `qa`.
