# [CARD-354] Autonomous Telemetry Auditor: Overnight Skill Friction Detection & Runbook Optimizer Routine

> **Status**: Ready  
> **Created**: 2026-09-17  
> **Spec Reference**: `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`, CARD-004, CARD-352  
> **Labels**: `type:feature`, `AutoReiv.Routines`, `AutoReiv.Observability`, `domain:skills`, `domain:learning`  

---

## 1. TODO Before Work Starts (Discussion & Alignment)

Before calling `build` on this card, align on these three decisions with Jacob:
1. **Friction Signatures**: Which telemetry patterns should trigger friction flags? (e.g. redundant verification loops after successful mutations, tool output payload spikes > 8 KB, repeated consecutive search calls, turn count > 8 with low completion tokens).
2. **Optimization Output Mode**: Should the optimizer automatically commit targeted patches to user-data `SKILL.md` under `## Common Pitfalls & Forbidden Paths`, or stage them into an "Optimization Recommendations" inbox in Forge / Observability Studio for operator review?
3. **Execution Schedule**: Should this run as an autonomous recurring routine (e.g. nightly at 03:00) with an on-demand "Run Telemetry Audit" button in Observability Studio?

---

## 2. Three Beats

### Beat 1: What Jacob means
AutoReiv records rich telemetry on every turn and tool execution in SQLite (`telemetry_spans`, `messages`). Rather than requiring the human operator to manually inspect logs and notice when an agent wastes tokens on redundant verification turns or bloated payloads, AutoReiv should run an autonomous background routine (e.g. overnight) that audits recent conversation traces, diagnoses cognitive friction, and automatically refines the relevant agent's `SKILL.md` runbook with anti-pattern rules.

### Beat 2: What AutoReiv does now
* Spans are captured in `telemetry_spans` with `duration_ms`, `ttft_ms`, `prompt_tokens`, `completion_tokens`, and tool names.
* However, no system or agent ever reads or analyzes these spans for performance optimization.
* If an agent routinely calls `wiki_template_list` immediately after `wiki_template_create`, this inefficiency repeats indefinitely unless a human spots it in SQLite and manually edits the runbook.

### Beat 3: What will change
1. **Telemetry Trace Friction Analyzer (`src/domain/observability/friction_analyzer.py`)**:
   * Scans sessions for defined friction heuristics:
     * *Redundant Verification*: Read/list tool executed immediately after a successful create/update.
     * *Bloated Payloads*: Single tool results exceeding 8 KB.
     * *Search Thrashing*: Multiple search calls with high string similarity without reading results.
2. **Autonomous Routine Task (`src/application/routines/tasks/skill_optimizer.py`)**:
   * Registers a periodic maintenance routine `audit_and_optimize_skills`.
   * For detected friction patterns, it retrieves the agent's associated `SKILL.md` runbook and synthesizes a concise, surgical addition under `## Common Pitfalls & Forbidden Paths`.
3. **Review & Adoption Bridge**:
   * Saves recommendations to `packs/<agent_id>/skills/<skill_id>/recommendations.json` and optionally auto-patches if configured.
   * Surfaces friction findings in Observability Studio.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Telemetry analyzer detects redundant verification tool calls and payload bloat from SQLite trace history.
- [ ] Routine task `audit_and_optimize_skills` runs autonomously via the routine engine.
- [ ] Optimizer drafts targeted anti-pattern additions for `SKILL.md` runbooks.
- [ ] Operator can review and adopt proposed runbook optimizations in Observability or Forge Studio.
- [ ] Unit tests verify friction detection heuristics and runbook patching logic.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Skills must be updated strictly under user data packs (`packs/<agent_id>/skills/`), never under git checkout.
- No code without Jacob's explicit `build` instruction.
