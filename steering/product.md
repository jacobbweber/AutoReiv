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

## 3. The Web Studios

AutoReiv has 11 studios in one responsive web app. The sidebar names them Chat Studio, Wiki, Projects, Agents (Agent Studio), Skill Studio, Tools Studio, Routines, Metrics (observability), Settings, Prompts and Education, plus a Study button that opens the Tutor. The main ones:

1. **Chat Studio (`chat.js`)**:
   - Multi-session persistent chat interface with token streaming.
   - Dynamic agent selection, verified refinement tool loops, and goal mode.
   - Human-in-the-Loop (HITL) tool approval parking and interactive decision modals.
   - Direct session thread export to Wiki staging inbox.

2. **Routines Studio (`routines.js`)**:
   - Automated routine lifecycle management (create, edit, pause, delete, trigger).
   - Dual-cron syntax and human-interval scheduling expressions.
   - Lead-agent routine binding, execution history logs, and status telemetry.

3. **Metrics (`observability.js`)**:
   - Real-time KPI dashboards (total turns, token throughput, average latency, error rates).
   - Agent-by-agent performance breakdown and tool invocation metrics.
   - In-memory event log buffer with live auto-refresh and severity filtering.

4. **Agent Studio (`forge.js`)**:
   - Custom agent meta-builder with SQLite persistence.
   - Purpose classification (Fast, Reasoning, Task Execution, Coding, Vision, Auxiliary).
   - Prompt engineering controls, tone selection (Concise, Balanced, Elaborate), and skill on/off ticks (an agent's tools come only from its ticked skills, ADR-0061).

5. **Settings Studio (`settings.js`)**:
   - Multi-provider gateway configuration (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Together, vLLM).
   - Live model discovery and automatic parameter quantization parsing.
   - Hardware Fit Calculator evaluating local RAM/VRAM suitability.
   - Model Purpose Matrix routing tasks to optimal local or cloud models.

6. **Skill Studio, Tools Studio, Education, Projects, Prompts, Wiki**:
   - Skill Studio: write and lint skills; authoring jobs go to Toolsmith. Tools Studio: runtime-built tools (enable/disable, show code) and the tool catalog.
   - Education: Tutor-first learning (ADR-0059). Projects: the active project for Architect and Developer. Prompts: saved prompts. Wiki: the vault and notes.

7. **System documentation (no Docs Studio ship)**:
   - There is **no** shipped `Docs Studio (docs.js)` in the SPA studio set (current studios: chat, education, forge (Agent Studio), observability, projects, prompts, routines, settings, skill-studio, tools-studio, wiki). The Agent Training Factory is retired ([ADR-0060](../docs/adr/0060-retire-the-agent-training-factory.md)); its leftover screen was removed in CARD-496.
   - Architecture decisions live under `docs/adr` and `steering/*`; user and developer docs are indexed in `docs/README.md`.
   - Historical CARD-018/019 "documentation browser" intent remains **not** a separate `docs.js` studio — do not treat product copy as claiming one.

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
