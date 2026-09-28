# [CARD-173] Platform-Owned PARA-Wiki Architecture, Scheduled Curation Routine, and Deterministic Vault

> **Status**: Done
> **Created**: 2026-09-06
> **Spec Reference**: docs/specs/wiki/; CARD-125; CARD-141; CARD-148
> **Labels**: `type:architecture`, `type:feat`, `AutoReiv.Wiki`, `AutoReiv.Routines`, `AutoReiv.Web`, `AutoReiv.Agents`

---

## 1. Why / Intent

Jacob established the locked vision for the AutoReiv Wiki:

1. **Single Platform-Owned System**:
   - Standardize exclusively on **Jacob's PARA-Wiki** (no external frameworks or multi-provider switchers).
   - The Wiki is owned by the AutoReiv platform, not an individual agent.
2. **Per-Agent Access Control**:
   - Agent Studio provides an explicit toggle (`allow_wiki_access`) to grant or deny Wiki access per agent.
3. **The Hybrid Folder Hierarchy**:
   - `00_Inbox/`: The single drop-zone where all raw notes land first (human or AI).
   - `01_Notes/<domain>/<topic>/`: The permanent 2-depth warehouse (`domain` = Degree field, `topic` = Course/Subject). No `projects` folder.
   - `02_Resources/`: Reusable templates (`02_Resources/_Templates/`) and operating manuals (`02_Resources/operating_manuals/`).
   - `03_Archive/`: Retired or superseded notes.
4. **Two-Tier Frontmatter Schema**:
   - **Staging Schema (`00_Inbox/`)**: 10 essential fields (`uid`, `title`, `document_type`, `summary`, `domain`, `topic`, `tags`, `status: "inbox"`, `author`, `date_created`, `schema_version`). Fast, zero-friction capture without hallucinated fields.
   - **Graduated Schema (`01_Notes/`)**: Full 27-key deterministic metadata added during curation (`content_hash`, `word_count`, `context_tokens`, `parent`, `related`, `moc`, `supersedes`, `superseded_by`, `confidence_score`, `priority`, `sensitivity`, `last_updated`).
5. **Verbatim Body Rule (Content Protection)**:
   - The curation routine scrubs AI conversational preambles/sign-offs and validates metadata, but **never rephrases, summarizes, or deletes human technical content**. Technical bodies are preserved verbatim.
6. **Tag Authority (Check First, Invent & Register If Needed)**:
   - Maintains a canonical dictionary in `02_Resources/_Templates/tag-authority.md`.
   - The routine checks existing tags first and normalizes variants (e.g. `#sys-admin` &rarr; `#sysadmin`).
   - If a genuinely new topic emerges, the routine coins a clean, lowercase `snake_case` tag and automatically registers it into `tag-authority.md`.
7. **Scheduled & On-Demand Curation Routine (`WikiCurationRoutine`)**:
   - Background routine in `AutoReiv.Routines` (runs on schedule or via `[⚡ Curate Inbox Now]` in Wiki Studio).
   - Validates frontmatter, matches templates from `02_Resources/_Templates/`, checks `01_Notes/` for duplicate or append candidates, scrubs conversational fluff, and graduates the note to `01_Notes/<domain>/<topic>/<slug>.md`.
8. **Dual-Zone Note Search**:
   - Note search and lookup tools search across **both** `00_Inbox/` and `01_Notes/` with summary-first token efficiency.

---

## 2. What Jacob Sees & Controls (UI / UX)

### Agent Studio (`#viewAgentStudio`):
- **Per-Agent Wiki Access Toggle**:
  - `[x] Allow Wiki Access` (`#forgeAllowWikiAccessCheckbox`) under Card 4/5.
  - Controls whether the agent has access to `wiki_note_search`, `wiki_note_read`, `wiki_note_create`, `wiki_note_append`.

### Settings & Routines (`#viewSettings`):
- **Wiki Vault Path**: Configuration for `%LOCALAPPDATA%\AutoReiv\wiki\` or custom path.
- **Wiki Curation Routine**: Visible under Routines dashboard, scheduled to run daily or triggerable on demand.

### Wiki Studio (`#viewWiki`):
- Navigation tree reflecting:
  - `00_Inbox/` (staged notes waiting for curation).
  - `01_Notes/<domain>/<topic>/` (curated knowledge warehouse).
  - `02_Resources/` (templates and operating manuals).
  - `03_Archive/` (retired notes).
- **`[⚡ Curate Inbox Now]` Action**: Button in the toolbar to run the curation routine immediately.

---

## 3. Core Architecture & Primitives

```
+-----------------------------------------------------------------------------+
|                            AutoReiv Control Plane                           |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |                          Platform PARA-Wiki                           |  |
|  |                                                                       |  |
|  |  00_Inbox/ ---------------------------------------------------+       |  |
|  |  (All new captures land here with 10-field staging schema)     |       |  |
|  |                                                               |       |  |
|  |  +---------------------------------------------------------+  |       |  |
|  |  |           Autonomous Background Curation Routine        |  |       |  |
|  |  |  1. Validate YAML frontmatter (10-field staging)        |  |       |  |
|  |  |  2. Select canonical template from 02_Resources/       |  |       |  |
|  |  |  3. Check 01_Notes/ for existing/duplicate notes        |  |       |  |
|  |  |  4. Tag Authority: check first, invent & register new  |  |       |  |
|  |  |  5. Verbatim Rule: scrub fluff, preserve technical body |  |       |  |
|  |  |  6. Graduate & move to 01_Notes/ (27-field metadata)    |  |       |  |
|  |  +---------------------------------------------------------+  |       |  |
|  |                               |                               |       |  |
|  |                               v                               |       |  |
|  |  01_Notes/<domain>/<topic>/ <---+                             |       |  |
|  |  (Permanent 2-depth warehouse)                                |       |  |
|  |                                                               |       |  |
|  |  02_Resources/_Templates/tag-authority.md                     |       |  |
|  |  03_Archive/                                                  |       |  |
|  +-----------------------------------------------------------------------+  |
|                                     |                                       |
|                    Dual-Zone Search & Read Tools                            |
|             (Searches both 00_Inbox/ and 01_Notes/)                         |
|                                     |                                       |
|                   Per-Agent Access Gate [allow_wiki_access]                 |
|                                     |                                       |
|          +--------------------------+--------------------------+            |
|          |                                                     |            |
|  Platform: Assistant [x]                               User Pack: Hyper-V [ ] |
+-----------------------------------------------------------------------------+
```

1. **`WikiStore` (`src/domain/wiki/store.py`)**:
   - Enforces the folder convention: `00_Inbox/`, `01_Notes/`, `02_Resources/`, `03_Archive/`.
   - `file_note()`: Writes all new captures directly into `00_Inbox/` with initial staging YAML frontmatter.
   - `search_notes()`: Searches across both `00_Inbox/` and `01_Notes/`, returning summary snippets first.
2. **Fluff Scrubber (`clean_note_content`)**:
   - Regex/AST filter that strips conversational chatter ("Sure thing!", "Here is your note:", emojis, sign-offs) while preserving all code blocks and technical content verbatim.
3. **Tag Authority (`02_Resources/_Templates/tag-authority.md`)**:
   - Canonical tag list; routine checks and normalizes existing tags, and appends genuinely new tags in lowercase `snake_case`.
4. **`WikiCurationRoutine` (`src/application/routines/wiki_curator.py`)**:
   - Autonomous routine in `AutoReiv.Routines`.
   - Processes notes in `00_Inbox/`, inspects domain/topic, deduplicates against `01_Notes/`, applies template, enriches frontmatter to 27 keys, and graduates the note to `01_Notes/<domain>/<topic>/`.
5. **`wiki` Platform Skill (`SKILL.md`)**:
   - Operating manual guiding agents on search-before-read, 2-depth naming, and inbox filing.

---

## 4. Acceptance Criteria

- [x] [REQ-WIKI-010] Vault scaffold updated to `00_Inbox/`, `01_Notes/`, `02_Resources/`, and `03_Archive/`.
- [x] [REQ-WIKI-011] `file_note()` enforces the one-door policy: all new notes land in `00_Inbox/` with 10-field staging frontmatter.
- [x] [REQ-WIKI-012] Pre-write fluff scrubber purges conversational preamble and sign-offs while preserving technical content verbatim.
- [x] [REQ-WIKI-013] Note search and listing tools search across both `00_Inbox/` and `01_Notes/`, returning title + 2-sentence summary first.
- [x] [REQ-WIKI-014] Background `WikiCurationRoutine` implemented: validates frontmatter, deduplicates, conforms to templates, and graduates notes to `01_Notes/<domain>/<topic>/`.
- [x] [REQ-WIKI-015] Tag Authority policy implemented: check-first, normalize variants, and register new legitimate tags to `02_Resources/_Templates/tag-authority.md`.
- [x] [REQ-WIKI-016] Wiki Studio provides `[⚡ Curate Inbox Now]` button connected to the routine trigger endpoint.
- [x] [REQ-WIKI-017] Agent Studio provides `allow_wiki_access` toggle, persisted in `pack.json` and agent profiles.
- [x] [REQ-WIKI-018] Existing notes in `data/wiki/` migrated cleanly to the new folder structure without data loss.
- [x] [REQ-WIKI-019] Full unit and frontend tests pass cleanly with zero lint errors.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Do not add Google OKF or multi-provider switchers; Jacob's PARA-Wiki is the single standard.
- Work strictly on local `qa` branch.
