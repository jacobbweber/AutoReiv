# [CARD-239] P0 — HITL / session cohesion (parent owns phase Approve)

> **Status**: Done (merged grok @ 636ff3a)
> **Created**: 2026-09-11
> **Spec Reference**: CoS P0; Architect REQ-HITL-ORIGIN-001..003; hold CARD-238 merge until fixed
> **Labels**: type:bug, P0, AutoReiv.HITL, Education, Chat
> **Branch**: `feat/hitl-session-cohesion-239` (off `grok` @ 5fc219d)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When Education Ask (or Chat) mints a standing Job and the agent needs approval, **Approve must show on the same conversation he started** — not a different orphan session he has to hunt for.
2. He waited forever on the Education/origin chat, then found Approve under **Formulate / Execute** phase sessions and approved blindly — unsafe and theatre.
3. Education Jobs list should make **Needs approval** obvious (deep-link back to the right Chat surface) if HITL is parked on a phase child.
4. **Hold** merge of `feat/education-learning-os-238` until this is fixed and Priming/Dual Coding re-verified.

### Beat 2: What AutoReiv Does Now
1. Standing Jobs spawn phase child sessions (`…::phase::…`); HITL parks with `session_id` on the phase child.
2. Chat pending-HITL poll can render cards, but session selection often leaves the operator on the parent while Approve lives on the child (or vice versa).
3. Education Ask (CARD-237) creates a **fresh** session and **cancels the SSE stream after `job_created`** — so the origin Education session is not the live HITL surface; phase Formulate/Execute sessions become the only place Approve appears.
4. Education Jobs row opens Chat by `session_id` but does not surface **Needs approval** status.

### Beat 3: What Will Change
1. **Invariant:** Parent/origin session (Education Ask session or Chat session that minted the Job) **owns** HITL UX for that Job — Approve/Reject visible there for phase-child parks (`parent` + `::phase::` / child ids).
2. Education Jobs (and/or Chat Job strip): when Job/phase is `waiting_approval`, show **Needs approval** + deep-link that selects the correct session and focuses the HITL card.
3. Education Ask **keeps the SSE open** after `job_created` (no early cancel) so the origin thread receives HITL; Chat may auto-select that session.
4. Triage **wiki_overview ERR** on Observe Journey if cheap (fail-closed catalog gap); otherwise note follow-on.
5. Proof: Priming or Dual Coding Ask → one origin Chat shows Approve (no orphan hunt) → Job + Wiki write-back + Observe still work. Then Jacob may merge 238.

---

## 2. Acceptance Criteria (Architect locked — REQ-HITL-ORIGIN)

- [x] **[REQ-HITL-ORIGIN-001]**: Phase-child `approval_required` parks are visible and actionable from the **originating parent session** Chat UI (Education Ask session or minting Chat session). Operator does not need to manually open Formulate/Execute orphans.
- [x] **[REQ-HITL-ORIGIN-002]**: Education Jobs row (and/or Chat Job strip) shows **Needs approval** when applicable, with a deep-link that opens the HITL surface.
- [x] **[REQ-HITL-ORIGIN-003]**: Education Ask must **not** cancel the SSE stream after `job_created` — keep the origin thread live for HITL/events. Proof: Priming or Dual Coding → Approve on origin path → Job + Wiki + Observe. CARD-238 merge blocked until Jacob confirms.
- [ ] **[REQ-HITL-ORIGIN-004]** (stretch): Journey `wiki_overview` ERR triaged as fail-closed catalog gap (fix or documented follow-on).

## 3. Constraints

- feat off `grok` only. Never qa/main. Do not merge 238 until this card's proof passes.
- Prefer extending Chat HITL poll + Education Jobs — not a second approval product.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD order (CoS): parent-session HITL ownership first; Education Needs-approval deep-link next; wiki_overview stretch last.

## 4. Hypothesis (verify in TDD)

Education's early SSE cancel after `job_created` + HITL bound to `::phase::` session ids is the orphan path. Fix = keep SSE + parent-session HITL projection + Needs-approval deep-link (not "find the phase chat").

## 5. Proof

- Vitest: education SSE keep-alive + Needs approval; chat pprovalBelongsToOriginSession.
- Operator: Education Ask (Priming/Dual Coding after merging 238 onto this feat) → origin Chat shows Approve → Wiki + Observe. Hold 238→grok until Jacob confirms.
