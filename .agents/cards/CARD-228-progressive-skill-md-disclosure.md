# [CARD-228] Progressive SKILL.md Disclosure

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Extend Capability Catalog C (CARD-217) + UserSkillCatalog progressive disclosure + standing Job/Phase bind (CARD-220)
> **Labels**: type:architecture, type:feature, AutoReiv.Skills, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Catalog/resolve returns skill metadata only**: `id`, `title`, `risk`, HITL flags — **NO** full `SKILL.md` body (qwen context tax / theatre).
2. **Full runbook body loads only when a phase binds/selects that skill** — one body per bind event, never dump-all at resolve.
3. **CRITICAL AGENTS.md invariant**: Chat still lists that agent's **ticked tools** every turn — progressive skills ≠ hiding tool schemas behind skills.
4. **Proof**: resolve payload has no skill body; bind event loads one body; tool schemas still present on Chat turn.
5. **Not this card**: new Studios, hiding tools behind skills, dump-all bodies "for convenience".

### Beat 2: What AutoReiv Does Now
1. Capability Catalog C match-only resolve returns full `CapabilityIndexEntry.model_dump()` (summary/keywords/metadata) — skill rows can carry / leak body-sized blobs via `metadata`.
2. `UserSkillCatalog` already has list=frontmatter / `load_body` / `skill_view` progressive disclosure for Chat runbooks, but standing catalog resolve + Job/Phase path does not bind one body on phase select.
3. Chat mounts ticked tools via `get_tools_for_agent` every turn (CARD-117/121) — must remain untouched by progressive skills.

### Beat 3: What Will Change
1. Resolve serialization: skill matches → metadata-only view (`id`, `title`, `risk`, `requires_hitl`); strip body keys; forbid dump-all skill bodies at resolve.
2. Standing Job/Phase `bind_skill_for_phase` loads **one** `SKILL.md` body via `UserSkillCatalog` / `DynamicSkillLoader`; records `skill_bound` journey/SSE event.
3. Wire bind on phase start (select one matched skill — not dump-all). Chat tool schemas remain on every turn.
4. TDD red→green; scorecard + CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-PSKILL-001]**: Catalog/resolve returns skill **metadata only** (`id`, `title`, `risk`, HITL flags) — no full `SKILL.md` body in resolve payload.
- [x] **[REQ-PSKILL-002]**: Full runbook body loads only when a phase **binds/selects** that skill (one body per bind).
- [x] **[REQ-PSKILL-003]**: Dump-all skill bodies at resolve is forbidden (no `dump_all_skill_bodies` / resolve-with-bodies theatre).
- [x] **[REQ-PSKILL-004]**: Chat still lists that agent's **ticked tools** every turn (AGENTS.md / CARD-117/121 invariant) — progressive skills do not hide tool schemas.
- [x] **[REQ-PSKILL-005]**: Proof: resolve payload has no skill body; bind event loads one body; tool schemas still present on Chat turn path.
- [x] **[REQ-PSKILL-006]**: Automated tests red→green; ruff clean; CHANGELOG + scorecard; push `feat/*` only — never qa/main. Live proof on Jarvis → Done when holds.

---

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: metadata-only resolve + one-body bind + tools still on Chat turn.
- Out of scope: new Studios, replacing `skill_view`, hiding tools behind skills.

## 4. Modules Likely Touched

- `src/application/capabilities/progressive_skills.py` (new)
- `src/application/capabilities/resolver.py` (resolve view)
- `src/application/orchestration/job_phase_orchestrator.py` (bind path)
- `src/application/skills/user_catalog.py` (metadata helpers / index)
- `src/web/routers/capabilities.py` + `chat.py` (bind API / SSE)
- `tests/unit/capabilities/test_progressive_skill_disclosure.py`
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- TDD: red "resolve has no skill body; bind loads one; tools still on Chat" first, then green.
- Extend catalog + UserSkillCatalog + standing bind — do not invent a second skill product.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- `progressive_skills.entry_to_resolve_view` / `skill_metadata_view`: resolve skill rows = id/title/risk/HITL only.
- `ResolveResult.as_dict()` sets `skill_bodies_omitted=true`; body keys stripped from metadata.
- `JobPhaseOrchestrator.bind_skill_for_phase` + `bind_matched_skill_on_phase_start` load one SKILL.md via UserSkillCatalog; durable `skill_bound` standing journey event.
- Chat: `catalog_resolved` includes `skill_metadata` (no bodies); phase loop emits `skill_bound` SSE and injects one bound body into phase context.
- API: `POST /api/capabilities/bind-skill`. UserSkillCatalog `list_skill_metadata` / `index_metadata_into_capability_catalog`.
- AGENTS.md invariant preserved: Chat still mounts ticked tools via `get_tools_for_agent` every turn.
- Tests: `tests/unit/capabilities/test_progressive_skill_disclosure.py` (6) green; related catalog suites green; ruff clean.
- Live smoke: `notes/marathon-card228-live-smoke.json`.
- Status: **Done** when unit + live proof hold; push `feat/*` only.
