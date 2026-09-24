---
id: CARD-455
title: "Isolate CARD-388 agents API test from AppData / live global app"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-388
  - CARD-451
labels:
  - type:test
  - area:agents
  - area:testing
  - P2
---

# [CARD-455] Isolate CARD-388 agents API test from AppData / live global app

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-451 broad `tests/unit` run on Jarvis — `test_req_388_002_api_returns_developer_and_tutor` failed with `assert 'Super Developer' == 'Developer'`
> **Related**: CARD-388 (original restoration), CARD-451 (noticed during)
> **Labels**: `type:test`, `area:agents`, `area:testing`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine isolation approach — **still no product code** |
| **`build`** | Make the CARD-388 API test hermetic (temp user-data / injected store) |
| **`merge to qa`** | After the named test passes with live AppData still present and renamed agents allowed |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

The CARD-388 contract that `GET /api/agents` returns platform seed names (`Developer`, `Tutor`) must not flake when Jacob's real Jarvis user-data has operator renames or other live state.

### Beat 2: What AutoReiv does now

1. `tests/unit/agent_packs/test_card_388_developer_tutor_restoration.py::test_req_388_002_api_returns_developer_and_tutor` builds `TestClient(app)` from **`from src.web.app import app`** (module-level singleton).
2. That global app bootstraps against the process environment, including **`AUTOREIV_DATA_DIR=C:\Users\jacob\AppData\Local\AutoReiv`** and the live SQLite store under `database/autoreiv.db` (`custom_agents` / overlays), not a pytest `tmp_path` store.
3. Observed failure during CARD-451 broad run:
   - `AssertionError: assert 'Super Developer' == 'Developer'`
   - on `agent_map["developer"]["name"] == "Developer"`
4. Root cause (as far as known): **live user-data / env leak into the test**. Operator-facing agent display name for `developer` came back as `Super Developer` from the process-bound control plane (AppData-backed registry) instead of the immutable platform seed name in `platform-packs/developer/pack.json` (`"name": "Developer"`). The test asserts canonical seed naming but does not isolate storage, so any rename (or other live overlay) in Jarvis AppData / the already-constructed global `app` makes the contract fail even though platform packs on disk are correct.
5. Contrast: other router/unit contracts (e.g. system updates tests) call `create_app(state_store=SQLiteStateStore(tmp_db), …)` under a temp wiki/data dir and stay hermetic.

### Beat 3: What will change

1. Rewrite `test_req_388_002` (and any sibling in that file that imports global `app`) to use **`create_app` + temp `SQLiteStateStore` + temp data dir**, with `AUTOREIV_DATA_DIR` / DB path pointed at the temp tree for the test duration (or equivalent fixture already used elsewhere).
2. Optionally assert seed names from the **platform pack manifest** when testing catalog purity, and separately (if desired) add an operator-contract that renamed AppData agents are allowed at runtime — without conflating the two.
3. Keep platform packs on disk unchanged; do not require Jacob to rename `Super Developer` back for CI green.

### Beat 4: What dies today

1. `TestClient(app)` against the live global FastAPI singleton for CARD-388 seed-name assertions.
2. Silent coupling between Jarvis AppData operator edits and unit-suite greenness for platform pack restoration.

---

## 2. Acceptance criteria (EARS)

- **[REQ-455-001]** WHEN `test_req_388_002_api_returns_developer_and_tutor` runs, THE SYSTEM SHALL use an isolated temp user-data / state store (not `%LOCALAPPDATA%\AutoReiv` / the live global `app` singleton).
- **[REQ-455-002]** WHILE live AppData still contains a renamed `developer` agent (e.g. display name `Super Developer`), WHEN the isolated CARD-388 test runs, THE SYSTEM SHALL still assert seed `name == "Developer"` / `Tutor` from the hermetic app and SHALL pass.
- **[REQ-455-003]** THE test SHALL NOT mutate or require cleanup of Jacob's real AppData packs or `custom_agents` rows to go green.

---

## 3. Proof / live-test notes

1. With AppData left as-is, `uv run pytest tests/unit/agent_packs/test_card_388_developer_tutor_restoration.py::test_req_388_002_api_returns_developer_and_tutor -q` passes.
2. Negative: grepping the test file shows no `from src.web.app import app` for that contract (or equivalent global singleton use).

---

## 4. Notes for Jacob — local feat branches seen in Settings branch picker (do NOT auto-delete)

Observed on Jarvis during CARD-451 Settings updates work (branch picker / `GET /api/system/updates/branches`), **in addition to** the active `feat/card-451-settings-software-updates`. These are **local** feat branches for Jacob to review later (merge, keep, or delete himself — **agents must not delete them**):

1. `feat/card-400-education-monolith-decomposition`
2. `feat/card-438-chat-quiz-flashcard-durable-grading`
3. `feat/card-439-due-reviews-in-tutor-education-mode`
4. `feat/card-440-wiki-curation-from-links-curriculum`
5. `feat/card-441-progress-you-can-trust-non-studio-surface`
6. `feat/card-447-education-studio-operator-strip-and-tutor-context`
7. `feat/card-448-education-studio-players`

---

## 5. Constraints

- Docs-only until **build**.
- Do not reset `qa`; no force-push; no deleting local branches as part of this card.
- Prefer matching existing hermetic FastAPI fixtures over inventing a second test app factory.

---

## 6. Reply phrases

- Refine isolation approach: say **continue**.
- Start the test fix: say **build**.
- After green hermetic proof: say **merge to qa**.
