# Requirements Specification: Session Artifact Store and Context-Isolated Batch Worker Skill

## 1. System Intent & Scope
Provide a robust **Ephemeral Session Artifact Store** and **Context-Isolated Batch Worker Skill** enabling `assistant` and `autoreiv` to execute large-scale, exhaustive repository or multi-file inspections without context window blowup. Heavy outputs are stored as ephemeral session artifacts with automatic TTL cleanup and cascade deletion upon chat removal, keeping the Wiki Vault pristine while offering 1-click artifact inspection and promotion in Chat Studio.

---

## 2. EARS Requirements Matrix

### [REQ-ART-001] SQLite Session Artifact Schema & Cascade Constraints
- **Type**: Ubiquitous
- **Description**: The AutoReiv State Store SHALL persist session-scoped artifacts in a `session_artifacts` table with foreign key cascading deletion bound to `sessions(id)` and indexed TTL timestamps.
- **Acceptance Criteria**:
  1. Table `session_artifacts` contains columns `id`, `session_id`, `title`, `content_type`, `content`, `summary`, `item_count`, `is_pinned`, `expires_at`, `created_at`.
  2. Deleting a session from `sessions` automatically purges all linked records from `session_artifacts`.

### [REQ-ART-002] Session Artifact Repository & TTL Garbage Collection
- **Type**: Ubiquitous
- **Description**: The `SessionArtifactRepository` SHALL support saving artifacts, retrieving artifacts by ID, listing artifacts by session, toggling pinned status, and pruning unpinned artifacts past their `expires_at` timestamp.
- **Acceptance Criteria**:
  1. `save_artifact(artifact)` persists records with a default 7-day expiration timestamp.
  2. `pin_artifact(artifact_id, is_pinned)` toggles the pin state.
  3. `prune_expired_artifacts()` deletes unpinned artifacts where `expires_at < CURRENT_TIMESTAMP` and returns count pruned.

### [REQ-ART-003] Context-Isolated Batch Worker Skill
- **Type**: Event-Driven
- **Description**: WHEN an agent invokes `batch_worker_scan(session_id, target_paths, objective)` with a list of files or search pattern, the system SHALL chunk the target list across parallel isolated subagent worker loops, store the consolidated structured report into `session_artifacts`, and return a 2-sentence summary with an artifact link `artifact://<id>`.
- **Acceptance Criteria**:
  1. Each worker subagent runs with an isolated context window in memory, processing only its assigned chunk.
  2. The aggregated results are saved to `session_artifacts` without writing scratch files to the Wiki Vault.
  3. `promote_artifact_to_wiki(artifact_id, wiki_slug)` copies the artifact markdown into `data/wiki/<wiki_slug>.md` with structured YAML frontmatter.

### [REQ-ART-004] Session Artifact REST API Endpoints
- **Type**: Ubiquitous
- **Description**: The AutoReiv Web Gateway SHALL expose REST API endpoints for listing session artifacts, fetching artifact content, toggling pin status, promoting to Wiki Vault, and deleting artifacts.
- **Acceptance Criteria**:
  1. `GET /api/sessions/{session_id}/artifacts` returns artifact metadata list for the session.
  2. `GET /api/artifacts/{artifact_id}` returns full artifact content.
  3. `POST /api/artifacts/{artifact_id}/promote` converts the artifact to a permanent Wiki note.
  4. `DELETE /api/artifacts/{artifact_id}` removes the artifact record.

### [REQ-ART-005] Chat Studio Interactive Artifact Cards & Modal Viewer
- **Type**: Ubiquitous
- **Description**: The Chat Studio UI SHALL render interactive artifact cards in chat bubbles when an `artifact://` link or artifact payload is present, opening an interactive slide-over drawer / modal to inspect raw content and trigger 1-click Wiki promotion.
- **Acceptance Criteria**:
  1. Chat bubbles render a structured Artifact pill/badge with title, item count, and view button.
  2. Clicking the artifact opens `#artifactModal` displaying formatted markdown/JSON with a "⭐ Promote to Wiki Vault" button.

### [REQ-ART-006] Comprehensive Verification Gate
- **Type**: Ubiquitous
- **Description**: All automated test suites (Pytest, Vitest, Playwright smoke, ESLint, Ruff) SHALL pass with 100% green status.
- **Acceptance Criteria**:
  1. Unit tests for `SessionArtifactRepository` and `BatchWorkerSkill` pass.
  2. API contract integration tests for `/api/artifacts` pass.
  3. Pre-flight verification script passes cleanly.
