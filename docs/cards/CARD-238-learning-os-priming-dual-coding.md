# [CARD-238] Learning OS 1–2 — Priming + Dual Coding

> **Status**: Done (merged grok @ 636ff3a)
> **Created**: 2026-09-11
> **Spec Reference**: Architect REQ-LOS-012-001..003; Research Priming + Dual Coding (Paivio); Education B after CARD-237
> **Labels**: type:feature, AutoReiv.Studio, Education, Skills
> **Branch**: `feat/education-learning-os-238` (off `grok` @ 5fc219d)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. After the Education shell, the first real pedagogy is **how to start learning a topic** — not quizzes or video yet.
2. **Priming**: before deep detail, build a schema — outline, prerequisites, learning goals — grounded in **his Wiki**.
3. **Dual Coding**: each concept gets **two codes** — clear prose + a structured diagram (Mermaid for local qwen), written back to Wiki.
4. **Not this card**: quiz/SRS, concept-player / Lumina film, learner-model depth, amplifiers.

### Beat 2: What AutoReiv Does Now
1. Education Studio shell (CARD-237) mints standing Jobs via Chat (CARD-236) with free-form "how to teach me".
2. Skills = one `SKILL.md` runbook; progressive disclosure (CARD-228) — name/title/risk first; body on bind.
3. Wiki tools + standing Job path exist; no Education Priming / Dual Coding skills yet.

### Beat 3: What Will Change
1. Seed Education pack skills: `education-priming` + `education-dual-coding` under skills tree (copy-if-missing into `$DATA_DIR/skills`).
2. Education Ask gains mode chips (or equivalent): **Priming** / **Dual Coding** / default teach style — Ask shapes the standing outcome + binds those skills.
3. Done-when / `success_rule` expects Wiki write-back (schema note and/or concept+diagram note).
4. Proof: Education Ask (Priming or Dual Coding) → durable `job_…` → Wiki artifact → Observe journey. Feat off `grok` only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-LOS-012-001]**: Education pack skills: Priming (schema/outline/prereqs from Wiki) + Dual Coding (concept + Mermaid/structured diagram pair); progressive `SKILL.md` (228).
- [x] **[REQ-LOS-012-002]**: Education Ask with those modes runs as standing Job (236/237); writes schema/diagram notes back to Wiki when `success_rule` says so.
- [x] **[REQ-LOS-012-003]**: No quiz/SRS/concept-player in this card. Proof: Education Ask → Job + Wiki artifact + Observe journey. Feat off `grok`.

## 3. Constraints

- Reuse Chat standing Job mint + Wiki tools. No second corpus.
- Skill = one `SKILL.md` (CARD-117). Progressive load (228). Chat still lists ticked tools every turn.
- Mermaid / structured diagram first — not Lumina film.
- feat off `grok` only. Never qa/main.

## 4. Follow-on (not this card)

- Retrieval + Retention (quiz verifier + SRS)
- Learner-model memory
- Visual amplifiers / concept-player

## 5. Proof

- Pytest: `tests/unit/skills/test_education_learning_os_seeds.py`
- Vitest: Education mode shaping in `education_studio.test.js`
- Operator: Education → Priming or Dual Coding → Ask → `job_…` → Wiki note → Observe

- Live smoke: notes/marathon-card238-live-smoke.json — Dual Coding ask minted job_4bc03de2ee9c; mode chips on Education shell.
