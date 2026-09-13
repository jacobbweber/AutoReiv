# [CARD-251] Forge Approve resumes same job_id (origin session)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Parked HITL in Forge Approve resumes **same** `job_id` (origin session); no orphan. Live: Education/Chat create parks -> Forge Approve -> Execute continues; Observe one tree. Research: Forge Approve = origin session / same correlation id, not new Job. Skip soft-delete parked Jobs.
> **Labels**: type:bug, P1, ControlPlane, Forge, HITL, AntiTheatre, JobResume
> **Branch**: `feat/forge-approve-job-resume-251` (off `feat/control-plane-serve-hygiene-256` @ 298a8c4)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When Education/Chat mints a standing Job that **parks** for HITL (incl. mid-job scaffold park), **Forge Studio Approve** must resume the **same** `job_id` on the **origin session** - Execute continues, Observe shows **one** tree.
2. Forge Approve must **not** mint an orphan Job, invent a second correlation id, or soft-delete the parked Job as a "cleanup".
3. CARD-239/240 already put Approve + Job chrome on origin Chat. The gap is the **Forge Studio Approve** path (scaffold candidate queue / mid-job HITL).
4. Do **not** start CARD-252 in this slice.

### Beat 2: What AutoReiv Does Now
1. Mid-job scaffold (CARD-233) parks the Job (`waiting_approval`) and stamps `metadata.job_id` / `phase_id` on the Forge candidate.
2. Forge UI Approve calls `POST /api/capabilities/scaffold/{id}/approve` which only runs `spine.hitl_approve` - promotes trusted but **does not** `promote_mid_job_scaffold`, **does not** `start_phase` unpark, **does not** resume origin Chat.
3. A later Education/Chat outcome ask on the same session can call `create_job_from_catalog_resolve` while the parked Job is still open -> **orphan** second tree in Observe.
4. Chat Approve path (239) already does `submitHitlDecision` + `executeChatTurn('', { resume: true })` on origin - Forge does not.

### Beat 3: What Will Change
1. Forge Approve (scaffold with `metadata.job_id`) -> `promote_mid_job_scaffold` + `start_phase` on the **same** parked `job_id`; return `job_id` + `session_id` + `resumed=true`. Never mint. Never soft-delete.
2. Forge UI: on resumed approve, select origin session + Chat resume turn; Observe standing journey loads that `job_id` (one tree).
3. Chat standing mint guard: if session already has open `waiting_approval` Job, **do not** mint a second Job (orphan_prevented); operator Approves/resumes same id.
4. TDD + live smoke `notes/marathon-card251-live-smoke.json`. Mark CARD-256 Done (already). Do not start 252.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-FORGE-RESUME-001]**: Forge Approve on a mid-job parked candidate resumes the **same** `job_id` (origin `session_id` / correlation) - promote + unpark/`start_phase`. No new Job.
- [x] **[REQ-FORGE-RESUME-002]**: Parked Jobs are **not** soft-deleted / cancelled by Forge Approve. Observe standing journey shows **one** tree for that `job_id` after approve.
- [x] **[REQ-FORGE-RESUME-003]**: Forge UI after Approve triggers origin Chat resume (or returns enough for Execute to continue); Education/Chat create -> park -> Forge Approve -> Execute continues same id.
- [x] **[REQ-FORGE-RESUME-004]**: Chat standing outcome mint does **not** create an orphan Job while an open `waiting_approval` Job exists on the session (`orphan_prevented`).
- [x] **Proof**: pytest green + live smoke JSON + CHANGELOG + push on feat branch (never merge to grok).

## 3. Constraints

- Branch `feat/forge-approve-job-resume-251` off `feat/control-plane-serve-hygiene-256` @ 298a8c4 (or grok+256 tip). Never qa/main. Do **not** merge to grok.
- Extend CARD-218/233 spine + Chat resume - do not invent a second approval product.
- Skip soft-delete parked Jobs. Chat still lists ticked tools every turn (AGENTS.md).
- Do not start CARD-252.

## 4. Out of scope

- CARD-252+
- Soft-deleting parked Jobs
- Replacing Chat origin Approve (239/240 stay)

## 5. Proof

- Unit: Forge Approve same `job_id`; no soft-delete; orphan mint prevented; Observe one tree kinds.
- Live: park -> Forge Approve -> continue same `job_id` -> `notes/marathon-card251-live-smoke.json`.
