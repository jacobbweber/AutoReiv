# Technical Architecture & Design: Prune Legacy System Architect CoPilot from Agent Forge Studio

## 1. Context & Architecture Overview

Before Refactor:
```
+-------------------------------------------------------------------------------+
| AGENT FORGE STUDIO                                                            |
| +------------------------------------+--------------------------------------+ |
| | Character Sheet Cards (7-8 cols)   | System Architect Co-Pilot (4-5 cols) | |
| |  - Identity & Persona              |  - Co-Pilot Message Stream           | |
| |  - System Prompt                   |  - Starter Prompt Chips              | |
| |  - Skill Scopes & Tools            |  - Prompt Input Bar                  | |
| |  - Telemetry & Routines            |  - POST /api/chat/stream (system-agt)| |
| +------------------------------------+--------------------------------------+ |
+-------------------------------------------------------------------------------+
```

After Refactor:
```
+-------------------------------------------------------------------------------+
| AGENT FORGE STUDIO                                                            |
| +---------------------------------------------------------------------------+ |
| | Character Sheet Container (Full Width / max-w-6xl mx-auto)                | |
| |  - ROW 1: Identity & Avatar (col-1) | Persona & Tone (col-2)               | |
| |  - ROW 2: Operating Manual & Constitution (System Prompt)                 | |
| |  - ROW 3: Authorized Skill Capabilities (RBAC Scope with MCP Server Packs)| |
| |  - ROW 4: Agent Telemetry & Lifetime Stats                                | |
| |  - ROW 5: Assigned Background Routines                                    | |
| +---------------------------------------------------------------------------+ |
+-------------------------------------------------------------------------------+
```

---

## 2. Component Design & Changes

### 2.1 HTML Template (`src/web/templates/index.html`)
- Remove the Co-Pilot column entirely (`#copilotMessages`, `#copilotForm`, `#copilotInput`, `#applyBlueprintBtn`, `.copilot-chip`).
- Change the outer workspace container from `grid grid-cols-1 lg:grid-cols-12` to a clean `flex-1 overflow-y-auto p-4 md:p-6 space-y-4 max-w-6xl mx-auto w-full`.

### 2.2 JavaScript Module (`src/web/static/modules/studios/forge.js`)
- Remove Co-Pilot DOM element references (`copilotForm`, `copilotInput`, `copilotMessages`, `applyBlueprintBtn`, `copilotChips`).
- Remove `activeBlueprint` state and Co-Pilot streaming submission handler.
- Keep agent profile loading, editing, avatar selection, tone selection, purpose matrix, skill pack toggle, routine assignment, and save/delete lifecycle intact.

---

## 3. UI ASCII Wireframe

```text
+-----------------------------------------------------------------------------------------------+
| Agent Forge Studio  [RPG Character Sheet]                                                      |
| [ Assistant (Built-in) v ]                    [ + New Agent ]       [ 💾 Save Profile ]        |
+-----------------------------------------------------------------------------------------------+
| 🆔 Identity & Avatar                       | 🎭 Persona & Tone                                |
| Name: [ Assistant                        ] | Tone   : [ Concise (Direct & punchy)           ] |
| Slug: [ assistant                        ] | Purpose: [ General (Daily workflow coordinator)] |
| Icon: [ 🤖 bot (Assistant)             v ] | Model  : [ Inherit from Purpose Slot           ] |
+-----------------------------------------------------------------------------------------------+
| 📜 Operating Manual & Constitution (System Prompt)                                            |
| [ You are AutoReiv's primary general-purpose assistant...                                   ] |
+-----------------------------------------------------------------------------------------------+
| 🧰 Authorized Skill Capabilities (RBAC Scope)                                                 |
| [x] Core System Tools (delegate_task, system_info) - [📌 Pinned]                              |
| [x] Wiki Knowledge Pack (wiki_note_create, wiki_note_read)                                    |
| [x] MCP: github-tools (create_issue, get_repo)                                                |
+-----------------------------------------------------------------------------------------------+
| 📊 Agent Telemetry & Lifetime Stats                                                           |
| Turns: 42  |  Tokens: 18.5k  |  Tool Calls: 12  |  Error Rate: 0.0%  |  Avg Latency: 420ms     |
+-----------------------------------------------------------------------------------------------+
```
