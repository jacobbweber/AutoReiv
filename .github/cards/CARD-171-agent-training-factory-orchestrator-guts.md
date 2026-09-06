# [CARD-171] Agent Training Factory orchestrator guts (replace costume runner)

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/; CARD-159; CARD-164; CARD-165; CARD-166; CARD-169; CARD-125
> **Labels**: `type:architecture`, `type:feat`, `AutoReiv.Orchestration`, `AutoReiv.Wiki`

---

## 1. Why / Intent

AutoReiv is a **local-first control plane** for a roster of portable **Agent Packs**. Forever core: **Assistant** + **AutoReiv** (platform SRE). Scale = new **user packs**, not refactoring the plane.

**Agent Training Factory** is the built-in system capability that researches, authors, verifies, optimizes, and promotes skills/tools into a target user pack (Hyper-V admin, finance, gardening, Ansible, …). Same loop every time; contents differ. Local large models make deep multi-phase reasoning affordable.

**Walked (2026-09-05 Jacob):** Surface (Train Agent, monitor, backlog, auto-train, promote) stays. **Guts replace costume:** today’s `FactoryRunner` is a deterministic template walker with five persona packs that never run as LLM workers. That cannot research a role, ground in Wiki, or truly certify tools.

**Official name:** Agent Training Factory. Code/modules/APIs use `agent_training_factory` consistently. No personas / no factory agents — **phases only**.

This is a **product card**. Do not implement until Jacob says **build**. Do not name third-party products in repo artifacts.

---

## 2. Locked decisions

| Lock | Decision |
|------|----------|
| Name | **Agent Training Factory** (feature). Code: `agent_training_factory`. |
| Shape | One built-in **FactoryOrchestrator** (system capability), not a roster of factory personas. |
| Phases | Ground → Blueprint → Author → Verify → Optimize → Promote |
| Extensibility | Thin **phase registry**: phase module + ordered pipeline + rinse edges. No nested meta-engine. |
| Wiki | Existing Wiki + YAML front matter. Ground writes; later phases read. **Factory note front-matter contract v1** in this card. Full wiki redesign = CARD-125 later. |
| Live feedback | Gap → Needs Training backlog **or** auto-train re-enters phases → resume original job. Same orchestrator. |
| Five packs | `platform-packs/{conductor,inspector,coder,sandbox_runner,critic}` are **not** the Factory. Retire from Factory story; UI shows phases. Fold any real tools into phase tooling. SDLC Conductor (cards), if present as a user pack, stays separate. |
| Surfaces | Keep Train Agent / Train New / Train in Lab / Lab Monitor / backlog / auto-train / promote — rename copy to Agent Training Factory. |

### Phase context contracts

| Phase | Must have | Must produce |
|-------|-----------|--------------|
| Ground | role brief, optional path, seed objectives | Wiki notes: operating manual + medium map |
| Blueprint | those Wiki notes + pack inventory | skill list + tools-per-skill (no overlap) |
| Author | one skill/tool slice + Wiki slice | `SKILL.md` + tool code |
| Verify | authored files + medium rules | pass/fail + concrete gaps |
| Optimize | full pack + verify history | merge/split/regroup plan (or no-op) |
| Promote | green Verify + final files | HITL → `$DATA_DIR/packs/<id>/` |

### Factory Wiki front-matter contract v1 (this card)

Deterministic YAML for Factory grounding notes (exact keys locked at implement with Jacob if needed): at least `type` (e.g. `factory-grounding`), `agent_id`, `medium`, plus stable optional `factory_job_id` / `status`. Written only via existing wiki tools. CARD-125 extends the rest of the wiki from this pattern later.

---

## 3. What to Build

1. **Rename** factory modules/routes/UI strings to Agent Training Factory / `agent_training_factory` (router prefix, package paths, monitor titles). Prefer one clean rename in this card over permanent dual names.
2. **FactoryOrchestrator + phase registry** under e.g. `src/application/agent_training_factory/` — replace hard-coded costume steps in `factory_runner.py`.
3. Each phase module: context builder (exact language for that purpose) → LLM/tools → artifact writer → done-when. Rinse edges (e.g. Verify fail → Author).
4. **Ground** uses Wiki write/read with front-matter contract v1.
5. **Author/Verify** produce real pack files and real verification — not `ToolSynthesizer`-only templates as the sole path (templates may seed; LLM + grounding are required).
6. Retire Factory narrative/usage of the five persona platform packs; remove or stop seeding them as Factory team if nothing else needs them (do not break non-Factory Conductor if it is a distinct user pack).
7. Keep surfaces; wire them to the new orchestrator. Live gap/auto-train resume uses the same pipeline.
8. Tests: phase registry, context contracts, Wiki front-matter v1, rename smoke, promote path. Update specs/ADR pointers; supersede CARD-169 nomenclature work into this card where overlapping.
9. CHANGELOG Unreleased. Status **In Review** after code. **Not Done** until Jacob live-tests. Local commit on `qa`. Push only if he asks.

---

## 4. Acceptance Criteria

- [ ] Codebase and UI say Agent Training Factory / `agent_training_factory` consistently (no persona Factory team in UI).
- [ ] FactoryOrchestrator runs Ground→…→Promote with LLM phase context; phase registry allows insert/reorder without rewrite.
- [ ] Ground persists Wiki notes with front-matter contract v1; Blueprint/Author read them.
- [ ] Five costume Factory packs no longer presented as the Factory runtime.
- [ ] Surfaces still work: train, monitor (phases not personas), backlog, auto-train, promote, resume.
- [ ] Unit/vitest green; ruff clean. Status In Review. Not Done until live test.

---

## 5. Constraints & Honor Flags

- No factory personas/agents — phases only.
- No nested phases-of-phases meta-engine.
- Do not bypass Wiki YAML front matter.
- Do not reverse CARD-117/121 (Chat still lists ticked tools every turn).
- Do not start full CARD-125 or CARD-116 unless Jacob says.
- Do not push unless Jacob asks. Work on `qa`.
- Zero third-party product names in cards/UI/artifacts unless literally integrating.

---

## 6. Pickup

Say **build** / **continue**. Prefer live-test any open In Review Factory cards (159/164/165/166) against the new guts after implement, or fold their Done into this card’s live test.

---

## Implementation notes (live-test follow-up, 2026-09-05)

Jacob Hyper-V live train (unattend ISO + template) exposed costume success: Ground missed `hyperv`/ISO keywords → computation + `{slug}-cli`; objectives never persisted on `FactoryJob` so Author/Verify saw `[]`; Author/Verify accepted shallow stubs; Lab Monitor had no clickable artifact preview.

Follow-up on `qa` (status stays **In Review**):
- A) `FactoryJob.objectives` + SQLite `objectives_json` + create-job copy + PhaseContext merge with work-packet facts
- B) Ground keyword heuristics + rich operating manual (seed/objectives/paths); heuristic wins over LLM garbage for Hyper-V/cli
- C) Author quality gate + enrich Purpose/Objectives
- D) Verify `is_shallow_stub_artifact` gate
- E) Lab Monitor artifact pills + preview modal with expected pack paths

Commit: `fix(agent-training-factory): CARD-171 live-test grounding author verify preview`

## Follow-up (2026-09-06) — max verify rinse + fail reasons

Still **In Review / Not Done**. Live-test showed Author→Verify FAILED→Author forever (~90s) with feed hiding `critic_notes`; Windows `"C:\` in tool code falsely tripped stage-2 preflight.

Shipped on `qa` (this commit family):
- Cap verify rinses (default 3) then terminal `failed` with notes in packet.
- Lab Monitor feed shows short Reason line on Verify fail / terminal fail.
- Path guard allows absolute Windows paths; still blocks `..` traversal.
- Author receives last Verify failure notes for adaptive rewrite.

