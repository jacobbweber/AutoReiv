# [CARD-264] Scoped repo write/patch under HITL (REQUIRE_CONFIRM)

> **Status**: In Review
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon slice 2 after CARD-263 Homelab-class outcome smoke. Architect Done bars: checkout write/patch = REQUIRE_CONFIRM via CARD-221; Deny leaves tree unchanged; rollback/revert path; live Park→Approve proves file change; deny leaves tree clean. Stack on `feat/homelab-outcome-smoke-263` tip `b6beb50`. Do NOT start CARD-265. Do NOT merge grok/qa/main.
> **Labels**: type:feat, P0, ControlPlane, RepoTools, HITL, Honesty, Homelab, AntiTheatre, WritePath
> **Branch**: `feat/repo-write-hitl-264` (off `feat/homelab-outcome-smoke-263` @ b6beb500ddee881759bae5a7a65040a38c622d7f; push feat only; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Homelab-class Jobs that must **edit the checkout** use catalog-scoped `repo_file_write` / `repo_file_patch` — never silent FS writes, never invent paths.
2. Every write/patch is **REQUIRE_CONFIRM** (CARD-221) → existing HITL park/resume. Deny = **tree unchanged** (tool never ran).
3. After an approved write, operator has a **rollback/revert** path that restores prior content (or deletes if the write created the file).
4. Live on Jarvis→Ollama: Ask parks on write → Approve → file change proven on disk; separate Deny probe leaves tree clean. Same `job_id` honesty; Journey reflects park/approve.
5. This card is ONLY scoped repo write HITL. Do not start CARD-265. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. CARD-262 shipped read-only `repo_file_list` / `repo_file_read` (SAFE/ALLOW). CARD-263 proves Homelab-class Wiki + repo read outcome honesty.
2. `write_project_file` already REQUIRE_CONFIRM under SDLC project roots — no parallel checkout write tools jailed under `AUTOREIV_CHECKOUT_ROOT`.
3. ToolPolicyGate + HITLApprovalEngine high-risk set cover write_project_file / wiki writes; repo write names were absent.

### Beat 3: What Will Change
1. Catalog-registered `repo_file_write` + `repo_file_patch` jailed under checkout root (same sandbox/denylist as 262).
2. Policy: both tools in `_DEFAULT_REQUIRE_CONFIRM` + HITL high-risk — Deny never executes (tree unchanged).
3. Durable pre-write snapshot + `repo_file_rollback` restores prior bytes / removes created file.
4. Homelab + Assistant packs gain write/patch (HITL). Live `notes/marathon-card264-live-smoke.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-RWHITL-001]**: Catalog-registered scoped `repo_file_write` and `repo_file_patch` under checkout jail + sensitive denylist (extend CARD-262 sandbox; no FS escape).
- [x] **[REQ-RWHITL-002]**: Write/patch = REQUIRE_CONFIRM via CARD-221 ToolPolicyGate + HITL high-risk; Deny leaves tree unchanged (tool never ran).
- [x] **[REQ-RWHITL-003]**: Rollback/revert path restores prior content (or deletes if write created the file) after an approved write.
- [ ] **[REQ-RWHITL-004]**: Live Jarvis→Ollama: Park → Approve → file change proven; Deny probe leaves tree clean; artifact `notes/marathon-card264-live-smoke.json`.
- [x] **[REQ-RWHITL-005]**: TDD red→green; CHANGELOG [Unreleased]; push `feat/repo-write-hitl-264` only — never qa/main; do not merge to grok. Do not start 265.

## 3. Constraints

- Feat stacked on `feat/homelab-outcome-smoke-263` tip `b6beb50` (includes 260+261+262+263). Never qa/main. Never merge grok.
- Extend RepoCheckoutTools + ToolPolicyGate + HITL — do not invent a second orchestrator or parallel HITL.
- Prefer minimal surface: write + patch + rollback. No git_commit in this card. `memory.db` ≠ `storage.db`. Honesty. Quality > speed.

## 4. Modules Likely Touched

- `src/application/skills/repo_tools.py` (write / patch / rollback + register)
- `src/application/safety/tool_policy_gate.py` (`_DEFAULT_REQUIRE_CONFIRM`)
- `src/application/kernel/hitl_engine.py` (high-risk set)
- `src/infrastructure/agents/registry.py` (already boots RepoCheckoutTools)
- `src/domain/agents/profiles.py` + `platform-packs/{assistant,homelab}/pack.json`
- `tests/unit/skills/test_card264_repo_write_hitl.py` (new)
- `notes/scripts/repo_write_hitl_264.py` (validate + live)
- `.github/cards/CARD-264-repo-write-hitl.md`
- `CHANGELOG.md`, `notes/marathon-card264-live-smoke.json`

## 5. CoS smoke prompts

```
1) Approve path: Using repo_file_write, create notes/_card264_live_probe.txt with content exactly "CARD264-APPROVE-PROBE". Done-when: after I Approve the HITL park, the file exists with that content. Keep under 80 words.
2) Deny path: Using repo_file_write, create notes/_card264_deny_probe.txt with content "SHOULD-NOT-LAND". Done-when: I Deny the HITL park and the file does not exist. Keep under 60 words.
3) Rollback: After an approved write to notes/_card264_rollback_probe.txt, call repo_file_rollback for that path so prior content (or absence) is restored. Done-when: tree matches pre-write.
```

```
python notes/scripts/repo_write_hitl_264.py --validate
python notes/scripts/repo_write_hitl_264.py --live
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD first; live Jarvis→Ollama proof required.
- Do NOT merge to grok/qa/main. Do NOT start 265.

## 7. Marathon Build Notes

Stacked on CARD-263 tip `b6beb500ddee881759bae5a7a65040a38c622d7f`. Unit/validate green. Live job_ids must come from Jarvis SSE — never invented.
