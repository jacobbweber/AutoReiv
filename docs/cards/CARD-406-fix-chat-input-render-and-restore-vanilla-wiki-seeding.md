---
id: CARD-406
title: "Fix Chat Input Render and Restore Vanilla Wiki Seeding"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:bug
  - area:chat
  - area:wiki
---

# [CARD-406] Fix Chat Input Render and Restore Vanilla Wiki Seeding

> **Status**: Done
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:bug`, `area:chat`, `area:wiki`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

1. **Chat UI Input Visibility**: When a user types and sends a prompt in Chat Studio, the user's message bubble must stay visible in the chat feed above the assistant's streaming answer instead of disappearing.
2. **Vanilla Clean Wiki Seeding**: When AutoReiv is installed clean or the server starts with an empty wiki, it must scaffold strictly the vanilla folder structure (`00_Inbox`, `01_Notes`, `02_Resources/_Templates`, `03_Archive`) populated solely with canonical templates. It must never create an unnumbered `notes` directory and must never pre-populate arbitrary starter notes or pre-filled weekly notes containing fake project tasks.

---

## 2. What AutoReiv Does Now (Beat 2)

1. **Chat Bubble Append**:
   - In `src/web/static/modules/studios/chat.js` line 730:
     ```javascript
     appendMessageBubbleDirect('user', userPrompt, messagesContainer, { activeAgentId, sessionId })
     ```
   - In `src/web/static/modules/studios/chat/render.js` line 394:
     ```javascript
     export function appendMessageBubble(role, content, options = null, { messagesContainer, ... } = {})
     ```
   - `messagesContainer` is passed as the 3rd argument (`options`), but `appendMessageBubble` expects it in the 4th destructuring argument.
   - Line 403 checks `if (!messagesContainer) return null;` which evaluates to `true` and returns `null` immediately without appending the bubble to the DOM.
2. **Rogue Unnumbered `notes/` Folder & Pre-filled Mock Weekly Notes**:
   - In `src/application/skills/weekly_notes_tools.py` line 322:
     ```python
     rel_path = f"notes/weekly/{formatted_week_str}.md"
     full_path = self.wiki_root / rel_path
     full_path.parent.mkdir(parents=True, exist_ok=True)
     ```
     This creates an unnumbered `notes/` folder in the root of the wiki.
   - In `src/domain/wiki/store.py` lines 1553–1555 (`cleanup_vault()`):
     ```python
     ops_worklog = self.root_dir / "notes" / "operations" / "worklog"
     ops_worklog.mkdir(parents=True, exist_ok=True)
     ```
     This also recreates an unnumbered `notes/` folder.
   - In `src/application/skills/weekly_notes_tools.py` lines 33–36:
     `DEFAULT_TEMPLATE` contains hardcoded fake projects (*Server Currency*, *AQS Migration*, *Leaders Life*).
   - In `src/application/routines/matcher.py` lines 239–240:
     `if routine.last_run_at is None: return True`
     On a fresh boot, any routine with `last_run_at is None` (such as `weekly-note-rollover`) fires on the very first scheduler tick (10 seconds after boot), generating weekly notes for the current and prior weeks.
   - In `src/domain/wiki/store.py` lines 585–695:
     `_seed_starter_notes_if_empty()` populates mock notes (`welcome_to_autoreiv.md`, `local_agent_architecture.md`, `telemetry_and_metrics.md`, `librarian_workflow_manual.md`) rather than keeping the vault vanilla with templates only.

---

## 3. What Will Change (Beat 3)

1. **Polymorphic Container Resolution**:
   - In `src/web/static/modules/studios/chat/render.js`:
     Update `appendMessageBubble` to resolve `messagesContainer` polymorphically from either the 3rd argument (if it is an `HTMLElement`) or from the 4th argument options (`extraOptions?.messagesContainer || options?.messagesContainer`).
   - In `src/web/static/modules/studios/chat.js`:
     Pass `messagesContainer` inside the options object:
     ```javascript
     appendMessageBubbleDirect('user', userPrompt, null, {
       messagesContainer,
       activeAgentId: state.selectedAgentId,
       sessionId: state.activeSessionId,
     });
     ```
2. **Strictly Numbered Wiki Structure & Clean Seeding**:
   - In `src/application/skills/weekly_notes_tools.py`:
     - Change weekly notes output path to `01_Notes/weekly/{formatted_week_str}.md`.
     - Completely eliminate creation of `notes/weekly/`.
     - Update candidate lookup paths to look first in `01_Notes/weekly/` and only read from `notes/weekly/` if a legacy file exists without writing to `notes/`.
     - Purge fake projects (*Server Currency*, *AQS Migration*, *Leaders Life*) from `DEFAULT_TEMPLATE`.
     - Update template loader to look in `02_Resources/_Templates/weekly_notes.md`.
   - In `src/domain/wiki/store.py`:
     - Add clean `weekly_notes.md` to `CORE_STRUCTURED_TEMPLATES`.
     - In `scaffold()`: Ensure fresh directory creation is strictly the canonical vanilla structure:
       `00_Inbox`, `01_Notes`, `02_Resources/_Templates`, `03_Archive`.
     - Remove `_seed_starter_notes_if_empty()` so no fake domain notes are created on clean installs.
     - In `cleanup_vault()`: Fix references to use `01_Notes/operations/worklog` and never recreate `notes/`.
   - In `src/application/routines/matcher.py`:
     - Prevent unexecuted routines from firing immediately on boot by initializing `next_run_at = ScheduleMatcher.compute_next_run(r)` during routine seeding or checking.
   - In `src/domain/routines/manifests.py`:
     - Ensure `WEEKLY_NOTE_ROLLOVER_ROUTINE` prompt references `02_Resources/_Templates/weekly_notes.md` instead of obsolete `03_Resources/templates/weekly_notes.md`.

---

## 4. What Dies Today (The Prune List - Beat 4)

1. **`src/application/skills/weekly_notes_tools.py`**:
   - Delete `rel_path = f"notes/weekly/{formatted_week_str}.md"` and all creation of unnumbered `notes/` directories.
   - Delete hardcoded mock projects (*Server Currency*, *AQS Migration*, *Leaders Life*) from `DEFAULT_TEMPLATE`.
   - Delete lookup to obsolete `03_Resources/templates/weekly_notes.md`.
2. **`src/domain/wiki/store.py`**:
   - Delete `_seed_starter_notes_if_empty()` and all calls that pre-fill domain notes into `00_Inbox` or `01_Notes`.
   - Delete `self.root_dir / "notes" / "operations" / "worklog"` creation inside `cleanup_vault()`.
   - Delete `self.root_dir / "01_Notes" / "general" / "notes"` empty directory scaffold.
3. **`src/application/routines/matcher.py`**:
   - Delete `if routine.last_run_at is None: return True` instant-fire behavior on server startup.
4. **`src/domain/routines/manifests.py`**:
   - Delete obsolete `03_Resources/templates/weekly_notes.md` path reference from `WEEKLY_NOTE_ROLLOVER_ROUTINE`.

---

## 5. Acceptance Criteria (EARS Syntax)

- **AC-1 (Ubiquitous)**: THE SYSTEM SHALL keep user prompt bubbles visible in Chat Studio upon sending a message.
- **AC-2 (Event-Driven)**: WHEN `executeChatTurn` is called with a user prompt, THE SYSTEM SHALL append a user message bubble to `messagesContainer` before creating the assistant streaming bubble.
- **AC-3 (Ubiquitous)**: THE SYSTEM SHALL seed new wiki vaults with strictly the canonical numbered structure: `00_Inbox`, `01_Notes`, `02_Resources/_Templates`, and `03_Archive`.
- **AC-4 (Negative Assertion)**: Automated tests shall verify that a freshly seeded wiki contains ZERO markdown files under `00_Inbox/`, ZERO markdown files under `01_Notes/`, and ZERO unnumbered `notes/` directories.
- **AC-5 (Negative Assertion)**: Automated tests shall verify that `weekly_notes_tools` creates weekly notes under `01_Notes/weekly/` and contains ZERO occurrences of "Server Currency", "AQS Migration", or "Leaders Life".
- **AC-6 (Event-Driven)**: WHEN AutoReiv server starts with fresh state, THE SYSTEM SHALL NOT immediately execute the `weekly-note-rollover` routine on the initial tick.

---

## 6. Constraints & Verification Plan

- Run unit tests: `uv run pytest tests/unit/wiki/ tests/unit/skills/test_weekly_notes_tools.py`
- Run fresh wiki seeding test verifying directory layout and template presence.
- Run frontend linter: `npm run lint:frontend`
- Run boundary check: `uv run python .agents/skills/boundary-audit/scripts/boundary_check.py`

---

## Triage closure (2026-09-23)

Marked **Done** on `qa` tip `97c22bd6`. Original intent is shipped and further covered by later Done cards:

- **Chat user bubble stay visible (AC-1/AC-2)**: `appendMessageBubble` in `chat/render.js` resolves `messagesContainer` polymorphically; `chat.js` passes it in the 4th-arg options. Covered/extended by [CARD-415](./CARD-415-chat-studio-transcript-durability-live-equals-refresh.md) (live == refresh durability, action rows, Save to Wiki).
- **Vanilla wiki seeding (AC-3/AC-4)**: numbered `00_Inbox` / `01_Notes` / `02_Resources/_Templates` / `03_Archive`; `_seed_starter_notes_if_empty` is a no-op; tests in `tests/unit/wiki/test_vanilla_wiki_seeding.py`. Empty Notes scrub completed by [CARD-416](./CARD-416-wiki-notes-empty-scrub.md).
- **No fake starter/weekly mock projects (AC-5)**: vanilla tests assert zero `Server Currency` / `AQS Migration` / `Leaders Life`.
- **Cron cold-boot (AC-6)**: CRON path returns `False` when `last_run_at is None` (no instant weekly-note-rollover fire).

**Superseded/covered by CARD-415 and CARD-416** for remaining chat-durability and Notes-empty follow-through. No new Ready follow-up.
