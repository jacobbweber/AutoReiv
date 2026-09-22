---
id: CARD-420
title: "Developer-Mediated Authoring v1 (Visible Build/Review Job + Apply-Back)"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:agents
  - area:skills
---

# [CARD-420] Developer-Mediated Authoring v1 (Visible Build/Review Job + Apply-Back)

> **Status**: Ready  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted**)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:agents`, `area:skills`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md)  
> **Depends on**: [CARD-418](./CARD-418-skill-studio-extract-from-factory.md) Done; [CARD-419](./CARD-419-agent-studio-skill-toggle-pills.md) Done

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC / packet schema / which Studio gets Build first — **no product code** |
| **`build`** | Implement on `feat/card-420-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

ADR-0057 locks **developer-mediated authoring**: Studio fields are the operator draft; **Build / Review** submits a structured packet to the **developer** specialist as a **visible standing job / conversation** (default). The operator watches Observe or Chat, can reply with context, and accepts field patches back into the Studio. Invisible LLM rewrite is not the default — only **cheap lint** (valid frontmatter, catalog tool ids, contract linter) may stay silent in-form.

After CARD-418 / CARD-419, Skill Studio and Agent Studio skill pills exist, but there is still no Studio **Build / Review** wire to the `developer` pack as a watchable job with apply-back. Non-developer operators need that gate so “good agent / good skill” standards stay teachable and durable.

This card is ADR-0057 build-order step 3. It does **not** build Tools Studio.

---

## 2. What AutoReiv does now (Beat 2)

- **Skill Studio** writes skill bodies + SQLite `skill_tool_bindings` (CARD-411 / CARD-418).
- **Agent Studio** scopes skills with toggle pills only; Open in Skill Studio for detail (CARD-419).
- **Factory** is a thin agent-brief shell + link into Skill Studio.
- Platform pack `developer` (`platform-packs/developer/`) exists as the software-engineer specialist; Chat can select `developer`; Projects Studio can default to it. It is **not** wired as the canonical Studio Build/Review gate.
- Standing jobs / Observe Studio / Chat multi-phase chrome exist for other journeys (e.g. education, View Job → Observe). No shared “Studio form packet → developer job → patch apply-back” contract for Skill or Agent Studio yet.
- Capability / frontmatter linters exist for skills; they are not yet framed as the only invisible path beside a visible Build job.

---

## 3. What will change (Beat 3)

### v1 product shape (recommended defaults — refine on **continue** if needed)

1. **Primary surface first: Skill Studio.** Add **Build** / **Review** actions on Skill Studio that submit the current draft (skill id, metadata, SKILL.md body, selected tool ids, lint summary) as a structured packet to a **visible** job owned by agent id `developer`.
2. **Visible job**: open or focus Observe (and/or Chat) on that `job_id` so the operator can watch and reply. Reuse existing standing-job / View Job patterns where they fit; do not invent a second hidden orchestration bus.
3. **Packet schema (v1)**: versioned JSON (or equivalent) with studio = `skill`, draft fields, operator intent (`build` vs `review`), and blockers already known from cheap lint. Document the schema in-card or a short `docs/` note during build.
4. **Apply-back**: developer (or a thin apply path) returns proposed field patches; operator **Accept** writes into Skill Studio draft / save path (still SQLite + skill store — no dual truth). Reject leaves the draft unchanged.
5. **Cheap lint stays invisible** in-form (frontmatter valid, catalog tool ids, existing contract linter). Full rewrite / standards coaching must not be silent-only.
6. **Agent Studio Build** for agent-brief / “good agent” standards is **optional follow-on in this card only if thin**; otherwise explicitly defer to a successor after Skill Studio path proves out. Prefer Skill Studio first to keep the slice shippable.
7. Vitest (and any existing job API tests) for: Build creates visible job with packet; Accept applies patches; pill/save paths unchanged; no silent full LLM fill as default.

**Out of scope:** Tools Studio; custom MCP tool factories; tier removal; storage folder redesign; replacing Skill Studio Save with developer-only writes; invisible-only full LLM mediation.

---

## 4. What dies (Beat 4)

- Expectation that Studio Save alone is the only quality gate for “good skill” (Save remains persistence; Build/Review becomes the standards coaching gate).
- Invisible full LLM fill as the default Build experience.
- Any second binding writer invented for apply-back (must reuse CARD-411 / Skill Studio save).

---

## 5. Acceptance criteria (EARS)

- **[REQ-420-001]** WHEN the operator activates **Build** or **Review** on Skill Studio with a draft skill, THE SYSTEM SHALL create or resume a **visible** standing job/conversation assigned to the `developer` agent and attach a structured form packet describing the draft.
- **[REQ-420-002]** WHEN that job is created, THE SYSTEM SHALL expose a watchable operator path (Observe and/or Chat with `job_id`) without requiring the operator to invent the job id by hand.
- **[REQ-420-003]** WHEN the developer returns approved field patches and the operator Accepts, THE SYSTEM SHALL apply those patches into the Skill Studio draft (and persist only through the existing Skill Studio / CARD-411 save path when the operator saves).
- **[REQ-420-004]** WHEN only cheap lint runs (frontmatter / catalog ids / contract linter), THE SYSTEM MAY report in-form without opening a developer job; THE SYSTEM SHALL NOT use silent-only LLM rewrite as the default Build path.
- **[REQ-420-005]** THE SYSTEM SHALL NOT change Agent Studio skill toggle pills or Skill Studio SQLite binding ownership as part of this card.

---

## 6. Verification

- Unit/Vitest: packet shape; Build → job create stub; Accept → draft fields updated; lint-only path does not mint a full mediation job.
- Manual live test:

1. Open Skill Studio, load or draft a skill, click **Build** (or **Review**).
2. Observe/Chat shows a visible developer job with the packet context.
3. After developer suggests patches (or a test fixture injects them), Accept updates Studio fields; Reject leaves them alone.
4. Save still writes skill store + `skill_tool_bindings` as before.
5. Cheap lint (bad tool id / broken frontmatter) still surfaces in-form without requiring a full silent LLM pass.

---

## 7. Open refine points (say **continue** to lock before **build**)

| # | Question | Default if Jacob says **build** without further note |
|---|----------|------------------------------------------------------|
| 1 | Skill Studio only vs Agent Studio Build in same card | **Skill Studio only** in v1 |
| 2 | Observe-first vs Chat-first for watching the job | Prefer **Observe** with Chat link if both exist |
| 3 | Auto-save after Accept vs Accept-to-draft then Save | **Accept-to-draft**, operator still Saves |

