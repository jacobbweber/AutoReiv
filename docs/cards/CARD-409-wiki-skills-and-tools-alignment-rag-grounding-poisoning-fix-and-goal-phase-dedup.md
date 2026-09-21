---
id: CARD-409
title: "Wiki Skills and Tools Alignment, RAG Grounding Poisoning Fix, and Goal Phase Dedup"
status: Ready
created: 2026-09-21
adr: none
labels:
  - type:bug
  - type:refactor
  - area:wiki
  - area:orchestration
  - area:agents
  - area:ux
---

# [CARD-409] Wiki Skills and Tools Alignment, RAG Grounding Poisoning Fix, and Goal Phase Dedup

> **Status**: Ready  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:bug`, `type:refactor`, `area:wiki`, `area:orchestration`, `area:agents`, `area:ux`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

When Jacob asks AutoReiv:
> *"hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"*

The experience should be fast, crisp, and high quality:
1. **Canonical Wiki Note Intake**: AutoReiv should inspect system health telemetry and save a clean, well-formatted standalone note to the Wiki via `wiki_note_create` into `00_Inbox/` (the One-Door staging policy). It should NOT hijack Jacob's personal weekly calendar worklog (`01_Notes/weekly/2026-Wxx.md`).
2. **Clear Separation Between Wiki Knowledge Vault & Weekly Worklogs**:
   - `wiki` skill tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_search`, etc.) manage knowledge documentation, atomic notes, runbooks, and reports.
   - `tasks` skill tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`) manage daily operator check-ins and to-do carryover.
   AutoReiv must never confuse saving a general note to the wiki with appending a task checkbox to a weekly worklog.
3. **No RAG Grounding Poisoning**:
   When an operator requests *creating* a new artifact or saving a note, the system must not pre-query the vault, pull up unrelated historical files (such as `2026-W35.md`), and inject a hard prompt constraint claiming: *"Allowed grounding paths: `01_Notes/weekly/2026-W35.md`... Never invent Wiki paths... If you need sources not in the allowed list, park"*. This constraint poisons the LLM's attention and forces it to write to whatever random historical file was retrieved.
4. **No Chat Output Duplication (Single Voice / Single Message)**:
   The multi-phase goal runner must not concatenate Phase 0 (Formulate) and Phase 1 (Execute) deliverables together with `\n\n---\n\n`, repeating the same 30-line status summary 3 to 4 times in a single assistant bubble.
5. **Fast & High Quality**:
   Executing a health telemetry collection and staging a wiki note should take 1 to 2 concise turns (under 10 seconds total), not multiple minutes across redundant multi-phase loops.

---

## 2. What AutoReiv Does Now (Beat 2: Detailed Deep Dive of Recent Sessions)

A forensic audit of the two recent chat sessions (`job_6d52efca00ae` and `job_dbfed34b2810`) in `autoreiv.db` revealed the exact chain of failures:

### Attempt 1: Nemotron Lightning
1. **RAG Search Injection**: Before Phase 0 ran, `WikiThinGrounding` ran a keyword search for `"hi you do system health check then save"`. It matched `01_Notes/weekly/2026-W35.md`, `02_Resources/_Templates/sop-runbook.md`, and `tag-authority.md`.
2. **Grounding Trap**: It injected into the LLM system context:
   `Allowed grounding paths: 01_Notes/weekly/2026-W35.md`
   `Never invent Wiki paths or titles. Do not claim a note path unless wiki_note_read or wiki_note_create returned it in this Job.`
3. **Docstring Bias**: In `src/application/skills/weekly_notes_tools.py`, `get_or_create_weekly_note` had the parameter description:
   `"week_str": "Optional ISO week identifier like '2026-W35'. Defaults to current week."`
4. **Model Behavior**: Nemotron saw that `01_Notes/weekly/2026-W35.md` was the only "allowed" path, saw the tool parameter example `'2026-W35'`, and called `get_or_create_weekly_note("2026-W35")` and `log_daily_work_item("2026-W35", ...)`! It appended an ugly task checkbox into an old August week (`2026-W35.md`), completely bypassing `00_Inbox/`.

### Attempt 2: Alternative Model
1. **Same Grounding Trap**: The system again injected `hit_paths=['01_Notes/weekly/2026-W35.md', ...]`.
2. **Model Attempt to Self-Correct**: The model noticed that W35 was in the past and current week was W39. However, because `get_or_create_weekly_note` was positioned as the primary "note" tool, it called `get_or_create_weekly_note()` and `log_daily_work_item("2026-W39", ...)` into `01_Notes/weekly/2026-W39.md`.
3. **Safety Policy Rejection**: In `src/application/orchestration/wiki_thin_grounding.py`, line 367 only considers paths from `wiki_note_create` or `wiki_note_read` as provenanced. It did not recognize `get_or_create_weekly_note`!
4. **Fail-Closed Honesty Gate**: The job completed, but the post-job honesty gate overrode the output with:
   `"Not done — ungrounded Wiki path claim. Job job_dbfed34b2810. Invented/unprovenanced path(s): '01_Notes/weekly/2026-W39.md'. Tool-provenanced paths this Job: (none). Fail-closed [CARD-260]: Chat may only claim paths from wiki_note_create/read."`
5. **Chat Message Stuttering / Quadruplication**:
   In `src/web/routers/chat.py` lines 1205–1208:
   ```python
   if completed_deliverables and final_content:
       filtered_priors = [d for d in completed_deliverables if d.strip() != final_content.strip()]
       if filtered_priors:
           final_content = "\n\n---\n\n".join(filtered_priors) + f"\n\n---\n\n{final_content}"
   ```
   Phase 0 (Formulate) executed tools and emitted a complete summary deliverable.
   Phase 1 (Execute) executed tools and emitted a second complete summary deliverable.
   Lines 1205–1208 joined Phase 0 + Phase 1 + Final Honesty Block together, dumping 4 duplicate summaries into the user's chat bubble!

---

## 3. What Will Change (Beat 3)

1. **Disambiguate Wiki Vault vs. Weekly Notes Primitives**:
   - In `src/application/skills/weekly_notes_tools.py`, update tool descriptions and parameter docstrings:
     - Clarify that `get_or_create_weekly_note` and `log_daily_work_item` are exclusively for *personal daily worklogs and to-do carryover*, NOT general note creation.
     - Remove the hardcoded `'2026-W35'` example string from the docstrings.
   - In `platform-packs/autoreiv/pack.json` and system prompts:
     - Explicitly state: When asked to save a note, record a report, or capture information to the Wiki, ALWAYS use `wiki_note_create` to stage the note into `00_Inbox/`. Only use `log_daily_work_item` when the user explicitly asks to log a daily task or update their weekly review.
2. **Context-Aware Wiki Thin Grounding**:
   - In `src/application/orchestration/wiki_thin_grounding.py`:
     - Distinguish between **Knowledge Retrieval** requests (asking questions about existing notes) and **Creation / Staging** requests ("save note", "create note", "write note").
     - When the goal contains creation/staging intent, do NOT inject restrictive "allowed grounding paths" constraints that forbid creating novel notes.
     - Add `get_or_create_weekly_note`, `log_daily_work_item`, and `wiki_note_create` to recognized provenanced path collectors so that legitimate tool outputs are never flagged as "invented paths".
3. **Eliminate Multi-Phase Output Concatenation Duplication**:
   - In `src/web/routers/chat.py`:
     - Remove the naive `\n\n---\n\n.join(filtered_priors)` deliverable concatenation in `execute_goal_job_phases()`.
     - Deliverable emission must present only the definitive outcome or an explicit unified synthesis—never a raw concatenation of every prior phase's intermediate working notes.
4. **Structured Health Check Wiki Note Template**:
   - Provide a clean, dedicated frontmatter template for platform health pulses (`00_Inbox/system_health_<timestamp>.md`) so the resulting wiki note has high quality, clean tables, and proper metadata rather than an ugly single-line task checkbox.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **PRUNE**: Rigid `\n\n---\n\n` deliverable concatenation in `src/web/routers/chat.py` lines 1205–1208.
- **PRUNE**: Hardcoded `'2026-W35'` docstring example from `weekly_notes_tools.py`.
- **PRUNE**: Creation-blocking RAG constraint injection in `wiki_thin_grounding.py` for note-creation intents.
- **PRUNE**: Exclusion of weekly notes tools from `wiki_thin_grounding.py` provenanced path resolution.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-409-001] Canonical Wiki Note Creation for Health Pulses**:
  - *Event-Driven*: WHEN an operator asks AutoReiv to perform a health check and save it to the wiki, THE SYSTEM SHALL invoke `wiki_note_create` and stage a structured note into `00_Inbox/` with valid YAML frontmatter, and SHALL NOT append it as a to-do item in a weekly worklog.
- **[REQ-409-002] Intent-Aware Wiki Grounding**:
  - *Event-Driven*: WHEN a job goal indicates note creation or staging, `WikiThinGrounding` SHALL NOT restrict tool execution to historical search hits nor declare newly created notes as "invented paths".
- **[REQ-409-003] Provenanced Path Whitelist Parity**:
  - *Ubiquitous*: THE SYSTEM SHALL recognize paths returned by `wiki_note_create`, `wiki_note_read`, and `get_or_create_weekly_note` as provenanced paths in safety gates.
- **[REQ-409-004] Multi-Phase Output Dedup**:
  - *Ubiquitous*: THE SYSTEM SHALL render a single coherent final deliverable in Chat Studio upon multi-phase job completion, without repeating intermediate phase summaries across `---` dividers.
- **[REQ-409-005] Weekly Notes Tool Clarification**:
  - *Ubiquitous*: THE SYSTEM SHALL provide tool docstrings in `weekly_notes_tools.py` that describe daily task logging without hardcoded historical week examples (`2026-W35`).

---

## 6. Constraints & Verification Plan

### Automated Tests
- `pytest tests/unit/wiki/test_wiki_thin_grounding_creation_intent.py`: Verify creation-intent prompts bypass restrictive RAG grounding constraints.
- `pytest tests/unit/orchestration/test_chat_multiphase_deliverable_dedup.py`: Verify multi-phase deliverables are not duplicated via `\n\n---\n\n`.
- `pytest tests/unit/skills/test_weekly_notes_provenanced_paths.py`: Verify `get_or_create_weekly_note` paths are accepted by honesty gates.
- Full regression suite: `uv run pytest tests/unit/` + `npm run test:unit:frontend` + `npm run lint:frontend` + `uv run ruff check src/ tests/`.

### Manual Verification
- In Chat Studio with `AutoReiv`, send: `"hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"`.
- Verify:
  1. A standalone note is created in `00_Inbox/` (e.g. `00_Inbox/system_health_check_...md`).
  2. The weekly note (`01_Notes/weekly/2026-Wxx.md`) is NOT hijacked.
  3. The chat response is rendered once, cleanly, without repetition or `---` duplicate sections.
  4. The job succeeds cleanly without ungrounded path error banners.
