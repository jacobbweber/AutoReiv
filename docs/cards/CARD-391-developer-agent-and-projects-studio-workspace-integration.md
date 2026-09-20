---
id: CARD-391
title: "Developer Agent and Projects Studio Workspace Integration"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:developer
  - domain:projects
  - area:sdlc
---

# [CARD-391] Developer Agent and Projects Studio Workspace Integration

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md), [ADR-0051](file:///d:/Projects/Active/AutoReiv/docs/adr/0051-dotagents-protocol-and-kiro-sdlc-standardization.md)  
> **Labels**: `type:feature`, `domain:developer`, `domain:projects`, `area:sdlc`  

---

## 1. Why / Intent (Beat 1)

With the Developer platform agent restored (CARD-388), it needs to be directly connected to the active development workspace in **Projects Studio** (`#view-projects`).

In our DotAgents SDLC standard (ADR-0051), the Developer agent operates against project repositories containing `.agents/` governance (`cards/`, `steering/`, `skills/`) and `AGENTS.md`. Jacob needs Projects Studio to not only allow setting the "Active Project", but to seamlessly bridge into a paired engineering session with Developer—letting Developer inspect the active project's file tree, read cards, run git status/diff, and execute tests directly against that repo.

---

## 2. What AutoReiv Does Now (Beat 2)

1. Projects Studio (`src/web/static/modules/studios/projects.js`) allows selecting an active project and viewing a file tree and artifact viewer.
2. However, there is no direct link between the active project in Projects Studio and the active agent in Chat Studio.
3. When chatting with Developer, the agent must be manually told which folder to inspect, or it relies on a hardcoded fallback path.

---

## 3. What Will Change (Beat 3)

1. **Projects Studio Direct Bridge (`projects.js`, `index.html`)**:
   - Add a prominent `[ 💻 Pair with Developer ]` button next to the `[Active Project]` badge.
   - Clicking it navigates directly to Chat Studio, selects Developer, and initializes a session pre-grounded with the active project's path and `.agents/` summary.
2. **Context-Aware Developer Tool Execution**:
   - Ensure Developer's file and git tools (`read_project_file`, `write_project_file`, `list_project_dir`, `git_status`, `git_diff`) resolve relative paths against the active project root dynamically fetched from project state or settings.
3. **Session Indicator in Chat**:
   - When chatting with Developer, display the active project name as a clickable pill in the Chat header, allowing instant navigation back to Projects Studio.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire manual folder path copy-pasting into chat prompts.
- Prune static fallback project path defaults in developer tool invocations.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-391-001] (Ubiquitous)**: THE SYSTEM SHALL allow setting an active project in Projects Studio that dynamically scopes Developer agent tool executions.
- **[REQ-391-002] (Event-Driven)**: WHEN an operator clicks `Pair with Developer` in Projects Studio, THE SYSTEM SHALL navigate to Chat Studio with Developer selected and the active project context loaded.
- **[REQ-391-003] (State-Driven)**: WHILE Developer runs project tools (`read_project_file`, `git_status`), THE SYSTEM SHALL resolve target paths relative to the active project root.
- **[REQ-391-004] (Negative Assertion)**: Automated tests shall explicitly assert that Developer rejects mutating files outside the active project root without explicit operator authorization.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-391-developer-projects-integration` cut from `qa`.
- Unit and integration tests: `tests/unit/agents/test_developer_project_grounding.py`, Vitest for `projects.js`.
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
