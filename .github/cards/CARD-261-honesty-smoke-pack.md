# [CARD-261] Standing Honesty / Smoke Pack (tip merge gate)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon slice 2. Architect Done bars after CARD-260 Wiki-thin tip. Stack on `feat/wiki-thin-grounding-260` @ cdf0988. Freeze stress classes (timeout/gate/tool/honesty + kill/resume) as standing tip merge gate — red blocks FF. Live proof pack runs on tip; green required before merge ask. Do NOT start 262. Do NOT merge grok/qa/main.
> **Labels**: type:chore, P0, ControlPlane, Honesty, SmokePack, MergeGate, AntiTheatre
> **Branch**: `feat/honesty-smoke-pack-261` (off `feat/wiki-thin-grounding-260` @ cdf0988; push feat only; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Stress classes from CARD-258/259 must stop living as ad-hoc notes only. Freeze them as a **standing tip merge gate**: `timeout | gate | tool | honesty | kill_resume | pass`.
2. **Red blocks FF**: Done-on-FAILED theatre, honesty theatre (no Not-done rewrite), and silent SSE death (abort/SSE end without kill checkpoint / orphan worker).
3. Honesty (CARD-257) and kill/resume (CARD-259) are required coverage — never Done-on-FAILED; kill must checkpoint + resume same `job_id`.
4. Live proof on Jarvis→Ollama: pack runs on tip; green required before any merge ask. Artifact `notes/marathon-card261-live-smoke.json`.
5. This card is ONLY the standing honesty/smoke pack + merge gate. Do not start CARD-262. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. CARD-258 stress pack JSON + CARD-259 kill/resume smoke exist as marathon notes, not a CI/preflight gate.
2. Unified preflight (`.agents/skills/rtm-sync/scripts/preflight.py`) runs lint/tests/smoke/RTM — no honesty stress class gate.
3. Operators can miss Done-on-FAILED / silent SSE death regressions between tips because classification is manual.

### Beat 3: What Will Change
1. **Classifier module** `src/application/orchestration/honesty_smoke_pack.py` — freeze stress + red classes with TDD.
2. **Standing script** `notes/scripts/honesty_smoke_pack_261.py` — `--validate` (CI/preflight fixtures) and `--live` (Jarvis→Ollama).
3. **Wire merge gate**: preflight stage + runbook `docs/architecture/honesty-smoke-pack-merge-gate.md`; document in this card.
4. Live `notes/marathon-card261-live-smoke.json` with per-class results; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-HSP-001]**: Stress classes `timeout|gate|tool|honesty|kill_resume|pass` are a standing tip merge gate — red (Done-on-FAILED / honesty theatre / silent SSE death) blocks FF.
- [x] **[REQ-HSP-002]**: Standing script classifies those classes and exits non-zero on red honesty / Done-on-FAILED / silent SSE death.
- [x] **[REQ-HSP-003]**: Wired into preflight (`--validate`) + documented merge gate runbook; card references both.
- [x] **[REQ-HSP-004]**: Live proof on tip (Jarvis→Ollama); includes honesty (no Done-on-FAILED) and kill/resume (259); artifact `notes/marathon-card261-live-smoke.json`.
- [x] **[REQ-HSP-005]**: Tests red→green; CHANGELOG [Unreleased]; push `feat/honesty-smoke-pack-261` only — never qa/main; do not merge to grok. Do not start 262.

## 3. Constraints

- Feat stacked on `feat/wiki-thin-grounding-260` @ cdf0988 (one FF gets both). Never qa/main. Never merge grok.
- Reuse/refresh CARD-258 stress scenarios where useful; must include honesty + kill/resume.
- Quality > speed. Do not invent a second orchestrator.

## 4. Modules Likely Touched

- `src/application/orchestration/honesty_smoke_pack.py` (new)
- `notes/scripts/honesty_smoke_pack_261.py` (new)
- `tests/unit/orchestration/test_card261_honesty_smoke_pack.py` (new)
- `docs/architecture/honesty-smoke-pack-merge-gate.md` (new)
- `.agents/skills/rtm-sync/scripts/preflight.py` (wire `--validate` stage)
- `CHANGELOG.md`, `notes/marathon-card261-live-smoke.json`

## 5. CoS / merge-gate commands

```
python notes/scripts/honesty_smoke_pack_261.py --validate
python notes/scripts/honesty_smoke_pack_261.py --live
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis→Ollama proof required.
- Do NOT merge to grok/qa/main. Do NOT start 262.

## 7. Marathon Build Notes

(see Done section below)

## Marathon Build Notes (Done)

- **Tip**: pending final commit on `feat/honesty-smoke-pack-261` (stacked on `feat/wiki-thin-grounding-260` @ `cdf0988`). Not merged to grok/qa/main.
- **Validate**: `python notes/scripts/honesty_smoke_pack_261.py --validate` exit 0 — all 6 stress classes + red negatives block FF.
- **Live smoke** (`notes/marathon-card261-live-smoke.json`, pass=true, Jarvis→Ollama @ tip `d224ba3`):
  | Class | Source | Result |
  |-------|--------|--------|
  | pass | live `job_e2f9a96aa2ff` | DONE |
  | tool | live `job_4aeee3510126` | missing-note path |
  | kill_resume | live `job_3b08557f677f` | abort checkpointed+resumable; same job_id DONE |
  | honesty | fixture fill (CARD-257 Not-done) | not red |
  | timeout | fixture fill (CARD-258) | not red |
  | gate | fixture fill (waiting_approval) | live need-sources ask completed pass |
- **Red**: zero (`done_on_failed` / `silent_sse_death` absent). merge_gate.allowed=true.
- **Wire**: preflight stage Honesty Smoke Pack (CARD-261); runbook `docs/architecture/honesty-smoke-pack-merge-gate.md`.
- **Design-room**: Standing tip merge gate freezes timeout|gate|tool|honesty|kill_resume|pass; red Done-on-FAILED / silent SSE death blocks FF.
- Stop here — parent owns CARD-262.
