# Requirements Specification: [Feature Name]

> **Spec Status**: Draft / In Review / Approved  
> **Target Release**: [Milestone / Sprint]  
> **Primary Component**: [C4 Component Name]

---

## 1. Executive Summary & Intent
<!-- Brief explanation of why this feature is being built and what value it creates -->

---

## 2. User Stories & EARS Functional Requirements

Every requirement must use EARS syntax and carry a unique identifier.

### [REQ-DOMAIN-001]: [Requirement Title]
- **Type**: Ubiquitous / Event-Driven / State-Driven / Optional / Complex
- **EARS Statement**: `WHEN <trigger> THE SYSTEM SHALL <action>`
- **Acceptance Criteria**:
  - [ ] Given [precondition], when [action], then [expected outcome].
  - [ ] Given [invalid state], when [action], then [expected error].

### [REQ-DOMAIN-002]: [Requirement Title]
- **Type**: Ubiquitous / Event-Driven / State-Driven / Optional / Complex
- **EARS Statement**: `THE SYSTEM SHALL <action>`
- **Acceptance Criteria**:
  - [ ] Criterion 1
  - [ ] Criterion 2

---

## 3. Non-Functional & Boundary Constraints
- **Performance**: Response time < 200ms at p95.
- **Security**: Zero cleartext sensitive data in logs.
- **Reliability**: Graceful fallback if external dependency is unavailable.

---

## 4. Out of Scope
<!-- Explicit boundaries to prevent scope creep -->
- Explicit exclusion 1
- Explicit exclusion 2
