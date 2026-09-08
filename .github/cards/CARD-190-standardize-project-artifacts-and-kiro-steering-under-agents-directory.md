# [CARD-190] Standardize Project Artifacts and Kiro Steering Under .agents Directory

> **Status**: Ready
> **Created**: 2026-09-08
> **Spec Reference**: none
> **Labels**: `type:feature`, `area:sdlc`, `area:developer`

---

## 1. Why / Intent
Standardize all project-level engineering and agentic artifacts inside a single canonical `.agents/` folder rather than scattering them across `.github/`, `docs/`, and root directories. Align steering and specifications strictly with the official AWS Kiro framework (persistent steering documents and 3-file specifications), enhanced with the Three Beats operating instructions (What he means, What AutoReiv does now, What will change) for cards and human alignment.

---

## 2. What to Build

### A. Canonical Project Directory Structure under `.agents/`
1. **Work Cards**: `.agents/cards/` — Individual task and feature cards (`CARD-xxx-*.md`).
2. **Kiro Specifications**: `.agents/specs/<feature-slug>/` — AWS Kiro 3-file specifications:
   - `requirements.md` (EARS format, user stories, acceptance criteria, `[REQ-xxx]`).
   - `design.md` (C4 components, Mermaid sequence diagrams, data contracts).
   - `tasks.md` (Sequential, testable vertical slices).
3. **Kiro Steering**: `.agents/steering/` — Persistent architectural guidance:
   - `product.md` (Product vision, target users, high-level capabilities).
   - `tech.md` (Technology stack, frameworks, operational constraints).
   - `structure.md` (Folder organization, module boundaries, naming conventions).
   - `roadmap.md` (Milestone progress and backlog roadmap).
4. **Architecture Decision Records**: `.agents/adr/` — Immutable global ADRs (`0001-*.md`).
5. **Requirements Traceability**: `.agents/rtm.json` — Machine-readable RTM matrix.
6. **Artifact Templates**: `.agents/templates/` — Standard templates for cards, specs, and ADRs:
   - `card.template.md` (Header metadata, Why/Intent, What to Build, Acceptance Criteria, Three Beats).
   - `requirements.template.md` (EARS patterns: Ubiquitous, Event-driven, State-driven, Unwanted).
   - `design.template.md` (Context, Component, Sequence, Data models).
   - `tasks.template.md` (Vertical slices linked to `[REQ-xxx]`).
   - `adr.template.md` (Context, Decision, Consequences, Compliance).

### B. Tooling and Path Resolution Updates
1. **`CardTools` (`src/application/skills/card_tools.py`)**:
   - `_cards_dir`: Check `.agents/cards/` first; fall back to `.github/cards/` if absent.
   - `_specs_dir`: Check `.agents/specs/` first; fall back to `docs/specs/` if absent.
   - `_steering_dir`: Check `.agents/steering/` first; fall back to `steering/` if absent.
2. **`ProjectsService` (`src/application/sdlc/projects_service.py`)**:
   - Update project scaffolding to create `.agents/` tree, template files, and starter Kiro steering files (`product.md`, `tech.md`, `structure.md`, `roadmap.md`).
3. **Template Tree (`templates/sdlc-project/`)**:
   - Update scaffold files to place starter steering, specs, and templates under `.agents/`.
4. **Repository Invariants (`AGENTS.md`)**:
   - Explicitly define the `.agents/` paths, AWS Kiro framework standards, and the Three Beats operating rhythm.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `CardTools` correctly resolves `.agents/cards/`, `.agents/specs/`, and `.agents/steering/` with legacy fallback.
- [ ] Project scaffolding (`templates/sdlc-project/`) generates the canonical `.agents/` layout with Kiro steering files and templates.
- [ ] `templates/sdlc-project/.agents/templates/` provides standard templates for cards, specs, and ADRs including the Three Beats.
- [ ] `AGENTS.md` is updated with canonical path documentation.
- [ ] Automated unit tests pass cleanly for `CardTools` and `ProjectsService`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Strict AWS Kiro compliance for steering (`product.md`, `tech.md`, `structure.md`) and specs (`requirements.md`, `design.md`, `tasks.md`).
- Backward compatibility: existing projects with `.github/cards/` or `docs/specs/` continue to resolve without breaking.
- Local commit on `qa`. Card remains `Ready` until user says `build`.
