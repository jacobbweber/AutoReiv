# [CARD-007] Responsive Web & Mobile Front-Door with Wiki Export

> **Status**: Completed (Merged to `qa`)  
> **Milestone**: Milestone 7 (v0.7.0)  
> **Primary Component**: `AutoReiv.Web`  
> **Spec Reference**: `docs/specs/responsive-web-interface-and-wiki-export/`  
> **ADR Reference**: [`docs/adr/0008-responsive-web-single-page-app-and-wiki-export.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0008-responsive-web-single-page-app-and-wiki-export.md)  
> **Requirements**: `[REQ-WEB-001]` to `[REQ-WEB-006]`

---

## 1. Why / Intent
Users must be able to interact with all agents and control plane features seamlessly from both Desktop PC and Mobile Phone browsers over the local network. Features must include real-time SSE token streaming, collapsible `<think>` reasoning bubbles, one-click clipboard copying, and instant export of chat threads or individual messages into a local PARA-Wiki markdown structure with YAML frontmatter.

---

## 2. What Was Built
- **FastAPI Control Plane Server (`src/web/app.py`)**: REST and SSE streaming endpoints for chats, sessions, wiki exports, settings matrix, provider endpoints, and routines.
- **`WikiExportService`**: Formats markdown notes with strict YAML frontmatter (`id`, `title`, `agent_id`, `created_at`, `tags`, `category`) and enforces security path jailing within `./data/wiki`.
- **Zero-Build Responsive SPA (`src/web/templates/index.html`, `src/web/static/app.js`)**:
  - Desktop two-column layout + mobile slide-out drawer navigation.
  - Interactive Chat Studio with real-time SSE token streaming and tool badges.
  - Collapsible `<think>` reasoning bubbles.
  - One-Click **"Copy"** and **"Export to Wiki"** action buttons.
  - Routines studio, Observability dashboard, and Settings studio views.

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-WEB-001]`: Real-time SSE chat streaming verified.
- [x] `[REQ-WEB-002]`: Reasoning `<think>` toggle bubbles verified.
- [x] `[REQ-WEB-003]`: One-click PARA-Wiki markdown exporter and path jailing verified.
- [x] `[REQ-WEB-004]`: Unified REST API endpoints verified (`/api/agents`, `/api/settings`, `/api/routines`, `/api/observability`).
- [x] `[REQ-WEB-005]`: Automated unit and integration test suite passing (`tests/unit/web/`).
- [x] `[REQ-WEB-006]`: 100% RTM traceability compliance.
