# [CARD-372] Dogfood Overnight Skill Improvement Harvest Routine

> **Status**: Done  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:dogfooding`, `routines`, `skills`, `verification`, `autonomous-loop`

---

## 1. Why / Intent
Dogfood and live-validate the overnight skill improvement harvest loop (`skill-eval-sleep`), verifying that conversational failures and tool execution errors are harvested from SQLite, clustered into gap patterns, filtered through safety checker gates, drafted into actionable uncommitted proposals, and applied to pack `SKILL.md` runbooks upon operator approval without corrupting state, frontmatter, or source files.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When an agent encounters failures in conversations or tool calls during daily operations, the overnight routine must wake up, detect the failure pattern across SQLite telemetry, synthesize a concise and useful SOP refinement, and present it as an approval card. Jacob needs verification that this autonomous loop actually delivers high-quality runbook improvements rather than prompt noise, hallucinations, or dangerous writes to core code.

### Beat 2: What AutoReiv Does Now
- `skill-eval-sleep` is defined in `src/domain/routines/manifests.py` as a paused weekday 21:00 cron routine with backend execution engine in `src/application/routines/skill_eval_sleep.py`.
- Unit tests in `tests/unit/routines/test_skill_eval_sleep.py` test isolated functions with mock stores, but there is no full-system integration test or dogfooding run verifying that real failed turns produce an intelligible, compliant proposal, that the snapshot rollback works on live disk files, and that the operator approval flow correctly updates the pack's `SKILL.md`.

### Beat 3: What Will Change
- Create an automated end-to-end dogfooding test suite (`tests/integration/routines/test_dogfood_skill_eval_sleep.py`) exercising the full harvest-to-approval lifecycle.
- Seed synthetic, realistic failed turns and tool errors into an isolated test state store.
- Execute `run_skill_eval_job()` and assert:
  1. Failed turns are harvested within the configured lookback window.
  2. Failures are clustered by pack and tool, producing an insight $\le 400$ characters.
  3. Safety checker gates (`harvest_gate`) fail closed if a candidate attempts to target `src/` Python files or lacks a valid `pack_id`.
  4. An uncommitted proposal is stored in `skill_proposals` table with a snapshot of the pre-change `SKILL.md`.
  5. Approving the proposal through the application service / API cleanly updates the pack `SKILL.md` without damaging YAML frontmatter.
  6. Reverting the proposal restores the pre-change `SKILL.md` bit-for-bit from the snapshot.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Synthetic failure turns with tool execution errors in SQLite are harvested within the lookback window.
- [x] `mine_pack_gaps` clusters failures by pack and tool, producing an insight $\le 400$ characters.
- [x] `harvest_gate` blocks candidates attempting to modify core `src/` Python files or missing pack IDs.
- [x] An uncommitted proposal is created in SQLite with `status="draft"` and an accurate snapshot ID.
- [x] Approving the proposal updates `SKILL.md` cleanly without corrupting frontmatter or tools.
- [x] Reverting the proposal restores the snapshot bit-for-bit.
- [x] Automated regression tests pass via `pytest tests/integration/routines/test_dogfood_skill_eval_sleep.py`.
- [x] Zero lint errors via `ruff check src tests`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Live data root isolation must be strictly preserved (no writes to repo root or checkout live data).
- Single isolated `feat/card-372-dogfood-skill-eval-sleep` branch cut from `qa` upon Jacob's `build` approval.
