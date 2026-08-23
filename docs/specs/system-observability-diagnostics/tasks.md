# Tasks Specification: System Observability Live Event Stream & Diagnostics

> **Document ID**: `TASKS-OBS-002`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-OBS-007]`, `[REQ-OBS-008]`, `[REQ-AGENTS-007]`, `[REQ-WIKI-010]`

---

## Vertical Slices

- [ ] **Slice 1: In-Memory System Event Logger & REST Log Buffer**
  - [ ] Task 1.1: `[REQ-OBS-007]` Implement `SystemLogBuffer` in `src/application/observability/log_buffer.py` and attach to Python logging.
  - [ ] Task 1.2: `[REQ-OBS-007]` Implement `GET /api/observability/logs` in `src/web/app.py`.
  - [ ] Task 1.3: `[REQ-OBS-007]` Add unit tests in `tests/unit/observability/test_log_buffer.py`.

- [ ] **Slice 2: Observability Studio Live Event Terminal UI**
  - [ ] Task 2.1: `[REQ-OBS-008]` Add Live Log Terminal section with level filtering and search to `index.html`.
  - [ ] Task 2.2: `[REQ-OBS-008]` Add auto-polling/rendering logic for logs in `app.js`.

- [ ] **Slice 3: System Agent Diagnostic Tooling & Skill Pack**
  - [ ] Task 3.1: `[REQ-AGENTS-007]` Add `get_recent_errors`, `get_session_transcript`, `get_agent_sessions`, `test_provider_connectivity`, and `get_system_logs` to `SystemAgentSkill`.
  - [ ] Task 3.2: `[REQ-AGENTS-007]` Register tools and update System Agent profile in `src/domain/agents/profiles.py`.
  - [ ] Task 3.3: `[REQ-AGENTS-007]` Add unit tests in `tests/unit/skills/test_system_agent_skill.py`.

- [ ] **Slice 4: Librarian Inbox Note Triage & Organization Engine**
  - [ ] Task 4.1: `[REQ-WIKI-010]` Add `organize_note()` to `WikiStore` and `wiki_note_organize` to `LibrarianSkill`.
  - [ ] Task 4.2: `[REQ-WIKI-010]` Update Librarian profile system prompt with inbox triage instructions.
  - [ ] Task 4.3: `[REQ-WIKI-010]` Add unit tests in `tests/unit/skills/test_librarian_skill.py`.
  - [ ] Task 4.4: `[REQ-OBS-007]` Run pre-flight DoD quality gates.
