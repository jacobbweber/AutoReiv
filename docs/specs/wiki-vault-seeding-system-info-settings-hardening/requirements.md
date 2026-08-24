# Requirements: Wiki Vault Seeding, System Info Resiliency & Settings Matrix Hardening

## User Stories & EARS Acceptance Criteria

### [REQ-WIKI-011] Starter Knowledge Seeding & Vault Tree Dynamic Expansion
- **Precondition**: When `WikiStore.scaffold()` runs and `data/wiki` has zero notes on disk.
- **Trigger**: The system shall seed starter knowledge notes across inbox (`inbox/welcome_to_autoreiv.md`), notes (`notes/computer_science/artificial_intelligence/local_agent_architecture.md`, `notes/systems_engineering/observability/telemetry_and_metrics.md`), and resources (`resources/operating_manuals/librarian_workflow_manual.md`, `resources/templates/standard_note_template.md`).
- **Response**: The system shall dynamically auto-expand all active domain and topic folders whenever new notes are created or refreshed, allowing instant discovery of all files and folders.

### [REQ-WIKI-012] Mind Map 2D Canvas Reflow & Mermaid Graph Resilience
- **Precondition**: When the user opens the Mind Map (`#wikiMindMapModal`) or Knowledge Graph (`#wikiGraphModal`).
- **Trigger**: The system shall calculate canvas dimensions via `requestAnimationFrame` after container reflow, render node hover halos with valid 2D alpha blending on hex colors, sanitize Mermaid graph IDs with underscore identifiers (`wiki_graph_12345`), and support backdrop/Escape dismissals.

### [REQ-SYST-004] System Info Default Topic Hydration & Visual Error Recovery
- **Precondition**: When the user opens the System Info Studio (`#view-docs`).
- **Trigger**: The system shall pre-render topic categories and auto-load the default architectural overview (`platform-overview`), ensuring the documentation browser is instantly populated and never blank.

### [REQ-SET-009] Resilient Model Discovery Fallbacks & Atomic Matrix Persistence
- **Precondition**: When `/api/models/discover` is queried while a provider is offline or unreachable.
- **Trigger**: The system shall catch provider connection errors and return preset recommended catalog models (`llama3.2:1b`, `llama3.2:3b`, `qwen2.5-coder:7b`, `gpt-4o`, `claude-3-5-sonnet`) with offline status notes, preventing 500/503 errors and ensuring the model picker dropdown is always populated.
- **Response**: `POST /api/settings/matrix` shall accept both nested `purposes` dictionaries and flat purpose mappings, ensuring model selections persist reliably in SQLite.
