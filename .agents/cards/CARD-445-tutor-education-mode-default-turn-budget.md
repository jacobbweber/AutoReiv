---
id: CARD-445
title: "Global Default Turn Budget 50 for All Agents (One-Time Upgrade From 10)"
status: Done
completed: 2026-09-24
created: 2026-09-23
updated: 2026-09-24
branch: qa
adr: none
parent: CARD-438
related:
  - CARD-443
  - CARD-444
  - CARD-449
  - CARD-450
  - CARD-460
  - CARD-461
  - CARD-462
labels:
  - type:feature
  - area:agents
  - area:kernel
  - area:tutor
  - P1
---

# [CARD-445] Global Default Turn Budget 50 for All Agents (One-Time Upgrade From 10)

> **Status**: Done (Jacob: "merge to qa" 2026-09-24 8:52 PM ET; merged `--no-ff` into qa)
> **Created**: 2026-09-23 - **Rewritten**: 2026-09-24 after Jacob's decisions (was "Tutor Education-Mode Default Turn Budget")
> **Observed during**: CARD-438 live test - Tutor Learning OS quiz/flashcard tool loops ran out of the hidden default of 10 turns.
> **ADR Reference**: none (a default value change, not an architecture change)
> **Labels**: `type:feature`, `area:agents`, `area:kernel`, `area:tutor`, `P1`
> **Parent**: [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md)
> **Related**: [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md), [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-449](./CARD-449-scalar-operator-edits-max-turns-must-not-lock-platform-pack-promotion.md), [CARD-450](./CARD-450-studio-ui-platform-pack-promotion-skips.md), [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md), [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md), [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md)

---

## Plain words: what a "turn" is

A turn is one pass of the agent's work loop inside a single reply: the model thinks, maybe calls a tool, reads the result, and goes again. `max_turns` caps how many passes one reply may take. The cap exists to stop runaway loops, stop one reply hogging the GPU, keep the conversation from overflowing the context window, and stop a reply going silent for minutes.

---

## Jacob's decisions (locked 2026-09-24)

| Decision | Value |
|----------|-------|
| Allowed range | **1-1000** (0 stays rejected) - unchanged |
| Fresh-install default | **50 for every agent** (no Tutor-only pack number) |
| Existing agents | One-time upgrade: stored value **exactly 10 -> 50**; any other value kept |
| Operator values | Saved Agent Studio values survive restart and platform sync |
| Skill text | Fix flashcard-turn `SKILL.md` "default budget of 10" |
| Pack manifest `max_turns` | **Not added** (see Beat 3, item 6) |

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the card - **still no product code** |
| **`build`** | Change the default to 50 everywhere it lives for agents, add the one-time 10 -> 50 upgrade, fix the SKILL text |
| **`merge to qa`** | After In Review + the Human Verification Runbook below passes on Jarvis |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | Nothing open. CARD-449 (operator scalars survive sync) and CARD-450 (reset/backup) are Done. |
| **Related** | [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md) - what happens when the budget runs out (summary instead of a bare error) |
| **Related** | [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md) - catches loops early so a bigger budget is not wasted |
| **Related** | [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md) - owns the orchestration / job-phase `max_turns=10` fields left alone here |
| **Blocked by** | Nothing |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Out of the box, every agent should get 50 passes per reply, not a hidden 10. Ten is too few for real tool work (Learning OS quiz/flashcard turns, Developer work).
2. My own choices win. If I set Tutor to 100 or Developer to 25 in Agent Studio, that stays through restarts and platform updates.
3. Agents still sitting on the old 10 get moved to 50 once, automatically, and it never happens again.

### Beat 2: What AutoReiv does now

1. The implicit agent default of **10** lives in several places:
   - `src/domain/kernel/models.py:87` - `AgentProfile.max_turns: int = Field(default=10, ge=1, le=1000)`
   - `src/domain/agents/guardrails.py:98` - `int(payload.get("max_turns", 10))`; range check 1-1000 on the next line
   - `src/web/routers/agents.py:41` - request model `max_turns: Optional[int] = 10`
   - `src/infrastructure/memory/schema.py:254` - `custom_agents.max_turns INTEGER DEFAULT 10` (`agent_overrides.max_turns`, line 214, has no default)
   - `src/infrastructure/memory/repositories/settings.py:701` and `:844` - `max_turns=r["max_turns"] or 10`
   - `src/application/skills/agent_builder_tools.py:239` - new-agent scaffold draft `"max_turns": 10`
   - `src/application/orchestration/handoff_engine.py:330` - child-agent fallback `getattr(target_profile, "max_turns", 10) or 10` (the envelope bound itself belongs to CARD-462)
   - `src/web/static/modules/studios/forge.js:272` (`agent.max_turns || 10`) and `:479` (`parseInt(..., 10) || 10`)
   - `src/web/templates/index.html` - `#forgeMaxTurnsInput value="10"` (min 1, max 1000)
2. `src/application/agents/registry.py:143` overlays `override.max_turns` when set; the kernel loops `range(agent.max_turns)` (`agent_kernel.py` sync ~L949, stream ~L1325) and ends with `Execution terminated: Max turn budget of {N} reached.` There is **no** separate education-mode budget.
3. Platform packs (`platform-packs/*/pack.json`) carry no `max_turns`. `AgentPackManifest` (`src/application/agent_packs/schema.py` ~L537) has no such field and ignores unknown keys. The new-install data dict in `agent_packs/service.py` (~L577) omits `max_turns`, so fresh installs fall through to the default above; the existing-agent path keeps `existing.max_turns` (~L558).
4. Agent Studio Save writes `max_turns` to `custom_agents` / `agent_overrides` (DB is the source of truth). CARD-449 `_preserve_operator_scalars` keeps operator scalars through platform sync.
5. Live Jarvis values today (`custom_agents` / `agent_overrides`): **autoreiv 10 / -**, **direct 10 / -**, **developer 25 / 25**, **tutor 100 / 100**.
6. `platform-packs/tutor/skills/flashcard-turn/SKILL.md:42` says both paths "fit under the default budget of 10 without raising `max_turns`".
7. Tests that pin 10: `tests/unit/kernel/test_agent_profile.py:36` (`assert profile.max_turns == 10`). `tests/unit/education/test_card444_flashcard_turn_skill_efficiency.py` reads the default from `AgentProfile.model_fields`, so it follows automatically.

### Beat 3: What will change

1. **One constant.** Add `DEFAULT_AGENT_MAX_TURNS = 50` in the domain layer (next to `AgentProfile`) and use it in every agent site in Beat 2 item 1. No new literal 10s or 50s scattered around.
2. **Schema default.** `custom_agents.max_turns` default becomes 50 for new databases. Existing rows are handled by item 3, not by a table rebuild.
3. **One-time upgrade (idempotent, recorded).** On startup, after platform pack sync (the same boot path as CARD-443/449 promotion), run once:
   - For each agent, if the stored `custom_agents.max_turns` is exactly 10, set it to 50; if `agent_overrides.max_turns` is exactly 10, set it to 50.
   - Leave every other value alone (Developer 25, Tutor 100 stay).
   - Record completion in settings key `agent_max_turns_default_50_applied` = `{applied_at, raised: [agent ids]}`. If the key exists, do nothing. This also makes the double bootstrap in CARD-459 harmless.
4. **Frontend.** Agent Studio shows 50 for a new or unset agent (`forge.js` fallbacks and `#forgeMaxTurnsInput` default).
5. **SKILL text.** Replace "fit under the default budget of 10 without raising `max_turns`" with wording that does not hard-code a number (e.g. "stay far under the default turn budget").
6. **Pack manifest decision: not added.** A global default does not need `max_turns` on `AgentPackManifest`, install, or export: new installs already omit it and fall through to the profile default, and existing agents keep their DB value. Adding it would create a second source of truth that platform sync would then have to guard. Explicit non-goal: pack export does not carry `max_turns`.

**Out of scope (owned elsewhere):**

- What happens at the limit (a summary instead of a bare error) -> [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md).
- Loop detection changes -> [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md).
- Orchestration / job / handoff `max_turns=10`: `domain/orchestration/models.py` (`HandoffEnvelope` L43, Phase / PhaseSpec L175-184, 212, 245-247, 304, 410), `job_phase_orchestrator.py:179`, `phases.max_turns DEFAULT 10` (schema L38). Nothing enforces those phase values today; the kernel uses `agent.max_turns`. Handoff children use `min(max(envelope, profile, 10), 15)` (`bound_child_max_turns`), so a delegated child is still capped at **15** even when its profile says 50 - that cap is CARD-462's to revisit. -> [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md).
- `developer_authoring` / `developer_mediation` internal budget of 8 (a separate flow).

### Beat 4: What dies today

1. Literal `10` default for agent `max_turns` in `models.py`, `guardrails.py`, `routers/agents.py`, `settings.py` (both `or 10` fallbacks), `agent_builder_tools.py`, the `handoff_engine.py:330` profile fallback, `forge.js` (both fallbacks) and `#forgeMaxTurnsInput value="10"`.
2. `custom_agents.max_turns INTEGER DEFAULT 10` for new databases.
3. The "default budget of 10" sentence in `platform-packs/tutor/skills/flashcard-turn/SKILL.md`.
4. `assert profile.max_turns == 10` in `tests/unit/kernel/test_agent_profile.py` (replaced by a 50 assertion via the constant).
5. The old Tutor-only plan (a pack-declared education-mode number of 40/50) - retired by Jacob's global-default decision.

---

## 2. Acceptance criteria (EARS)

- **[REQ-445-001]** THE SYSTEM SHALL use one shared constant `DEFAULT_AGENT_MAX_TURNS = 50` for every agent-level `max_turns` default (profile model, guardrails fallback, agents API request model, settings repository fallbacks, agent builder scaffold, handoff child-profile fallback, Agent Studio UI default).
- **[REQ-445-002]** WHEN an agent is installed fresh (no stored value), THE SYSTEM SHALL give it `max_turns` 50, visible in `GET /api/agents/{id}` and Agent Studio.
- **[REQ-445-003]** THE SYSTEM SHALL keep accepting 1-1000 and SHALL keep rejecting 0 and values above 1000.
- **[REQ-445-004]** WHEN the app starts and settings key `agent_max_turns_default_50_applied` is absent, THE SYSTEM SHALL raise every stored `max_turns` of exactly 10 (in `custom_agents` and `agent_overrides`) to 50, leave all other values unchanged, and write the key with `applied_at` and the list of raised agent ids.
- **[REQ-445-005]** WHILE `agent_max_turns_default_50_applied` exists, THE SYSTEM SHALL NOT run the upgrade again, even if an operator later saves 10 on purpose or bootstrap runs twice.
- **[REQ-445-006]** WHEN an operator saves a `max_turns` in Agent Studio, THE SYSTEM SHALL keep that value across restart and platform pack sync.
- **[REQ-445-007]** THE flashcard-turn `SKILL.md` SHALL NOT state a numeric default budget.
- **[REQ-445-008]** THE SYSTEM SHALL NOT add `max_turns` to `AgentPackManifest` or pack export (explicit non-goal).

### Tests (write first at build)

1. `test_agent_profile.py`: default equals `DEFAULT_AGENT_MAX_TURNS` (50); 0 and 1001 rejected; 1 and 1000 accepted.
2. Guardrails: payload without `max_turns` validates to 50.
3. Upgrade: a temp DB with agents at 10 / 25 / 100 -> after one run: 50 / 25 / 100; settings key lists only the raised id; a second run changes nothing; an operator saving 10 after the key exists stays 10.
4. Sync: an operator value of 100 survives a platform pack sync (extend the existing CARD-449 test rather than duplicating it).
5. Grep guard: no literal `max_turns` default of 10 remains in the agent sites in Beat 2 item 1.
6. Frontend: Agent Studio shows 50 for an agent with no stored value.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa on Jarvis and restart the app with the serve-hygiene skill (one serve on `:8000`).
2. Open **Agent Studio** -> **AutoReiv**: Max turns shows **50** (was 10). Open **Direct**: **50**.
3. Open **Developer**: still **25**. Open **Tutor**: still **100**.
4. Restart the app again. All four values are unchanged (the upgrade does not re-run).
5. Optional: `python -c "import sqlite3,os; c=sqlite3.connect(os.path.expandvars(r'%LOCALAPPDATA%\AutoReiv\database\autoreiv.db')); print(c.execute('select value_json from settings where key=?',('agent_max_turns_default_50_applied',)).fetchone())"` prints `applied_at` and `raised: ["autoreiv", "direct"]`.

**Failure signals:** Developer or Tutor changed; AutoReiv or Direct still at 10; values change again on the second restart.

---

## 4. Constraints

- Docs-only until **build**.
- Do not touch operator-chosen values other than exactly 10, and only once.
- Known and accepted: restoring a CARD-450 backup that contains 10 puts 10 back (an explicit operator action). A deliberately chosen 10 is raised once by the upgrade.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 5. Build notes (2026-09-24, branch `feat/card-445-global-turn-budget-50`)

**What shipped**

1. `DEFAULT_AGENT_MAX_TURNS = 50` in `src/domain/kernel/models.py`, used by `AgentProfile`, `guardrails.py`, `routers/agents.py` (`AgentProfilePayload`), both `settings.py` fallbacks, `agent_builder_tools.py`, and the `handoff_engine.py` child-profile fallback. Frontend: `forge.js` exports `DEFAULT_AGENT_MAX_TURNS = 50` for both fallbacks; `#forgeMaxTurnsInput value="50"`. A unit contract keeps the JS/HTML value equal to the Python constant.
2. `custom_agents.max_turns DEFAULT 50` for new databases. Existing databases keep the old column default (SQLite cannot alter a default without a table rebuild), which is harmless: both inserts (`save_custom_agent_profile`, `save_agent_override`) always bind `max_turns` explicitly - covered by a test that inserts a fresh profile into a DB and reads back 50.
3. `src/infrastructure/agents/max_turns_upgrade.py` `apply_default_max_turns_upgrade(store)` + repository `raise_agent_max_turns(from, to)`: updates only the `max_turns` column on rows stored at exactly 10 in `custom_agents` and `agent_overrides` (never `user_modified`, per CARD-449), then writes settings key `agent_max_turns_default_50_applied` = `{applied_at, from: 10, to: 50, raised: [...]}`. Called from `install_platform_agent_packs` right after `promote_platform_packs` (startup path); failures are logged, never block boot. If the key exists it does nothing.
4. flashcard-turn `SKILL.md`: no numeric budget. The Tutor pack is not locked, so CARD-443 promotion copies the new SKILL.md into AppData at startup (checked live below).
5. `test_card444_flashcard_turn_skill_efficiency.py` now keeps its own tight `CARD444_EFFICIENCY_CEILING = 10`, so the bigger default cannot hide a flashcard-turn efficiency regression.
6. Pack manifest: no `max_turns` (REQ-445-008 test).

**Correction found during build:** handoff children are clamped by `bound_child_max_turns` to 10..15, so a delegated child still gets at most 15 turns. Left to CARD-462 (open decision 5 there).

**Tests:** new `tests/unit/agents/test_card445_global_turn_budget.py` (28 tests, Red first). Broad `tests/unit`: 2002 passed, 11 skipped, 2 failed - CARD-454 linter (known) and `test_req_388_002` (fails on clean qa too: live Developer is named "Super Developer"; tracked by CARD-455). Platform-pack suites (unit agent_packs + pack integration contracts): 132 passed, 5 skipped, same 388 failure. Vitest: 750 passed, 5 failed (the known CARD-456 set). Playwright smoke: 7/7 (run with a scratch data dir - see CARD-467). Honesty smoke `--validate`: green. Ruff on touched files clean (full-repo ruff: the 10 known CARD-454 errors); ESLint `forge.js` clean (full lint: known CARD-456 errors in education/study/settings modules).

**Backup before live restart:** `%LOCALAPPDATA%\AutoReiv\backups\autoreiv-pre-card445-20260924-203202.db` (integrity ok). Pre-values: autoreiv 10, direct 10, developer 25/25 (locked), tutor 100/100; keep-customizations on.

---

## 6. Reply phrases

- Refine the card: say **continue**.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.
