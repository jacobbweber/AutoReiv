# [CARD-252] Frozen operator eval pack (Chat + Education + Wiki + Forge resume)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Frozen eval pack: 3-5 operator asks (Chat + Education + Wiki Job) with Observe job_id checklist; CI/scriptable. Live: All green on grok+qwen; fail = card not Done. Include Forge resume ask per Research sharpen. Skip: smoke-JSON-only theatre without runnable pack.
> **Labels**: type:test, P1, ControlPlane, EvalPack, AntiTheatre, Observe, CI
> **Branch**: `feat/frozen-eval-pack-252` (off `feat/forge-approve-job-resume-251` @ c70075e)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Lock a **frozen** operator eval pack (3-5 asks) covering **Chat outcome Job**, **Education Ask/quiz**, **Wiki Job**, and **Forge Approve -> same job_id** (Research sharpen) - each with an **Observe `job_id` checklist**.
2. Pack must be **CI/scriptable** (pytest or python under `notes/scripts`) - not vibes, not smoke-JSON-only theatre.
3. Live Done bar: all asks green on grok+qwen evidence (prior marathon live smokes + live Observe probes); any fail = card not Done.
4. Mark CARD-251 Done. Do **not** start CARD-253.

### Beat 2: What AutoReiv Does Now
1. Wave-2 operator eval (`notes/marathon-wave2-operator-eval-2026-09-11.md`) proved operator feel but left standing Job/`job_id` gaps for asks 2-4.
2. Individual card live smokes (236 Chat mint, 237 Education Ask, 242 quiz/retention, 251 Forge resume) exist as JSON, but there is **no single frozen pack + runnable validator** that binds them to an Observe checklist.
3. CI runs full pytest but does not gate a frozen control-plane operator pack.

### Beat 3: What Will Change
1. Author frozen pack definition + operator checklist (asks, expect, Observe path).
2. Ship `notes/scripts/frozen_eval_pack_252.py` + `tests/unit/eval/test_frozen_eval_pack_252.py` that validate pack structure, prior smoke artifacts (`ok` + `job_id`), and (live mode) health + Observe standing-journey for recorded ids.
3. Record live pack run in `notes/marathon-card252-live-smoke.json`. Mark 251 Done. Push feat branch only.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EVAL-PACK-001]**: Frozen pack defines 3-5 operator asks covering Chat outcome Job, Education Ask/quiz path, Wiki Job, and Forge approve->same job_id; each ask lists Observe `job_id` checklist items.
- [x] **[REQ-EVAL-PACK-002]**: Runnable CI-friendly script/pytest under `notes/scripts` and/or `tests/unit/eval` validates pack structure + prior marathon smoke artifacts (not smoke-JSON-only theatre).
- [x] **[REQ-EVAL-PACK-003]**: Live pack run records results in `notes/marathon-card252-live-smoke.json`; all asks green (artifact `ok` + Observe path where live ids exist); fail = not Done.
- [x] **[REQ-EVAL-PACK-004]**: CARD-251 remains Done; CHANGELOG + card Proof checked; no merge to grok; do not start 253.
- [x] **Proof**: pytest green for pack validator + live smoke JSON + push on feat branch.

## 3. Constraints

- Branch `feat/frozen-eval-pack-252` off `feat/forge-approve-job-resume-251` @ c70075e. Never qa/main. Do **not** merge to grok.
- Prefer validating prior live smoke artifacts + live Observe probes over re-running multi-minute LLM walks every CI.
- Skip inventing a second eval product / dashboard.

## 4. Out of scope

- CARD-253+
- Merging to grok / qa / main
- Replacing card-specific unit suites

## 5. Proof

- Unit: pack schema + artifact gates green in pytest.
- Live: `notes/marathon-card252-live-smoke.json` all asks green.
