# [CARD-217] Capability Catalog C (Match-Only Progressive Load)

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: Design room lock after CARD-216; progressive capability match (not dump-all)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Match, do not dump**: When a task/role/keyword arrives, AutoReiv loads only the **matched subset** of capabilities into context - never the whole catalog into the prompt.
2. **One index over primitives**: Catalog entries cover `agent`, `skill` (SKILL.md), `tool`, `pack`, and `routine` with keywords/roles for progressive match.
3. **Trust + risk honesty**: Self-authored entries start at trust tier `candidate` and can promote to `reviewed` then `trusted`. Risk level + HITL flags stay on the entry; unknown kinds fail closed.
4. **Operator path**: Agent Forge / Observability can inspect registry and last match results. That operator view is capped and is **not** a prompt dump-all path.
5. **Not this card**: Self-scaffold write spine (next after C). Do not invent auto-write of new capabilities here.

### Beat 2: What AutoReiv Does Now
1. Skills/tools/agents/routines live in separate registries (Agent Studio, Skills Studio, Routines) with no standing match-only resolve for prompt subsetting.
2. `list_available_skills_and_tools` / skills catalog endpoints can expose broad lists - standing policy for C must not add a full-catalog-into-prompt API.
3. Capability **gaps** (`agent_capability_gaps`) track missing training needs - not a progressive capability index.
4. Observability shows KPIs/logs but not capability match results.

### Beat 3: What Will Change
1. Domain `CapabilityIndexEntry` + trust/risk/HITL fields + durable SQLite `capability_index`.
2. Application resolver: intent/role/keyword -> matched subset only; empty/unknown -> fail closed / empty subset (never dump-all).
3. Resolve API + kernel-friendly hook returning subset; **no** dump-all / full-catalog-for-prompt function or endpoint.
4. Minimal Observability surface to run a match query and see registry rows (operator, capped).
5. Proof: red tests then green for subset match + absence of dump-all. Out of scope: self-scaffold write spine.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-CAPCAT-001]**: Durable capability index entries for primitives `agent | skill | tool | pack | routine` with keywords, roles, trust tier (`candidate|reviewed|trusted`), risk, and HITL flag.
- [x] **[REQ-CAPCAT-002]**: Self-authored entries default to trust tier `candidate`.
- [x] **[REQ-CAPCAT-003]**: Resolve(intent/role/keyword) returns a **matched subset only**; empty/unknown intent fails closed (empty or explicit miss) - never the full catalog.
- [x] **[REQ-CAPCAT-004]**: No dump-all path exists for loading the full catalog into a prompt (no `dump_all` / `list_all_for_prompt` / unbounded full-catalog prompt endpoint).
- [x] **[REQ-CAPCAT-005]**: Persistence in SQLite under data dir (extend existing store/schema patterns).
- [x] **[REQ-CAPCAT-006]**: Minimal Observability/Studio surface shows match results or capped registry rows.
- [x] **[REQ-CAPCAT-007]**: Automated tests: match returns subset; assert no dump-all API/function; ruff clean; work on `feat/*` - never merge `qa`/`main`.
- [x] **[REQ-CAPCAT-008]**: CHANGELOG `[Unreleased]` notes Capability Catalog C thin slice; out of scope called out (self-scaffold write spine).

---

## 3. Constraints & Honor Flags

- Status: **In Review** (thin match-only slice live on Jarvis).
- Branch: continue `feat/standing-job-graph-runtime`. Never push `qa`/`main`.
- Out of scope: self-scaffold write spine, ATF/Lab rewrite, Homelab domain outcomes.
- Anti-theatre: durable `capability_index` rows + resolve subset + Observability match panel; failure mode = empty subset / 400 on unknown kind.

---

## 4. Modules Likely Touched

- `src/domain/capabilities/` - models
- `src/application/capabilities/` - match-only resolver
- `src/infrastructure/memory/schema.py` + `repositories/capability_catalog.py`
- `src/web/routers/capabilities.py` + Observability SPA panel
- `tests/unit/capabilities/`

---

## 5. Marathon Notes

- Slice C thin: index + resolve + persist + obs panel. Write spine is next card.

## 6. Marathon Build Notes (Jarvis 2026-09-10)

- Thin slice landed on `feat/standing-job-graph-runtime`: domain models, match-only resolver, SQLite `capability_index`, `/api/capabilities/resolve` + capped registry, Observability match panel.
- Unit: `tests/unit/capabilities/test_capability_catalog_match_only.py` 9 passed.
- Live smoke (restarted @ feat branch): upsert 5 entries; resolve `wiki search notes`+role librarian → matched 1/5 `subset_only=true`; empty intent → miss; unknown kind → 400; registry capped `prompt_dump_forbidden=true`; OpenAPI only `/resolve` + `/registry`.
- Observability panel `#capCatResolveBtn` / `#capCatResultsBody` present in `index.html` + `observability.js`.
- Write spine still out of scope (next card).
