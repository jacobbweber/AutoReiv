# ADR-0028: Live System Observability Log Stream & Agent Diagnostics

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 27 (`CARD-027`)  
> **Requirements**: `[REQ-OBS-007]`, `[REQ-OBS-008]`, `[REQ-AGENTS-007]`, `[REQ-WIKI-010]`

---

## Context
When agents encounter runtime or network issues (e.g. gateway timeouts), the user had no visibility into system logs or runtime events without inspecting background task files. Additionally, the System Agent lacked tools to inspect session transcripts and error logs, and the Librarian lacked a single-step inbox filing tool.

---

## Decision
1. **In-Memory System Event Logger**:
   - Implement `SystemLogBuffer` with a 1,000-entry ring buffer connected to Python's root logger.
   - Expose via `GET /api/observability/logs` and render in a terminal UI in Observability Studio.
2. **System Agent Diagnostic Suite**:
   - Equip `SystemAgentSkill` with tools to query error traces, inspect session history, test provider network connectivity, and tail system logs.
3. **Librarian Inbox Organization Engine**:
   - Add `wiki_note_organize` to move inbox files to `notes/<domain>/<topic>/` with full frontmatter hydration.

---

## Consequences
- Complete transparency and real-time observability across the platform.
- System Agent can diagnose errors directly in chat conversations.
- Librarian can autonomously triage and organize the knowledge vault.
