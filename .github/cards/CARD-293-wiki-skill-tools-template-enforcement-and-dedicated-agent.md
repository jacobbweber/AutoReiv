# [CARD-293] Wiki Skill, Tools, Template Enforcement & Dedicated Wiki Agent

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: DotAgents Protocol / Wiki Document Management (`docs/adr/0023-wiki-document-management-system-and-librarian-architecture.md`, `docs/specs/wiki-document-management`)
> **Labels**: `type:discussion`, `wiki`, `skills`, `tools`, `agents`, `architecture`
> **Branch**: `qa` (Ready card for alignment; build branch to be cut upon approval)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Disciplined, Structured Knowledge**: The Wiki should not be a dumping ground for arbitrary, unstructured text blocks. When agents or users create documentation or study notes, they must follow proven, structured cognitive patterns (e.g., Feynman technique, concept maps, DIKW pyramids, Zettelkasten atomic notes, standard operating procedures, or conceptual comparison tables).
2. **Mandatory Template in Metadata**: Every note or document created in the wiki must record the template it used in its YAML front matter metadata (e.g., `template: feynman-technique` or `template: concept-comparison`).
3. **Architectural primitive alignment**:
   - Should we introduce a **dedicated Wiki Agent** (e.g., "Wiki Librarian" or "Archivist") whose explicit role and prompt instructions are to groom, categorize, cross-link, and write structured wiki notes?
   - Should we enhance the **Wiki Platform Skill and Toolset** (`wiki_tools.py`, `WikiStore`) so that template selection and metadata tracking are enforced programmatically for all callers?
   - Or should we do **both** (enforce tool/schema invariants in the skill, while providing a dedicated agent for knowledge curation)?

---

### Beat 2: What AutoReiv Does Now
1. **Wiki Store & Core Templates**: `src/domain/wiki/store.py` (`CORE_STRUCTURED_TEMPLATES`) defines 5 built-in templates:
   - `feynman-technique.md` (Feynman Study Note)
   - `concept-map-system-hub.md` (System Hub Concept Map with Mermaid)
   - `dikw-pyramid-of-insight.md` (DIKW Framework: Data → Info → Knowledge → Wisdom)
   - `zettelkasten-atomic.md` (Atomic Note with Wikilinks)
   - `sop-runbook.md` (Standard Operating Procedure / Runbook)
2. **Tool Implementation**: `src/application/skills/wiki_tools.py` has `create_wiki_note()`:
   - It accepts an optional `template: Optional[str] = None` argument.
   - If provided, it sets `extra_frontmatter["template"] = template` and replaces `${TITLE}` if content is empty.
   - **Gap**: `template` defaults to `None`. Agents can call `create_wiki_note` with arbitrary string blobs without specifying a template, resulting in notes without `template:` front matter or consistent structure.
3. **Agent Roster**: The current agent fleet (`packs/` and `platform-packs/`) includes Assistant and specialized domain agents, but there is no dedicated "Wiki Librarian" or "Knowledge Archivist" agent whose primary responsibility is maintaining the knowledge vault and curating notes into the Degree/Class taxonomy.
4. **Wiki Studio UI**: `src/web/static/modules/studios/wiki.js` displays a note tree, front matter inspector, and preview pane, but does not provide a template picker when manually minting a note.

---

### Beat 3: What Will Change
1. **Architectural Evaluation & Options**:
   - **Option A: Dedicated Wiki Agent**:
     - Scaffold a new agent pack (e.g. `packs/librarian/` or `packs/wiki_archivist/`) whose system prompt enforces knowledge curation, taxonomy management (`00_Inbox` triage → `01_Degree_Programs` / `02_Knowledge_Base`), and template selection.
     - *Trade-off*: Concentrates wiki responsibility in one cognitive specialist, but does not prevent other agents from creating unstructured notes if they have access to wiki tools.
   - **Option B: Enhanced Platform Skill & Tool Enforcement**:
     - Update the Wiki Platform Skill runbook (`skills/wiki/SKILL.md`) and tool schemas (`create_wiki_note`, `update_wiki_note`).
     - Expose `list_wiki_templates` as an atomic callable so agents discover available templates before writing.
     - Make `template` mandatory (or default to a structured `atomic_note` template) and enforce that `template` is written to YAML front matter on every note creation.
     - *Trade-off*: Enforces invariants across the entire system regardless of which agent is active, but lacks a dedicated conversational persona for active knowledge grooming.
   - **Option C (Recommended Hybrid)**:
     - **Tool & Skill Invariant**: Enhance `WikiTools` to require a `template` parameter (with available templates queryable via `list_wiki_templates`) and ensure `template: <id>` is always written to the YAML front matter.
     - **Dedicated Librarian Agent**: Provide a dedicated Wiki Archivist agent in the agent roster configured with the enhanced Wiki skill as its primary role, while allowing other agents to invoke the same structured tools when needed.
2. **New Template Candidate (Concept Distinction / Study Note)**:
   - Add a 6th core template (`concept-comparison.md` or `study-distinction.md`) based on the reference example below to support clear structural comparisons (e.g., Structure vs. Interaction vs. Polish).

---

## 2. Reference Template Example: UI/UX Design — Structure vs. Polish

The following reference document illustrates the standard of structure, clear tables, and precise definitions desired for wiki study notes:

```markdown
# UI/UX Design — Structure vs. Polish
One-sentence version: Structure (layout, navigation, placement) decides what the user sees and in what order — that's the "where does this button go" thinking. Polish (visual design, behavior) decides how it looks and feels — that's the "make corners soft, round, spaced by measurement" thinking. Both are design; only one is decoration.

1. The two words, precisely
| Term | What it means | Question it answers |
| --- | --- | --- |
| UX (User Experience) | The whole experience of using the product — flow, logic, ease, frustration | "Can the user complete the task, and how does it feel end-to-end?" |
| UI (User Interface) | The concrete visual + interactive surface — screens, buttons, text, motion | "What exactly does the user see and touch?" |

UX is upstream of UI. You design the UX (the flow) first, then build the UI (the screens) to express it.

2. The Structure layer — "where does this button go"
This is the thinking of information architecture: organizing content and actions so users can find and do things without thinking.

| Term | Meaning |
| --- | --- |
| Information Architecture (IA) | The map of the product: what pages/screens exist and how they relate |
| User flow / user journey | The ordered path a user takes to complete a goal (e.g., browse → cart → checkout) |
| Wireframe | Low-fidelity sketch of a screen — boxes and arrows, no colors. Structure only. |
| Hierarchy | What matters most gets the most attention: biggest, first, top-left |
| Layout / grid | The invisible skeleton that aligns everything: columns, rows, gutters |
| Whitespace (negative space) | Deliberate empty space that separates and groups — a structural tool, not "wasted" space |
| Affordance | A design cue that signals how something works (a button looks pressable, a link looks clickable) |
| Signifier | The explicit label/icon that tells the user what an element does |
| Primary vs. secondary action | One dominant action per screen (the big button); everything else is quieter |
| Navigation patterns | Tabs, breadcrumbs, sidebars, hamburger menus — the "roads" of the product |
| Wayfinding | Always knowing where you are and how to get back |
| Progressive disclosure | Show only what's needed now; reveal the rest when asked |
| Mental model | The user's picture of how the product works; good design matches it |

Structure test: can a user complete the core task with labels stripped and colors removed? If not, the structure is broken — no amount of polish fixes it.

3. The Polish layer — "make corners soft, round, spaced by measurement"
Polish is the visual design + behavior layer applied on top of a working structure.

| Term | Meaning |
| --- | --- |
| Visual design / art direction | Color, typography, imagery — the "look" |
| Typography | Font choice, size, weight, line-height — text as a design material |
| Color system | A palette with roles: primary, neutral, success/warning/error |
| Spacing scale | Measured, consistent spacing (e.g., a 4pt or 8pt grid) — "spaced by measurement," not by eye |
| Corner radius | How rounded an edge is (border-radius); a small, consistent value reads as a style decision, not an accident |
| Elevation / shadow | Layering: what floats above what (cards, modals) |
| States | What an element looks like when hovered, focused, active, disabled, loading, error |
| Microinteraction / motion | Small animations that confirm actions (button press, screen transition) |
| Design tokens | Named values for color/spacing/radius so the whole product stays consistent |
| Design system | The library of tokens + components that keeps polish consistent at scale |

Polish test: does it look intentional and consistent — or like a pile of small decisions made by eye?

4. The core distinction
| Structure (the real design) | Polish (visual enhancement) |
| --- | --- |
| Decides: What exists, where, in what order | Decides: How it looks and feels |
| Artifacts: IA, user flows, wireframes | Artifacts: Style guide, tokens, components |
| Failure mode: User is lost, can't finish the task | Failure mode: Looks cheap, inconsistent, untrustworthy |
| Fixable later? No — restructuring is expensive | Fixable later? Yes — reskinning is cheap |
| Thinking type: "Where does this button go?" | Thinking type: "Make the corners soft, spaced by measurement" |

Rule of thumb: you can polish a broken layout, but you cannot fix a bad layout with polish. Order of work: IA → flows → wireframes → visual design → motion/behavior. Skipping straight to "make it pretty" is how you get a beautiful product nobody can use.

5. One analogy
Building a house: structure is the floor plan — where rooms, doors, and the kitchen go (you can't move the kitchen after the walls are up). Polish is the paint, trim, and hardware (repaintable any time). A gorgeous paint job doesn't help if the bedroom has no door.

Study note — general design vocabulary, not tied to any specific design system.
```

---

## 3. Acceptance Criteria (Proposed for Alignment)

- [ ] **[REQ-WIKI-293-001]**: Tool-layer template discovery callable (`list_wiki_templates`) returns all available template identifiers, descriptions, and schemas.
- [ ] **[REQ-WIKI-293-002]**: `create_wiki_note` enforces template selection (`template` parameter required, falling back to a structured default like `zettelkasten-atomic` if unspecified).
- [ ] **[REQ-WIKI-293-003]**: Front matter metadata contract requires `template: <id>` in all newly created or curated wiki notes.
- [ ] **[REQ-WIKI-293-004]**: Introduce new core structured template `concept-comparison.md` (distinction/comparison note) modeled after the Structure vs. Polish reference format.
- [ ] **[REQ-WIKI-293-005]**: Decide and scaffold either a dedicated Wiki Archivist agent pack (`packs/wiki_librarian/`) or an enhanced Wiki Platform Skill runbook (`skills/wiki/SKILL.md`) with explicit template prompting directives.

---

## 4. Constraints

- Ready status only; **do not implement until Jacob explicitly approves and says build**.
- Maintain 100% backward compatibility with existing notes in `data/wiki/`.
- Conventional commits and strict TDD on future implementation branch.
- No third-party product names in card, UI, or documentation.
