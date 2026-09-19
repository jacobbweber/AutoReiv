# Requirements Specification: Chat to Wiki Inbox Export & Flat Staging Vault

> **Document ID**: `SPEC-WIKI-INBOX-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-WIKI-007]`, `[REQ-WIKI-008]`, `[REQ-WIKI-009]`

---

## 1. User Story

**As a** user chatting with AutoReiv agents,  
**I want** single message "Save to Wiki" and full conversation "Export to Wiki" actions to create structured notes directly in my Wiki's flat `inbox/` staging folder,  
**So that** my knowledge captures immediately appear in Wiki Studio without folder fragmentation or manual sorting overhead.

---

## 2. EARS Requirements

### [REQ-WIKI-007] Flat Inbox Staging Vault Engine (Ubiquitous)
The `WikiStore` SHALL scaffold and persist all staging notes directly within `data/wiki/inbox/<slug>.md` without `need_to_do`, `should_do`, or `want_to_do` subdirectories, returning all staged notes directly under `tree["inbox"]`.

### [REQ-WIKI-008] Chat-to-Wiki Direct Inbox Artifact Generator (Event-Driven)
WHEN a user triggers "Save to Wiki" on an assistant message OR "Export to Wiki" on a conversation thread, the system SHALL construct a 35-field YAML frontmatter markdown note formatted with conversation turns and persist it directly to `inbox/<slug>.md` via `WikiService`.

### [REQ-WIKI-009] Flat Inbox Tree Navigation & Modal UX (Ubiquitous)
The Wiki Studio explorer SHALL display notes directly under the `inbox (Staging) (X)` folder toggle without priority group partitions, and the New Note modal SHALL simplify inbox creation to a single flat target.
