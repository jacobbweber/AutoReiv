---
trigger: glob
globs: 'docs/cards/**,.agents/skills/sdd-workflow/**'
description: Card-Driven Development (Cards as canonical contracts) and EARS requirement syntax.
---

# Rule: Card-Driven Development & EARS Syntax

## 1. Single Canonical Contract (The Card)

AutoReiv enforces a lean, single-contract specification model:

- Every product code change begins with an active work card: `docs/cards/CARD-xxx.md`.
- The Card is the **canonical specification** for bugs, features, and refactors alike.
- Separate 3-file specifications (`docs/specs/`) and the RTM matrix are **retired and archived** under `docs/archive_artifacts/`.
- Major architectural decisions belong in `docs/adr/` (Architecture Decision Records).
- System-level container and component topology belongs in `steering/structure.md`.

### Required Sections in the Card

1. **Why / Intent**: User motivation and business value (the Four Beats: Beat 1).
2. **What AutoReiv Does Now**: Current code path, DOM structure, and behavior (Beat 2).
3. **What Will Change**: Concrete files, endpoints, and UI elements touched (Beat 3).
4. **What Dies Today (The Prune List)**: Non-empty list of retired functions, variables, CSS rules, routes, or DOM elements (Beat 4).
5. **Acceptance Criteria (DoD)**: Verifiable checklist of functional and negative outcomes.
6. **Human Verification Runbook**: Step-by-step instructions to verify the change in under 2 minutes.

---

## 2. EARS (Easy Approach to Requirements Syntax)

When authoring functional acceptance criteria in the Card, express statements using the 5 EARS patterns to eliminate ambiguity:

| Pattern                | Template                                                 | Example                                                                                            |
| :--------------------- | :------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **Ubiquitous**         | `THE SYSTEM SHALL <action>`                              | `THE SYSTEM SHALL encrypt all stored passwords using bcrypt with work factor 12.`                  |
| **Event-Driven**       | `WHEN <trigger> THE SYSTEM SHALL <action>`               | `WHEN a user submits valid login credentials THE SYSTEM SHALL issue a signed JWT access token.`    |
| **State-Driven**       | `WHILE <state> THE SYSTEM SHALL <action>`                | `WHILE an assistant response is streaming THE SYSTEM SHALL keep the stream bubble mounted in DOM.` |
| **Optional Feature**   | `WHERE <feature enabled> THE SYSTEM SHALL <action>`      | `WHERE multi-factor authentication is enabled THE SYSTEM SHALL prompt for a TOTP code upon login.` |
| **Complex / Unwanted** | `WHILE <state> WHEN <trigger> THE SYSTEM SHALL <action>` | `WHEN an invalid API key is provided THE SYSTEM SHALL respond with HTTP 401 Unauthorized.`         |
