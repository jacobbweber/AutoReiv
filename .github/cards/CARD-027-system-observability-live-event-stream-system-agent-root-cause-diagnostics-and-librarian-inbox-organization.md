# [CARD-027] System Observability Live Event Stream, System Agent Root Cause Diagnostics and Librarian Inbox Organization

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/system-observability-diagnostics/`
> **Labels**: `type:feature`, `milestone:27`, `domain:observability`

---

_Parked 2026-08-29 board hygiene. Not in flight. Observability studio exists; leftover diagnostics stay here._

## 1. Why / Intent
1. When an agent experiences a runtime issue (such as an LLM gateway timeout or network disconnect), users have no visual way to inspect server logs, events, and stack traces inside the UI.
2. The System Agent lacked diagnostic tools to inspect recent session errors, transcripts, or probe LLM endpoints, preventing it from root-causing user-reported issues.
3. The Librarian Agent lacked a single-step `wiki_note_organize` tool to move staged inbox files into `notes/<domain>/<topic>/` while hydrating YAML frontmatter.

---

## 2. What to Build
1. **Live App Logs & Event Stream Engine (`[REQ-OBS-007]`, `[REQ-OBS-008]`)**:
   - `SystemLogBuffer` in-memory circular log ring buffer capturing server logs, gateway events, tool calls, and error traces.
   - REST endpoints: `GET /api/observability/logs` and `POST /api/observability/logs/clear`.
   - UI Terminal in Observability Studio with log level filter (`ALL`, `INFO`, `WARN`, `ERROR`), search filter, pause/resume, and auto-scroll.
2. **System Agent Diagnostic Tooling & Skill Pack (`[REQ-AGENTS-007]`)**:
   - Upgrade `SystemAgentSkill` with tools:
     - `get_recent_errors(limit, agent_id)`
     - `get_session_transcript(session_id, agent_id, limit)`
     - `get_agent_sessions(agent_id, limit)`
     - `test_provider_connectivity(provider_id, host_url)`
     - `get_system_logs(lines, level)`
   - Update System Agent system prompt for proactive troubleshooting.
3. **Librarian Inbox Triage & Organization Engine (`[REQ-WIKI-010]`)**:
   - Add `wiki_note_organize(source_path, target_domain, target_topic, document_type, summary, tags)` to `LibrarianSkill` and `WikiStore`.
   - Update Librarian prompt with explicit instructions on inbox triage.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-OBS-007]`: Server maintains in-memory circular log ring buffer with level filtering and REST endpoint `GET /api/observability/logs`.
- [ ] `[REQ-OBS-008]`: Observability Studio renders real-time terminal log viewer with search, level filters, and pause toggle.
- [ ] `[REQ-AGENTS-007]`: System Agent possesses diagnostic tools to inspect errors, transcripts, system logs, and test provider connectivity.
- [ ] `[REQ-WIKI-010]`: Librarian Agent possesses `wiki_note_organize` tool to atomically move notes from `inbox/` to `notes/<domain>/<topic>/` with full frontmatter hydration.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing passing tests.
- Single isolated branch cut from `qa`.
