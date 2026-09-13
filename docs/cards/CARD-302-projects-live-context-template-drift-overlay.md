# [CARD-302] Projects live context template drift overlay

> **Status**: In Review  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: Jacob review + Architect lock + Research path-manifest bar
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Set Active must reload Project Artifact Explorer from the real disk tree of that folder (not a stub). Ship a versioned Project path manifest; structure-only drift (missing=red); scaffold new / adopt align from the same manifest. Root picker must paint above the explorer.

## 2. What to Build
- `project_template_manifest.json` (versioned required paths)
- Drift API + Align action (structure only)
- Set Active → explorer reloads from selected root; show active path
- Drawer z-order above workspace/explorer

## 3. Acceptance Criteria
- [x] Manifest file + template_version in drift payload
- [x] GET `/api/projects/drift` + POST `/api/projects/align`
- [x] Set Active reloads tree from disk (`project_root` matches selection)
- [x] Missing paths shown red; Align scaffolds missing only
- [x] `#projectsDrawer` z-index above `#projectsWorkspace`
- [x] Vitest + pytest green

## Design lock
Live disk tree on Active; structure-only drift; picker above explorer.
