# [CARD-147] Prompt Catalog and Saved Prompts Manager

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Memory`

---

## 1. Why / Intent

Users frequently execute repetitive or specialized prompts (system audits, meeting summaries, task rollovers, structured code reviews, research queries). Rather than manually copy-pasting prompts or retyping them, users need a central **Prompt Catalog** to store, categorize, and search prompt templates, with instant 1-click insertion into the Chat Studio input box.

---

## 2. What to Build

1. **Storage & Persistence (`src/infrastructure/memory/repositories/prompts.py` or `schema.py`)**:
   - SQLite table `prompt_catalog`:
     - `id TEXT PRIMARY KEY`
     - `title TEXT NOT NULL`
     - `description TEXT`
     - `category TEXT DEFAULT 'general'`
     - `template_text TEXT NOT NULL`
     - `tags TEXT` (comma-separated or JSON array)
     - `is_builtin INTEGER DEFAULT 0`
     - `created_at TIMESTAMP`
     - `updated_at TIMESTAMP`
   - Built-in curated seed templates:
     - *"System Health Diagnostic"*
     - *"Weekly Summary & Task Rollover"*
     - *"Code Architecture Review"*
     - *"Meeting Notes to Wiki"*
     - *"Executive Document Summary"*
2. **REST API Endpoints (`src/web/routers/prompts.py`)**:
   - `GET /api/prompts`: List all prompts with optional category and query filtering.
   - `POST /api/prompts`: Create a new custom saved prompt.
   - `PUT /api/prompts/{prompt_id}`: Update a custom prompt.
   - `DELETE /api/prompts/{prompt_id}`: Delete a custom prompt.
3. **Frontend Prompt Catalog Modal (`src/web/templates/index.html` & `chat.js`)**:
   - In `#chatOptionsDrawer`, wire `#chatPromptsBtn` (`[ 📝 Prompt Catalog ]`).
   - Modal `#promptCatalogModal` with:
     - Category filter pills (All, System, Productivity, Coding, Analysis).
     - Search input.
     - Prompt cards with Title, Description, and Template preview snippet.
     - `[ Insert into Chat ]` button: pastes text into `#promptInput`, closes modal, and focuses input.
     - `[ + New Prompt ]` button with inline creation form.
     - Delete and edit actions for custom prompts.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-PROMPT-001]`: SQLite repository and schema for `prompt_catalog` with built-in seeds.
- [x] `[REQ-PROMPT-002]`: REST API endpoints for listing, creating, updating, and deleting prompts.
- [x] `[REQ-PROMPT-003]`: Chat Studio `#chatPromptsBtn` opens the Prompt Catalog modal with search and category filters.
- [x] `[REQ-PROMPT-004]`: 1-click **Insert into Chat** pastes the template into `#promptInput` and focuses the typing area.
- [x] Automated tests green via `pytest tests/unit/web` and `npm run test:unit:frontend`.
- [x] Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing passing tests.
- Local `qa` branch is source of truth.
- Mobile responsive layout with ergonomic touch targets.
