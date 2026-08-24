# Requirements Specification: Steering & Product Documentation Truth Sync

> **Spec Status**: Approved  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-037](file:///.github/cards/CARD-037-steering-and-product-documentation-truth-sync.md)  

> **Primary Component**: AutoReiv Steering & Architecture Documentation (`steering/`, `docs/`, `README.md`)

---

## 1. Executive Summary & Intent

As the concluding card of Milestone 10 (P1 Quality & Testability), **CARD-037** synchronizes and hardens the top-level repository steering, product definitions, and architectural documentation (`steering/product.md`, `steering/tech.md`, `steering/structure.md`, `steering/roadmap.md`, `README.md`). It ensures documentation accurately reflects the full 7-studio modular architecture, pure physics and reactive store utilities, 6-stage pre-flight quality pipeline, and concludes Milestone 10.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-DOCS-005] Product Steering & 7-Studio Architecture Specification
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** update `steering/product.md` to comprehensively document the 7 operational studios (Chat, Routines, Observability, Agent Forge, Settings, Docs, Wiki & Mind Map), core domain capabilities, and local-first architectural boundaries.

### [REQ-DOCS-006] Technical Stack & Dual-Runtime Environment Steering
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** update `steering/tech.md` and `steering/structure.md` to document the dual-runtime architecture (FastAPI + UV backend and Native ES Modules + Vitest + ESLint + Playwright frontend) and standardized CLI commands.

### [REQ-DOCS-007] Milestone 10 Closure & Roadmap Synchronization
- **EARS Pattern**: State-Driven
- **Requirement**: When CARD-037 verification passes, the system **shall** mark Milestone 10 (v0.10.0) 100% complete across `steering/roadmap.md`, sync `docs/rtm.json`, and finalize the release changelog in `CHANGELOG.md`.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `steering/product.md` documents all 7 modular studios, domain boundaries, and local-first architecture.
- [ ] `AC-2`: `steering/tech.md` and `steering/structure.md` document the full dual-runtime stack and directory structure.
- [ ] `AC-3`: `steering/roadmap.md` marks Milestone 10 as 100% complete.
- [ ] `AC-4`: `npm run preflight` passes all 6 gates 100% cleanly.
