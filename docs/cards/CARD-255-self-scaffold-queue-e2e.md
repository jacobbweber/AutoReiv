# [CARD-255] Self-Scaffold Queue E2E (Candidate -> Trusted + Rollback)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Candidate skill/tool -> sandbox -> HITL -> trusted; rollback path. Live: Gap Ask -> candidate in Forge -> Approve -> next Job can use it. Research: Copy candidate->sandbox->HITL->trusted. Adapt: Education gap Ask proof. Skip: auto-trust new tools. Reuse CARD-251 Forge Approve same job_id resume; CARD-233 mid-job scaffold exists - close full loop E2E + rollback.
> **Labels**: type:architecture, type:feature, P1, ControlPlane, SelfScaffold, Forge, HITL, AntiTheatre
> **Branch**: `feat/self-scaffold-queue-e2e-255` (off `feat/verifier-replan-harden-254` @ b6a70e9)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Close the **full self-scaffold queue loop** end-to-end: candidate skill/tool -> sandbox -> HITL Approve -> **trusted**; plus a real **rollback** path.
2. Live proof (Education gap Ask adaptation): Gap Ask opens a **candidate in Forge** -> Approve -> a **next Job** can match/use the new trusted skill/tool.
3. **Never auto-trust** new tools/skills - standing Job catalog resolve uses **trusted only** until HITL promote.
4. Reuse **CARD-251** Forge Approve -> same `job_id` resume for HITL on scaffold candidates; reuse **CARD-233** mid-job gap -> 218 spine (do not invent a second product).
5. Mark CARD-254 Done. Do **not** invent CARD-257.

### Beat 2: What AutoReiv Does Now
1. CARD-218 spine: draft -> sandbox -> version -> HITL -> trusted + Forge candidate queue + rollback API.
2. CARD-233: mid-job gap opens candidate + park; promote re-resolves matched IDs on the **same** job.
3. CARD-251: Forge Approve resumes the parked same `job_id` (no orphan).
4. Standing catalog `resolve` still matches **candidate** trust tiers - next Job could auto-trust without HITL (theatre vs Done bar).
5. No single Education-gap-Ask -> Forge -> Approve -> **next Job uses it** + rollback E2E proof artifact.

### Beat 3: What Will Change
1. Standing Job catalog resolve path is **trusted-only** (no auto-trust of candidates).
2. Queue-loop helper: Education-style gap Ask -> candidate in Forge -> sandbox/HITL (251) -> trusted; **next Job** resolve includes the skill; rollback restores prior trusted.
3. TDD red->green for full path + rollback + no auto-trust; live smoke `notes/marathon-card255-live-smoke.json`.
4. CHANGELOG + scorecard; push `feat/*` only - never qa/main; do not merge to grok; do not invent 257.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-SSQ-001]**: Full path candidate -> sandbox -> HITL -> trusted (218 spine + 233 mid-job + 251 Forge Approve); no shortcut auto-trust.
- [x] **[REQ-SSQ-002]**: Rollback path restores prior trusted snapshot after a promoted revision.
- [x] **[REQ-SSQ-003]**: Standing Job catalog resolve is **trusted-only** - candidates never auto-match into a next Job.
- [x] **[REQ-SSQ-004]**: Live Education gap Ask proof: Gap Ask -> Forge candidate -> Approve -> **next Job** can use the trusted skill/tool; artifact `notes/marathon-card255-live-smoke.json`.
- [x] **[REQ-SSQ-005]**: Automated tests red->green; CHANGELOG + scorecard; push `feat/self-scaffold-queue-e2e-255` only - never qa/main; do not invent 257.

## 3. Constraints

- Branch `feat/self-scaffold-queue-e2e-255` off `feat/verifier-replan-harden-254` @ b6a70e9. Never qa/main. Do **not** merge to grok.
- Copy candidate->sandbox->HITL->trusted; adapt Education gap Ask; skip auto-trust.
- Reuse 233 + 251 + 218 - do not invent a parallel scaffold product.
- Do **not** invent CARD-257.

## 4. Out of scope

- CARD-257+
- Merging to grok / qa / main
- Auto-trusting new tools without HITL
- Replacing 218 spine or 251 resume semantics

## 5. Proof

- Unit: full loop + rollback + trusted-only next Job + no auto-trust.
- Live: `notes/marathon-card255-live-smoke.json` (Gap Ask -> Forge -> Approve -> next Job uses skill).

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- Standing Job catalog resolve is **trusted-only** (`CapabilityCatalogResolver.resolve(trusted_only=True)` from `create_job_from_catalog_resolve` + mid-job re-resolve) - candidates never auto-match (no auto-trust).
- Queue E2E helper `self_scaffold_queue_e2e.py`: Education gap Ask -> Forge candidate (233) -> sandbox/HITL Approve (251 same job_id) -> trusted; **next Job** uses skill; rollback restores prior trusted pack.
- Reuses 218 spine + 233 mid-job + 251 Forge Approve - no second scaffold product.
- Tests: `tests/unit/orchestration/test_self_scaffold_queue_e2e_255.py` (6) + 218/233/251/catalog suites green.
- Live smoke PASS: `notes/marathon-card255-live-smoke.json`.
- Status: **Done**. Do not invent CARD-257. Push `feat/*` only; never merge to grok.
