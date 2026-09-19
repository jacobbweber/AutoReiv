# Requirements Specification: User Intent Review and Product Alignment

> **Spec Status**: Approved (review artifact)
> **Target Release**: Alignment dialogue (no code milestone)
> **Primary Component**: PRODUCT / KERNEL / ORCHESTRATION / SKILLS / WEB
> **Hardware**: Local Ollama on Nimo. This spec does not add load.

---

## 1. Executive Summary & Intent

This spec is **not a feature**. It is a user-intent review. Jacob is new to software. AutoReiv currently mixes live behavior, leftover APIs, brochure packs, and overlapping names. The source of truth is indings.md in this folder.

Grok compared the current qa code to the product story (homelab Okta, self-improve, Goal/Verify, HITL, SDLC cards, data dir). Jacob will next speak in plain language, then walk features one by one. Grok will compare his intent to these findings and the live code. No implementation order is mandated here.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-INTENT-001]: Findings are the SSOT
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL treat docs/specs/user-intent-review/findings.md as the source of truth for "what we meant vs what it does today" until Jacob closes or revises a finding in dialogue.
- **Acceptance Criteria**:
  - [x] findings.md lists numbered findings with the six required bullets.
  - [x] Findings were verified against current qa code, not only chat recap.

### [REQ-INTENT-002]: Review artifact, not a coding card
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL record CARD-114 as Ready review-only work and SHALL NOT treat this spec as permission to change product code.
- **Acceptance Criteria**:
  - [x] CARD-114 status is Ready.
  - [x] No product fix ships on this card.

### [REQ-INTENT-003]: Dialogue before rebuild
- **Type**: Event-Driven
- **EARS Statement**: WHEN Jacob walks a feature in plain language THE SYSTEM SHALL compare his stated intent to the matching finding and the current code before proposing a card.
- **Acceptance Criteria**:
  - [ ] Given a finding Jacob disagrees with, when he names his intent, then Grok updates the finding rather than coding first.
  - [ ] Given a leftover path (theatre / dead engine), when Jacob says ignore it, then it stays listed as debt until a later card.

### [REQ-INTENT-004]: Vocabulary collision is in scope
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL document overlapping product words (skill, tool, workflow, job, card, routine, agent, phase, pack) as findings so Jacob can pick the words he wants.
- **Acceptance Criteria**:
  - [x] Overlapping names appear as a finding, not a glossary lecture.

---

## 3. Non-Functional & Boundary Constraints
- **Audience**: Plain language. Jacob is new to software.
- **Honesty**: Incomplete, conflict, overlap, theatre, and poor design must be named.
- **No mandate**: A suggested discussion order is allowed. An implementation order is not.

---

## 4. Out of Scope
- Product code changes, refactors, or closing other cards.
- Pushing qa.
- LangGraph / vendor ACE lectures.
- Mandating which finding to fix first.
