---
id: CARD-409
title: "Wiki Architecture Overhaul: Single-Lever Wiki Tools, wiki_tasks Runbook, Granular Skills Split, RAG Grounding Poisoning Fix, and Goal Phase Dedup"
status: Complete
created: 2026-09-21
adr: none
labels:
  - type:feat
  - type:bug
  - type:refactor
  - area:wiki
  - area:orchestration
  - area:agents
  - area:skills
  - area:ux
---

# [CARD-409] Wiki Architecture Overhaul: Single-Lever Wiki Tools, wiki_tasks Runbook, Granular Skills Split, RAG Grounding Poisoning Fix, and Goal Phase Dedup

> **Status**: Complete  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:feat`, `type:bug`, `type:refactor`, `area:wiki`, `area:orchestration`, `area:agents`, `area:skills`, `area:ux`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

Jacob requires the AutoReiv Wiki and task tracking subsystem to be bulletproof, predictable, and architecturally clean across both daily assistant conversations and deep knowledge curation:

1. **Canonical Staging Without Poisoning**:
   When Jacob asks AutoReiv (or any general assistant):
   > *"hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"*
   - The system must collect telemetry and stage a clean note into `00_Inbox/` via `wiki_note_create`.
   - It must **never** hijack Jacob's personal weekly worklogs (`01_Notes/weekly/2026-Wxx.md`).
   - It must **never** poison the model's prompt with restrictive historical search hits claiming novel paths are forbidden.
   - It must **never** falsely fail-closed with "Not done — ungrounded Wiki path claim" when valid note tools are invoked.
   - It must **never** stutter or quadruplicate output across multi-phase jobs.

2. **Single Primary Companion (No Separate Wiki Agent)**:
   - AutoReiv remains the single primary companion holding wiki and task capabilities. No secondary `@wiki` agent pack to fragment user context or create agent confusion.

3. **Single Lever Invariant for Note Creation**:
   - Exactly **ONE** tool creates notes across the entire platform: `wiki_note_create`.
   - Complete pruning of the 5 bespoke weekly tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`).

4. **SOP Runbook-Driven Task Management (`wiki_tasks`)**:
   - Weekly notes, task checkboxes (`- [ ]`), and daily work logs are managed via an SOP runbook (`wiki_tasks`) using canonical wiki tools (`wiki_note_read`, `wiki_note_create`, `wiki_note_update`, `wiki_template_read`).
   - Tools remain atomic, verb-noun primitives; the skill runbook provides the contextual intelligence and templates.

5. **Granular Skill Separation**:
   - `wiki_tasks`: Weekly work journaling, task rollover, and daily log tracking (4 tools: `wiki_note_read`, `wiki_note_create`, `wiki_note_update`, `wiki_template_read`).
   - `wiki-knowledge`: Vault read and search (3 tools: `wiki_note_search`, `wiki_note_read`, `wiki_note_list`).
   - `wiki-inbox`: Intake drop-zone (2 tools: `wiki_note_create`, `promote_artifact_to_wiki`).
   - `wiki-curation`: Deep grooming, template management, deduplication, merging, and archiving (6 tools: `wiki_note_organize`, `wiki_note_update`, `wiki_note_archive`, `wiki_template_list`, `wiki_template_read`, `wiki_overview`).

6. **Intelligent Curation, Deduplication & Merging with Zero Data Loss**:
   - Triggered either by the nightly routine or by Jacob clicking `[⚡ Curate Inbox Now]` in Wiki Studio.
   - Evaluates notes in `00_Inbox/` one-by-one: validates YAML frontmatter, checks against available templates, checks `01_Notes/` for overlapping topics.
   - If material overlaps: merges into a unified note in `01_Notes/`, links `supersedes` in frontmatter, and preserves the superseded original in `03_Archive/<slug>_superseded_<timestamp>.md`.
   - When updating or migrating an existing graduated note to a new template: automatically backs up the prior version to `03_Archive/` before writing the new structure.

7. **Strict Naming (`snake_case`)**:
   - Eliminate duplicate shadow tool registrations (`list_wiki_templates`, `get_wiki_template`). Standardize strictly on canonical names (`wiki_template_list`, `wiki_template_read`, `wiki_note_archive`).

---

## 2. What AutoReiv Does Now (Beat 2: Current Code Path & Failures)

1. **RAG Search Injection Trap**: `WikiThinGrounding` searches the vault using the user's prompt keywords. It matches unrelated files (`01_Notes/weekly/2026-W35.md`, `sop-runbook.md`) and injects a hard rule into the LLM context:
   `Allowed grounding paths: 01_Notes/weekly/2026-W35.md`
   `Never invent Wiki paths or titles... If you need sources not in the allowed list, park`.
   This forbids the LLM from creating any new note path in `00_Inbox/`.
2. **Weekly Note Shadow Tools**: Bespoke tools (`get_or_create_weekly_note`, `log_daily_work_item`, etc.) competed with canonical wiki tools, confusing model routing and violating the Single Lever Invariant.
3. **Honesty Gate Tool Blindspot**: `wiki_thin_grounding.py` only counted `wiki_note_create` and `wiki_note_read` as provenanced.
4. **Chat Deliverable Stuttering**: `src/web/routers/chat.py` joined Phase 0 and Phase 1 deliverables with `\n\n---\n\n`, repeating summaries 3 to 4 times.
5. **Duplicate Tool Registrations**: `wiki_tools.py` registered both `wiki_template_list` and `list_wiki_templates`, as well as `wiki_template_read` and `get_wiki_template`.
6. **Monolithic Wiki Skill**: A single bloated `wiki` skill bundled all 14 tools, preventing granular scoping.

---

## 3. What Will Change (Beat 3: Technical Implementation)

1. **Domain & Store Layer (`src/domain/wiki/store.py`)**:
   - Add `archive_note(relative_path: str, reason: str = "") -> Dict[str, Any]` to safely move notes to `03_Archive/<slug>_archive_<timestamp>.md` with updated metadata (`status: "archived"`).
   - Add `backup_to_archive: bool = False` option to `write_note()` to preserve previous versions on major update or template conversion.
   - Refine `search_notes()` to exclude templates and tag authority files from general note search results.
2. **Universal Wiki Tools (`src/application/skills/wiki_tools.py`)**:
   - Register `wiki_note_archive`.
   - Prune shadow tool aliases `list_wiki_templates` and `get_wiki_template`. Canonical tools are `wiki_template_list` and `wiki_template_read`.
   - Provide standard aliases for note operations (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_archive`, `wiki_note_organize`, `wiki_note_search`, `wiki_note_list`, `wiki_note_append`).
3. **Prune Bespoke Weekly Tools (`src/application/skills/weekly_notes_tools.py`)**:
   - Deleted `weekly_notes_tools.py` and its tests entirely.
   - Removed `weekly-notes` from `BUILTIN_TOOL_GROUPS` in `manifest.py`.
4. **Orchestration & Grounding Safety (`src/application/orchestration/wiki_thin_grounding.py`)**:
   - Detect creation/staging intent (`is_wiki_create_ask`): do NOT inject restrictive path constraints when the goal is to create a note.
   - Expand `_PROVENANCE_TOOLS` to include `wiki_note_create`, `wiki_note_update`, `wiki_note_organize`, `wiki_note_archive`, `wiki_template_create`, and `wiki_template_update`.
5. **Chat Router Multi-Phase Dedup (`src/web/routers/chat.py`)**:
   - Prune naive prior deliverable concatenation in `execute_goal_job_phases()`. Emit only the definitive outcome.
6. **Granular Skills Architecture (`src/application/agent_packs/schema.py` & `manifest.py`)**:
   - Granular skills declared in `autoreiv` pack and Forge UI:
     - `wiki_tasks` (`wiki_note_read`, `wiki_note_create`, `wiki_note_update`, `wiki_template_read`)
     - `wiki-knowledge` (`wiki_note_search`, `wiki_note_read`, `wiki_note_list`)
     - `wiki-inbox` (`wiki_note_create`, `promote_artifact_to_wiki`)
     - `wiki-curation` (`wiki_note_organize`, `wiki_note_update`, `wiki_note_archive`, `wiki_template_list`, `wiki_template_read`, `wiki_overview`)
7. **Curation Routine Enhancement (`src/application/routines/wiki_curator.py`)**:
   - Add deduplication and archival preservation to inbox graduation.

---

## 4. What Dies Today (Beat 4: The Prune List)

- **PRUNE**: `get_or_create_weekly_note` tool and implementation.
- **PRUNE**: `log_daily_work_item` tool and implementation.
- **PRUNE**: `complete_weekly_task` tool and implementation.
- **PRUNE**: `rollover_weekly_tasks` tool and implementation.
- **PRUNE**: `get_weekly_summary` tool and implementation.
- **PRUNE**: `weekly-notes` tool group in `manifest.py`.
- **PRUNE**: `src/application/skills/weekly_notes_tools.py` source file.
- **PRUNE**: `list_wiki_templates` tool registration and references (canonical: `wiki_template_list`).
- **PRUNE**: `get_wiki_template` tool registration and references (canonical: `wiki_template_read`).
- **PRUNE**: Naive `\n\n---\n\n` prior deliverable concatenation in `src/web/routers/chat.py`.
- **PRUNE**: Restrictive RAG path-constraint injection for creation-intent goals in `wiki_thin_grounding.py`.
- **PRUNE**: Monolithic `wiki` and `tasks` skill directories in `platform-packs/autoreiv/skills/`.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-409-001] Canonical Wiki Note Staging**:
  - *Event-Driven*: WHEN an operator asks an agent to record a note or perform a health check and save it to the wiki, THE SYSTEM SHALL invoke `wiki_note_create` and stage a note into `00_Inbox/` with valid YAML frontmatter, and SHALL NOT append it to a weekly worklog.
- **[REQ-409-002] Single Lever Note Creation**:
  - *Ubiquitous*: THE SYSTEM SHALL provide exactly one tool (`wiki_note_create`) for creating wiki notes and tasks across all packs and skills, with zero shadow weekly creation tools.
- **[REQ-409-003] Intent-Aware Wiki Grounding**:
  - *Event-Driven*: WHEN a job goal indicates note creation or staging, `WikiThinGrounding` SHALL NOT restrict tool execution to historical search hits nor declare newly created notes as "invented paths".
- **[REQ-409-004] Provenanced Path Whitelist Parity**:
  - *Ubiquitous*: THE SYSTEM SHALL recognize paths returned by `wiki_note_create`, `wiki_note_update`, `wiki_note_organize`, `wiki_note_archive`, and `wiki_template_create` as provenanced paths in safety gates.
- **[REQ-409-005] Multi-Phase Output Dedup**:
  - *Ubiquitous*: THE SYSTEM SHALL render a single coherent final deliverable in Chat Studio upon multi-phase job completion, without repeating intermediate phase summaries across `---` dividers.
- **[REQ-409-006] Granular Skill Scoping**:
  - *Ubiquitous*: THE SYSTEM SHALL expose granular skills (`wiki_tasks`, `wiki-knowledge`, `wiki-inbox`, `wiki-curation`) in `AutoReiv` pack and Forge UI.
- **[REQ-409-007] Archive Lever & Version Preservation**:
  - *Event-Driven*: WHEN `wiki_note_archive` is invoked or when `update_wiki_note` is called with `backup_to_archive=True`, THE SYSTEM SHALL move the target note or prior version to `03_Archive/` with timestamped filename and archived status metadata.
- **[REQ-409-008] Canonical Single Lever Tool Naming**:
  - *Ubiquitous*: THE SYSTEM SHALL expose strictly `wiki_template_list` and `wiki_template_read` and SHALL NOT register alias shadow tools `list_wiki_templates` or `get_wiki_template`.
- **[REQ-409-009] Capability Catalog Pruning & Zombie Elimination**:
  - *Ubiquitous*: THE SYSTEM SHALL automatically reconcile and prune obsolete `source="builtin"` capabilities and all `RETIRED_TOOL_NAMES` from `capability_index` on startup, preventing dead or deleted tools from matching in planning prompts.
- **[REQ-409-010] Dotenv Timeout Loading**:
  - *Ubiquitous*: THE SYSTEM SHALL load `.env` during FastAPI startup (`create_app`) and when resolving phase LLM timeouts (`resolve_standing_phase_llm_timeout`), guaranteeing user-configured timeouts (e.g. `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800`) are respected under Uvicorn servers.
- **[REQ-409-011] Capability Catalog Stopword Immunity & Underscore Tokenization**:
  - *Ubiquitous*: THE SYSTEM SHALL filter `ENGLISH_STOPWORDS` from intent and candidate token sets, split underscore-delimited identifiers into constituent tokens (`_TOKEN_RE`), and apply compound match bonuses so substantive keywords dominate over noise words in capability resolution.
- **[REQ-409-012] Chat Options Drawer Interaction Resilience**:
  - *Ubiquitous*: THE SYSTEM SHALL support both positional boolean and object options signatures in `toggleChatOptionsDrawer` and manage `aria-expanded` on `chatOptionsToggleBtn`, guaranteeing clicking `+ Options` toggles the drawer reliably.

---

## 6. Constraints & Verification Plan

### Automated Tests
- `pytest tests/unit/wiki/test_wiki_archive.py`: Verify `archive_note` moves files cleanly to `03_Archive/` with updated metadata, and `backup_to_archive=True` preserves prior versions.
- `pytest tests/unit/skills/test_wiki_tasks.py`: Verify negative assertions for 5 pruned weekly tools and verify task management via canonical wiki tools.
- `pytest tests/unit/orchestration/test_wiki_thin_grounding_creation_intent.py`: Verify creation-intent prompts bypass restrictive grounding path pinning and all provenanced tools pass honesty gates.
- `pytest tests/unit/orchestration/test_chat_multiphase_deliverable_dedup.py`: Verify multi-phase deliverables do not duplicate text across `---`.
- Full regression suite: `uv run pytest tests/unit/` + `npm run test:unit:frontend` + `npm run lint:frontend` + `uv run ruff check src/ tests/`.

### Manual Verification
1. In Chat Studio with `AutoReiv`, send: `"hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"`.
   - Verify: Note lands in `00_Inbox/`, chat response renders once without duplication, and no ungrounded path error occurs.
2. In Chat Studio with `AutoReiv`, test weekly task tracking:
   - Ask AutoReiv: `"create my weekly task note for this week and add a task to review Card 409"`.
   - Verify: Uses `wiki_tasks` runbook + `wiki_note_create` with the weekly template.
