---
id: CARD-603
title: "Per-agent template folders: General (AutoReiv) and Education (Tutor); AutoReiv sends study to Tutor; no run-state facts"
status: Done
created: 2026-10-02
completed: 2026-10-02
branch: feat/card-603-per-agent-template-folders
related:
  - CARD-598
  - CARD-596
  - CARD-597
  - CARD-570
labels:
  - type:feature
  - area:wiki
  - area:agents
  - area:memory
  - P1
needs_decision: none
milestone: M24
proof:
  journeys: []
  checks:
    - tests/unit/wiki/test_card603_template_folders.py
    - full pytest
    - fast preflight
    - live-qa :8770 (Spark nemotron) checks a-d, desktop
log:
  minutes: 120
  qa_runs: 1
  findings: 2
---

# [CARD-603] Per-agent template folders: General (AutoReiv) and Education (Tutor); AutoReiv sends study to Tutor; no run-state facts

> **Status**: Done
> **Labels**: `type:feature`, `area:wiki`, `area:agents`, `area:memory`, `P1`

## Problem

All wiki templates sat in one folder (`02_Resources/_Templates/`), and every agent with template tools saw all of them. On 2026-10-02 the live check (ui1002 b) showed what that does: asked a flashcard question, AutoReiv found the `education-flashcard` template and spent 50 wiki tool steps looking for due cards, instead of telling Jacob to open Tutor. The same failed turn saved run state as memory facts (`system.max_steps_per_reply: 50`, `project.spaced_flashcard_template: identified_in_wiki_vault`).

## Change

1. **Template folder per agent.** `AgentProfile.template_folder` is a vault-relative folder, edited in Agent Studio (Agent Preferences > Template folder) and saved in the agent file. Shipped agents set it in `platform/agents/`: AutoReiv `02_Resources/_Templates/General`, Tutor `02_Resources/_Templates/Education`. The save path validates it (relative to the vault, no `..`, no drive or leading slash) and normalizes slashes. A Studio save with no `template_folder` keeps the saved value; an empty string clears it.
2. **No folder = no template access** (decision). An agent with no folder gets an empty template list, "not found" for read/update/use, and a create that says to set a folder in Agent Studio. Choosing no access over a default keeps templates from leaking between agents: a new custom agent opts in by naming a folder.
3. **Template tools stay in the folder.** `wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update` and "use" (`wiki_note_create(template=...)`) only see and write the calling agent's folder. A slug outside it answers "Template '<slug>' not found." The folder comes from the tool context (`template_folder`, set by `ScopedToolRegistry.execute`); there are no per-agent paths in the tools. Platform callers with no agent in the context (routines code, the Wiki studio API) still see every template under `02_Resources/_Templates/` (recursive).
4. **Search skips other agents' template folders.** `wiki_note_search`, `wiki_note_list` and `wiki_overview` hide every other agent's template folder from the caller (a folder inside the caller's own stays visible); `wiki_note_read`, `wiki_note_update`, `wiki_note_append`, `wiki_note_archive` and `wiki_note_organize` answer "not found" for those paths.
5. **Seeding.** The shipped templates are seeded into their group folder (`education-*` and `feynman-technique` into Education, the rest into General; `store.SEED_TEMPLATE_GROUPS`, which mirrors the shipped agents' settings and is not used by the tools). A template whose file name already exists anywhere under `02_Resources/_Templates/` is not seeded again, so Jacob's unsorted vault gets no duplicates. `tag-authority.md` and `note_template.md` stay at the templates root (platform files, not agent templates). Empty or missing folders are fine: list is empty, read is not found, create makes the folder.
6. **(a) AutoReiv study routing.** The AutoReiv prompt now says study, flashcards, quizzes, spaced review and learning sessions belong to Tutor: answer in one or two sentences telling the user to open Tutor in Chat, with no wiki search or tool call. With the split, AutoReiv also no longer sees the education templates.
7. **(b) No run-state facts.** `is_run_state_fact` (part of `is_short_lived_fact`, so both extraction and the CARD-597 startup clean-up use it) drops step/turn/tool limits, context or token budgets, search progress, last action, and `*_identified` / `identified_in_*`-style "what I found this reply" facts. The extraction prompt says the same. Durable facts (preferences, OS platform, template names) are kept.
8. Optional shared folder: not done (out of scope for now).

Not changed: Tutor keeps its skills (template list/read and use through `wiki_note_create`); it has no create/update template tools unless the `wiki-templates` skill is ticked for it.

## Proposed template sort (Jacob's real wiki, not moved)

No files were moved. The real vault has 21 templates plus `tag-authority.md`, all directly in `02_Resources/_Templates/`. Proposed destinations:

| Template file | Title | Proposed folder |
|---|---|---|
| adr-decision.md | Architecture Decision Record (ADR / Trade-Off) | General |
| concept-comparison.md | Concept Comparison & Distinction | General |
| concept-map-system-hub.md | System Hub (Concept Map) | General |
| dikw-pyramid-of-insight.md | Pyramid of Insight (DIKW Framework) | General |
| sop-runbook.md | Standard Operating Procedure (SOP / Runbook) | General |
| weekly_notes.md | Weekly notes ({{week_title}}) | General |
| zettelkasten-atomic.md | Zettelkasten (Atomic Note) | General |
| education-concept.md | Education Concept Brief (Mental Model) | Education |
| education-dual-coding.md | Education Dual Coding (Prose + Visual Map) | Education |
| education-elaboration.md | Education Elaboration & Conceptual Interrogation | Education |
| education-flashcard.md | Education Spaced Flashcard | Education |
| education-lab.md | Education Construction & Application Lab | Education |
| education-method.md | Education Method Runbook (Procedural Recipe) | Education |
| education-portfolio.md | Education Growth Portfolio & Depth Trajectory | Education |
| education-priming.md | Education Priming & Schema Blueprint | Education |
| education-problem.md | Education Problem Scenario (Diagnostic Lab) | Education |
| education-quiz.md | Education Retrieval Quiz Arena | Education |
| education-score.md | Education Mastery Ledger Scorecard | Education |
| education-tool.md | Education Tool Reference (Interface Sheet) | Education |
| feynman-technique.md | Feynman Technique Study Note | Education |
| note_template.md | Standard Note Template | stays at root (platform default; scaffold recreates it there) |
| tag-authority.md | Wiki Tag Authority | stays at root (not a template) |

Important: until these files are moved, AutoReiv and Tutor see no templates in the real vault (the tools look only in their own folder, and seeding skips names that already exist under the templates root). Move them right after the merge, or before it.

## Findings

- (fixed) AutoReiv looped 50 wiki steps on a flashcard question instead of sending the user to Tutor (ui1002 b, 2026-10-02).
- (fixed) Memory extraction saved AutoReiv run state (`max_steps_per_reply`, `identified_in_wiki_vault`).
- (to findings list) AutoReiv still saves low-value facts about what it just did (`system.template_path`, `system.create_command`, `project.template_format`). These are not run state, so they pass the filter; worth a later look at the extraction prompt.

## Results

| Check | Result | Notes |
|---|---|---|
| `tests/unit/wiki/test_card603_template_folders.py` | PASS | 21 passed: confinement (list/read/create/update/use), search/read hiding, no-folder agent, missing folder, platform callers, folder validation and save, seeding into groups without duplicates, AutoReiv prompt, run-state facts |
| Full pytest | PASS | 2303 passed, 12 skipped (3 stale seeding/collision tests updated for the group folders) |
| Fast preflight (`--base qa`) | PASS | ruff, eslint, pytest guard 188, changed 36, mapped 951 (1 skipped), vitest 944 |
| Live (a) AutoReiv creates a template | PASS | `wiki_template_create` -> `02_Resources/_Templates/General/incident-postmortem-44778.md` (and -25283 in a second run); nothing in notes |
| Live (b) AutoReiv flashcard question | PASS | no tool calls, no handoff; "Please open Tutor in Chat" (2 of 2 runs) |
| Live (c) saved facts | PASS | Tutor saved only the study preferences (evening, 10 minutes), each with `observed_at`; due count (0) not saved; no run-state facts on either agent |
| Live (d) Tutor code/host request | PASS | no tools; stays in its educational scope and points to Developer (2 of 2 runs) |
| Agent Studio | PASS | Template folder field shows General for AutoReiv and Education for Tutor |

Live env: throwaway :8770 from the branch commit, Spark nemotron-3.5-lightning only (no model swap). Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002b\` (`ui1002b-a-autoreiv.png`, `ui1002b-b-autoreiv.png`, `ui1002b-c-tutor.png`, `ui1002b-d-tutor.png`, `ui1002b-studio-autoreiv-template-folder.png`, `ui1002b-studio-tutor-template-folder.png`, results in `ui1002b-results.json`).

## Release note

Each agent has its own wiki template folder (Agent Studio > Template folder; AutoReiv General, Tutor Education), and template tools and template search stay in it. AutoReiv sends study and flashcard questions to Tutor, and memory no longer saves run state such as step limits.
