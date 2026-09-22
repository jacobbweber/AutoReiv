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

- **[REQ-420-001]** WHEN the operator activates **Ask developer** on Skill Studio with a draft skill, THE SYSTEM SHALL create or resume a **visible** standing job/conversation assigned to the `developer` agent and attach a structured form packet describing the draft. (Chrome pass: one button, intent `build`. The jobs API still accepts `review`.)
- **[REQ-420-002]** WHEN that job is created, THE SYSTEM SHALL open Observe on that `job_id` and show the id on the Skill Studio job strip, without requiring the operator to invent the id. The strip does not keep Watch or Open in Chat buttons.
- **[REQ-420-003]** WHEN the developer returns approved field patches and the operator Accepts, THE SYSTEM SHALL apply those patches into the Skill Studio draft (and persist only through the existing Skill Studio / CARD-411 save path when the operator saves).
- **[REQ-420-004]** WHEN only cheap lint runs (frontmatter / catalog ids / contract linter), THE SYSTEM MAY report in-form without opening a developer job; THE SYSTEM SHALL NOT use silent-only LLM rewrite as the default Build path.
- **[REQ-420-005]** THE SYSTEM SHALL NOT change Agent Studio skill toggle pills or Skill Studio SQLite binding ownership as part of this card.

Operator surface for this branch (section 11): **Generate / Refine Runbook**, **Save skill**, **Delete skill**, and source context above the editor. REQ-420-001 through REQ-420-003 stay in the authoring module. Skill Studio does not show Ask developer, a job strip, or Accept/Reject until a later pass actually runs the developer.

---

## 6. Verification

- Unit/Vitest: packet shape; job helper posts a job and does not call the silent runbook endpoint; Accept helper updates a draft object and does not save; Skill Studio template has no Ask developer controls.
- Manual live test: section 11.

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

HTTP (routes stay mounted; Skill Studio does not call them in this pass):

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

- `tests/integration/operator_contracts/test_oc420_skill_studio_developer_authoring.py` — lint does not mint a job; the authoring post creates one durable job; Observe returns it for `developer`; a second post for the same skill resumes the same id; unknown patch fields are refused; Accept does not write `skill_tool_bindings`.
- `tests/unit/frontend/card_420_skill_authoring.test.js` — packet and job helpers remain; Skill Studio template and bindings have no Ask developer button, job strip, or Accept/Reject; delete still requires confirm; Save ownership and Agent Studio pills are untouched.
- `tests/unit/skills/test_skills_studio_archive_delete.py` — confirmed delete of an operator skill also drops that id’s pack copy and SQLite bindings; a bundled seed such as `wiki` stays (409) without `confirm_seed`.

The authoring job API still leaves a created job `queued`. This card does not run the developer model. Skill Studio does not open Observe for that path.

### Live test

Use section 11.

## 10. Chrome pass (locked after the job-wire live test)

Still In Review. Same branch. Jacob locked this layout after the developer job wire worked:

| Control | Locked |
|---------|--------|
| **Ask developer** | One primary button. Same job path as Build, intent `build`. |
| **Save skill** | Unchanged durable write. |
| **Generate / Refine Runbook** | Quieter secondary control. |
| Job strip | `job_…` id only. Observe opens once on success. No permanent jump buttons. |
| Source context | Above the SKILL.md editor, with metadata and tools. |
| **Delete skill** | Confirm dialog. Existing user-pack delete. Hidden when the skill is not an operator store file, or when it is a bundled seed. After delete, clear the workshop selection. Also drops that id’s pack copies and SQLite bindings. |

## 11. Operator surface for this merge (locked)

Still In Review. Same branch. Jacob removed the visible Ask developer path after the queued job did not run the developer.

Skill Studio shows:

- **Generate / Refine Runbook** (quiet secondary)
- **Save skill**
- **Delete skill** with confirm, operator-owned skills only
- External source context and intent/reference notes above the SKILL.md editor

Skill Studio does not show **Ask developer**, a job id strip, or Accept/Reject, and it does not open Observe from that path.

`developer_authoring` and `/api/skill_studio/authoring/*` stay in the tree for a later wire, when mediation actually runs the developer. A queued Observe job is not that wire.

### Re-verify

1. Pull `feat/card-420-developer-mediated-authoring-v1`, reload serve, hard-refresh the browser.
2. Open Skill Studio. The action bar is **Save skill**, **Generate / Refine Runbook**, and **Delete skill** when the loaded skill can be deleted. There is no **Ask developer** button, no job id, and no Accept or Reject.
3. External source context and reference notes sit above the SKILL.md editor.
4. **Save skill** still writes the skill store and SQLite bindings. **Delete skill** asks you to confirm, then the form clears. A bundled seed such as `wiki` does not offer delete.
5. Agent Studio skill pills for platform and pack skills are unchanged. A skill saved in Skill Studio also appears under **Operator skills** after you reopen Agent Studio, and its pill writes `allowed_skill` only.

