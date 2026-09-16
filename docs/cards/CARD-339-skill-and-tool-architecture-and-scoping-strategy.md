# [CARD-339] Skill and Tool Architecture and Scoping Strategy

> **Status**: Ready
> **Created**: 2026-09-16
> **Spec Reference**: docs/specs/skill-and-tool-architecture-and-scoping-strategy/ (and ADR-0052)
> **Labels**: `type:architecture`, `domain:tools`, `domain:skills`, `domain:kernel`

---

## 1. Why / Intent

The telemetry audit in Observe Studio revealed that chatting with `autoreiv` loads 40 tools, consuming 16,164 tokens (52.3% of the prompt) in raw JSON schema overhead on every turn.

### The Three Beats
1. **What Jacob means**: Every standard conversation carries 40 tool schemas in memory, bloating token usage, inflating TTFT, increasing costs, and degrading model focus. Jacob wants a deep design and architectural review of AutoReiv's skill and tool strategy to settle the boundaries once and for all and eliminate harness bloat.
2. **What AutoReiv does now**:
   - Every agent inherits `REQUIRED_PLATFORM_TOOLS` by default. As features were added, platform tools accumulated to over 30 baseline tools (wiki read/list, coordination, handoffs, approvals, capability catalog, etc.).
   - Agent packs add pack-specific tools on top.
   - All 40+ function JSON schemas are formatted and injected into the LLM context on *every turn*, even when the user asks a simple question like "How does the system health look?".
   - The distinction between a **Skill** (runbook / procedural knowledge) and a **Tool** (callable code function) often blurs, causing tools to be created where skills suffice, or skills to mount dozens of tools simultaneously.
3. **What will change**:
   - Author a comprehensive Architecture Decision Record (`docs/adr/0052-skill-and-tool-scoping-and-progressive-activation.md`) and specification.
   - **Lean OS Baseline**: Dramatically slim down `REQUIRED_PLATFORM_TOOLS` from 30+ tools to a minimalist set (5–7 essential coordination tools, e.g. handoff, ask_clarification, get_session_info).
   - **Progressive / Skill-Bound Tool Mounting**: Tools belong to specific skills or domains (e.g. wiki write tools belong to the Wiki skill; git/exec tools belong to the coding skill). Tools are only mounted when that skill is active or when a specialized specialist agent is invoked.
   - **Tool Search / Meta-Tool Exploration**: Evaluate dynamic tool lookup (the agent searches or activates tools on demand) versus strict agent handoffs.
   - Audit and prune duplicate, orphaned, or obsolete tools across all platform packs.

---

## 2. What to Build

### 1. Architectural Review & ADR-0052
- Deep-dive analysis of all currently registered tools in `src/infrastructure/agents/registry.py` and `src/application/kernel/tool_registry.py`.
- Formalize ADR-0052:
  - Skill vs. Tool contract.
  - Platform baseline tool boundaries (what *must* be on every agent vs. what *must* be scoped).
  - Progressive tool activation model (skill-driven tool binding).

### 2. Implementation & Tool Pruning
- Refactor `src/application/kernel/tool_registry.py` and `src/application/agent_packs/schema.py`:
  - Split `REQUIRED_PLATFORM_TOOLS` into a lean baseline (~5-7 tools) and domain-specific tool groups.
  - Ensure standard agents (like `autoreiv` and `assistant`) do not load 40 tools on plain chat turns.
  - Audit all pack manifests (`platform-packs/*/pack.json`) to remove bloated or duplicate tool declarations.

### 3. Observability & Verification
- Measure the reduction in Observe Studio: verify that `autoreiv` prompt schemas drop from 16,164 tokens (>50%) down to under 3,000 tokens (<15%).
- Ensure all existing unit and e2e integration tests for agent handoffs and tool execution continue to pass.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Complete architectural inventory and audit of all 40+ tools currently mounted.
- [ ] Published `docs/adr/0052-skill-and-tool-scoping-and-progressive-activation.md`.
- [ ] `REQUIRED_PLATFORM_TOOLS` slimmed down to essential platform primitives.
- [ ] Non-essential tools moved to skill-bound or pack-specific scoping.
- [ ] Verified via Observe Studio that tool schema token count on standard turns decreases by at least 60%.
- [ ] All backend unit tests (`pytest`) pass with zero regressions.
- [ ] All frontend checks (`npm run lint:frontend`, `vitest`) pass with zero errors.

---

## 4. Constraints & Honor Flags

- Do not break existing agent handoff paths (e.g. `handoff_to_agent` must remain available).
- Follow SDLC: cut dedicated feature branch `feat/CARD-339-skill-and-tool-scoping-strategy` from `qa`.
- No code without active card approval.

