# [CARD-295] Chat journey and HITL stay intact without refresh

> **Status**: Done (live Qwen smoke: chit-chat HITL pending after turn_done without reload; session c0269185)  
> **Branch**: `feat/super-marathon-ui`
> **Priority**: P0
> **Created**: 2026-09-13
> **Spec Reference**: docs/cards/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Operator sees Formulate/Execute strips and HITL approve in the same live chat without browser refresh; refresh currently reveals HITL but loses journey chrome (progress honesty failure).

---

## 2. What to Build
Bind Chat UI journey chrome + HITL park to the same job_id/SSE through Formulate to Execute to waiting_approval; durable transcript; live smoke without refresh.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] **[REQ-HITL-JOURNEY-295-001]**: After Formulate\u2192Execute parks HITL, Approve/Deny appears in the **same** live chat thread without browser refresh (stream park + `refreshPendingHitl`).
- [x] **[REQ-HITL-JOURNEY-295-002]**: Journey chrome (job phase strip + inline Formulate/Execute) stays bound to the same `job_id` through park via `updateJobChromeFromEvent`; session select/refresh rehydrates from `/journey`.
- [x] Automated frontend unit tests: `tests/unit/frontend/chat_hitl_journey_295.test.js` (vitest).
- [ ] Jacob live smoke on Jarvis (Qwen) \u2014 see `scratch/CARD-295-live-smoke.md`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Done bar (anti-theatre)

1. Trigger a Chat path that parks HITL (chit-chat or multi-phase job) **without** refreshing the browser.
2. Operator sees Formulate/Execute (or equivalent journey strips) **and** the HITL Approve/Deny control in the **same** live chat thread.
3. Journey chrome remains bound to the same `job_id` / SSE through park; refresh is not required to reveal HITL.
4. After Approve/Deny, journey continues or closes honestly (no silent wait).
5. Automated or scripted live smoke artifact under `scratch/` (not AppData laundry in repo).

## Design lock (UI/UX \u2014 marathon)
- No UI rearrange this card.
- Journey strips + HITL Approve/Deny must appear in the **same live thread** without refresh.
- Bind to the same `job_id` / SSE through park (`waiting_approval`).

## Live proof (2026-09-13)
- Tip: `32f024b`
- Session: `c0269185-c549-49d7-b5a1-f300ddd13129`
- Agent: agent-builder / propose_skill
- Live SSE: turn_done + `/api/approvals/pending` returned `appr_efbbc2a5dc09` with **no page reload** (stream-end `refreshPendingHitl` path).
- Note: this run was ReAct (no Job/Phase); `approval_required` was not on the wire; react_state ended DONE. Job Formulate-Execute park still covered by unit tests + hydrate-on-select.
- Artifact: `scratch/CARD-295-live-smoke.md`

