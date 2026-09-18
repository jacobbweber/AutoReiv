# [CARD-354] Autonomous Telemetry Auditor: Overnight Skill Friction Detection & Runbook Optimizer Routine

> **Status**: In Review  
> **Created**: 2026-09-17  
> **Updated**: 2026-09-18  
> **Spec Reference**: `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`, CARD-004, CARD-111, CARD-337, CARD-352  
> **Labels**: `type:feature`, `AutoReiv.Routines`, `AutoReiv.Observability`, `domain:skills`, `domain:learning`  

---

## 1. Locked Decisions (Human Visionary Alignment)

Decisions locked with Jacob on 2026-09-18:
1. **Friction Signatures for Day 1**:
   * *Signature A (Redundant Verification)*: A mutating tool (`*_create`, `*_update`, `*_write`, `*_patch`) completes successfully, followed immediately in the next step by a read/list tool querying the same resource/entity.
   * *Signature B (Payload Bloat)*: Single tool result exceeds 8 KB (8,192 bytes), distinguishing between missing pagination/limit parameters (runbook SOP guidance) vs missing tool pagination capability (Factory Studio escalation bridge).
   * *Signature C (Search Thrashing)*: 3 or more consecutive search tool calls within the same turn without reading any returned note/file.
2. **Output Mode**:
   * Staged proposals stored in SQLite (`proposals` table / recommendations store) and surfaced in Observability Studio with diff preview and 1-click `[ ✅ Apply Patch ]` and `[ ✕ Dismiss ]` actions.
   * Autonomous background writes to live `SKILL.md` remain OFF by default (`auto_apply: false`) to safeguard active agent SOPs against overnight corruption.
3. **Execution Schedule & GPU Control**:
   * Routine seeded paused (`enabled=False`) in `src/domain/routines/manifests.py` as `telemetry-friction-auditor`, scheduled for weekday 21:00 America/New_York (matching CARD-111 conventions to avoid surprise GPU load).
   * Observability Studio includes an on-demand "Run Telemetry Audit" button for manual execution whenever the operator wishes.

---

## 2. Three Beats

### Beat 1: What Jacob means
AutoReiv records execution telemetry across turns, tools, and message transcripts. Rather than forcing the human operator to manually inspect raw logs and SQLite tables to identify when an agent wastes tokens on redundant verification loops, pulls massive unpaginated payloads, or gets stuck in search loops, AutoReiv should run a telemetry auditor routine. This routine audits recent conversation traces, diagnoses procedural friction, maps the offending tool to the owning skill runbook, and presents surgical improvements to `SKILL.md` under `## Common Pitfalls & Forbidden Paths` for operator review and 1-click adoption.

### Beat 2: What AutoReiv does now
* Spans are captured in `telemetry_spans` with `duration_ms`, `ttft_ms`, `prompt_tokens`, `completion_tokens`, and tool names.
* Full tool outputs and assistant call arguments are stored in the `messages` table.
* CARD-337 provides deterministic cost and token attribution reports in `src/application/observability/audit_service.py`.
* CARD-111 harvests failed turns via `skill-eval-sleep`.
* However, no service evaluates successful turns for operational friction, links tool inefficiencies back to `SKILL.md` runbooks, or generates staged anti-pattern patches for Observability Studio.

### Beat 3: What will change
1. **Telemetry Trace Friction Analyzer (`src/domain/observability/friction_analyzer.py`)**:
   * Correlates `telemetry_spans` with `messages` history to evaluate turns against the 3 Day-1 friction heuristics (Redundant Verification, Payload Bloat >8 KB, Search Thrashing).
   * Enriches `record_tool_span` in `src/application/kernel/agent_kernel.py` to record `payload_bytes` directly in span metadata for future fast scans.
2. **Tool-to-Skill Resolver (`src/domain/observability/tool_skill_resolver.py`)**:
   * Maps `(agent_id, tool_name)` to the corresponding `SKILL.md` in user data (`$DATA_DIR/packs/<agent_id>/skills/` or `$DATA_DIR/skills/`), never touching the git checkout.
   * Classifies remedies between runbook SOP rules (parameter adjustments) and tool deficiencies (escalation to Factory Studio).
3. **Autonomous Routine Task (`src/application/routines/telemetry_friction_auditor.py`)**:
   * Registers routine `telemetry-friction-auditor` in `src/domain/routines/manifests.py` (paused by default).
   * Dispatched in `src/application/routines/executor.py`.
   * Synthesizes structured recommendations and stages them in SQLite (`proposals` table / recommendations).
4. **Observability Studio Integration (`web/routers/observability.py`, `web/static/modules/studios/observability.js`)**:
   * Adds a "Run Telemetry Audit" button in Observability Studio.
   * Surfaces active "Skill Friction & Runbook Recommendations" with side-by-side Markdown diff preview and 1-click `[ ✅ Apply Patch ]` and `[ ✕ Dismiss ]` controls.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] Telemetry analyzer detects redundant verification loops, payload bloat (>8 KB), and search thrashing from session transcripts.
- [x] Tool-to-skill resolver maps offending tools to their user-data `SKILL.md` runbook path without touching git checkout.
- [x] Routine `telemetry-friction-auditor` is registered, seeded paused by default, and executable via the routine executor.
- [x] Background routine stages recommendations in SQLite without overwriting `SKILL.md` when `auto_apply` is false.
- [x] Observability Studio exposes `/api/observability/friction/audit` and `/api/observability/friction/recommendations` endpoints.
- [x] Observability Studio UI provides an on-demand "Run Telemetry Audit" button and an interactive recommendation card with 1-click adoption and dismissal.
- [x] Applying a recommendation safely updates the targeted `SKILL.md` under `## Common Pitfalls & Forbidden Paths` in user data.
- [x] Comprehensive automated tests cover friction heuristics, tool-to-skill resolution, routine execution, and adoption persistence.
- [x] Preflight validation passes: zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Skills must be updated strictly under user data (`$DATA_DIR/packs/<agent_id>/skills/` or `$DATA_DIR/skills/`), never under the git checkout root.
- No code without Jacob's explicit `build` instruction.

