# [CARD-120] Rename Python Skill modules so skill means runbook

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; CARD-121; docs/specs/user-intent-review/findings.md (Finding 15)
> **Labels**: `type:refactor`, `type:docs`

---

## 1. Why / Intent
Python modules currently named `*Skill` (WikiSkill, GitSkill, CardSkill, and similar) are **tool groups**, not runbooks. After CARD-117, **skill in code should mean a `SKILL.md` runbook**. Those modules need rename/align so the word "skill" is not overloaded.

This is **refactor-and-alignment**. Foundations first (CARD-117 then CARD-121). **No new features** on this card.

**Walked (2026-08-30, not build-now):** section 5 is the locked rename-only plan. Do after CARD-117 and CARD-121. Do not implement on this card.

---

## 2. What to Build
Rename/align only, and only after the skills primitive (CARD-117) and the tools primitive (CARD-121) are aligned. Do not add features. Do not implement on this card until those foundations are accepted.

- Inventory Python modules/classes currently called skills (WikiSkill, GitSkill, CardSkill, AgentBuilderSkill, etc. under `src/application/skills/`).
- Treat those as **tool groups** (callable actions), not runbooks.
- Rename/align so `skill` in code means one `SKILL.md` runbook.
- No new features, no behavior change beyond naming/alignment.
- `wiki_read` vs `wiki_write` split belongs to CARD-121, not extra scope here.
- Record the 2026-08-30 walked rename-only lock (section 5, not build-now).
- CHANGELOG Unreleased note that this walk was recorded.
- Local commit only. Do not push. (When this card is later executed: still no new features.)

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Inventory of Python `*Skill` modules/classes exists (WikiSkill, GitSkill, CardSkill, and the rest under `src/application/skills/`).
- [x] Those modules are treated as tool groups, not runbooks.
- [x] Rename/align plan (and later code) makes `skill` mean a `SKILL.md` runbook.
- [x] Walked 2026-08-30 rename-only lock is recorded (section 5, not built): after CARD-117 and CARD-121; no new features; no behavior change; `wiki_read` vs `wiki_write` is CARD-121 scope, not extra here.
- [x] No new features on this card. Foundations (CARD-117 then CARD-121) first.
- [x] Rename implemented on `qa` after CARD-117 and CARD-121. Local commit only. No push. Status **Done** after live-test pass.

---

## 4. Constraints & Honor Flags
- Status: **Done** (live-test pass; Jacob said ok next).
- Work on `qa`. Do not push. Do not clone.
- Rename/align only. No new features. No behavior change.
- Zero breaking change to tool behavior; tests stay green after any rename.
- Do not conflate this with Agent Packs (CARD-119) or Skills Studio (CARD-118).
- `wiki_read` vs `wiki_write` split belongs to CARD-121. Do not pull that split into this rename card.
- Do not name inspiration products in this card (Jacob t157u).
- Walked 2026-08-30 (section 5) is the locked intent. Section 6 is the execution.

---

## 5. Walked 2026-08-30

Locked rename-only plan. **Not build-now.** No product Python/JS. Status stays **Ready**.

1. **After CARD-117 and CARD-121.** Rename-only. Do not start this card until the skill primitive (CARD-117) and the tool primitive (CARD-121) are aligned.
2. **Python `*Skill` modules are tool groups, not runbooks.** WikiSkill, GitSkill, CardSkill, and the rest under `src/application/skills/` (`wiki_skill.py`, `git_skill.py`, `card_skill.py`, etc.) group callable tools. They are not `SKILL.md` runbooks.
3. **After rename, skill in code means `SKILL.md`.** The word skill is reserved for the runbook primitive. Tool-group modules get a non-skill name.
4. **No new features, no behavior change.** Rename/align identifiers, imports, docs, and tests only. Tool behavior stays the same.
5. **`wiki_read` vs `wiki_write` split belongs to CARD-121.** Not extra scope here. Do not split, merge, or redesign those tools on this card.

---

## 6. Implemented 2026-08-30

Executed after CARD-117 and CARD-121 (Jacob: "ok next"). Rename-only. Folder `src/application/skills/` kept because it still holds the runbook catalog (`user_catalog.py`, `dynamic_loader.py`, `skill_curator.py`) plus tool groups.

**Kept as skill (runbook primitive):** `UserSkillCatalog`, `UserSkillManifest`, `DynamicSkillLoader`, `allowed_skill`, `skill_view`, `list_user_skill_packs`, SKILL.md curator/seed.

**Tool groups old → new:**

| Old file / class | New file / class |
| --- | --- |
| `wiki_skill.py` / `WikiSkill` | `wiki_tools.py` / `WikiTools` |
| `librarian_skill.py` / `LibrarianSkill` | `librarian_tools.py` / `LibrarianTools` |
| `git_skill.py` / `GitSkill` | `git_tools.py` / `GitTools` |
| `card_skill.py` / `CardSkill` | `card_tools.py` / `CardTools` |
| `agent_builder_skill.py` / `AgentBuilderSkill` | `agent_builder_tools.py` / `AgentBuilderTools` |
| `delegate_skill.py` / `DelegateSubtaskSkill` | `delegate_tools.py` / `DelegateSubtaskTools` |
| `project_file_skill.py` / `ProjectFileSkill` | `project_file_tools.py` / `ProjectFileTools` |
| `memory_skill.py` / `EpisodicMemorySkill` | `memory_tools.py` / `EpisodicMemoryTools` |
| `planning_skill.py` / `PlanningSkill` | `planning_tools.py` / `PlanningTools` |
| `sandbox_skill.py` / `SandboxExecutionSkill` | `sandbox_tools.py` / `SandboxExecutionTools` |
| `orchestration_skill.py` / `OrchestrationSkill` | `orchestration_tools.py` / `OrchestrationTools` |
| `sysadmin_skill.py` / `SysadminSkill` | `sysadmin_tools.py` / `SysadminTools` |
| `task_tracker_skill.py` / `TaskTrackerSkill` | `task_tracker_tools.py` / `TaskTrackerTools` |
| `github_issue_skill.py` / `GitHubIssueSkill` | `github_issue_tools.py` / `GitHubIssueTools` |
| `system_agent_skill.py` / `SystemAgentSkill` | `system_agent_tools.py` / `SystemAgentTools` |
| `verification_skill.py` / `VerificationSkill` | `verification_tools.py` / `VerificationTools` |
| `weekly_notes_skill.py` / `WeeklyNotesSkill` | `weekly_notes_tools.py` / `WeeklyNotesTools` |
| `worker_skill.py` / `BatchWorkerSkill` | `worker_tools.py` / `BatchWorkerTools` |

**Manifest clustering (not a new feature):** `SkillTier` → `ToolGroupTier`, `SkillPackManifest` → `ToolGroupManifest`, `SKILL_TIERS` → `TOOL_GROUP_TIERS`, `BUILTIN_SKILL_PACKS` → `BUILTIN_TOOL_GROUPS`, `get_hierarchical_skills_catalog` → `get_hierarchical_tool_groups`. API JSON keys (`skill_packs`, `platform_skills`, `pack_owned_skills`) unchanged so Studio UI does not shift.

Callable names unchanged (`wiki_note_read`, `list_user_skill_packs`, `skill_view`, `execute_code`, …).
