# Requirements Specification: System Observability Live Event Stream, System Agent Root Cause Diagnostics & Librarian Inbox Organization

> **Document ID**: `SPEC-OBS-002`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-OBS-007]`, `[REQ-OBS-008]`, `[REQ-AGENTS-007]`, `[REQ-WIKI-010]`

---

## 1. User Stories

1. **As a** platform operator and user,  
   **I want** to view live system logs and runtime events inside the Observability Studio,  
   **So that** I can inspect gateway calls, tool executions, background ticks, and error traces directly from the browser.

2. **As a** user troubleshooting an agent problem,  
   **I want** the System Agent to have diagnostic tools to inspect recent session errors, transcripts, and probe provider network health,  
   **So that** I can ask it why an agent failed and receive an immediate, actionable root-cause analysis.

3. **As a** user organizing my knowledge vault,  
   **I want** the Librarian Agent to have a dedicated `wiki_note_organize` tool,  
   **So that** it can atomically file staged inbox notes into degree/topic directories and hydrate all YAML frontmatter.

---

## 2. EARS Requirements

### [REQ-OBS-007] In-Memory System Event Logger & REST Log Buffer (Ubiquitous)
The platform SHALL maintain an in-memory thread-safe circular ring buffer of system logs and runtime events (`SystemLogBuffer`) exposed via `GET /api/observability/logs` supporting level filtering (`INFO`, `WARN`, `ERROR`), search queries, and line limits.

### [REQ-OBS-008] Observability Studio Live Event Terminal UI (Ubiquitous)
The Observability Studio SHALL render a real-time terminal console with log level dropdown filter, text search filter, auto-scroll toggle, pause/resume streaming button, and clear log actions.

### [REQ-AGENTS-007] System Agent Diagnostic Skill Pack & Tools (Event-Driven)
WHEN prompted to troubleshoot or inspect system health, the System Agent SHALL utilize diagnostic tools (`get_recent_errors`, `get_session_transcript`, `get_agent_sessions`, `test_provider_connectivity`, `get_system_logs`) to examine recent failures, inspect conversation turns, and test LLM provider connectivity.

### [REQ-WIKI-010] Librarian Inbox Note Triage & Organization Engine (Event-Driven)
WHERE an agent organizes or cleans up a staged inbox note, the Librarian Skill SHALL provide a `wiki_note_organize` tool that atomically moves the note to `notes/<domain>/<topic>/<slug>.md`, hydrates missing YAML metadata, and removes the staged inbox artifact.
