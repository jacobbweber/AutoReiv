# Product Steering: AutoReiv

> **Purpose**: Defines the high-level business vision, target users, core domain boundaries, and strategic value propositions for AutoReiv.

---

## 1. Product Vision & Executive Summary
AutoReiv is a versatile, local-first hybrid autonomous AI agent control plane and personal assistant platform. It provides seamless multi-session streaming interactions, human-in-the-loop (HITL) approval gates, autonomous routine scheduling, multi-provider LLM routing (local Ollama, vLLM + cloud providers), and cross-platform desktop/mobile support.

---

## 2. Target Personas & Users
- **Human Visionary / Power User**: Operates the system via the Web SPA across desktop and mobile, interacting with agents, defining routines, and reviewing telemetry.
- **Autonomous Subsystems & Agents**: Execute scheduled background routines, orchestrate subagent handoffs, and manage the knowledge vault.
- **System Administrator / API Consumer**: Configures local/cloud providers, connects MCP servers, and integrates with external control planes.

---

## 3. The 7 Integrated Web Studios
AutoReiv is structured into 7 purpose-built studios accessible via a responsive SPA interface:

1. **Chat Studio (`chat.js`)**:
   - Multi-session persistent chat interface with token streaming.
   - Dynamic agent selection, verified refinement tool loops, and goal mode.
   - Human-in-the-Loop (HITL) tool approval parking and interactive decision modals.
   - Direct session thread export to Wiki staging inbox.

2. **Routines Studio (`routines.js`)**:
   - Automated routine lifecycle management (create, edit, pause, delete, trigger).
   - Dual-cron syntax and human-interval scheduling expressions.
   - Lead-agent routine binding, execution history logs, and status telemetry.

3. **Observability Studio (`observability.js`)**:
   - Real-time KPI dashboards (total turns, token throughput, average latency, error rates).
   - Agent-by-agent performance breakdown and tool invocation metrics.
   - In-memory event log buffer with live auto-refresh and severity filtering.

4. **Agent Forge Studio (`forge.js`)**:
   - Custom agent meta-builder with SQLite persistence.
   - Purpose classification (Fast, Reasoning, Task Execution, Coding, Vision, Auxiliary).
   - Prompt engineering controls, tone selection (Concise, Balanced, Elaborate), and granular skill/tool scoping.

5. **Settings Studio (`settings.js`)**:
   - Multi-provider gateway configuration (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Together, vLLM).
   - Live model discovery and automatic parameter quantization parsing.
   - Hardware Fit Calculator evaluating local RAM/VRAM suitability.
   - Model Purpose Matrix routing tasks to optimal local or cloud models.

6. **Docs Studio (`docs.js`)**:
   - Interactive C4 architectural documentation viewer.
   - Collapsible navigation tree with pan-tilt-zoom (PTZ) Mermaid.js diagram canvas.
   - System information specifications, runtime blueprints, and ADR browser.

7. **Wiki Studio & Knowledge Graph (`wiki.js`)**:
   - 2D force-directed physics Mind Map with dynamic Euler integration.
   - Hierarchical category and topic document navigation tree.
   - YAML frontmatter parser and markdown editor with live preview toggle.
   - Wikilink (`[[Note]]`) relation graph and flat inbox staging vault.

---

## 4. Core Capabilities & Strategic Value Drivers
1. **Zero Hallucination Delivery**: Formal EARS requirements (`[REQ-xxx]`) ensure implementation strictly matches business intent.
2. **Deterministic Quality**: Test-Driven Development (TDD) across backend Pytest suites, frontend Vitest pure logic suites, and Playwright smoke suites guarantees zero regressions.
3. **Traceability**: Machine-readable Requirements Traceability Matrix (`docs/rtm.json`) connects 100% of requirements to specs, ADRs, source code, and test suites.
4. **Local-First Privacy & Safety**: Private data, SQLite states, and markdown vaults reside entirely on the local machine with automated secret masking in UI payloads.
