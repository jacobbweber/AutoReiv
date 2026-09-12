# [CARD-270] Foundation audit - Training Factory truth (gap → trusted or honest can't)

> **Status**: Ready
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit after CARD-269. Architect Done: real capability gap → candidate→sandbox→HITL→trusted (or honest "can't") — no invent-theatre; Approve makes it usable on the next Job. Stack on `feat/agent-instructions-backfill-269` @ `e5aeb39`. Hold FF until Jacob merge phrase.
> **Labels**: `type:chore`, `P0`, `FoundationAudit`, `TrainingFactory`, `AntiTheatre`
> **Branch**: `feat/training-factory-truth-270` (off 269 tip; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Training Factory must be **real**, not a costume: a real capability gap becomes a candidate, runs sandbox, waits HITL, then becomes **trusted** — or AutoReiv says honestly it **can't**.
2. After Approve, the new tool/skill is usable on the **next Job** (not just a green toast).
3. No invent-theatre: do not mark gaps "trained" before promote; do not synthesize tools at promote that never passed sandbox.
4. **Not this card**: 271 ReAct/Job spine, 272 install/Compose, UI marathon, Lumina.

### Beat 2: What AutoReiv Does Now
1. `POST /api/agents/{id}/gaps/{gap_id}/train` queues an ATF job then immediately sets gap status to **`trained`** — theatre (HITL/sandbox not done).
2. `POST /api/agent_training_factory/jobs/{id}/promote` can **ToolSynthesizer.synthesize_tool** when `files_to_write` is empty — invent at Approve, skipping sandbox.
3. CARD-255 closed scaffold spine (candidate→trusted + rollback); this card audits **ATF / Needs Training** path specifically.
4. Gap statuses are effectively `pending` | `trained` | `dismissed` — no in-flight `training` or terminal `cant`/`failed`.

### Beat 3: What Will Change
1. Gap lifecycle: `pending` → `training` (train starts) → `trained` (only after promote **approved** + pack write) | `cant`/`failed` (reject, verify exhausted, or promote refused for missing sandbox artifacts).
2. Promote **refuses** empty/unverified pack files with honest error — no last-second ToolSynthesizer invent.
3. Link `gap_id` on factory job (objectives/metadata) so promote/reject updates the originating gap.
4. TDD + live smoke `notes/marathon-card270-live-smoke.json`: gap→train status honesty; promote without sandbox → can't; approve with sandbox artifacts → next Job sees tool (or catalog/trusted resolve).
5. CHANGELOG; push feat; hold FF until merge.

## 2. Acceptance Criteria

- [ ] **[REQ-FAUD-270-001]**: Train starts → gap status `training` (not `trained`); only promote-approve sets `trained`.
- [ ] **[REQ-FAUD-270-002]**: Promote with no sandbox-verified pack files → honest refuse (`cant`/4xx); no ToolSynthesizer invent at gate.
- [ ] **[REQ-FAUD-270-003]**: Promote reject / verify-exhausted path sets gap `cant` or `failed` (operator-visible).
- [ ] **[REQ-FAUD-270-004]**: Approve with real files → pack/tool usable on next Job (import or trusted catalog).
- [ ] **[REQ-FAUD-270-005]**: Tests + live artifact + CHANGELOG; push feat only; hold FF. No qa/main.

## 3. Constraints

- Quality > speed. Reuse ATF + gaps + CARD-255 spine semantics — do not invent a second factory.
- Out of scope: 271–272, UI marathon, horizon D.

## 4. Modules Likely Touched

- `src/web/routers/gaps.py`
- `src/web/routers/agent_training_factory.py`
- `src/infrastructure/memory/repositories/capability_gaps.py` (status values)
- `tests/unit/.../test_card270_*.py`
- `notes/scripts/training_factory_truth_270.py`
- `CHANGELOG.md`

## 5. Design-room one-liner

Training Factory truth: real gap → sandbox → HITL → trusted, or honest can't — Approve usable next Job; no invent-theatre.

## 6. Build lock

CoS keep-rolling / Architect 270 Done bar: Builder may implement immediately on this Ready card.
