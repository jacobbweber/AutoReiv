# ADR-0037: Steering and Product Documentation Truth Synchronization

## Context and Problem Statement
Following the rapid delivery of frontend modularization across 7 studios, force-directed graph physics, reactive store primitives, ESLint/Prettier tooling, and hermetic API integration tests, top-level steering documents (`steering/product.md`, `steering/tech.md`, `steering/structure.md`, `steering/roadmap.md`, `README.md`) risked drifting from the live implementation truth.

## Decision Drivers
- **Single Source of Truth**: Keep persistent steering documentation strictly synchronized with the implemented codebase.
- **Formally Conclude Milestone 10**: Certify all quality and testability deliverables for v0.10.0 (CARD-034 through CARD-037).
- **Zero Drift Guarantee**: Maintain 100% traceability across all 174 business requirements in `docs/rtm.json`.

## Considered Options
1. **Option 1**: Allow steering documentation to lag until major releases.
2. **Option 2 (Accepted)**: Perform a comprehensive steering truth synchronization card at the conclusion of Milestone 10.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Architectural blueprints, technology stacks, execution runbooks, and domain boundaries accurately document the 7 operational studios and dual-runtime architecture.
- Full verification of Milestone 10 across all 6 pre-flight quality gates.
- Complete traceability in `docs/rtm.json`.

### Negative Consequences / Trade-offs
- None.
