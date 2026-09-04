# [CARD-155] Repository Constitution and Agentic Rules Ingestion for Local LLMs

> **Status**: Ready
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Packs.Coding`

---

## 1. Why / Intent

When operating on a codebase, an agent needs to automatically discover and respect the project's specific working agreements and rules (such as `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, and folders like `.agents/skills/` or `.github/skills/`). 

Instead of baking this into the core AutoReiv agent or the system kernel, this capability belongs inside a specialized **'Coding' Agent Pack**. By providing this as a set of Skills and Tools within the Coding pack, agents equipped with this pack can dynamically detect these "agentic code assist files", extract their core rules, and inject them into their working memory. This is especially critical for local models (like Ollama) that have tighter context limits, requiring smart compaction of these rules so the agent honors the repository's SDLC invariants without breaking the context window.

---

## 2. What to Build

1. **Coding Pack Rule Discovery Tool (`agent-packs/coding/tools/...`)**:
   - A tool that the Coding agent can call to scan the active working directory for known agentic rule files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`.
   - Discovers skill and workflow directories: `.agents/skills/`, `.github/skills/`.
2. **Coding Pack Context Ingestion Skill (`agent-packs/coding/skills/...`)**:
   - A runbook/skill that instructs the agent on *when* and *how* to use the discovery tool when entering a new repository.
   - Logic to safely parse and ingest these discovered rules into the agent's active context.
   - If the combined rules exceed a safe threshold for local Ollama models, the tool/skill applies a compaction or priority strategy (e.g., hard invariants first) before loading them into memory.
3. **Agent Integration**:
   - This remains entirely decoupled from the core AutoReiv agent. Only agents utilizing the Coding pack will have the tooling to perform this repository constitution scan.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-RULES-001]`: The Coding Agent Pack includes a tool to detect standard agentic files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, etc.) in the target repository.
- [ ] `[REQ-RULES-002]`: The Coding Agent Pack includes a skill instructing it to read and apply these files when working on code.
- [ ] `[REQ-RULES-003]`: The ingestion tool/skill handles context compaction so it works reliably with local Ollama models without context exhaustion.
- [ ] `[REQ-RULES-004]`: Automated unit tests verify the tool's discovery and parsing logic.
- [ ] `[REQ-RULES-005]`: Zero linting errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- This is strictly an Agent Pack feature, NOT a core system kernel modification.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
