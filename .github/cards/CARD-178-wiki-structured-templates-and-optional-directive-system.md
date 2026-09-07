# [CARD-178] Wiki Structured Templates and Optional Directive System

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/wiki/; CARD-173; CARD-177
> **Labels**: `type:feature`, `AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Agents`

---

## 1. Why / Intent

Jacob wants a collection of proven note-taking frameworks (such as the Feynman Technique, System Hub / Concept Maps, DIKW Pyramid of Insight, Zettelkasten Atomic Notes, SOP / Runbooks, and Architecture Decision Records) readily available in the AutoReiv Wiki.

### Critical Invariants:
1. **Zero Regression on Natural Qwen Synthesis**:
   - Qwen's default note generation produces balanced, clear technical breakdowns that flow naturally.
   - Rigid templates must **NEVER** be forced as mandatory defaults. Freeform topic synthesis remains the platform standard when no template is requested.
2. **Optional Directive Only**:
   - Templates are only invoked when explicitly requested:
     - **In Chat**: Asking an assistant agent (e.g. *"Write a note on Hyper-V virtual switches using the Feynman template"*).
     - **In UI**: Selecting an optional template from a dropdown in the Wiki **[+ New Note]** modal (`#wikiNewNoteModal`).

---

## 2. What Jacob Sees & Controls (UI / UX)

### A. Wiki Studio New Note Modal (`#wikiNewNoteModal`):
```text
+-------------------------------------------------------------+
| [+ Create New Wiki Note]                                [X] |
+-------------------------------------------------------------+
| Title:    [ Hyper-V Virtual Switch Architecture           ] |
| Category: [ 00_Inbox (Staging)                            v ] |
| Template: [ None (Default Freeform)                       v ] |
|           | None (Default Freeform)                         |
|           | 🧠 Feynman Technique (Learning & Concepts)      |
|           | 🕸 System Hub (Concept Map & Architecture)       |
|           | 📐 DIKW Pyramid of Insight (RCA & Decisions)    |
|           | ⚡ SOP / Runbook (Procedures & Verification)    |
|           | ⚖️ ADR / Trade-Off (Architecture Decision)      |
|           | 🔗 Zettelkasten (Atomic Note)                   |
| Domain:   [ systems_engineering                           ] |
| Topic:    [ virtualization                                ] |
| Summary:  [ High-level overview of external vSwitches     ] |
| Body:                                                       |
| +---------------------------------------------------------+ |
| | (Auto-populates with the chosen template outline, or     | |
| | stays blank for freeform input if 'None' is selected)   | |
| +---------------------------------------------------------+ |
| [ Cancel ]                                   [ Create Note ] |
+-------------------------------------------------------------+
```

### B. Natural Chat Directive with Assistant:
```text
Jacob: "Write a note on AI agent reflection using the Feynman template"
Assistant: (Fetches 02_Resources/_Templates/feynman-technique.md, populates Core Explanation, Plain Analogy, Concrete Example, Knowledge Gaps, and stages the note in 00_Inbox/ for curation)
```

---

## 3. Core Technical Architecture & Files

1. **Vault Template Repository (`02_Resources/_Templates/`)**:
   Canonical markdown template files seeded into the vault:
   - `feynman-technique.md`: Core concept, plain-English analogy, concrete walkthrough, identified knowledge gaps.
   - `concept-map-system-hub.md`: Core hub, components/nodes table, directional connections, feedback loops, leverage points, Mermaid diagram.
   - `dikw-pyramid-of-insight.md`: Raw Data observations, contextual Information patterns, Knowledge cause-and-effect hypothesis, Wisdom strategic action items.
   - `zettelkasten-atomic.md`: Single atomic idea, explicit bidirectional wikilinks, emerging questions.
   - `sop-runbook.md`: Purpose, prerequisites, step-by-step commands/actions, verification test, rollback plan.
   - `adr-decision.md`: Context & problem, options considered & trade-offs, decision outcome, consequences & blast radius.

2. **Domain Store (`src/domain/wiki/store.py`)**:
   - `list_templates() -> List[Dict[str, Any]]`: Discovers and parses all `.md` files under `02_Resources/_Templates/` (excluding non-template authority files like `tag-authority.md`).
   - `get_template(slug: str) -> Optional[Dict[str, Any]]`: Returns template title, description, and raw body skeleton.

3. **REST API (`src/web/routers/wiki.py`)**:
   - `GET /api/wiki/templates`: Returns JSON array of available templates for the frontend modal and agent tools.

4. **Frontend View Controller (`src/web/static/modules/studios/wiki.js` & `index.html`)**:
   - Populate `#newNoteTemplateSelect` dropdown on modal open.
   - On change, if a template is selected, pre-populate `#newNoteBodyInput` with the template markdown. If reverted to "None", preserves existing text or resets to blank.

5. **Agent Tools & Kernel (`src/skills/builtin/wiki_tools.py`)**:
   - Extend `wiki_note_create` tool definition to accept optional `template: Optional[str] = None`.
   - If provided, resolves template skeleton and instructs the LLM to follow the template structure while strictly maintaining 10-field staging frontmatter.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-WIKI-030] The 6 structured template files (`feynman-technique.md`, `concept-map-system-hub.md`, `dikw-pyramid-of-insight.md`, `zettelkasten-atomic.md`, `sop-runbook.md`, `adr-decision.md`) exist in `02_Resources/_Templates/`.
- [ ] [REQ-WIKI-031] `WikiStore.list_templates()` dynamically discovers and returns available templates from the vault.
- [ ] [REQ-WIKI-032] `GET /api/wiki/templates` returns available templates over REST API.
- [ ] [REQ-WIKI-033] Freeform topic synthesis remains the default when no template is selected or specified.
- [ ] [REQ-WIKI-034] Assistant agent can be directed via prompt to use a specific template when creating notes via `wiki_note_create`.
- [ ] [REQ-WIKI-035] Wiki Studio `#wikiNewNoteModal` includes an optional `#newNoteTemplateSelect` dropdown that pre-fills `#newNoteBodyInput`.
- [ ] [REQ-WIKI-036] Automated tests in `tests/unit/wiki/` verify template listing and resolution.
- [ ] [REQ-WIKI-037] Frontend tests in `tests/unit/frontend/` verify template select dropdown behavior.

---

## 5. Constraints & Honor Flags

- **Ready card only. Do not implement until Jacob says build.**
- Never overwrite or degrade Qwen's freeform note generation capability.
- Local working branch: `qa`.
