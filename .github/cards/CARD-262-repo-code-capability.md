# [CARD-262] Repo / code capability path (Homelab-class checkout read)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Bones marathon slice 3 (LAST). Architect Done bars after CARD-261 honesty pack tip. Stack on `feat/honesty-smoke-pack-261` @ a9d764e (includes 260). Catalog + HITL tools/agents that can read a checkout for Homelab-class outcomes; Jobs claim only what was actually read (no invent-about-code). Do NOT merge grok/qa/main.
> **Labels**: type:feat, P0, ControlPlane, RepoTools, Catalog, HITL, Honesty, Homelab, AntiTheatre
> **Branch**: `feat/repo-code-capability-262` (off `feat/honesty-smoke-pack-261` @ a9d764e; push feat only; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Homelab-class Jobs that need code awareness must **read the checkout** via catalog tools - not invent what `AGENTS.md` or source files say.
2. Repo tools are **catalog + CARD-221 HITL only**. Prefer read-only; write/destructive stay REQUIRE_CONFIRM (prefer none in this card).
3. Jobs may claim only what was actually `repo_file_read` / `repo_file_list`'d - no invent-about-checkout.
4. Live proof on Jarvis→Ollama: Job asks about AutoReiv checkout (e.g. AGENTS.md cards) → tool read → grounded answer; without tool / failed read → park or honest fail.
5. This card is ONLY the repo/code capability path. Wave tip = 260+261+262. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. `ProjectFileTools` exist for SDLC project roots; Homelab coordinator only has wiki tools - cannot ground Homelab-class code asks on the AutoReiv checkout.
2. Wiki-thin grounding (CARD-260) fail-closes Wiki path claims; no parallel guard for checkout file claims.
3. Catalog resolve can match wiki tools for note asks; no trusted `repo_file_*` catalog entries for checkout read.

### Beat 3: What Will Change
1. **Catalog-registered read-only tools** `repo_file_list` / `repo_file_read` jailed under configured checkout root (`AUTOREIV_CHECKOUT_ROOT` or AutoReiv detect) with path sandbox - no FS escape; sensitive denylist.
2. **HITL/policy**: read-only in SAFE / auto; no write tools in this card (write stays REQUIRE_CONFIRM if added later).
3. **Standing Job/Chat path**: code-aware outcomes get a repo grounding constraint; claim guard only allows tool-provenanced paths; failed/missing read → honest fail (not invent).
4. Homelab + Assistant packs/profiles gain the read tools. Live `notes/marathon-card262-live-smoke.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-REPO-001]**: Catalog-registered read-only `repo_file_list` / `repo_file_read` under checkout root with path jail (no arbitrary FS escape); sensitive paths denied.
- [x] **[REQ-REPO-002]**: HITL/policy: read-only ALLOW/SAFE per CARD-221 patterns; no write/destructive tools added in this card.
- [x] **[REQ-REPO-003]**: Standing Job/Chat code-aware ask must use the tool and only claim what was read; without tool / failed read → park or honest fail (no invent-about-checkout).
- [x] **[REQ-REPO-004]**: Live proof Jarvis→Ollama: AGENTS.md cards ask grounded via tool; negative no-invent; artifact `notes/marathon-card262-live-smoke.json`.
- [x] **[REQ-REPO-005]**: Tests red→green; CHANGELOG [Unreleased]; push `feat/repo-code-capability-262` only - never qa/main; do not merge to grok.

## 3. Constraints

- Feat stacked on `feat/honesty-smoke-pack-261` @ a9d764e (one FF gets 260+261+262). Never qa/main. Never merge grok.
- Repo tools = catalog + 221 HITL only. Prefer read-only. `memory.db` ≠ `storage.db`. Honesty. Quality > speed.
- Extend standing Chat + catalog - do not invent a second orchestrator. Lumina parked.

## 4. Modules Likely Touched

- `src/application/skills/repo_tools.py` (new)
- `src/application/orchestration/repo_code_grounding.py` (new)
- `src/infrastructure/agents/registry.py` (register)
- `src/application/safety/tool_policy_gate.py` (SAFE)
- `src/domain/agents/profiles.py` + `platform-packs/{assistant,homelab}/pack.json`
- `src/web/routers/chat.py` (standing path + claim guard)
- `tests/unit/skills/test_repo_tools.py`, `tests/unit/orchestration/test_card262_repo_code_grounding.py`
- `CHANGELOG.md`, `notes/marathon-card262-live-smoke.json`

## 5. CoS smoke prompts

```
1) Positive: Using repo_file_read, what does AGENTS.md say about cards? Done-when: answer cites only content returned by repo_file_read of AGENTS.md. Keep under 120 words.
2) Negative: Using repo_file_read, what does TotallyFakeCheckoutFile-ZZZ.md say about the three beats? Done-when: if read fails, honest fail / park - do not invent. Keep under 80 words.
```

## 6. Marathon Build Lock

- Architect Done bars locked - Builder implements now.
- TDD where practical; live Jarvis→Ollama proof required.
- Do NOT merge to grok/qa/main.

## 7. Marathon Build Notes

(see Done section below)

## Marathon Build Notes (Done)

- **Tip**: pending final commit on eat/repo-code-capability-262 (stacked on eat/honesty-smoke-pack-261 @ 9d764e; includes 260). Not merged to grok/qa/main.
- **Live smoke** (
otes/marathon-card262-live-smoke.json, pass=true, Jarvis→Ollama):
  - positive AGENTS.md cards → grounded via 
epo_file_read — job_ec9100fbda9e
  - negative missing file → no invent / honest fail — job_feb5218e38ea
- **Done bars**: catalog 
epo_file_list/
epo_file_read jailed + denylist; SAFE HITL; standing Chat repo grounding + claim guard; Homelab+Assistant packs.
- **Design-room**: Homelab-class checkout reads via catalog repo_file_*; Jobs claim only tool-provenanced paths — failed/missing read honest-fails, never invents.
- Wave tip = 260+261+262. Stop here — parent owns FF ask.
