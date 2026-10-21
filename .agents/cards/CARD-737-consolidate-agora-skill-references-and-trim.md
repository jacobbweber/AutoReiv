---
id: CARD-737
title: "Consolidate Agora skill references and trim per-turn pinned tool schemas"
type: feature
status: In Review
priority: P2
milestone: M32
needs_decision: none
proof:
  journeys: [card-737-consolidate-agora-skill-references-and-trim]
  checks:
    - tests/unit/architecture/test_card737_agora_skill_cleanup.py
    - tests/unit/architecture/test_card693_agent_skill_consolidation.py
branch: feat/card-737-consolidate-agora-skill-references-and-trim
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-20
---

# CARD-737 Consolidate Agora skill references and trim per-turn pinned tool schemas

## Intent
`AutoReiv` currently mounts 11 pinned skills on every chat turn (sending 46 tool schemas on Turn 1, including heavy or rarely used vault curation, autonomous worker, and legacy standalone native-tool callables), while only the 5 developer/SDLC skills under `platform/skills/` use progressive `references/*.md` files. Jacob approved a cleanup slice to move specialized/legacy skills (`wiki-curation`, `proposals`, `worker`) into `ON_DEMAND_SHIPPED_SKILLS`, move standalone `register_native_tool`/`view_native_tool`/`plan_native_folder` tool bindings from `capability-authoring` to `proposals`, and enrich `wiki-knowledge`, `socratic-tutoring`, and `proposals` with progressive `references/*.md` guides while consolidating the unticked `education-application` micro-skill into `socratic-tutoring`.

## Goal
- `AutoReiv` sends 38 baseline pinned tool schemas on Turn 1 (down from 46), while `wiki-curation`, `proposals`, and `worker` appear in the progressive skill index and mount their tools (`wiki_note_organize`, `wiki_note_archive`, `wiki_overview`, `register_native_tool`, `view_native_tool`, `plan_native_folder`, `batch_worker_scan`, `get_session_artifact`) on demand when `skill_view(skill_id=...)` is called.
- `platform/skills/wiki-knowledge/references/`, `platform/skills/socratic-tutoring/references/`, and `platform/skills/proposals/references/` ship progressive reference guides readable via `skill_view(skill_id=..., reference=...)` and visible in Capabilities Studio (`#view-capabilities`).
- The unticked `platform/skills/education-application/` micro-skill folder is retired and aliased to `socratic-tutoring` in `CONSOLIDATED_SKILL_ALIASES`.

## Change
- `src/application/agent_skills/allowed_tools.py`: add `"wiki-curation"`, `"proposals"`, and `"worker"` to `ON_DEMAND_SHIPPED_SKILLS`.
- `src/infrastructure/content/store.py`: add `"education-application": "socratic-tutoring"` to `CONSOLIDATED_SKILL_ALIASES`.
- `platform/skills/capability-authoring/SKILL.md`: remove `register_native_tool`, `view_native_tool`, and `plan_native_folder` from `tools:` frontmatter (keeping the 8 Agora + proposal tools on `capability-authoring`) and direct standalone native-tool registration to `skill_view(skill_id="proposals", reference="native-tool-lane.md")`.
- `platform/skills/proposals/SKILL.md` + `platform/skills/proposals/references/native-tool-lane.md`: bind `register_native_tool`, `view_native_tool`, and `plan_native_folder` in `proposals/SKILL.md` and add progressive reference documentation for the standalone native-tool lane.
- `platform/skills/wiki-knowledge/SKILL.md` + `platform/skills/wiki-knowledge/references/vault-taxonomy.md` + `platform/skills/wiki-knowledge/references/curation-and-templates.md`: add progressive references covering the four-folder vault taxonomy (`00_Inbox/`, `01_Notes/`, `02_Resources/_Templates/`, `03_Archive/`) and curation/template workflows.
- `platform/skills/socratic-tutoring/SKILL.md` + `platform/skills/socratic-tutoring/references/learning-modes.md`: add progressive reference covering Priming, Dual Coding, Construction, and Application learning modes plus Learning OS turn orchestration.
- `platform/agents/autoreiv.md`: note `wiki-curation`, `proposals`, and `worker` in the on-demand `skill_view` routing guidance.
- `tests/unit/agent_skills/catalog.py` & `tests/unit/architecture/test_card693_agent_skill_consolidation.py`: include `"proposals"` on the legacy retired `toolsmith` test spec and update `ON_DEMAND_SHIPPED_SKILLS` / `RETIRED_MICRO_SKILLS` in the ADR-0066 guard test.

## What dies
- `platform/skills/education-application/SKILL.md` (consolidated into `platform/skills/socratic-tutoring/references/learning-modes.md` and aliased via `CONSOLIDATED_SKILL_ALIASES["education-application"] = "socratic-tutoring"`).
- Always-on Turn 1 schema mounting of `register_native_tool`, `view_native_tool`, `plan_native_folder`, `wiki_note_organize`, `wiki_note_archive`, `wiki_overview`, `batch_worker_scan`, and `get_session_artifact` on `AutoReiv` before `skill_view` is called.

## Proof
- Journey `card-737-consolidate-agora-skill-references-and-trim`:
  1. Verifies `/api/capabilities/tree` exposes `wiki-knowledge` (`vault-taxonomy.md`, `curation-and-templates.md`), `socratic-tutoring` (`learning-modes.md`), and `proposals` (`native-tool-lane.md`) with their new `references`, and that `education-application` is no longer listed as a standalone skill folder.
  2. Verifies `capability-authoring` declared tools exclude `register_native_tool`, `view_native_tool`, and `plan_native_folder` while `proposals` declares them.
  3. Opens Capabilities Studio (`#view-capabilities`) on desktop and phone viewports, expands `wiki-knowledge`, clicks `references/vault-taxonomy.md`, and verifies it loads into `#capabilitiesFileEditor` with zero horizontal overflow.
- Checks:
  - `tests/unit/architecture/test_card737_agora_skill_cleanup.py`
  - `tests/unit/architecture/test_card693_agent_skill_consolidation.py`

## Plan and decisions
- Approved by Jacob in session ("Let's do the small milestone slice doing the cleanups you recommend"):
  1. Move `wiki-curation`, `proposals`, and `worker` to `ON_DEMAND_SHIPPED_SKILLS` and move `register_native_tool`, `view_native_tool`, and `plan_native_folder` from `capability-authoring` to `proposals` so `AutoReiv`'s baseline Turn 1 tool schemas drop from 46 to 38 while preserving all 73 allowed tools and existing operator contracts.
  2. Enrich `wiki-knowledge`, `socratic-tutoring`, and `proposals` with progressive `references/*.md` guides and consolidate `education-application` into `socratic-tutoring`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-737-consolidate-agora-skill-references-and-trim` | desktop | PASS | `/tmp/autoreiv-qa/card-737/card-737-consolidate-agora-skill-references-and-trim-desktop-02-2-open-capabilities-studio-view-capabilities-and.png` |
| `card-737-consolidate-agora-skill-references-and-trim` | phone | PASS | `/tmp/autoreiv-qa/card-737/card-737-consolidate-agora-skill-references-and-trim-phone-02-2-open-capabilities-studio-view-capabilities-and.png` |

Screenshots:
- `/tmp/autoreiv-qa/card-737/card-737-consolidate-agora-skill-references-and-trim-desktop-01-1-verify-api-capabilities-tree-progressive-refer.png`
- `/tmp/autoreiv-qa/card-737/card-737-consolidate-agora-skill-references-and-trim-desktop-02-2-open-capabilities-studio-view-capabilities-and.png`
- `/tmp/autoreiv-qa/card-737/card-737-consolidate-agora-skill-references-and-trim-phone-02-2-open-capabilities-studio-view-capabilities-and.png`

## Release note
- Consolidated `education-application` into `socratic-tutoring` with progressive `references/*.md` guides across `wiki-knowledge`, `socratic-tutoring`, and `proposals`, and moved `wiki-curation`, `proposals`, and `worker` (plus standalone native-tool registration schemas) to on-demand session mounting (`CARD-737`).
