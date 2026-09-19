# Requirements Specification: Responsive Web & Mobile Front-Door with Wiki Export

> **Spec Status**: Implemented  
> **Target Release**: Milestone 7 (v0.7.0)  
> **Primary Component**: `AutoReiv.Web`  
> **Applicable ADRs**: `docs/adr/0008-fastapi-web-application-rest-streaming-api-and-responsive-multi-view-spa.md`

---

## 1. Executive Summary & Intent

Milestone 7 implements the complete **AutoReiv Control Plane Web Application & Front-Door**, uniting interactive streaming chat (with collapsible `<think>` reasoning tags), per-agent conversations, one-click PARA-Wiki markdown export, the Settings Studio with live model picker and hardware calculator, the Observability KPI dashboard, and Autonomous Routine controls in a zero-build-step responsive interface.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-WEB-001]: REST & SSE Streaming API Gateway
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator sends a chat prompt to /api/chat/stream THE SYSTEM SHALL stream real-time Server-Sent Events (tokens, reasoning chunks, tool execution indicators, and turn completion payload).`
- **Acceptance Criteria**:
  - [ ] Given a chat turn with tool invocation, when streamed via SSE, then emits `event: tool_start`, `event: token`, and `event: turn_done`.

### [REQ-WEB-002]: Responsive Multi-Agent Chat Interface
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL serve a responsive web application supporting desktop and mobile viewports with segregated chat histories per agent (General Assistant, Linux Sysadmin, Librarian, System Agent) and session switching.`
- **Acceptance Criteria**:
  - [ ] Given mobile and desktop clients, when loaded, then renders navigation drawer, session list, and agent picker.

### [REQ-WEB-003]: One-Click Markdown Wiki Export with Frontmatter
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator clicks 'Export to Wiki' on a message or entire session THE SYSTEM SHALL format content into a markdown note with YAML frontmatter (title, agent, session_id, created_at, tags) and persist it to the configured wiki storage directory.`
- **Acceptance Criteria**:
  - [ ] Given a session or message, when exported, then creates a `.md` file in the wiki directory containing valid YAML frontmatter and markdown body.

### [REQ-WEB-004]: Settings Studio & Live Model Control UI
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL render interactive controls to refresh available LLM models from Ollama/OpenAI, configure the Purpose Matrix (Reasoning, Task, Fast, Vision), and display hardware fit recommendations with custom RAM capacity inputs.`
- **Acceptance Criteria**:
  - [ ] Given the settings tab, when clicked refresh, then updates model lists and displays fit badges (OPTIMAL, RUNNABLE).

### [REQ-WEB-005]: Observability & KPI Dashboard Visualizer
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL render global platform KPI metric cards (Total Tokens, Active Turns, Error Rate, Average Latency), per-agent usage tables, and tool reliability metrics.`
- **Acceptance Criteria**:
  - [ ] Given `/api/observability/kpi`, when queried, then returns complete platform health and usage statistics.

### [REQ-WEB-006]: Autonomous Routine Control & Manual Trigger UI
- **Type**: Event-Driven
- **EARS Statement**: `THE SYSTEM SHALL display all autonomous routines with schedule status, run history, and provide an immediate 'Run Now' trigger button.`
- **Acceptance Criteria**:
  - [ ] Given a routine ID, when `POST /api/routines/{id}/trigger` is requested, then triggers immediate execution and returns the run result.

---

## 3. Non-Functional & Boundary Constraints

- **Zero Node.js / NPM Build Step**: The web UI is self-contained HTML5/CSS/JavaScript with CDN-hosted Tailwind CSS and Lucide icons, running seamlessly on Python `uvicorn`.
- **Path Jailing**: Wiki note exports are restricted to the configured `wiki_path` directory to prevent directory traversal exploits.
