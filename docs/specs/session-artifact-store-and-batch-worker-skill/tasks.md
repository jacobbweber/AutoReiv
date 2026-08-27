# Task Matrix: Session Artifact Store and Context-Isolated Batch Worker Skill

## Vertical Slices

### Slice 1: Database Schema & Session Artifact Repository (`[REQ-ART-001, REQ-ART-002]`)
- [ ] Task 1.1: [RED] Write unit tests for `SessionArtifactRepository` (`tests/unit/infrastructure/test_session_artifact_repo.py`).
- [ ] Task 1.2: [GREEN] Add `session_artifacts` DDL and indexes to `src/infrastructure/memory/schema.py`.
- [ ] Task 1.3: [GREEN] Implement `SessionArtifactRepository` in `src/infrastructure/memory/repositories/artifacts.py` with CRUD, cascade cleanup, and TTL pruning.
- [ ] Task 1.4: [REFACTOR] Wire repository into `SQLiteStateStore`.

### Slice 2: Batch Worker Skill & Map-Reduce Engine (`[REQ-ART-003]`)
- [ ] Task 2.1: [RED] Write unit tests for `BatchWorkerSkill` (`tests/unit/skills/test_worker_skill.py`).
- [ ] Task 2.2: [GREEN] Implement `BatchWorkerSkill` in `src/application/skills/worker_skill.py` with chunking, in-memory worker aggregation, and `promote_artifact_to_wiki`.
- [ ] Task 2.3: [GREEN] Register `BatchWorkerSkill` in `SKILL_PACKS` manifest (`src/application/skills/manifest.py`).

### Slice 3: REST API Endpoints & Chat Studio UI (`[REQ-ART-004, REQ-ART-005]`)
- [ ] Task 3.1: [RED] Write API contract tests for `/api/artifacts` and `/api/sessions/{id}/artifacts` (`tests/integration/test_artifacts_api.py`).
- [ ] Task 3.2: [GREEN] Implement artifact router in `src/web/routers/artifacts.py` and register in `src/web/app.py`.
- [ ] Task 3.3: [GREEN] Update Chat Studio UI (`src/web/templates/index.html` and `src/web/static/modules/studios/chat.js`) to render interactive artifact cards and modal viewer.

### Slice 4: Verification & DoD Gate (`[REQ-ART-006]`)
- [ ] Task 4.1: Run all unit, frontend, and smoke tests (`pytest`, `vitest`, `playwright`).
- [ ] Task 4.2: Update `docs/rtm.json` and `CHANGELOG.md`.
- [ ] Task 4.3: Run `python .agents/skills/rtm-sync/scripts/preflight.py`.
