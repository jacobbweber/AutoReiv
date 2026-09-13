# [CARD-290] LLM Providers — Refresh Models honesty (no ghost Custom/Saved)

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Priority 1 (Jacob + CoS 2026-09-13). UI marathon paused until provider config is 100% green. Screenshot: vLLM @ `http://192.168.1.218:8006/v1` discovers 1 live model (`qwen3.8-27b-fp8`) but Active Default still shows `Qwen/Qwen2.5-Coder-32B-Instruct (Custom / Saved)`.
> **Labels**: `type:bug`, `settings`, `llm-provider`, `priority-1`
> **Branch**: `feat/llm-provider-refresh-honesty-290` off `qa`
> **Note**: CARD-275–289 reserved on unmerged `feat/backlog-bd-capture-275` (B/D backlog stubs).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. LLM Providers Settings must be trustworthy end-to-end: preset, base URL, credentials, **Refresh Models**, and Active Default Model.
2. **No ghost models** — if Refresh discovers N models from the live vLLM/Ollama endpoint, the picker must not keep a stale “(Custom / Saved)” entry as if it were live.
3. Provider APIs and tool-calling correctness stay Priority 1 with this (CARD-274 fixed stream args; this card is Settings discovery/selection honesty).
4. UI marathon stays paused until this is green.

### Beat 2: What AutoReiv Does Now
1. `GET /api/models/discover` queries the active gateway provider (`gateway.list_models`) and returns live models (status text: “Discovered 1 model(s) from vllm …”).
2. In `src/web/static/modules/studios/settings.js` → `discoverAndPopulateModels()`, after live options are filled, if `state.savedDefaultModel` is **not** in the discovered list, the UI **injects** an option labeled `` `${targetModel} (Custom / Saved)` `` and can leave it selected.
3. Result (live screenshot): discovered = `qwen3.8-27b-fp8 (vllm)` only; ghost = `Qwen/Qwen2.5-Coder-32B-Instruct (Custom / Saved)` still highlighted as Active Default.
4. Save Provider persists `provider_settings.default_model_id` even when that id is absent from the live endpoint.
5. CARD-274 (merged on `qa`) fixed vLLM stream tool-arg merge; it does not fix Settings discovery UI honesty.

### Beat 3: What Will Change
1. Deep code review of provider config path: Settings UI ↔ `/api/models/discover` (+ refresh) ↔ `provider_settings` store ↔ gateway adapters (`list_models` for vLLM/Ollama/OpenAI-compat).
2. **Refresh Models** populates Active Default from **live discovery only** (plus explicit Auto-Select). Stale saved ids must not appear as live “(Custom / Saved)” ghosts.
3. If saved default is missing from live list: clear selection to Auto-Select / first live model, show honest warning (“saved default not on endpoint”), and do not silently re-save the ghost.
4. Optional: separate “orphaned saved default” affordance (clear / keep-as-override) only if Architect Done bars allow — default is **no ghost in the live picker**.
5. Regression: Refresh against Spark vLLM and (if available) Ollama shows only live models; Save then reload keeps honesty.
6. TDD: unit/integration covering discover response + settings.js selection rules (or backend contract if logic moves server-side).

---

## 2. Acceptance Criteria (CoS Done bars 2026-09-13)

- [ ] **[REQ-SET-290-001]**: No ghost / (Custom / Saved) entry in the Active Default Model picker unless that model id is **live on the current provider endpoint**.
- [ ] **[REQ-SET-290-002]**: **Refresh Models** rebinds the UI to live discovery for **that provider only** — vLLM/OpenAI-compat GET /v1/models (or Ollama tags) via /api/models/discover; count and options match live response.
- [ ] **[REQ-SET-290-003]**: **Save Provider** persists a default_model_id that is on the served list (or explicit Auto-Select); cannot stick a missing/stale id after Refresh.
- [ ] **[REQ-SET-290-004]**: Live proof: Chat or Standing Job tool-call on Spark vLLM still succeeds after honest model selection (regression with CARD-274 stream-arg merge).
- [ ] **[REQ-SET-290-005]**: Deep review note (or card section) lists modules touched + any follow-ons (purpose-matrix / per-agent overrides) without silent drops.

## 3. Constraints

- Feats off `qa` only. Do not reopen Job spine or UI marathon shells.
- Prefer honesty over preserving stale defaults.
- Coordinate with Architect if “keep offline override” is a real operator need — default recommendation is kill ghosts.
- Strict TDD; update CHANGELOG `[Unreleased]` on build.

---

## 4. Likely modules

- `src/web/static/modules/studios/settings.js` (`discoverAndPopulateModels`)
- `src/web/routers/settings.py` (`/api/models/discover`, provider save)
- `src/application/gateway/*` + `src/infrastructure/gateway/*` (`list_models`)
- `provider_settings` in AppData settings store

---

## 5. Build lock

Ready card scaffolded. Build when Jacob / CoS says **build CARD-290** (CoS: scaffold without waiting on Architect ceremony; Architect may tighten bars in-room).
