# [CARD-240] Unified Job phase chrome on Education origin

> **Status**: Done (merged grok @ ed41e03)
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar — ONE Job phase strip on origin for Education Ask and Chat Ask; reuse Chat chrome
> **Labels**: type:bug, P1, AutoReiv.Chat, Education, AntiTheatre
> **Branch**: `feat/unified-job-chrome-240` (off `grok` @ 636ff3a)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. After CARD-239, Approve on the Education origin Chat works — but while waiting he only saw his prompt.
2. Chat Ask shows the Formulate / Execute / Needs-approval **Job phase strip** live (grape-vine chrome).
3. Education Dual Coding finished with tools + Done-when only — **no** Formulate Done / Execute Running boxes on the origin session.
4. One strip for Education Ask and Chat Ask alike — reuse Chat chrome; no Education-only progress UI fork.

### Beat 2: What AutoReiv Does Now
1. Chat Ask SSE drives `updateJobPhaseFromEvent` → `applyJobPhaseEvent` → `renderJobPhaseStrip` on `job_created` / `phase_start` / `plan_formulated` / `approval_required` / etc.
2. Education Ask (CARD-239) keeps SSE open and `switchTab('chat')` + `selectSession` for HITL — but never feeds those events into Chat's strip.
3. `selectSession` calls `resetJobPhaseStrip()`, so even a one-shot mint paint would be cleared unless re-applied after select.
4. `updateJobPhaseFromEvent` / `renderJobPhaseStrip` live inside `initChatStudio` and are not on the chat controller export surface.

### Beat 3: What Will Change
1. Export Chat job-phase chrome hooks (`isJobPhaseChromeEvent` + controller `updateJobPhaseFromEvent`).
2. Education SSE `onEvent` forwards the same phase events into Chat's strip; after origin `selectSession`, re-apply the mint event so chrome is not blanked by reset.
3. Education must **not** invent a second progress UI — proof = Education Ask shows the same strip live while waiting.
4. Vitest covers Education path mounts/updates strip from `job_created` / `phase_start` / `plan_formulated` / waiting_approval-style events.

---

## 2. Acceptance Criteria (Architect locked — REQ-JOB-CHROME)

- [x] **[REQ-JOB-CHROME-001]**: Education Ask origin Chat shows the same Job phase strip (`jobPhaseStatusStrip` / Formulate·Execute·Needs-approval chrome) as Chat Ask while the standing Job is running — not prompt-only.
- [x] **[REQ-JOB-CHROME-002]**: Education reuses Chat `formatJobPhaseStrip` / `applyJobPhaseEvent` / `updateJobPhaseFromEvent` (or thin forwarder). No Education-only progress bar / phase chrome fork.
- [x] **[REQ-JOB-CHROME-003]**: Strip updates live from Education SSE events (`job_created`, `phase_start`, `plan_formulated`, `approval_required` / waiting_approval-style). Survives `selectSession` reset after origin switch. Proof: Education Ask → strip visible while waiting → Approve still on origin (239).

## 3. Constraints

- Feat off `grok` only. Never qa/main. Do not merge to grok unless asked.
- Chat still lists ticked tools every turn (AGENTS.md).
- Minimal glue — export Chat hooks if needed; Education must NOT invent a second progress UI.
- TDD first (vitest in `tests/unit/frontend/`).

## 4. Hypothesis (verify in TDD)

Education keeps SSE but never calls Chat's `updateJobPhaseFromEvent`; `selectSession` resets the strip on origin switch. Fix = forward Education SSE phase events into Chat chrome + re-apply after select.

## 5. Proof

- Vitest: Education forwarder + Chat event list; strip state from Education-style SSE sequence.
- Operator: Education Ask (Priming/Dual Coding) → origin Chat shows Formulate/Execute strip live while waiting → Approve still on origin.
