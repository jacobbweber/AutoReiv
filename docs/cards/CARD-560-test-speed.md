---
id: CARD-560
title: "Test suite runs faster: cheap app startup, slow tests out of the fast tier, dead tests removed"
type: feature
status: In Review
priority: P1
milestone: M22
needs_decision: none
proof:
  journeys: [card-454-tutor-trimmed-skills]
  checks: [tests/unit/capabilities/test_capability_seeder_407.py, tests/unit/skills/test_card559_card_and_preflight_scripts.py]
branch: feat/card-560-test-speed
log: {minutes: 105, qa_runs: 1, findings: 4}
created: 2026-09-27
---

# CARD-560 Test suite runs faster: cheap app startup, slow tests out of the fast tier, dead tests removed

## Intent
Jacob waits on preflight before every In Review and merge. The CARD-559 test-suite review (scratch/rules-draft/TEST-SUITE-REPORT.md) found two thirds of unit time went to building the FastAPI app per test, dead Factory/duplicate tests, and a fast tier that ran slow files (332 s on one card). Technical card, no build gate.

## Goal
Unit suite and full preflight are measurably faster with every guard and contract kept; a small change clears the fast tier in under a minute; a nightly run can be scheduled without writing into the repo.

## Change
- **App startup (a).** Profiling showed `create_app()` cost ~1.4 s per call, and ~0.8 s of that was `seed_builtin_capabilities` doing 119 `upsert_entry` calls, each opening a connection, committing and closing. New `CapabilityCatalogRepository.upsert_entries()` writes them on one connection with one commit; the seeder collects entries and calls it once (falls back to `upsert_entry` for repos without it). `create_app()` now ~0.3 s. This also speeds up real serve startup.
- **Shared app fixture (a).** `tests/conftest.py` adds module-scoped `shared_app` / `shared_client`: one `create_app()` per module in its own temp data dir, `dependency_overrides` restored after each test. Only for tests that never mutate app.state, settings, DB or data dir. Migrated (27 tests in 7 files):
  - `tests/unit/web/test_skill_studio_routes.py`: test_5 (5 redirect cases) and test_6 (11 removed-route 404 cases); tests 1-4 and 5b mutate state and stay function-scoped.
  - `tests/unit/web/test_static_css_396.py`: all 3 (GET only; `slow` marker removed, file now 0.8 s).
  - `tests/unit/web/test_ui_agent_select_and_discovery.py`: model discovery + index select (the provider-settings POST stays own-app).
  - `tests/unit/web/test_web_api.py`: index view, list agents.
  - `tests/unit/web/test_system_updates_router.py`: /health, /api/system/version.
  - `tests/unit/core/test_card_497_factory_backend_removal.py`: test_7, test_10 (read app.state).
  - `tests/unit/skills/test_capability_linter.py`: 3 `/api/skills/lint` tests.
  - Everything else that saves, posts real data, swaps `app.state.*`, or restarts on the same DB keeps its own app (with the seeder fix those now cost ~0.3-0.7 s instead of ~1.4 s).
- **429 test.** `test_openai_rate_limit_429` stubbed `asyncio.sleep` in the adapter and asserts it backed off (14 s -> 0 s).
- **Gate policy (build 2026-09-27).** No full unit/integration suite before merge to qa: card proof is `preflight --fast` plus the card's live journey; post-merge on qa is the fast tier against `origin/qa`. The full suite is `preflight --release` (renamed from `--full`), run only before merging qa into main. Nightly tier dropped: `--nightly`, `nightly_dir()` and `nightly_task.ps1` deleted. Updated preflight SKILL.md, merge-to-qa SKILL.md (step 4), `.agents/rules/testing.md` tiers, definition-of-done, live-qa SKILL.md (`--card ALL`). AGENTS.md card loop already says fast tier only.
- **Parallel pytest.** `pytest-xdist>=3.5` added to the `dev` extra (Jacob approved). Every preflight pytest stage adds `-n auto` when xdist is importable, else runs serially. New `serial` marker (pyproject); the release tier runs `-m "not serial"` in parallel, then `-m serial` without `-n`. Nothing needed the marker: unit + integration passed under `-n auto` (32 workers) with no fixes.
- **Fast tier (c).** `preflight.py` changed-tests stage runs `-m "not slow"` (slow ones run in full/nightly); an all-deselected run (pytest exit 5, "deselected") counts as PASS. Preflight SKILL.md updated.
- ~~**Nightly (d).**~~ Superseded by the gate policy above (nightly dropped). `preflight.py --nightly` writes its summary to `%LOCALAPPDATA%\AutoReiv\nightly\<date>.md` (`AUTOREIV_NIGHTLY_DIR` overrides), not `scratch/`. New `.agents/skills/preflight/scripts/nightly_task.ps1`: dry run prints the task (daily 02:30, console log `%LOCALAPPDATA%\AutoReiv\nightly\run-<date>.log`); `-Register` / `-Unregister`. **Not registered on Jarvis**; Jacob registers it if wanted.
- **Scratch (e).** Local cleanup (gitignored): 533 top-level items / 1,341 files of earlier-card scratch removed (c4xx/c5xx/b4xx/m4xx/i520/d520/t520/v520 dirs and scripts, e*.json, apply/patch/fix scripts, old html/js copies, vitest/smoke error dumps, `x/`, `__pycache__/`). scratch went from 591 to 58 top-level items, 9,596 to 8,255 files. Kept: rules-draft (TEST-SUITE-REPORT.md, raw/) until this card merges, the two 2026-09-27 review reports, live_qa_data, smoke_data, test_wiki, mcp_servers, tool_artifacts, appdata_backups, preflight, c560, `autoreiv_pre_c497_cleanup.db` (cited by CARD-523/524), blender_mcp (unreferenced but not clearly a card leftover) and the 2026-09-27 ComfyUI/media work (not card scratch).

## What dies
- `tests/unit/agent_packs/test_factory_packs.py` (7 tests): pinned retired Factory constants only. `FACTORY_PACK_IDS` and `RETIRED_FACTORY_PERSONA_PACK_IDS` removed from `src/application/agent_packs/schema.py` (no other users).
- `test_card502_adopt_persists.py::test_agent_studio_extra_tick_survives_restart`: duplicate of `tests/integration/test_card502_adopt_restart.py`.
- `test_image_turn_gating_475.py::test_vision_model_gets_the_current_turn_image`: duplicate of the OC475 contract `test_vision_marked_model_gets_the_image_once`.
- `test_image_turn_gating_475.py::test_poisoned_text_only_session_next_hi_sends_no_images`: duplicate of the OC475 contract `test_session_poisoned_before_the_fix_...`.
- Reviewed and kept: `test_card_411_factory_skill_bindings.py` (really a live `/api/skill_studio/save` contract), `test_card_497_factory_backend_removal.py` (CARD-498 still Ready; finding logged), `test_skill_studio_routes.py` (only partly Factory), the other tests in the 502/475 files (unique assertions), and all 16 whitebox/heavy-mock files (plan_engine, reflexion_engine, remote_tools, supervisor_orchestrator, ...): their modules are live and no contract test covers the same behaviour. No guard test touched.

## Proof
- Checks: `test_seeder_writes_all_entries_in_one_batch` (one batched write, no per-entry upsert); `test_fast_tier_changed_tests_skip_slow_and_nightly_writes_outside_repo`.
- App code changed (seeder, catalog repo), so one live journey: `card-454-tutor-trimmed-skills` (boots a real serve, whose startup runs the batched seeder, then drives Tutor skills).

## Plan and decisions
- Chose to make `create_app()` cheap over sharing one app across the suite: the global autouse fixture gives every test fresh data/DB/wiki dirs, and most app tests write state, so wide sharing would break isolation. The shared fixture is opt-in and limited to read-only tests.
- Not done here (finding): `test_card539_selection_narrows.py` (~21 s guard) is slow because every `resolve_allowed_tools` call runs `DataDirResolver().resolve()`, which peeks the live DB twice; fixing that is a runtime change that needs its own card.

## Findings
- 192.168.1.29 used as fake sample data in 5 test files: logged for the test-value pass (card triage), not pruned here.
- test_card539 guard cost root-caused (finding updated in docs/findings.md).
- Delete the Factory-pinned checks in test_card_497 when CARD-498 lands.
- Full-tier smoke is now the largest stage (364 s).

## Results
| Measure | Before | After |
|---|---:|---:|
| Unit suite (`pytest tests/unit`) | 501 s (2122 passed, 11 skipped) | 360 s (2119 passed, 6 skipped) |
| App-building unit files (98 files) | 302 s | 167 s |
| `create_app()` per call | ~1.4 s | ~0.3 s |
| Full preflight | 1004 s | 812 s, GREEN (unit 359, integration 77, vitest 9, smoke 364) |
| Fast tier, small change (1 src module + 1 test file) | 332 s worst case seen | 46 s, GREEN |
| Unit + integration, serial vs `-n auto` | 437 s (unit 360 + integration 77) | 71 s (2222 passed, 6 skipped) |
| Release tier (`--release`, with smoke) | 812 s (`--full`, serial) | 447 s, GREEN (smoke 357 s) |
| Fast tier for this card, `-n auto` | 81 s | 74 s, GREEN |

| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-454-tutor-trimmed-skills | desktop | PASS | 52 s; summary in %TEMP%\autoreiv-qa\card-560\summary.md |

## Release note
Faster startup: the capability catalog is seeded in one database transaction, and the test suite and preflight run about 25% faster.
