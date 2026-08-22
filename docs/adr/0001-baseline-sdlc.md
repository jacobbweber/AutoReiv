# ADR-0001: Adoption of AWS Kiro-Style SDD, TDD, and Machine-Readable RTM

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)

---

## 1. Context & Problem Statement
AI coding agents are susceptible to hallucinated requirements, ungrounded code generation ("vibe coding"), silent regressions, and cross-session architectural drift. We need a repeatable, deterministic SDLC framework that minimizes cognitive friction for the Human Visionary and QA Tester while enforcing rigorous engineering standards.

---

## 2. Decision Drivers
- **Low Cognitive Load**: The human focuses on product vision and QA validation without getting bogged down in low-level syntax.
- **Traceability**: Complete mapping from business requirement tokens `[REQ-xxx]` to code and test suites.
- **Deterministic Verification**: Mandatory TDD (Red-Green-Refactor) and automated verification before completion.
- **Maintainability**: Strategic SOLID boundaries at the edges, tactical KISS/YAGNI in implementations.

---

## 3. Considered Options
1. **Unstructured Prompting ("Vibe Coding")**: Fast initial output, but catastrophic drift, high regression rate, and impossible to maintain.
2. **Heavyweight Enterprise Tooling (Jira/Confluence integrations)**: High operational friction and slow agent iteration.
3. **AWS Kiro 3-File SDD + Antigravity Progressive Disclosure + JSON RTM (Selected)**: File-based specifications (`requirements.md` in EARS, `design.md`, `tasks.md`), persistent steering (`product.md`, `tech.md`, `structure.md`), and lightweight automated RTM validation.

---

## 4. Decision Outcome
Chosen option: **Option 3**, because it strikes the optimal balance between machine-executable rigor and human readability.

### Consequences
- **Positive**:
  - Deterministic requirement tracking via `[REQ-xxx]` tags.
  - Automated blast-radius calculation via `scripts/verify_rtm.py`.
  - Seamless collaboration between Human Visionary and AI Engineer.
- **Negative / Mitigations**:
  - Requires maintaining `docs/rtm.json` and spec files; mitigated by automated CLI verification scripts.
