---
trigger: glob
globs: 'docs/specs/**,docs/cards/**,.agents/skills/sdd-workflow/**'
description: Spec-Driven Development (Cards vs Specs) and EARS requirement syntax.
---

# Rule: Spec-Driven Development & EARS Syntax

## 1. Two-Tier Specification Hierarchy

To prevent speculative documentation bloat on minor fixes while maintaining rigorous architectural contracts on large systems, AutoReiv enforces a two-tier specification model:

### Tier 1: Card-First (Standard for Bugs, UI Tweaks, & Tactical Chores)

- Every product code change begins with an active work card: `docs/cards/CARD-xxx.md`.
- For bug fixes, UI improvements, and single-module refactors, the Card is the **canonical specification**.
- Required sections in the Card:
  1. **Why / Intent**: User problem or root cause.
  2. **What to Build**: Technical files touched and modifications made.
  3. **Acceptance Criteria (DoD)**: Verifiable checklist of outcomes.
- **No Spec Duplication**: Do NOT generate 3-file specs in `docs/specs/` for simple bug fixes or localized card changes.

### Tier 2: Spec-First (Major Epics, Subsystems, & Architectural Overhauls)

- When introducing a new subsystem, new studio, external integration, or cross-cutting architecture, author a complete specification under `docs/specs/<feature-name>/`:
  1. `requirements.md`: Business requirements and user stories formulated in **EARS**.
  2. `design.md`: Component topology, C4 diagrams, sequence flows, data contracts.
  3. `tasks.md`: Vertical slice checklist decomposing implementation into verifiable steps.

---

## 2. EARS (Easy Approach to Requirements Syntax)

When authoring functional requirements in `requirements.md` or formal card acceptance criteria, express statements using the 5 EARS patterns:

| Pattern                | Template                                                 | Example                                                                                            |
| :--------------------- | :------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **Ubiquitous**         | `THE SYSTEM SHALL <action>`                              | `THE SYSTEM SHALL encrypt all stored passwords using bcrypt with work factor 12.`                  |
| **Event-Driven**       | `WHEN <trigger> THE SYSTEM SHALL <action>`               | `WHEN a user submits valid login credentials THE SYSTEM SHALL issue a signed JWT access token.`    |
| **State-Driven**       | `WHILE <state> THE SYSTEM SHALL <action>`                | `WHILE an assistant response is streaming THE SYSTEM SHALL keep the stream bubble mounted in DOM.` |
| **Optional Feature**   | `WHERE <feature enabled> THE SYSTEM SHALL <action>`      | `WHERE multi-factor authentication is enabled THE SYSTEM SHALL prompt for a TOTP code upon login.` |
| **Complex / Unwanted** | `WHILE <state> WHEN <trigger> THE SYSTEM SHALL <action>` | `WHEN an invalid API key is provided THE SYSTEM SHALL respond with HTTP 401 Unauthorized.`         |

---

## 3. Requirement Tokenization

For major feature specs, assign unique identifier tokens:

- Format: `[REQ-<DOMAIN>-<NUMBER>]` (e.g. `[REQ-CHAT-017]`, `[REQ-GATEWAY-004]`).
- Reference these tokens in `design.md`, `tasks.md`, and test docstrings/comments.
