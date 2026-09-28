# [CARD-268] Foundation audit — Job honesty re-smoke (bones 1–5)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit slice 1 after CARD-266 Observe receipt on `grok` @ `185f1ca`. Architect feed 268→272. Prove bones-closed 1–5 still hold on tip under qwen: phase strip + Journey match Chat; HITL Approve/Reject; Wiki/repo provenance; kill/resume + Forge same `job_…`. Reuse CARD-261 honesty pack + frozen eval (252) — evidence re-smoke, not new product. No UI, no Lumina, no DAG canvas. Do NOT merge grok/qa/main until Jacob says merge feat into grok.
> **Labels**: `type:chore`, `P0`, `FoundationAudit`, `Honesty`, `AntiTheatre`
> **Branch**: `feat/foundation-honesty-resmoke-268` (off `grok` @ `185f1ca`; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Before Training Factory / Instructions / install work, **re-prove** the Job honesty spine on today’s tip — no theatre, no fragile “it worked last week.”
2. Bones 1–5 (Architect Done picture): copyable `job_…` + phase strip + Journey match Chat; Observe opens it (266); HITL Approve/Reject; Wiki/repo claims tool-provenanced only; kill/resume and Forge Approve keep the same `job_…`.
3. Live under **qwen** on Jarvis. Frozen pack green = gate; red blocks calling foundation “done.”
5. **Not this card**: UI marathon, Lumina, dossier, plugins, MCP server, DAG canvas, rename System, 269–272 impl.

### Beat 2: What AutoReiv Does Now
1. CARD-261 honesty/smoke pack + CARD-252 frozen eval exist and were green on earlier tips.
2. Tip advanced through 257–266 (honesty, kill/resume, Wiki-thin, repo, HITL write, A2A same-job, Observe receipt).
3. No single **foundation-audit** artifact that re-runs bones 1–5 against current `grok` and records pass/fail with job_ids.

### Beat 3: What Will Change
1. Standing script `notes/scripts/foundation_honesty_resmoke_268.py` (`--validate` / `--live`) that:
   - Runs honesty pack classes that cover Done-on-FAILED / provenance / kill_resume (261).
   - Proves Observe receipt for a live `job_…` (266 GET).
   - Proves HITL Approve lands / Deny clean **or** cites last green 264 artifact + one live HITL probe if cheap.
   - Proves kill/resume or Forge same-`job_…` path still holds (259/251 class).
2. Artifact `notes/marathon-card268-live-smoke.json` with per-bar results + real job_ids (no invent).
3. CHANGELOG `[Unreleased]`; push feat only. Hold FF until Jacob merge phrase.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-FAUD-268-001]**: Live tip under qwen: standing Job shows `job_…` + Journey/phase strip matching Chat (no Done-on-FAILED / honesty theatre).
- [x] **[REQ-FAUD-268-002]**: Observe canonical GET opens that finished/parked `job_…` (266); fake id = 404.
- [x] **[REQ-FAUD-268-003]**: HITL write path still honest — Approve lands file **or** Deny leaves tree clean (reuse 264 probe pattern).
- [x] **[REQ-FAUD-268-004]**: Wiki/repo claims on the smoke Job are tool-provenanced only (no invent paths).
- [x] **[REQ-FAUD-268-005]**: Kill/resume **or** Forge Approve continues the **same** `job_…` (259/251 class).
- [x] **[REQ-FAUD-268-007]**: Operator UI: Chat phase strip + Journey match the live `job_…`; Observe Studio loads the same id (screenshot or live checklist in artifact).
- [x] **[REQ-FAUD-268-006]**: Artifact + tests/`--validate` green; CHANGELOG; push `feat/foundation-honesty-resmoke-268` only — never qa/main. Hold FF until Jacob says merge feat into grok.

## 3. Constraints & Honor Flags

- Off `grok` @ `185f1ca`. Quality > speed. Evidence-only — no new orchestrator.
- Prefer reuse of `honesty_smoke_pack_261`, `frozen_eval_pack_252`, `observe_finished_job_266`, `repo_write_hitl_264` over rewriting.
- Out of scope: 269–272, UI, horizon D.

## 4. Modules Likely Touched

- `notes/scripts/foundation_honesty_resmoke_268.py` (new)
- `notes/marathon-card268-live-smoke.json` (live)
- `tests/unit/orchestration/test_card268_foundation_honesty_resmoke.py` (thin wrapper / fixtures)
- `CHANGELOG.md`
- Optional thin glue only — no product redesign

## 5. Design-room one-liner

Foundation audit 268: re-smoke bones 1–5 on tip under qwen with Chat/Observe UI proof — honesty, receipt, HITL, provenance, same-`job_…` — or call red.

## 6. Build lock

Built after Jacob **build CARD-268**. Live green; hold FF until **merge feat into grok**.

## Live proof (Jarvis)
- `notes/marathon-card268-live-smoke.json` ok=true (mode live_resume_failed after UI/HITL parse fix)
- Honesty pack green under qwen (pass/tool/kill_resume/honesty/timeout/gate)
- Observe + UI: `job_1b943c65852f` timeline loaded; Chat phase strip attached
- Kill/resume same job `job_e9a2f34311c9`; Forge same job `job_c261685f06d8`
- HITL 264: Approve landed + Deny tree clean (`pass=True`)
