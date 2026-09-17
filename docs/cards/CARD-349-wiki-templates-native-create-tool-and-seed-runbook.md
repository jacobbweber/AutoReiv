# [CARD-349] Wiki Templates Native Create Tool and Seed Runbook

> **Status**: In Review  
> **Created**: 2026-09-17  
> **Spec Reference**: none  
> **Labels**: `type:feature`, `domain:wiki`, `domain:tools`, `domain:skills`  

---

## 1. Locked Decisions (from Jacob)

1. **Vault Path Structure**: Flat slugs (Option A). Stored directly under the vault's templates directory (`02_Resources/_Templates/<slug>.md` or `resources/templates/<slug>.md`).
2. **Collision & Update Behavior**: 
   * `wiki_template_create`: Strictly fails closed if the template slug already exists.
   * `wiki_template_update`: Dedicated update tool to modify an existing template's title, description, tags, or content. Fails closed if the template does not exist.
3. **Template Schema Standard**:
   ```yaml
   ---
   title: <title>
   description: <description>
   type: template
   tags: [wiki, template]
   ---
   ```

---

## 2. Three Beats

### Beat 1: What Jacob means
AutoReiv needs dedicated, first-class capabilities to author, update, and manage structured wiki templates. When an operator asks AutoReiv in Chat to create a wiki template, the agent must recognize that templates are distinct from wiki notes. It must use a dedicated template creation tool (`wiki_template_create`) that writes strictly into the template directory with validated YAML frontmatter (`type: template`), rather than falling back to `wiki_note_create` which saves notes inside `notes/resources/`. If a template already exists, creation must fail closed, and modifications must use a dedicated `wiki_template_update` tool.

### Beat 2: What AutoReiv does now
* `src/application/skills/wiki_tools.py` and `src/domain/wiki/store.py` only support reading templates (`list_wiki_templates`, `get_wiki_template`). There are **no creation or update tools** for templates.
* There is no platform skill runbook (`SKILL.md`) instructing the agent on template structure or conventions.
* When asked to create a template, the model falls back to `wiki_note_create`, which creates ordinary notes inside `notes/resources/`.

### Beat 3: What will change
1. **Domain Store Methods (`src/domain/wiki/store.py`)**:
   * `create_template(slug: str, title: str, description: str, content: str, tags: list[str] = None) -> dict`:
     * Resolves templates directory (`02_Resources/_Templates` or `resources/templates`).
     * Normalizes slug (e.g. `sop-runbook` -> `sop-runbook.md`).
     * Fails closed with `{"success": False, "error": "Template ... already exists. Use wiki_template_update to modify."}` if file exists.
     * Formats YAML frontmatter (`title`, `description`, `type: template`, `tags`) and writes file.
   * `update_template(slug: str, title: str = None, description: str = None, content: str = None, tags: list[str] = None) -> dict`:
     * Fails closed if template does not exist.
     * Merges updated fields into frontmatter and body, writing back cleanly.
2. **Application Skill Tools (`src/application/skills/wiki_tools.py`)**:
   * Implement `wiki_template_create` and `wiki_template_update` handlers.
   * Register both in `ScopedToolRegistry`.
3. **Schema & Scoping Mapping (`src/application/agent_packs/schema.py`)**:
   * Add `wiki_template_create` and `wiki_template_update` to `PLATFORM_SKILL_TOOLS["wiki"]`.
4. **Platform Skill Runbook (`platform-packs/autoreiv/skills/wiki-templates/SKILL.md`)**:
   * Standardized runbook instructing agents on:
     * When to use templates vs notes.
     * How to check existing templates with `list_wiki_templates`.
     * How to call `wiki_template_create` and `wiki_template_update`.
     * Pitfalls: Never use `wiki_note_create` for templates; never invent unauthorized directories.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `create_template` and `update_template` implemented on `WikiStore` in `src/domain/wiki/store.py`.
- [x] `create_template` fails closed if slug already exists; `update_template` fails closed if slug does not exist.
- [x] Templates write strictly to the resolved templates directory under user data vault root, never under checkout or `notes/`.
- [x] `wiki_template_create` and `wiki_template_update` exposed as tools in `src/application/skills/wiki_tools.py`.
- [x] Both tools registered in `ScopedToolRegistry` and added to `PLATFORM_SKILL_TOOLS["wiki"]` in `schema.py`.
- [x] `platform-packs/autoreiv/skills/wiki-templates/SKILL.md` authored and seeded.
- [x] Comprehensive unit tests in `tests/unit/wiki/test_wiki_templates.py` pass 100%.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Strict checkout hygiene: tests and runtime must write only to isolated temp fixtures or user data root, never to repo root.
- No code changes without Jacob's explicit `build` instruction.
