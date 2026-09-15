# [CARD-293] Wiki Skill, Tools, Template Enforcement & Dedicated Wiki Agent

> **Status**: In Review
> **Created**: 2026-09-13
> **Spec Reference**: DotAgents Protocol / Wiki Document Management (`docs/adr/0023-wiki-document-management-system-and-librarian-architecture.md`, `docs/specs/wiki-document-management`)
> **Labels**: `type:discussion`, `wiki`, `skills`, `tools`, `agents`, `architecture`, `grounding-honesty`
> **Branch**: `feat/card-293-wiki-agent-templates`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Disciplined, Structured Knowledge**: The Wiki should not be a dumping ground for arbitrary, unstructured text blocks. When agents or users create documentation or study notes, they must follow proven, structured cognitive patterns (e.g., Feynman technique, concept maps, DIKW pyramids, Zettelkasten atomic notes, standard operating procedures, or conceptual comparison tables).
2. **Mandatory Template in Metadata**: Every note or document created in the wiki must record the template it used in its YAML front matter metadata (e.g., `template: feynman-technique` or `template: concept-comparison`).
3. **No Lost Wiki Location / No Filesystem Wandering**: In a real chat session, the agent created a note without a template, and when asked to update it with the user's manual expansions, it panicked because the tool response was truncated. It then completely lost track of where the wiki vault was, confused the repo's `notes/` scratch directory with the vault, searched `data/wiki` fruitlessly, and burned its entire 10-turn budget aimlessly hunting the disk until it died. We have a serious logic gap: agents must be unambiguously grounded on the canonical vault location and must never wander the disk searching for wiki files.
4. **Truncation-Safe Updates**: Reading a wiki note for updates must never cause an agent to panic about "clobbering user edits" due to truncation. The tool layer must provide safe, full-content reading and structured update/append mechanisms.
5. **Architectural Primitive Alignment**:
   - Should we introduce a **dedicated Wiki Agent** (e.g., "Wiki Librarian" or "Archivist") whose explicit role and prompt instructions are to groom, categorize, cross-link, and write structured wiki notes?
   - Should we enhance the **Wiki Platform Skill and Toolset** (`wiki_tools.py`, `WikiStore`) so that template selection, metadata tracking, and path grounding are enforced programmatically for all callers?
   - Or should we do **both** (enforce tool/schema invariants in the skill, while providing a dedicated agent for knowledge curation)?

---

### Beat 2: What AutoReiv Does Now
1. **Wiki Store & Core Templates**: `src/domain/wiki/store.py` (`CORE_STRUCTURED_TEMPLATES`) defines 5 built-in templates:
   - `feynman-technique.md` (Feynman Study Note)
   - `concept-map-system-hub.md` (System Hub Concept Map with Mermaid)
   - `dikw-pyramid-of-insight.md` (DIKW Framework: Data → Info → Knowledge → Wisdom)
   - `zettelkasten-atomic.md` (Atomic Note with Wikilinks)
   - `sop-runbook.md` (Standard Operating Procedure / Runbook)
2. **Tool Implementation & Template Bypass**: `src/application/skills/wiki_tools.py` has `create_wiki_note()`:
   - It accepts an optional `template: Optional[str] = None` argument.
   - If provided, it sets `extra_frontmatter["template"] = template` and replaces `${TITLE}` if content is empty.
   - **Gap 1 (No Template Enforcement)**: `template` defaults to `None`. Agents can call `create_wiki_note` with arbitrary string blobs without specifying a template, resulting in notes without `template:` front matter or consistent structure.
   - **Gap 2 (No Template Discovery)**: There is no dedicated `list_wiki_templates` tool callable surfaced to chat or kernel agents, making templates invisible unless hardcoded in agent prompts.
3. **Vault Grounding & Path Ambiguity**:
   - `paths.wiki_path` can resolve to `%LOCALAPPDATA%\AutoReiv\data\wiki` (runtime default) or local `./data/wiki`.
   - The repository also contains a `./notes/` scratch directory.
   - **Gap 3 (Lost Location & Disk Crawling)**: When tools return note metadata, they return relative paths like `00_Inbox/ui_ux_...md`. They do not ground the agent with the explicit absolute `vault_root`. When the agent tried to bypass tools with raw shell/file access, it guessed `./notes/` and `./data/wiki/`, failed to locate the staged note, and exhausted its turn budget.
4. **Tool Truncation Panic**:
   - When an agent reads an expanded note (~1,900 words), output truncation in tool envelopes leads the agent to believe it does not possess the full file, causing it to abandon the wiki tools in favor of raw OS file reads.
5. **Agent Fleet**: No dedicated Wiki Librarian persona exists in `packs/` or `platform-packs/`.

---

### Beat 3: What Will Change
1. **Architectural Evaluation & Options**:
   - **Option A: Dedicated Wiki Agent**:
     - Scaffold a new agent pack (`packs/wiki_librarian/`) whose system prompt enforces knowledge curation, taxonomy management (`00_Inbox` triage → `01_Degree_Programs` / `02_Knowledge_Base`), template selection, and wikilink graph maintenance.
     - *Trade-off*: Concentrates wiki responsibility in one cognitive specialist, but does not prevent other agents from creating unstructured notes if they have access to wiki tools.
   - **Option B: Enhanced Platform Skill & Tool Enforcement**:
     - Update the Wiki Platform Skill runbook (`skills/wiki/SKILL.md`) and tool schemas (`create_wiki_note`, `update_wiki_note`).
     - Expose `list_wiki_templates` as an atomic callable so agents discover available templates before writing.
     - Make `template` mandatory (or default to a structured `atomic_note` template) and enforce that `template` is written to YAML front matter on every note creation.
     - *Trade-off*: Enforces invariants across the entire system regardless of which agent is active, but lacks a dedicated conversational persona for active knowledge grooming.
   - **Option C (Recommended Hybrid)**:
     - **Tool & Skill Invariant**: Enhance `WikiTools` to require a `template` parameter (queryable via `list_wiki_templates`), enforce `template: <id>` in YAML front matter, return explicit `vault_root` in return envelopes, and provide truncation-safe read/update methods.
     - **Dedicated Librarian Agent**: Provide a dedicated Wiki Archivist agent in the agent roster configured with the enhanced Wiki skill as its primary role, while allowing other agents to invoke the same structured tools when needed.
2. **Canonical Vault Grounding Invariant**:
   - All wiki tool envelopes must return `vault_root` (absolute path) and `relative_path`.
   - Agent base instructions (`good_agent_instructions.py`) must include a strict directive: *Never hunt the disk with shell commands for the wiki vault. Always use the canonical `wiki_*` tools.*
3. **Truncation-Safe Read / Update API**:
   - `read_wiki_note` must provide guaranteed complete note content or explicit chunking parameters, eliminating the fear of clobbering user edits.
   - Introduce or document structured section updating so agents can restyle a note into a template without needing to rewrite manual user content from scratch.
4. **New Template Candidate (Concept Distinction / Study Note)**:
   - Add a 6th core template (`concept-comparison.md` or `study-distinction.md`) based on the reference example below to support clear structural comparisons (e.g., Structure vs. Interaction vs. Polish).

---

## 2. Real-World Failure Case: Template Bypass, Truncation Panic & Lost Vault Location

The following live chat failure demonstrates the exact logic gaps and cascading errors this card eliminates:

```text
USER:
Create me a note in the wiki, I want you to break down the concept of UI/UX design. Explain the concepts and terminology that get used to do different things like designing layout, navigation flow vs polish like visual asthetics and behavior, like make corners soft rounded spaced by measurement. I want to understand the language and concepts behind the difference of just visual enhancements vs actual overall design and ui navigation flow, locations, what buttons where type of thinking. Succes is when the note is in the wiki and i can read it and is done.

---

ASSISTANT:
Job job_d64d54a0547b FAILED during Execute: parked. Not done — Journey shows FAILED; no deliverable claimed.

---

ASSISTANT:
Done ✅ — the note is in the Wiki and I've read it back to verify.

Note details:
- Path: 00_Inbox/ui_ux_design_structure_vs_polish_the_language_behind_layout_flow_visuals.md
- Title: UI/UX Design — Structure vs. Polish: The Language Behind Layout, Flow & Visuals
- UID: 20260913-100434
- Status: inbox (staged per one-door policy — it'll be verified and can graduate to 01_Notes/)
- Word count: 868

What it covers:
1. UI vs. UX, precisely — UX = the whole experience/flow (upstream), UI = the concrete visual surface
2. The Structure layer — the "where does this button go" thinking: information architecture, user flows, wireframes, hierarchy, grid/layout, whitespace, affordance, signifier, primary vs. secondary actions, navigation patterns, wayfinding, progressive disclosure, mental models
3. The Polish layer — the "make corners soft, round, spaced by measurement" thinking: visual design, typography, color systems, spacing scales (4pt/8pt grids), corner radius, elevation/shadow, states, microinteractions/motion, design tokens, design systems
4. The core distinction — side-by-side table: structure decides what exists, where, in what order (failure = user is lost; expensive to fix later); polish decides how it looks and feels (failure = looks cheap; cheap to reskin). Plus the rule of thumb: you can polish a broken layout, but you cannot fix a bad layout with polish.
5. The house analogy — floor plan vs. paint: a gorgeous paint job doesn't help if the bedroom has no door

---

USER:
When you created that, did you use any wiki templates or try to find if any would make sense first?

---

ASSISTANT:
Honest answer: No — I didn't. I jumped straight to wiki_note_create with hand-written content and no template. That was a process gap on my part, and I just checked what was actually available to confirm.

What's in the vault (verified via search):
| Template | Fit for your ask | Verdict |
|---|---|---|
| feynman-technique.md — "Explaining complex concepts in plain language..." | High — your ask was literally "break down the concept so I understand it" | ⭐ Best fit |
| zettelkasten-atomic.md — one atomic idea per note | Medium — multi-concept | Possible if split |
| concept-map-system-hub.md — components, dependencies, Mermaid | Low-Medium | Not a fit |
| note_template.md — generic Context/Details/References | Low — too generic | Not a fit |

Why it matters:
The Feynman template would have given the note:
- Step 1: Teach It Simply — plain-language explanation (I did this, but ad hoc)
- Step 2: Gaps — explicit "what I don't understand yet" section (I skipped this — it's the most valuable part for learning)
- Step 3: Refined Takeaway — condensed version
- Step 4: Review Checklist — self-test questions (I skipped this too)

Want me to fix it?
I can update the existing note (same path, no duplicate) to wrap it in the Feynman structure — keeping all the terminology tables, and adding the Gaps and Review Checklist sections. Say the word and I'll do it.

---

USER:
Yes, I want you to update that note, I just made some updates to it manually. But go ahead and get it into a template

---

ASSISTANT:
You made manual edits, so let me read the note's current state first to make sure I preserve your changes before restructuring.

---

ASSISTANT:
I can see you've significantly expanded the note (868 → 1908 words, added a whole Interaction layer section). The read got truncated, so let me pull the full current content before I restructure anything — I don't want to clobber your edits.

---

ASSISTANT:
The wiki read truncates for my context budget, and I can't let your manual edits get clobbered — I need the complete current body before restructuring. Let me try to pull the full file from disk.

---

ASSISTANT:
The Wiki vault isn't under the project dir. Let me locate it on disk.

---

ASSISTANT:
There's a notes/ directory in the checkout — that's likely the Wiki vault. Let me find the note there.

---

ASSISTANT:
The notes/ directory here is the repository's scratch notes, not the Wiki vault (the Wiki is managed separately by the platform). The Wiki's read gets truncated by my context budget, so I'll try to find the vault on disk under the checkout's data/ directory.

---

ASSISTANT:
Found it — data/wiki is the vault. Let me locate the note file.

---

ASSISTANT:
Not in that folder. Let me check the other wiki subfolders.

---

ASSISTANT:
Execution terminated: Max turn budget of 10 reached.
```

### Key Breakdowns Revealed by this Incident:
1. **Initial Creation Failed Process**: The agent didn't query available templates, selected no template, and produced a note without template scaffolding or metadata.
2. **Truncation Triggered Panic**: When the agent saw truncated tool output on a 1,908-word note, it assumed it was blind to the full content and refused to use the wiki update tool out of fear of clobbering.
3. **Lost Vault Location & Directory Crawling**: The agent had no grounded absolute path to the active vault. It conflated `./notes/` with the wiki vault, then searched `./data/wiki/`, failed to find `00_Inbox`, and burned all remaining turns searching the filesystem.

---

## 3. Reference Template Example: UI/UX Design — Structure vs. Polish

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

## 4. Acceptance Criteria (Proposed for Alignment)

- [x] **[REQ-WIKI-293-001]**: Tool-layer template discovery callable (`list_wiki_templates`) returns all available template identifiers, descriptions, and schemas.
- [x] **[REQ-WIKI-293-002]**: `create_wiki_note` enforces template selection (`template` parameter required, falling back to a structured default like `zettelkasten-atomic` if unspecified).
- [x] **[REQ-WIKI-293-003]**: Front matter metadata contract requires `template: <id>` in all newly created or curated wiki notes.
- [x] **[REQ-WIKI-293-004]**: **Canonical Vault Grounding**: Wiki tool envelopes must return `vault_root` (absolute path) and `relative_path` on every call. `good_agent_instructions.py` includes a hard rule: *Never search disk for wiki notes; only interact with the wiki via `wiki_*` tools.*
- [x] **[REQ-WIKI-293-005]**: **Truncation-Safe Read / Update**: `read_wiki_note` provides full note content or structured chunks with `total_length` and `has_more` indicators so agents never panic about truncation or clobbering.
- [x] **[REQ-WIKI-293-006]**: Introduce new core structured template `concept-comparison.md` (distinction/comparison note) modeled after the Structure vs. Polish reference format.
- [x] **[REQ-WIKI-293-007]**: Decide and scaffold either a dedicated Wiki Archivist agent pack (`packs/wiki_librarian/`) or an enhanced Wiki Platform Skill runbook (`skills/wiki/SKILL.md`) with explicit template prompting directives.

---

## 5. Constraints

- Ready status only; **do not implement until Jacob explicitly approves and says build**.
- Maintain 100% backward compatibility with existing notes in the wiki vault.
- Conventional commits and strict TDD on future implementation branch.
- No third-party product names in card, UI, or documentation.
