# [CARD-190] Standardize Project Artifacts and Kiro Steering Under .agents Directory

> **Status**: Ready
> **Created**: 2026-09-08
> **Spec Reference**: none
> **Labels**: `type:feature`, `area:sdlc`, `area:developer`

---

## 1. Why / Intent
Adopt and align directly with the open **DotAgents Protocol** (`https://dotagentsprotocol.com/`) as our canonical `.agents/` directory convention for project-level agent configuration and procedural knowledge. Integrate the official **AWS Kiro** framework for persistent steering (`steering/`) and 3-file specifications (`specs/`), augmented with the **Three Beats** operating rhythm (What he means, What AutoReiv does now, What will change) for work cards (`cards/`). Because the DotAgents Protocol reserves `.agents/skills/`, `.agents/agents/`, `.agents/tasks/`, `.agents/memories/`, `.agents/agents.md`, and `.agents/mcp.json`, our SDLC engineering primitives (`cards/`, `specs/`, `steering/`, `adr/`, `rtm.json`, `templates/`) fit natively within this layout with zero namespace collision.

---

## 2. What to Build

### A. Canonical Project Directory Structure under `.agents/` (DotAgents + AWS Kiro)
```text
.agents/
├── agents.md             # Project guidelines (DotAgents / AGENTS.md open standard)
├── mcp.json              # MCP tool server configurations (DotAgents standard)
├── skills/               # Reusable agent skills & runbooks (DotAgents standard)
├── cards/                # AutoReiv Work Cards (CARD-xxx-*.md with Three Beats)
├── specs/<feature-slug>/ # AWS Kiro 3-File Specifications:
│   ├── requirements.md   # EARS format user stories & acceptance criteria [REQ-xxx]
│   ├── design.md         # C4 architecture, sequence diagrams, data contracts
│   └── tasks.md          # Sequential, testable vertical slices
├── steering/             # AWS Kiro Persistent Steering:
│   ├── product.md        # Product vision, target users, high-level capabilities
│   ├── tech.md           # Technology stack, frameworks, operational constraints
│   ├── structure.md      # Folder organization, module boundaries, code conventions
│   └── roadmap.md        # Milestone progress and backlog roadmap
├── adr/                  # Architecture Decision Records (0001-*.md)
├── rtm.json              # Requirements Traceability Matrix
└── templates/            # Standardized artifact templates:
    ├── card.template.md          # Card with Three Beats & Definition of Done
    ├── requirements.template.md  # AWS Kiro EARS syntax template
    ├── design.template.md        # AWS Kiro technical design template
    ├── tasks.template.md         # AWS Kiro vertical slices template
    └── adr.template.md           # Architecture Decision Record template
```

### B. Tooling and Path Resolution Updates
1. **`CardTools` (`src/application/skills/card_tools.py`)**:
   - `_cards_dir`: Check `.agents/cards/` first; fall back to `.github/cards/` if absent.
   - `_specs_dir`: Check `.agents/specs/` first; fall back to `docs/specs/` if absent.
   - `_steering_dir`: Check `.agents/steering/` first; fall back to `steering/` if absent.
2. **`ProjectsService` (`src/application/sdlc/projects_service.py`)**:
   - Update project scaffolding to create the DotAgents-compliant `.agents/` tree, template files, and starter Kiro steering files (`product.md`, `tech.md`, `structure.md`, `roadmap.md`).
3. **Template Tree (`templates/sdlc-project/`)**:
   - Update scaffold files to place starter steering, specs, and templates under `.agents/`.
4. **Repository Invariants (`AGENTS.md`)**:
   - Explicitly document the DotAgents Protocol `.agents/` standard, AWS Kiro framework standards, and the Three Beats operating rhythm.

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
