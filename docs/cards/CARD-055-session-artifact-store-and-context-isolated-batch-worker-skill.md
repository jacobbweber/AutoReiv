# [CARD-055] Session Artifact Store and Context-Isolated Batch Worker Skill

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/session-artifact-store-and-batch-worker-skill/
> **Labels**: `type:feature`, `milestone:19`

---

## 1. Why / Intent
Enable `assistant` and `autoreiv` to process massive context tasks (e.g. repository-wide audits, multi-file analyses, bulk log reviews) using parallel isolated subagent workers without exceeding the 200k context window. Intermediate heavy outputs are stored as ephemeral session artifacts with automatic TTL cleanup and cascade deletion upon chat removal, keeping the Wiki Vault pristine while offering 1-click artifact inspection and promotion in Chat Studio.

---

## 2. What to Build
1. **SQLite Session Artifact Store (`src/infrastructure/memory/`)**:
   - `session_artifacts` table with `id`, `session_id`, `title`, `content_type`, `content`, `summary`, `item_count`, `is_pinned`, `expires_at`, `created_at`.
   - Foreign key constraint `REFERENCES sessions(id) ON DELETE CASCADE`.
   - `SessionArtifactRepository` supporting CRUD, TTL pruning, and promotion.
2. **Context-Isolated Batch Worker Skill (`src/application/skills/worker_skill.py`)**:
   - `batch_worker_scan(session_id, target_paths, objective)`: Map-reduce pipeline chunking targets across isolated subagent tasks and storing the combined report into `session_artifacts`.
   - `promote_artifact_to_wiki(artifact_id, wiki_slug)`: 1-click promotion of golden artifacts into the permanent Wiki Vault.
3. **Artifact REST Endpoints (`src/web/routers/artifacts.py`)**:
   - `GET /api/sessions/{session_id}/artifacts`
   - `GET /api/artifacts/{artifact_id}`
   - `POST /api/artifacts/{artifact_id}/promote`
   - `DELETE /api/artifacts/{artifact_id}`
4. **Chat Studio UI Enhancements (`src/web/static/modules/studios/chat.js` & `index.html`)**:
   - Render structured interactive Artifact cards in message bubbles.
   - Slide-over Artifact drawer / modal to inspect raw content and trigger "⭐ Promote to Wiki".
5. **Background Maintenance Routine**:
   - Background task periodically purging unpinned artifacts where `expires_at < CURRENT_TIMESTAMP`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ART-001]`: SQLite schema `session_artifacts` with cascade session deletion and TTL indexing.
- [x] `[REQ-ART-002]`: `SessionArtifactRepository` supporting persistence, retrieval, pinning, and TTL garbage collection.
- [x] `[REQ-ART-003]`: `BatchWorkerSkill` map-reduce engine chunking files into isolated worker tasks.
- [x] `[REQ-ART-004]`: REST API endpoints for artifact inspection and 1-click Wiki promotion.
- [x] `[REQ-ART-005]`: Chat Studio interactive artifact cards and modal viewer.
- [x] `[REQ-ART-006]`: All automated tests (Pytest, Vitest, Playwright smoke suite, ESLint, Ruff) pass 100% green.

---

## 4. Constraints & Honor Flags
- Strict isolated `feat/session-artifact-store-and-batch-worker` branch cut from `qa`.
- Zero degradation of existing chat streaming, Wiki Vault, or database integrity.

