---
id: CARD-598
title: "Wiki templates: one storage folder, agents create/list/use templates there (AutoReiv saved a new template under notes again)"
status: Ready
created: 2026-10-01
branch: qa
related:
  - CARD-349
  - CARD-293
  - CARD-178
  - CARD-353
  - CARD-409
  - CARD-570
  - CARD-322
labels:
  - type:bug
  - area:wiki
  - area:skills
  - P1
needs_decision: none
milestone: M24
---

# [CARD-598] Wiki templates: one storage folder, agents create/list/use templates there (AutoReiv saved a new template under notes again)

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:bug`, `area:wiki`, `area:skills`, `P1`

## Why

Jacob asked AutoReiv to make a new template. It saved it as a note (00_Inbox → 01_Notes) instead of in the templates folder, and not for the first time (CARD-349 fixed this once).

## Trace (qa `ad2e994f`)

- **Folder.** The canonical folder is `02_Resources/_Templates/<slug>.md` (`domain/wiki/store.py`):
  - `_resolve_templates_dir`;
  - `scaffold()` seeds `CORE_STRUCTURED_TEMPLATES` and the education templates there;
  - `list_templates` falls back to legacy `resources/templates/`.
- **Tools** (`application/skills/wiki_tools.py`): `wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update`.
  - `create` writes under the templates folder and fails closed on an existing slug (CARD-349).
  - Their descriptions still name the legacy alias "resources/templates/<slug>.md".
- **Root cause.**
  - `platform/skills/wiki-templates/SKILL.md` has had **`tools: []`** since CARD-570 (`a180e5c4`, skills became files and the old SQLite bindings were dropped). It is also **ticked on no agent**.
  - So `wiki_template_create`/`update` reach no agent. AutoReiv only has `wiki_template_list`/`read` (via `wiki-curation` and `wiki_tasks`).
- **Fallback to notes.**
  - AutoReiv's only write tool is `wiki_note_create`. Its description is "Create, write, or save a new markdown note ... stages into 00_Inbox/".
  - `platform/agents/autoreiv.md` line 43 says to "stage all new notes, summaries, or reports into 00_Inbox/ using wiki_note_create (One-Door Policy)"; curation later graduates them to `01_Notes/`.
  - A new template therefore becomes a note.
- **Latent bug.** In `_resolve_safe_path`, the alias map checks `resources/` before `resources/templates/`, so the alias resolves to `02_Resources/templates/...` (wrong folder) whenever that path exists.

## Scope

1. **One storage location:** `02_Resources/_Templates/<slug>.md`, nothing else.
   - The tool descriptions, the `wiki-templates` skill and the prompts name this path. Drop the `resources/templates` wording.
   - Legacy `resources/templates/` is read only as a migration source.
2. **Bind and tick the tools.**
   - `wiki-templates` binds `wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update`.
   - Tick it on AutoReiv (CARD-596 scope: templates and docs).
   - Tutor keeps read-only access to education templates.
3. **Prompts.** AutoReiv's prompt and the `wiki-inbox` skill say: templates are made with `wiki_template_create`, never `wiki_note_create`; notes are made from a template with `wiki_note_create(template=<slug>)`.
4. **Guard.** `wiki_note_create` refuses a document whose frontmatter has `type: template` (or whose title ends with "Template"), and says to use `wiki_template_create` with the slug. Inbox graduation never moves files into or out of `_Templates`.
5. **Fix the alias order:** the longest prefix first.
6. **Wiki Studio** lists templates from the same folder (check, fix if needed).

## Test that reproduces the bug (write first, red on qa)

- `resolve_allowed_tools(<autoreiv>)` includes `wiki_template_create` and `wiki_template_update`. Fails today.
- `wiki_note_create` with `type: template` frontmatter is refused with a pointer to `wiki_template_create`.
- `_resolve_safe_path("resources/templates/x.md")` resolves to `02_Resources/_Templates/x.md`.

## Acceptance criteria

- **Live** (throwaway :8770, nemotron): "Make a new wiki template for a meeting summary" to AutoReiv.
  - Creates `02_Resources/_Templates/meeting-summary.md` via `wiki_template_create`.
  - Nothing new appears in `00_Inbox/` or `01_Notes/`.
  - `wiki_template_list` shows the template.
  - "Create a note from the meeting-summary template" stages a note in `00_Inbox/` with those sections.
- The 3 tests above are green, and existing wiki template tests stay green.
- Fast preflight is green.
