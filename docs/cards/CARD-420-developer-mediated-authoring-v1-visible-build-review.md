---
id: CARD-420
title: "Developer-Mediated Authoring v1 (Visible Build/Review Job + Apply-Back)"
status: In Review
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

> **Status**: In Review  
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

## 7. Locked at build (2026-09-22)

Jacob said **build** with no further refine. These defaults are the implementation:

| # | Question | Locked |
|---|----------|--------|
| 1 | Skill Studio only vs Agent Studio Build in same card | **Skill Studio only** |
| 2 | Observe-first vs Chat-first for watching the job | **Observe** first. **Open in Chat** selects `developer` and shows the same `job_id` on the Chat job strip (View Job still opens Observe) |
| 3 | Auto-save after Accept vs Accept-to-draft then Save | **Accept-to-draft**. Operator still clicks **Save skill** |

## 8. Packet schema v1

Schema name: `skill_studio_authoring_packet`. Version: `1`.

```json
{
  "schema": "skill_studio_authoring_packet",
  "version": 1,
  "studio": "skill",
  "intent": "build",
  "agent_id": "developer",
  "draft": {
    "skill_id": "wiki_digest",
    "name": "Wiki Digest",
    "description": "File a short wiki digest",
    "tier": "pack",
    "safety": {
      "read_only": true,
      "requires_hitl": false,
      "untrusted_input_allowed": false
    },
    "requires_tools": [],
    "markdown": "---\\nname: Wiki Digest\\n---\\n",
    "intent_notes": "",
    "source_context": ""
  },
  "lint": { "cheap": true, "blockers": [] },
  "llm_rewrite": false
}
```

`intent` is `build` or `review`. Patch fields the operator may Accept: `name`, `description`, `tier`, `safety`, `requires_tools`, `markdown`. `skill_id` and agent allowlists are refused.

The packet is stored on the standing job phase input (`template_id` `skill_studio_developer_authoring`, `agent_id` `developer`, session `skill-studio:{skill_id}`) and copied onto a standing-journey event `skill_studio_authoring_packet`. A second Build or Review for the same skill id resumes that open job.

Proposed patches live on that same phase output. Accept and Reject record `skill_studio_authoring_decision` on the job. Neither writes the skill store or `skill_tool_bindings`.

HTTP (Skill Studio is the only caller):

| Method | Path | Effect |
|--------|------|--------|
| POST | `/api/skill_studio/authoring/lint` | Cheap lint. No job. |
| POST | `/api/skill_studio/authoring/jobs` | Create or resume the visible developer job. |
| GET | `/api/skill_studio/authoring/jobs/{job_id}` | Packet plus current proposals. |
| POST | `/api/skill_studio/authoring/jobs/{job_id}/proposals` | Attach field patches (developer or a live-test fixture). |
| POST | `/api/skill_studio/authoring/jobs/{job_id}/decision` | `accept` or `reject`. Does not save the skill. |

Cheap lint checks YAML frontmatter, catalog tool ids, and `SkillContractCompiler`. **Generate / Refine Runbook** is unchanged and is not Build.

## 9. Verification notes

Automated:

- `tests/integration/operator_contracts/test_oc420_skill_studio_developer_authoring.py` — lint does not mint a job; Build creates one durable job; Observe returns it for `developer`; Review resumes the same id; unknown patch fields are refused; Accept does not write `skill_tool_bindings`.
- `tests/unit/frontend/card_420_skill_authoring.test.js` — packet shape, Build URL is not the silent runbook endpoint, Accept updates the draft, Reject leaves it, Agent Studio pills are untouched.

The job stays `queued`. This card does not mark it done and does not run a silent LLM rewrite.

### Live test

1. Open Skill Studio. Enter a skill name (or load a skill). Click **Build** or **Review**.
2. Observe opens on that `job_id`. The timeline shows a developer job and a Skill Studio packet line for the skill id. **Open in Chat** shows the same id on the Chat job strip. You do not type the id.
3. Attach a fixture patch (the queued job does not call the model by itself):

```bash
curl -s -X POST "http://127.0.0.1:8000/api/skill_studio/authoring/jobs/JOB_ID/proposals" \
  -H "Content-Type: application/json" \
  -d '{"patches":[{"field":"description","value":"Shorter trigger text"}]}'
```

4. Within a few seconds Skill Studio shows the patch. **Accept** changes the description in the form. **Save skill** still writes the skill store and SQLite bindings. **Reject** leaves the form as it was.
5. Break frontmatter or type a tool id that is not in the catalog, then leave the runbook field. The amber cheap-lint panel updates and does not open a second job. Agent Studio skill pills are unchanged.

