# [CARD-273] Repo hygiene, test alignment, and release v0.29.0

> **Status**: In Progress
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit and release wave (CARD-215 through CARD-272)
> **Labels**: `type:chore`, `release`, `hygiene`
> **Branch**: `grok` -> `qa` -> `main`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Clean all disposable scratch scripts (`_*`) and test probes out of the repository root.
2. Fix the 17 outdated test assertions (15 pytest, 2 vitest) so the entire test suite is 100% green without modifying production business logic.
3. Bring all changes from `grok` into `qa` and push to remote.
4. Release `v0.29.0` to `main` with release tag and push to remote.
5. Safely retire and delete the `grok` branch on local and remote.

### Beat 2: What AutoReiv Does Now
1. Over 110 untracked disposable scratch files (`_patch*.py`, `_commit_msg_*.txt`, etc.) clutter the root directory.
2. 15 backend tests and 2 frontend tests fail because earlier card assertions did not anticipate later card improvements (e.g. routine count 8->9, ATF honest can't 422, etc.).
3. `qa` and `main` are currently on release `v0.28.0` (`ea75253`), 135 commits behind `grok`.
4. All 35 feature branches are already merged into `grok`.

### Beat 3: What Will Change
1. All ~110 disposable root scratch files and ephemeral test files deleted; working directory clean.
2. The 17 test assertions updated to reflect current contracts; `pytest` (1,480+ tests) and `vitest` (370 tests) pass 100% green.
3. `qa` fast-forwarded to tip, verified, and pushed to `origin/qa`.
4. Release `v0.29.0` cut on `qa` with updated `package.json`, `pyproject.toml`, `CHANGELOG.md`, and merged to `main`, tagged `v0.29.0`, and pushed to `origin/main`.
5. Local and remote `grok` deleted.

---

## 2. Acceptance Criteria

- [ ] **[REQ-REL-273-001]**: Zero untracked disposable scratch files (`_*`) in the repository root.
- [ ] **[REQ-REL-273-002]**: 100% green backend tests via `pytest`.
- [ ] **[REQ-REL-273-003]**: 100% green frontend unit tests via `vitest`.
- [ ] **[REQ-REL-273-004]**: `qa` branch fast-forwarded and pushed to `origin/qa`.
- [ ] **[REQ-REL-273-005]**: Version bumped to `0.29.0` in `package.json`, `pyproject.toml`, and `src/autoreiv/__init__.py`.
- [ ] **[REQ-REL-273-006]**: `CHANGELOG.md` updated with `[0.29.0]` release header.
- [ ] **[REQ-REL-273-007]**: `main` branch merged from `qa`, tagged `v0.29.0`, and pushed to `origin/main`.
- [ ] **[REQ-REL-273-008]**: `grok` branch deleted locally and remotely.

---

## 3. Constraints

- Never alter production business logic to force green status; only align outdated test expectations or fix minor DOM test compliance (`$()` vs `document.getElementById`).
- Zero data loss in `data/`, `autoreiv.db`, `packs/`, or `platform-packs/`.
- Fast-forward merge only (no rebasing or rewritten history).
