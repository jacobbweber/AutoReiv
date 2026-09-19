# Technical Design Specification: Chat to Wiki Inbox Export & Flat Staging Vault

> **Document ID**: `DESIGN-WIKI-INBOX-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-WIKI-007]`, `[REQ-WIKI-008]`, `[REQ-WIKI-009]`

---

## 1. Architectural Overview

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant ChatUI as Chat Interface (app.js)
    participant API as FastAPI Router (app.py)
    participant WikiSvc as WikiService (service.py)
    participant Store as WikiStore (store.py)
    participant Vault as Flat Inbox Vault (data/wiki/inbox/)

    User->>ChatUI: Clicks "Save to Wiki" / "Export to Wiki"
    ChatUI->>API: POST /api/export/wiki { title, content/messages, agent_id, category: "inbox", tags: [...] }
    API->>WikiSvc: file_note(title, content, category="inbox", tags, ...)
    WikiSvc->>Store: file_note()
    Store->>Vault: Writes data/wiki/inbox/<slug>.md with 35-field frontmatter
    Store-->>API: { success: true, path: "inbox/<slug>.md", title: "...", uid: "..." }
    API-->>ChatUI: { status: "success", filepath: "inbox/<slug>.md", ... }
    ChatUI->>ChatUI: Flashes "Saved to Wiki!"
    Note over User,Vault: In Wiki Studio tab
    User->>ChatUI: Opens [📚 Wiki Studio]
    ChatUI->>API: GET /api/wiki/tree
    API->>Store: get_tree()
    Store-->>ChatUI: { inbox: [ { path: "inbox/<slug>.md", title: "..." } ], notes: {...}, resources: {...} }
    ChatUI->>ChatUI: Renders flat list in inbox (Staging) (1)
```

---

## 2. Directory Structure Changes

```text
data/wiki/
├── inbox/                        <-- Flat staging folder (NO subfolders)
│   ├── note_1.md
│   └── chat_export_20260823.md
├── notes/                        <-- Degree / Class Knowledge Base
│   └── information_technology/
│       └── ai_engineering/
│           └── agent_memory.md
└── resources/
    ├── operating_manuals/
    └── templates/
```
