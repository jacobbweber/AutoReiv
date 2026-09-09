# [CARD-197] Agent Creation and Training Pipeline Refinement

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Three Beats

### Beat 1: What you mean
Creating a new specialist agent and training its capabilities should produce production-grade, reliable AI agents that adhere to modern agentic AI industry standards.

You want to refine and elevate three interconnected layers of the platform:
1. **Agent Creation Directive & Socratic Discovery**:
   - What makes a *great* agent in code and prompt design? It needs role clarity, strict domain boundaries, safety guardrails, environment awareness, and structured execution protocols—not just a generic 2-sentence prompt.
   - AutoReiv's `build-agent-pack` skill and prompt directive must be instilled with this standard.
   - When an operator says *"I want an Ansible agent"* or *"I want a gardening agent"*, AutoReiv should engage in **Socratic Discovery**: asking the right number (3–4) of high-leverage clarifying questions (domain depth, target environment, safety/approval boundaries, tools needed) to synthesize a gold-standard system prompt and pack specification.
   - Operators should also have a fast-scaffold form in the UI for quickly spinning up an agent when they already have their brief ready, followed by an **instant handoff card** (`[ 🚀 Launch Training in Factory ]`) into Factory Studio.
2. **8-Stage Agent Training Factory Prompt & Context Refinement**:
   - In Factory Studio, evaluate each of the 8 pipeline stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) and refine their default system prompts and injected context variables.
   - Ask for each phase: *Is this truly the best context to provide to get the highest-quality outcome?*
   - Upgrade each phase prompt with concrete agentic AI patterns: few-shot reasoning, anti-bloat constraints, deterministic schema enforcement, and clear negative guardrails.
   - Add an **auto-healing loop** in Stage 6 (`Code Verify`) to automatically retry 1–2 times with the traceback if code generation hits syntax or import errors.
3. **Skills & Tools Governing Principles (Industry Standards)**:
   - Perform a comprehensive quality pass on the framing and structure of skills and tools:
     - **Skills**: Adhere strictly to the Matt Pocock progressive disclosure standard: one `SKILL.md` runbook with concise YAML frontmatter for turn-time selection and a rich markdown body (Order, Pitfalls, Done-when).
     - **Tools**: One atomic callable function with explicit Pydantic type signatures and docstrings engineered specifically for LLM tool-calling comprehension (intent, "Use when / Do not use when", parameter constraints, structured JSON returns).

---

### Beat 2: What AutoReiv does now
1. **Agent Creation Today**:
   - In Factory Studio, clicking `[ + New Agent ]` redirects to Chat Studio with a starter prompt `@autoreiv I want to create a new specialist agent...`.
   - `build-agent-pack/SKILL.md` only instructs AutoReiv to collect basic fields (`id`, `name`, `system_prompt`, `tone`, and existing tools). It does not guide AutoReiv on *how* to probe for domain boundaries, negative constraints, or execution protocols.
   - If an operator says *"I want an Ansible agent"*, AutoReiv may write a naive system prompt without safety checks (e.g. mutating production servers without dry-runs).
   - There is no fast-scaffold modal in Agent Studio or Factory Studio, and no direct handoff card into training after an agent is created.
2. **Training Pipeline Prompts Today (`prompt_registry.py`)**:
   - Each phase currently has a minimal 2–3 sentence prompt.
   - `Intent Distill` does not enforce structured EARS user stories or boundary definitions.
   - `Ground` does not thoroughly verify environment constraints or dependency availability.
   - `Blueprint` does not strictly enforce the separation between runbook knowledge (`SKILL.md`) and deterministic tools (`tools.py`).
   - `Author` does not enforce LLM-optimized docstring conventions or structured return envelopes.
   - If Stage 6 (`Code Verify`) hits an error, the job immediately halts without auto-correction.
   - The HITL Promotion modal shows raw JSON/text without a structured file diff view.

---

### Beat 3: What will change (Proposed Architecture & Refinements)

#### 1. Gold-Standard Agent Creation Directive & Socratic Discovery
- **The "Good Agent" Architectural Blueprint**:
  Instill standard system prompt sections into AutoReiv's agent-building directive:
  - `[IDENTITY & ROLE]`: Concise domain persona and specialization.
  - `[DOMAIN BOUNDARIES & REFUSALS]`: Strict negative boundaries (what it must reject or refer out).
  - `[EXECUTION PROTOCOL]`: Step-by-step reasoning order (e.g. read/inspect ➔ plan ➔ verify ➔ execute).
  - `[SAFETY & APPROVALS]`: Safety gates for mutating actions (e.g. dry-run `--check` mode before running).
  - `[TOOL USAGE RULES]`: How and when it invokes its tools, and what to do when a tool fails.
  - `[OUTPUT FORMAT]`: Expected formatting standards (markdown tables, checklists, code blocks).
- **AutoReiv Socratic Discovery Protocol (`build-agent-pack/SKILL.md`)**:
  When prompted with a new agent concept, AutoReiv responds with 3–4 targeted questions:
  1. *Core Specialization*: What exact workflows should this agent master (e.g. for Ansible: writing playbooks, linting syntax, running ad-hoc commands)?
  2. *Environment & Execution*: Where does it operate (local host, remote SSH servers from Credential Vault, Docker)?
  3. *Safety & Guardrails*: Should it require confirmation before mutating resources, or always perform dry-runs?
  4. *Initial Tool Needs*: Does it use existing platform tools (`cli_exec`, `remote_tools`), or does it need dedicated tools trained in the Factory?
- **Dual Creation Modalities & Instant Handoff**:
  - *Conversational*: Assisted chat with AutoReiv running the Socratic discovery protocol.
  - *Quick-Scaffold Modal (`#forgeNewAgentModal`)*: Quick manual entry modal in Factory and Agent Studio.
  - *Handoff Card*: Immediate post-creation card in chat:
    ```text
    +---------------------------------------------------------+
    | 🎉 Agent "<Agent Name>" Created Successfully!           |
    | Location: packs/<slug>/ (Manifest & DB initialized)      |
    | [ 🚀 Launch Training in Factory ]   [ ⚙️ Open in Studio ] |
    +---------------------------------------------------------+
    ```
    Clicking `[ 🚀 Launch Training in Factory ]` switches to Factory Studio with the new agent pre-selected.

#### 2. Agent Training Factory 8-Stage Prompt & Context Refinement
Audit and upgrade the default system prompts and injected contexts in `src/application/agent_training_factory/prompt_registry.py`:
- **Stage 1: Intent Distill**:
  - Enforces decomposing the operator's goal into user stories, identifying explicit boundary conditions, and classifying whether each capability requires a runbook (`SKILL.md`), a native Python tool, or an MCP server.
- **Stage 2: Environment Ground**:
  - Enforces probing host OS, CLI binaries, and Python packages. Formulates explicit environmental constraints (e.g. "Windows host, PowerShell 7 available, ansible-core installed").
- **Stage 3: Capability Blueprint**:
  - Architects atomic tools adhering to the Matt Pocock pattern. Enforces strict anti-bloat: separate procedural runbook steps from executable tools. Defines Pydantic input schemas and return contracts.
- **Stage 4: Tool & Skill Author**:
  - Generates production-ready Python code with complete docstrings engineered for LLM tool-calling (clear descriptions of *when* to call, argument types with examples, structured dictionary returns). Zero placeholders (`# TODO`). Generates matching `SKILL.md` with Order, Pitfalls, Done-when.
- **Stage 5: Scenario Verify**:
  - Generates 3+ realistic behavioral test scenarios (happy path, boundary input, and expected error/failure mode) to evaluate deliverables against end-to-end user journeys.
- **Stage 6: Code Battery Verify & Self-Healing Loop**:
  - Executes hermetic sandbox test runs. If syntax errors or runtime exceptions occur, captures the exact traceback and automatically triggers up to 2 repair iterations in Author/Optimize before failing.
- **Stage 7: Refactor & Optimize**:
  - Polishes docstrings for token economy, removes code duplication, ensures idempotent execution, and standardizes error envelopes.
- **Stage 8: Pack Promotion & HITL Inspection**:
  - Verifies `pack.json` schema version, checks tool name uniqueness against existing pack tools, and presents a clean tabbed diff inspector (Runbook preview, Python code, manifest patch) for human approval.

#### 3. Skills & Tools Governing Standards Alignment
- **Skills (`SKILL.md`)**:
  - YAML Frontmatter: crisp `name` and 1–2 sentence `description` for fast turn-time routing.
  - Body: Progressive disclosure with structured Markdown sections:
    - `## Overview`: Core purpose and scope.
    - `## Tools`: Ticked callable tools belonging to this skill.
    - `## Order`: Step-by-step execution protocol.
    - `## Pitfalls`: Common agent failure modes and explicit negative constraints.
    - `## Done-when`: Concrete verification checklist before marking a turn complete.
- **Tools (`tools.py`)**:
  - 1 Tool = 1 Atomic Callable.
  - Strict type hints (`str`, `int`, `bool`, `Optional[...]`, Pydantic models).
  - Docstring standard:
    - Summary line.
    - Detailed intent ("Use when... Do not use when...").
    - Args with type, constraints, and examples.
    - Returns: structured dict `{ "status": "success"|"error", "data": ..., "error": ... }`.
  - Storage vs Memory: application domain state goes to `<agent_slug>_storage.db`; cognitive brain facts go to `<agent_slug>_memory.db`.

---

## 2. Technical Scope & Affected Components

1. **Agent Creation & Runbooks**:
   - `platform-packs/autoreiv/skills/build-agent-pack/SKILL.md`: Upgraded with Socratic Discovery rules and the "Good Agent" architectural blueprint.
   - `src/infrastructure/skills/seeds/build-agent-pack/SKILL.md`: Seed sync for platform pack consistency.
   - `src/domain/agents/profiles.py`: Updated `AGENT_BUILDER_PROFILE` prompt directives.
2. **Factory Prompt Registry & Runners**:
   - `src/application/agent_training_factory/prompt_registry.py`: Comprehensive upgrade of all 8 phase default system prompts, descriptions, and context variables.
   - `src/application/agent_training_factory/orchestrator.py`: Self-healing retry loop between Stage 6 (`Code Verify`) and Stage 4/7, tracking phase durations.
   - `src/application/agent_training_factory/runners/code_verify.py`: Structured traceback extraction for auto-repair loops.
   - `src/application/agent_training_factory/runners/blueprint.py` & `author.py`: Enforced Matt Pocock skill layout and tool docstring standards.
3. **Web UI & User Experience**:
   - `src/web/templates/index.html`: Quick-scaffold modal (`#forgeNewAgentModal`), post-creation handoff card styling, and tabbed HITL deliverable diff modal.
   - `src/web/static/modules/studios/factory.js`: Pre-scoped agent launcher integration, phase duration badges on stepper, and tabbed code preview.
   - `src/web/static/modules/studios/forge.js`: Quick-scaffold trigger and creation validation.

---

## 3. Acceptance Criteria (When Scheduled for Implementation)

- [x] AutoReiv's `build-agent-pack` skill implements Socratic discovery, asking 3–4 high-leverage clarifying questions to produce industry-standard system prompts with role, boundaries, protocol, and output contracts.
- [x] Quick-scaffold agent creation modal available in Factory Studio and Agent Studio.
- [x] Post-creation handoff card renders in chat with one-click transition into Factory Studio pre-scoped with the new agent.
- [x] All 8 Factory phase prompts in `prompt_registry.py` upgraded with rigorous agentic AI standards, schema enforcement, and clear context variables.
- [x] Self-healing verification retry loop (up to 2 attempts with traceback) in `FactoryOrchestrator` before failing a training job.
- [x] HITL Promotion modal renders tabbed deliverable inspection (Runbook markdown preview, Python tool code with syntax formatting, and `pack.json` diff).
- [x] Per-phase execution duration metrics tracked in SQLite and displayed on visual stepper nodes.
- [x] Tool name collision guard preventing duplicate callable names in target agent packs.
- [x] Skills and tools generated by the factory strictly adhere to the Matt Pocock progressive disclosure standard and atomic tool return schemas.
- [x] Automated unit tests for Socratic prompt builder, self-healing loop, duration tracking, and deliverable inspectors.
- [x] Zero lint errors via `ruff` and `eslint`.
