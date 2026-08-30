# Requirements Specification: First-class per-agent memory (agent brain)

> **Spec Status**: Stub (research backlog)
> **Target Release**: undecided (research first)
> **Primary Component**: AutoReiv.Memory / AutoReiv.Agents / AutoReiv.Web (Agent Studio)
> **Card Reference**: [CARD-116](file:///.github/cards/CARD-116-research-first-class-per-agent-memory-agent-brain.md)

---

## 1. Executive Summary & Intent

Research stub only. Jacob (2026-08-30): each agent needs an **independent, first-class brain**. Not one markdown file for every agent. Not Chat session history alone.

Later talk (2026-08-30 t132u): shy away from LLM-Wiki (maintenance). Compare mem0 / Letta / Zep only as research. Coding's leaning is the three-shelf per-agent brain beside the existing ReAct kernel. A vendor is **not** the system. Mem0 may be named as the archive engine **to evaluate**; that is not a purchase.

Do **not** pick a vendor here as the design. Do **not** implement product code. Study Hermes `MEMORY.md` / `USER.md` as prior art, not a design to copy. Related: CARD-114 findings on memory; alignment talks; CARD-042 episodic facts; session history retention (chat prune is not the brain).

---

## 2. Research constraints (not a chosen design)

### [REQ-BRAIN-001]: Independent brain per agent
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL give each agent its own first-class memory (brain), not a single shared markdown file for all agents.
- **Acceptance Criteria**:
  - [ ] A Coding agent's brain is not the same store as a Sysadmin agent's brain.
  - [ ] Chat session transcripts alone do not satisfy this requirement.
  - [ ] One store per agent id (Coding brain != Okta Admin brain != Sysadmin brain).

### [REQ-BRAIN-002]: Not session history
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL treat Chat session history (`history_retention_days`, session/message rows) as distinct from the agent brain.
- **Acceptance Criteria**:
  - [ ] Pruning chat sessions does not, by itself, define brain lifetime.
  - [ ] Existing specs `agent-session-history-retention` and `episodic-memory-and-auto-recall` are inputs, not the answer.
  - [ ] `src/infrastructure/memory` SQLite (sessions/jobs filing cabinet) is not the brain.

### [REQ-BRAIN-003]: Agent Studio levers with hard bounds
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL expose per-agent fine-tune controls in Agent Studio (including how long facts live and other memory levers) AND SHALL enforce hard minimum and maximum values.
- **Acceptance Criteria**:
  - [ ] Controls are per agent, not a single global slider.
  - [ ] Hard min/max exist; the UI cannot save outside those bounds.
  - [ ] Brain data lives in the data dir, not git.

### [REQ-BRAIN-004]: Research before vendor
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL NOT treat a vendor, hosted memory product, or a copied Hermes layout as the CARD-116 design.
- **Acceptance Criteria**:
  - [ ] Hermes MEMORY.md/USER.md is cited as prior art to study.
  - [ ] This stub names no vendor as the locked solution / the system.
  - [ ] Research leaning may name Mem0 as the archive engine **to evaluate**; that is not a purchase and AutoReiv still owns namespace, Ollama extraction, Studio knobs, and prompt assembly.

### [REQ-BRAIN-005]: Three shelves AutoReiv owns
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL own three per-agent memory shelves: a pinned short block always in the prompt, recent work summaries for that agent, and an archive of searchable facts retrieved when relevant.
- **Acceptance Criteria**:
  - [ ] Pinned block is visible/editable in Agent Studio.
  - [ ] Recent work summaries are per agent, not a shared log.
  - [ ] Archive facts are retrieved when relevant; they are not dumped wholesale into every prompt.
- **Notes**: Memory is a subsystem beside the existing ReAct kernel. Vendor (if any) is an engine for a shelf, not the product.

### [REQ-BRAIN-006]: Not wiki, not Letta OS
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL NOT implement the agent brain as a compiled document wiki AND SHALL NOT replace the AutoReiv ReAct/Job/HITL/Ollama kernel with a second agent OS.
- **Acceptance Criteria**:
  - [ ] LLM-Wiki / WikiStore is user knowledge (Jacob's notes), not the agent brain. Maintenance is the known wiki failure mode.
  - [ ] Letta (ex-MemGPT) is not adopted as product; pin-vs-archive may be stolen as an idea only.
  - [ ] CARD-042 shared episodic facts and ACE notes remain distinct from the per-agent brain.

---

## 3. Out of Scope (this stub)
- Product Python/JS, schema migrations, or Agent Studio UI work.
- Treating a vendor as the design. Mem0 may be named as the archive engine to evaluate; that does not lock a purchase.
- Adopting LLM-Wiki as the brain, Letta as the agent runtime, or Zep hosted product (local-first; Community Edition deprecated Aug 2026).
- Copying Hermes blindly.
- Setting the card In Progress.
- Mixing this work into CARD-117 / CARD-121 PRs (memory is after skills + tools primitives).
- Pushing `qa`.
