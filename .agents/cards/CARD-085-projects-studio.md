# [CARD-085] Projects Studio

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/projects-studio/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Wiki stays knowledge. Projects are a separate studio. Card and file tools need a selected project under `projects_root` so Jacob can run many coding projects without mixing them into the wiki vault.

## 2. What to Build
- Setting `projects_root` (filesystem path). Default empty + placeholder (Jacob's lab path is placeholder text only).
- A project is a directory under that root.
- Studio: new sidebar tab, not wiki. List, create, open (select), delete with UI confirm.
- Selected project path is what card/file tools use when `project_root` is omitted.
- API: GET/POST/DELETE projects, GET/PUT settings projects_root.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-050]`: projects_root is get/put. Create/list stay jailed under the root.
- [x] `[REQ-SDLC-051]`: DELETE requires confirm. Studio is a separate tab from wiki.
- [x] `[REQ-SDLC-052]`: Selected project is the default root for card/file tools.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not merge this into wiki.
- Do not hardcode only `D:\Projects\Active` as the stored default.
- Scaffold template copy is CARD-086.
- Do not push. Stay on `qa`.
