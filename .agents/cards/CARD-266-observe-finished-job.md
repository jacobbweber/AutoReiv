# [CARD-266] Observe opens finished job_id (receipt honesty)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Follow-on honesty hole after CARD-265. Architect: do not reopen 265. Finished `job_…` must open in Observe — GET must load the tree the Job already wrote. Witnessed live: 265 smoke `observe_http=404` for `job_ed004b29cd44` while same-job stamps were green. Research: same class as Done-on-FAILED theatre. Off `grok` @ `dfa5835`. Do NOT merge grok/qa/main until Jacob says merge feat into grok.
> **Labels**: `type:bug`, `P0`, `Honesty`, `Observability`, `AntiTheatre`
> **Branch**: `feat/observe-finished-job-266` (off `grok` @ `dfa5835`; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Receipt must work**: A finished (or parked) standing Job with a real `job_id` must open in Observe — same tree Chat already wrote. No 404 on a job we just proved.
2. **One obvious GET**: Operators, smokes, and Education “Open in Observe” share one canonical path. Guessing `/api/observe/jobs/{id}` or `/api/jobs/{id}` must not look like the job never existed.
3. **Unknown vs known**: Missing `job_id` is an honest not-found. A job that exists is never an empty fake-success or a 404.
4. **Not this card**: Lumina, telemetry DB, UI marathon, Training Factory, agent rename, merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. Real Studio path `GET /api/observability/standing-journey?job_id=` **already loads** `job_ed004b29cd44` (200, job + phases + checkpoints). Education `openInObserve` uses that.
2. CARD-265 live smoke hit **non-routes** `GET /api/observe/jobs/{id}` then `GET /api/jobs/{id}` — both FastAPI 404. That is the witnessed “soft-404,” not a missing Job row.
3. Unknown ids on standing-journey still return **HTTP 200** with `ok:false` / null job — the other honesty hole (looks open, tree empty).
4. No first-class `/api/observe/jobs/{job_id}` alias. Receipt honesty depends on knowing the long query-string path.

### Beat 3: What Will Change
1. Canonical **`GET /api/observe/jobs/{job_id}`** (alias `GET /api/jobs/{job_id}` optional) returns the standing journey:
   - **200** when `store.get_job` finds the id (body = same payload as `build_standing_journey`).
   - **404** (`ok:false`, no invented job) only when the id is unknown.
2. Standing-journey query keeps working; same existence rule (no 200-empty for unknown).
3. 265 smoke + any Observe load helper use the canonical GET. Live: reopen `job_ed004b29cd44` (or a newly minted finished/parked job) → 200 + same `job_id` tree.
4. TDD + CHANGELOG `[Unreleased]`; push feat only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-OBSREC-001]**: `GET /api/observe/jobs/{job_id}` returns 200 + standing journey when the Job exists (finished, parked, or in-flight).
- [x] **[REQ-OBSREC-002]**: Same GET returns 404 when the Job does not exist — never invent a job row; never 200-empty for unknown.
- [x] **[REQ-OBSREC-003]**: Live Jarvis: a real `job_…` from Chat/delegate opens via that GET (reuse `job_ed004b29cd44` if still on disk, else mint + finish/park). Artifact `notes/marathon-card266-live-smoke.json`. No invented ids.
- [x] **[REQ-OBSREC-004]**: 265-class smoke no longer treats `/api/observe/jobs` 404 as “Observe missing” when the journey exists.
- [x] **[REQ-OBSREC-005]**: Tests red→green; CHANGELOG `[Unreleased]`; push `feat/observe-finished-job-266` only — never qa/main. Hold FF until Jacob says merge feat into grok.

## 3. Constraints & Honor Flags

- Off `grok` @ `dfa5835`. Quality > speed. Do not reopen CARD-265.
- Anti-theatre: receipt GET is real store lookup, not a cosmetic 200 wrapper.
- Out of scope: LLM journey telemetry, token DB, UI layout, Education chrome, Lumina.

## 4. Modules Likely Touched

- `src/web/routers/observability.py` (canonical GET + existence rule)
- `src/application/observability/standing_journey.py` (optional helper: exists vs empty)
- `tests/unit/.../test_card266_observe_finished_job.py` (new)
- `notes/scripts/observe_finished_job_266.py` (new; `--validate` / `--live`)
- `notes/scripts/a2a_same_job_handoff_265.py` (point at canonical GET)
- `CHANGELOG.md`, `notes/marathon-card266-live-smoke.json` (live only)

## 5. Design-room one-liner

Finished `job_…` always opens in Observe — canonical GET 200 with the real tree, 404 only if the job never existed.

## 6. Build lock

Built after Jacob **build CARD-266**. Hold FF until **merge feat into grok**.

## Live proof (Jarvis)
- `notes/marathon-card266-live-smoke.json` ok=true
- reused `job_ed004b29cd44`: observe=200 alias=200 query=200
- fake `job_doesnotexist999`: 404 / 404
- no invented ids
