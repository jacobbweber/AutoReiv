---
id: CARD-390
title: "Integrated Runbook Editor and Mechanical Capability Linter"
status: Done
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:skills
  - domain:forge
  - area:web
---

# [CARD-390] Integrated Runbook Editor and Mechanical Capability Linter

> **Status**: Done  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:skills`, `domain:forge`, `area:web`  

---

## 1. Why / Intent (Beat 1)

In our autonomic architecture ([ADR-0054]), skills are Standard Operating Procedures (SOPs) written in natural language Markdown (`SKILL.md`) with YAML frontmatter. Unlike arbitrary prompts, skills must adhere to strict mechanical invariants:
1. **Rule of 7 Tool Budget**: Maximum 6 tools declared per skill (`len(requires_tools) <= 6`) to prevent cognitive dilution and God-Agent sprawl.
2. **Mandatory Verification Contract**: Every skill must provide explicit, testable completion criteria (`## Done-When`) so the model knows when the procedure has succeeded.
3. **Trigger Clarity**: A clear trigger condition explaining when to activate.

Currently, operators editing runbooks in Agent Studio or drafting in Factory Studio write unguided markdown. Invalid runbooks are saved to disk and only discovered when tests or background checks fail. CARD-390 embeds real-time mechanical capability linting directly into the existing Agent Studio runbook editor and Factory Studio without introducing duplicate studio windows.

---

## 2. What AutoReiv Does Now (Beat 2)

1. In Agent Studio (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`), clicking "Edit Runbook" mounts `#studioRunbookEditor` with inputs for name, blurb, and markdown instructions (`#studioRunbookBody`), but offers zero validation feedback.
2. An operator can save runbooks that declare 10+ tools or omit `## Done-When` criteria.
3. `SkillContractCompiler` in `src/application/skills/linter.py` exists on the backend, but is not exposed via an HTTP endpoint for live interactive linting.
4. Clicking "New runbook" in Agent Studio opens an empty textarea with no template scaffolding.

---

## 3. What Will Change (Beat 3)

1. **Mechanical Capability Linter API (`POST /api/skills/lint`)**:
   - Accepts raw `SKILL.md` content or separate `name`, `description`, `instructions` fields.
   - Evaluates text using `SkillContractCompiler` against all 5 ADR-0054 capability rules:
     - `CAP-001`: Tool budget $\le 6$.
     - `CAP-002`: Mandatory testable `## Done-When` verification contract.
     - `CAP-003`: Security boundary collisions.
     - `CAP-004`: Runbook length cap.
     - `SYN-001`: YAML syntax validity.
   - Returns structured validation payload: `valid: bool`, `violations: list`, `tools_count: int`, and `detected_tools: list`.

2. **Interactive Runbook Validation Bar in Agent Studio (`forge.js`, `index.html`)**:
   - Add `[ 🔍 Validate Runbook ]` (`#studioRunbookValidateBtn`) adjacent to `#studioRunbookSaveBtn`.
   - Add live diagnostic banner (`#studioRunbookLintStatus`) displaying instant feedback:
     - Green badge on clean pass: `✅ Runbook valid (N declared tools, Done-when verified)`.
     - Amber/red warning list on violations: specific rule ID and actionable fix message.
   - Guard `studioRunbookSaveBtn` with automatic pre-save validation, warning if critical errors remain.

3. **Standard Runbook Blueprint Scaffolding**:
   - Clicking `#studioNewRunbookBtn` pre-fills `#studioRunbookBody` with the canonical Matt Pocock template:
     - `## Operating Principles`
     - `## Available Tools`
     - `## Done-When`

4. **Factory Studio Live Validation Integration (`factory.js`)**:
   - Provide the same `/api/skills/lint` check on `#factorySkillMarkdownEditor` when generating or saving skills in Column 2.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Unguided, unvalidated markdown saves in Agent Studio runbook editor.
- Blank canvas initialization on "New runbook" click.
- Stale proposal of reviving a duplicate standalone `#view-skills` window.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-390-001] (Ubiquitous)**: THE SYSTEM SHALL expose `POST /api/skills/lint` to evaluate draft `SKILL.md` content against ADR-0054 rules without requiring disk writes.
- **[REQ-390-002] (Event-Driven)**: WHEN an operator clicks `[ 🔍 Validate Runbook ]` in Agent Studio, THE SYSTEM SHALL display structured diagnostic feedback in `#studioRunbookLintStatus` showing pass/fail status and violations.
- **[REQ-390-003] (State-Driven)**: WHILE a draft runbook declares more than 6 tools or omits `## Done-When`, THE SYSTEM SHALL highlight the violation and caution the operator before saving.
- **[REQ-390-004] (Event-Driven)**: WHEN an operator clicks `New runbook` in Agent Studio, THE SYSTEM SHALL pre-populate `#studioRunbookBody` with the canonical Matt Pocock blueprint.
- **[REQ-390-005] (Negative Assertion)**: Automated tests shall verify that user skills are saved under `$DATA_DIR/skills/`, never inside the git checkout directory, and that no duplicate `#view-skills` container is created.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-390-runbook-linter-editor` cut from `qa`.
- Unit tests: `tests/unit/web/test_skill_lint_api.py`, `tests/unit/frontend/forge_runbook_linter.test.js`.
- Quality gates: `ruff check .`, `npm run lint:frontend`, `npm run test:unit:frontend`, `npm run test:smoke`, `npm run preflight`.
