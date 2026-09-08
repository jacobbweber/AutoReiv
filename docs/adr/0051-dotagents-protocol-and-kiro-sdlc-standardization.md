# [ADR-0051] DotAgents Protocol and AWS Kiro SDLC Directory Standardization

> **Status**: Accepted
> **Date**: 2026-09-08
> **Deciders**: Jacob (Visionary & Product Owner), Antigravity (Principal Software Engineer)

---

## Context
Project-level engineering artifacts in AutoReiv were previously scattered across disparate folders: work cards in `.github/cards/`, specifications in `docs/specs/`, ADRs in `docs/adr/`, and architectural steering in `steering/`. Furthermore, the emerging open-source **DotAgents Protocol** (`https://dotagentsprotocol.com/`) defines a unified `.agents/` directory standard for agent guidelines, skills, MCP servers, and agent configurations.

## Decision
We adopt the **DotAgents Protocol** as the canonical project-level directory convention under `.agents/` and unify all SDLC primitives alongside it:
1. `.agents/agents.md`: Open-standard project guidelines and constitution.
2. `.agents/cards/`: AutoReiv work cards with the Three Beats operating alignment.
3. `.agents/specs/<slug>/`: AWS Kiro 3-file specifications (`requirements.md`, `design.md`, `tasks.md`).
4. `.agents/steering/`: AWS Kiro persistent steering documents (`product.md`, `tech.md`, `structure.md`, `roadmap.md`).
5. `.agents/adr/`: Architecture Decision Records (`0001-*.md`).
6. `.agents/rtm.json`: Requirements Traceability Matrix.
7. `.agents/templates/`: Reusable artifact templates embedding the Three Beats and AWS Kiro standards.

`CardTools` and `ProjectsService` implement dual-path resolution: prioritizing `.agents/` while retaining fallback support for legacy `.github/cards/` and `docs/specs/`.

## Consequences
- **Positive**: Single predictable location for all agent and engineering artifacts. Zero namespace collision with DotAgents Protocol. Clean version control and project portability.
- **Negative / Trade-offs**: Scaffolding includes additional starter files; tooling must check fallback paths for older projects.

## Compliance & Verification
- Validated via automated unit tests in `tests/unit/skills/test_card_tools.py` and `tests/unit/sdlc/test_projects_service.py`.
- Enforced via platform invariants in `AGENTS.md`.
