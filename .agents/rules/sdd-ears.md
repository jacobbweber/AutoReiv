# Rule: Spec-Driven Development & EARS Syntax

## 1. The Specification Requirement
No code shall be written without an approved specification located in `docs/specs/<feature-name>/`.

Every specification must consist of three structured artifacts:
1. `requirements.md`: Business requirements and user stories formulated in **EARS**.
2. `design.md`: Architectural models, C4 diagrams, sequence flows, data contracts.
3. `tasks.md`: Vertical slice checklist decomposing the work into discrete TDD steps.

---

## 2. EARS (Easy Approach to Requirements Syntax)
All functional requirements must be expressed using one of the following 5 EARS patterns:

| Pattern | Template | Example |
| :--- | :--- | :--- |
| **Ubiquitous** | `THE SYSTEM SHALL <action>` | `THE SYSTEM SHALL encrypt all stored passwords using bcrypt with work factor 12.` |
| **Event-Driven** | `WHEN <trigger> THE SYSTEM SHALL <action>` | `WHEN a user submits valid login credentials THE SYSTEM SHALL issue a signed JWT access token.` |
| **State-Driven** | `WHILE <state> THE SYSTEM SHALL <action>` | `WHILE the payment gateway is disconnected THE SYSTEM SHALL queue checkout requests in durable storage.` |
| **Optional Feature**| `WHERE <feature enabled> THE SYSTEM SHALL <action>` | `WHERE multi-factor authentication is enabled THE SYSTEM SHALL prompt for a TOTP code upon login.` |
| **Complex / Unwanted**| `WHILE <state> WHEN <trigger> THE SYSTEM SHALL <action>` | `WHEN an invalid API key is provided THE SYSTEM SHALL respond with HTTP 401 Unauthorized.` |

---

## 3. Requirement Identifier Tokenization
Every requirement in `requirements.md` must have a globally unique identifier tag:
- Format: `[REQ-<DOMAIN>-<NUMBER>]` (e.g. `[REQ-AUTH-001]`, `[REQ-PAY-042]`).
- This token **must be referenced**:
  - In `design.md` corresponding components.
  - In `tasks.md` actionable tasks.
  - In unit and integration test docstrings / comments.
  - In `docs/rtm.json`.
