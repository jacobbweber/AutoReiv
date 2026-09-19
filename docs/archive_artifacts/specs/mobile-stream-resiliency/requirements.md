# Requirements: Mobile Stream Resiliency & Goal Markdown Synthesis

## 1. Introduction
This specification defines requirements for robust background execution decoupling, mobile tab reconnection synchronization, and structured Markdown deliverable synthesis for AutoReiv's Chat and Goal execution subsystems.

---

## 2. EARS Requirements

### [REQ-MOB-STREAM-001] Asynchronous Background Task Shielding
- **EARS Type**: Event-Driven
- **Requirement**: *When a client disconnects or aborts an active /api/chat/stream connection, the system SHALL ensure the underlying turn execution (Goal Mode, Reflexion, or standard kernel turn) continues in the background and saves the final assistant deliverable to SQLite.*

### [REQ-MOB-STREAM-002] Mobile Tab Visibility & Reconnection Sync
- **EARS Type**: Event-Driven
- **Requirement**: *When the user returns to the Chat Studio tab (document.visibilitychange or window.focus), the system SHALL inspect whether a background turn was in flight or interrupted, re-synchronize messages from /api/chat/sessions/{id}/messages, and gracefully restore the conversation thread without wiping existing bubbles.*

### [REQ-MOB-STREAM-003] Guaranteed Rich Markdown Synthesis
- **EARS Type**: Ubiquitous
- **Requirement**: *When the Goal Mode planning engine synthesizes the final deliverable, the system SHALL inject strict Markdown formatting directives (headers, summary tables, bulleted action items, checklists) and explicit negative constraints against raw JSON objects or code blocks.*

### [REQ-MOB-STREAM-004] Graceful JSON-to-Markdown Fallback Parser
- **EARS Type**: Optional
- **Requirement**: *When an assistant message content is received as a raw JSON string containing structured keys (goal, ction_plan, steps, summary), the system SHALL automatically format and parse it into human-readable Markdown with styled sections.*
