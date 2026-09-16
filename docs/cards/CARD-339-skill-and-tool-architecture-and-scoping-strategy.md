# [CARD-339] Skill and Tool Architecture, Scoping Strategy & Specialist Delegation

> **Status**: In Review
> **Created**: 2026-09-16
> **Unifies & Supersedes**: [CARD-336](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-336-specialist-intake-dispatch-and-standing-job-delegation.md)
> **Spec Reference**: docs/specs/skill-and-tool-architecture-and-scoping-strategy/ (and ADR-0052)
> **Labels**: `type:architecture`, `domain:tools`, `domain:skills`, `domain:kernel`, `domain:orchestration`

---

## 1. Why / Intent

The telemetry audit in Observe Studio revealed that chatting with `autoreiv` loads 40 tools, consuming 16,164 tokens (52.3% of the prompt) in raw JSON schema overhead on every turn. Simultaneously, when operators ask front-of-house agents (like `assistant`) to perform tasks requiring specialist tools (such as `wiki_note_*`), the job orchestrator locks the entire job graph to `assistant`, leading to mid-phase fail-closed stalemates (CARD-336).

These issues stem from the same foundational architecture flaw:
1. Treating every tool as a global platform default inherited by all agents.
2. Blurring the line between **Skills** (procedural runbooks) and **Tools** (executable code functions).
3. Lacking progressive tool disclosure and specialist dispatch during multi-step job graphs.

### The Three Beats
1. **What Jacob means**: Jacob wants a deep design and architectural review of AutoReiv's skill and tool strategy to settle boundaries once and for all. This must compare AutoReiv against industry platforms (**OpenHuman**, **Odysseus**, **Hermes**, **OpenClaw 2.0**) to understand how progressive tool loading, skill-to-tool binding, and specialist delegation are designed in modern architectures, eliminating the 40-tool harness bloat and fixing the specialist delegation deadlock.
2. **What AutoReiv does now**:
   - `REQUIRED_PLATFORM_TOOLS` injects 30+ tools by default onto every agent on every turn.
   - All 40+ function JSON schemas are formatted and injected into the LLM context on *every turn*, even for simple questions.
   - Front-of-house agents fail closed when assigned multi-step jobs that require specialist tools (e.g. Assistant assigned to a Wiki job).
   - No progressive disclosure or on-demand tool activation exists in the kernel.
3. **What will change**:
   - **Architectural Benchmark & ADR-0052**: Author a comprehensive comparative study across Hermes, OpenClaw 2.0, OpenHuman, and Odysseus, publishing `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`.
   - **Strict Skill vs. Tool Separation** (OpenClaw model): Tools are atomic code capabilities ("hands"); Skills are Markdown SOP playbooks ("brain").
   - **Lean OS Baseline** (Hermes progressive disclosure model): Shrink `REQUIRED_PLATFORM_TOOLS` from 30+ down to ~5–7 essential coordination and context primitives (`handoff_to_agent`, `ask_clarification`, `session_info`).
   - **Specialist Intake Dispatch & Multi-Agent Phase Graphs** (OpenHuman split-brain model / CARD-336): When an incoming request matches specialist capabilities (e.g. Wiki or Homelab), the job orchestrator dispatches the execution phase to that specialist rather than locking it to the front-of-house agent.
   - **Progressive / Skill-Bound Tool Mounting**: Tools outside the lean baseline are mounted dynamically when their owning skill is active or when a specialized specialist pack is invoked.

---

## 2. Comparative Architecture Review (Industry Systems)

| System | Tool Strategy | Skill Strategy | Orchestration / Delegation Model | Key Takeaway for AutoReiv |
| :--- | :--- | :--- | :--- | :--- |
| **Nous Research Hermes Agent** | **Progressive Tool Disclosure**: Avoids the "giant toolbox" by presenting 3 bridge tools (`tool_search`, `tool_describe`, `tool_call`) instead of 40+ full JSON schemas at turn start. | Modular Markdown procedural documents (`~/.hermes/skills/`) grouped into **Skill Bundles** (e.g. `/backend-dev`). | Single ReAct core with closed-loop reflection that crystallizes multi-step tool interactions into reusable skills. | Solve prompt bloat via bridge/lookup tools or skill-bundle tool activation rather than broadcasting all 40 schemas. |
| **OpenClaw 2.0** | **Atomic Capabilities ("Hands")**: Granular, typed, sandboxed execution tools (file, bash, browser). Never injected globally without policy. | **Operational Logic ("Brain")**: Markdown SOPs (`SKILL.md`) with YAML frontmatter instructing the agent *how and when* to sequence tools. | **Gateway Control Plane**: Routes incoming channel messages to specific isolated Agent Runtimes defined by identity and pack manifests (`SOUL.md`). | Enforce strict separation: Tools are callable code; Skills are runbooks. Packs define which skills/tools an agent possesses. |
| **OpenHuman (TinyHumans)** | Native tools + 118+ integrations, filtered aggressively with **TokenJuice** context compression to cut prompt overhead by up to 80%. | Markdown skill modules extending agent behavior. | **Split-Brain Architecture**: Fast "Reflex Agent" (triage / front-of-house with minimal tools) routes complex tasks to a deep reasoning core via **checkpointed task graphs** (`tinyagents`). | Directly solves CARD-336: Front-of-house (Assistant) triages, then job orchestrator assigns specialist execution phases to the proper specialist. |
| **Odysseus** | Local workspace execution tools + external **MCP (Model Context Protocol)** servers. | Workspace skills assigned per agent or loaded on demand. | Desktop workspace metaphor with local hardware awareness and hierarchical memory (TRACE) to eliminate token bloat. | Decouple native OS primitives from specialist tools and external MCP servers. |

---

## 3. What to Build

### 1. Architectural Review & ADR-0052
- Publish `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md` capturing the findings above.
- Establish the official contracts:
  - Skill vs. Tool definition.
  - Lean OS Baseline (5–7 essential tools).
  - Progressive Tool Disclosure & Skill-Bound tool sets.
  - Specialist Intake Dispatch & Multi-Agent Phase Graphs (CARD-336 resolution).

### 2. Implementation: Lean OS Baseline & Tool Pruning
- Refactor `src/application/kernel/tool_registry.py` and `src/application/agent_packs/schema.py`:
  - Prune `REQUIRED_PLATFORM_TOOLS` down to platform primitives (`handoff_to_agent`, `ask_clarification`, `get_session_info`, `lookup_agents`).
  - Move domain tools (`wiki_*`, `sandbox_*`, `repo_*`) to their respective specialist packs or skill attachments.
  - Audit all pack manifests (`platform-packs/*/pack.json`) to eliminate redundant tool declarations.

### 3. Implementation: Specialist Intake Dispatch (CARD-336 Resolution)
- Enhance `create_job_from_catalog_resolve()` and `JobPhaseOrchestrator`:
  - If resolved capabilities predominantly belong to a specialist pack (e.g. `wiki`), assign the execution phase to that specialist (`assigned_agent_id='wiki'`).
  - Pass formulated parameters across phase boundaries cleanly without requiring the front-of-house agent to hold specialist tools.

### 4. Observability & Verification
- Verify in Observe Studio that `autoreiv` and `assistant` prompt tool schemas drop from 16,164 tokens (>50%) down to under 3,000 tokens (<15%).
- Verify that asking Assistant to create/reorganize Wiki notes successfully dispatches to Wiki and produces notes without fail-closed deadlocks.
- Run the full test suite (`pytest`, `vitest`, `lint`, preflight).

---

## 4. Acceptance Criteria (Definition of Done)

- [x] Complete architectural inventory of all 40+ tools currently mounted across AutoReiv.
- [x] Published `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md` comparing industry benchmarks.
- [x] `REQUIRED_PLATFORM_TOOLS` slimmed down to 5 essential platform primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`).
- [x] Non-essential tools scoped to specialist packs or skill-bound activation.
- [x] Multi-step jobs requiring specialist capabilities correctly dispatch execution to the specialist agent (resolving CARD-336).
- [x] Verified via Observe Studio that tool schema token count on standard turns decreases by at least 60% (empirically 96.2% reduction: from 16,164 to 608 tokens).
- [x] All backend unit tests (`pytest`) pass with zero regressions.
- [x] All frontend checks (`npm run lint:frontend`, `vitest`) pass with zero errors.

---

## 5. Constraints & Honor Flags

- Do not break existing agent handoff paths (`handoff_to_agent` remains a baseline platform primitive).
- Follow SDLC: cut dedicated feature branch `feat/CARD-339-skill-and-tool-scoping-strategy` from `qa`.
- No code without Jacob's explicit `build` instruction.

