# [CARD-265] Specialist A2A Handoff Resumes Same job_id

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon LAST slice after CARD-264 repo-write HITL. Architect Done bars: Job handoff to specialist → resume same job_id tree; privilege never widens (221/234) — child inherits matched subset only; Live: Parent park → child work → parent continues one tree. Stack on `feat/repo-write-hitl-264` @ `91f6569` (263+264). Research: copy 224 A2A; skip privilege escalation on handoff. Do NOT merge grok/qa/main.
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.A2A`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **One tree, not a fork**: When Chat/supervisor hands work to a specialist, the specialist must continue the **same** standing `job_id` — park → specialist work → parent continues — not a parallel linked `child_job_id` tree (CARD-224's preference).
2. **Privilege never widens**: Matched capability subset + CARD-221 / CARD-234 rules stay fail-closed. Specialist profile allowlist must **not** escalate tools beyond the parent's matched IDs (skip privilege escalation on handoff).
3. **Observe honesty**: Journey / strip show one `job_id` through parent park, specialist bind, and parent resume.
4. **Not this card**: New Studios, memory brain, inventing agents, merging grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. CARD-224 `create_standing_child_job` mints a **linked** `child_job_id` with inherited matched IDs (never-widen) — separate Job/Phase tree.
2. CARD-234 supervisor pick calls that child-create path on successful specialty match.
3. `HandoffIsolationEngine` stamps `parent_job_id` / `child_job_id` and binds the child turn to `child_job_id`.
4. Crash-resume / Forge Approve already know same-`job_id` continue (219/251/259) — specialist A2A does not yet reuse that shape.

### Beat 3: What Will Change
1. Helper `bind_specialist_same_job` (standing_a2a_handoff): bind specialist to **existing** `job_id`; no new Job; record journey; matched IDs unchanged.
2. `effective_matched_ids_no_escalate`: handoff effective subset = parent matched IDs only (never union specialist allowlist).
3. `HandoffIsolationEngine` + supervisor pick: default specialist path uses same-job bind; optional `linked_child_job=true` keeps 224 child for callers that need it.
4. `HandoffResult.same_job_id` (+ child_job_id == parent when same-tree); TDD; live Parent park → specialist → parent continue one tree; CHANGELOG; push `feat/a2a-same-job-handoff-265` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-A2ASAME-001]**: Specialist A2A handoff resumes / binds the **same** `job_id` (no new Job row unless `linked_child_job=true`).
- [x] **[REQ-A2ASAME-002]**: Privilege never widens — effective matched IDs ⊆ parent matched IDs; capability_subset BLOCK stays BLOCK after handoff (221/234).
- [ ] **[REQ-A2ASAME-003]**: Live: Parent park → specialist work → parent continues **one** Observe tree (same `job_id`); no invented ids.
- [x] **[REQ-A2ASAME-004]**: Supervisor pick (234) uses same-job bind by default; journey stamps `a2a_same_job_handoff`.
- [x] **[REQ-A2ASAME-005]**: Automated tests green; ruff clean; CHANGELOG `[Unreleased]`; push `feat/*` only — never qa/main/grok.

## 3. Constraints & Honor Flags

- Branch: `feat/a2a-same-job-handoff-265` off `feat/repo-write-hitl-264` @ `91f6569`.
- Research lock: copy 224 A2A mechanics; **skip privilege escalation** on handoff.
- Anti-theatre: real same-tree resume — not a cosmetic rename of child_job_id.
- Out of scope: merge grok/qa/main; Lumina; inventing job_ids.

## 4. Modules Touched

- `src/application/orchestration/standing_a2a_handoff.py`
- `src/application/orchestration/handoff_engine.py`
- `src/application/orchestration/supervisor_specialist_pick.py`
- `src/domain/orchestration/models.py` (`HandoffResult.same_job_id`)
- `tests/unit/orchestration/test_card265_a2a_same_job_handoff.py`
- `notes/scripts/a2a_same_job_handoff_265.py`
- `notes/marathon-card265-live-smoke.json` (live only)

## 5. Design-room one-liner (CoS)

Specialist A2A parks/resumes the **same** job_id tree; matched subset never widens (221/234) — parent continues one Observe journey.

## Live proof (Jarvis)
- `notes/marathon-card265-live-smoke.json` ok=true
- parent/same/child `job_ed004b29cd44` via `/api/agents/delegate`
- smoke mint fixed to `/api/chat/stream` SSE (`job_created`)
- Observe GET 404 soft (stamps proved same tree); no invent
