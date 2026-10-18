---
id: CARD-709
title: "Fix study_entry.js broken #chatInput selector and listener short-circuit, live wiki_service refresh, API key query leak, and async SSH probe blocking"
type: bug
status: Done
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-709-web-and-ui-wiring-fixes]
  checks: [tests/unit/web/test_card709_web_and_ui_wiring_fixes.py]
branch: feat/card-709-web-and-ui-wiring-fixes
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-17
completed: 2026-10-17
---

# CARD-709 Fix study_entry.js broken #chatInput selector and listener short-circuit, live wiki_service refresh, API key query leak, and async SSH probe blocking

## Problem
1. **Broken `#chatInput` DOM selector and self-sabotaging listeners in `study_entry.js`**:
   - `src/web/static/modules/studios/study_entry.js` calls `$('chatInput')` at 6 call sites (lines 414, 612, 756, 819, 936, 1020) to prefill the Chat composer when starting a study session, due review, or wiki curation. `index.html:643` defines `id="promptInput"`, not `id="chatInput"`, so all 6 study composer prefills silently fail.
   - Lines 978–1040 attach bubble-phase `click` listeners to `#chatEducationModeProgressBtn`, `#chatEducationModeDueBtn`, and `#chatEducationModeCurateBtn` to open inline Chat education panels, while lines 1082–1098 immediately attach capture-phase (`true`) listeners to the exact same buttons calling `e.stopImmediatePropagation()`, making the inline panels unreachable.
2. **Stale `app.state.wiki_service` after `PUT /api/settings/wiki-path`**:
   - `src/web/routers/settings_data_backup.py:70-107` updates `request.app.state.wiki_path` when the operator changes the wiki directory, but `src/web/routers/wiki.py:26-30` (`_get_wiki_service`) returns the cached `request.app.state.wiki_service` created at boot, so `/api/wiki/*` keeps reading and writing the old wiki folder until a server restart. `wiki.py:29` also has a hardcoded `"./data/wiki"` fallback violating `.agents/rules/boundaries.md`.
3. **Missing `app.state.data_dir` in `save_mcp_server` & redundant `app.py` fallbacks**:
   - `src/web/routers/settings.py:642` reads `getattr(request.app.state, "data_dir", None)`, which is never set on `app.state` (`app.state.data_dir_paths` is set), so `data_dir` is always `None` when authoring companion skills for saved MCP servers.
4. **Plaintext API key leaked in `GET /api/models/discover` URL query string**:
   - `src/web/static/modules/studios/settings.js:760-762` appends `&api_key=${encodeURIComponent(currentKey)}` to the `GET` request URL, leaking secrets into access logs and browser history.
5. **Synchronous `paramiko` SSH probe blocking the FastAPI event loop**:
   - `src/web/routers/remote_hosts.py:146` (`test_remote_host`) calls synchronous `_probe_ssh()` directly inside an `async def` endpoint without `asyncio.to_thread()`, blocking the entire uvicorn loop for up to 10 seconds.
6. **Stale `selectedAgentId === 'developer'` check in `chat.js` and `projects.js`**:
   - From `docs/findings.md` (M29): `#chatActiveProjectPill` (`chat.js:385`) and `#projectsPairDeveloperBtn` (`projects.js:782`) still check `selectedAgentId === 'developer'` after `developer` was folded into `autoreiv` (`CARD-682`).

## Cause
- `#chatInput` was never updated when the composer ID became `#promptInput`, and the `CARD-447` deep-link capture listener was bolted onto `study_entry.js` without cleaning up the superseded bubble listeners.
- `put_wiki_path` updated `app.state.wiki_path` without rebuilding `app.state.wiki_service`.
- `settings.js` sent `api_key` in the query string instead of an HTTP header (`X-Provider-Api-Key`).
- `test_remote_host` omitted `await asyncio.to_thread(_probe_ssh, ...)`.

## Change
- Replace all `$('chatInput')` lookups in `src/web/static/modules/studios/study_entry.js` with `_composerInput()` (`$('promptInput') || $('chatInput')`), remove the duplicate shadowed bubble listeners on `#chatEducationModeProgressBtn`, `#chatEducationModeDueBtn`, and `#chatEducationModeCurateBtn` in `initStudyEntry()`, and update `chat.js` / `projects.js` to show the active project pill and select `autoreiv`.
- Refresh `request.app.state.wiki_service = WikiService(wiki_root=str(path))` in `PUT /api/settings/wiki-path` (`src/web/routers/settings_data_backup.py`) and remove the hardcoded `"./data/wiki"` fallback in `src/web/routers/wiki.py`.
- Resolve `data_dir` from `request.app.state.data_dir_paths.root` in `src/web/routers/settings.py:642` (and set `app.state.data_dir = str(data_paths.root)` in `src/web/app.py`).
- Pass unsaved `api_key` via the `X-Provider-Api-Key` request header (not URL query string) in `settings.js` and `settings.py` (`discover_models`).
- Wrap `_probe_ssh(...)` in `await asyncio.to_thread(...)` inside `test_remote_host` (`src/web/routers/remote_hosts.py`).
- Fix broken endpoint URLs in `src/web/static/modules/services/api.js` (`/api/sessions` instead of `/api/chat/sessions`).

## What dies
- Broken `$('chatInput')` lookups and duplicate shadowed bubble listeners on `progressBtn`, `dueBtn`, and `curateBtn` in `src/web/static/modules/studios/study_entry.js`.
- Plaintext `api_key` query string parameter on `GET /api/models/discover` in `settings.js`.
- Hardcoded `"./data/wiki"` fallback in `src/web/routers/wiki.py`.

## Proof
- Journey `card-709-web-and-ui-wiring-fixes`:
  1. Trigger a Study action that prefills `#promptInput` in Chat and verify `#promptInput` receives the study prompt on desktop and phone.
  2. Verify active project pill visibility on `AutoReiv` in Chat and verify `/api/models/discover` never puts `api_key` in the request URL.
- Checks:
  - `tests/unit/web/test_card709_web_and_ui_wiring_fixes.py`

## Plan and decisions
- Technical web and UI bug fixes under Phase 1 (Option 1 approved by Jacob).

## Findings
- Resolved and removed the M29 `projects-ui` finding in `docs/findings.md`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-709-web-and-ui-wiring-fixes` | desktop | PASS | `#chatStudyEntryBtn` populated `#promptInput` with `[Tutor Education Mode]`; `#chatActiveProjectPill` visible on `autoreiv`; `/api/models/discover` sent `X-Provider-Api-Key` header without URL leak |
| `card-709-web-and-ui-wiring-fixes` | phone | PASS | `#chatStudyEntryBtn` populated `#promptInput` with `[Tutor Education Mode]`; `#chatActiveProjectPill` visible on `autoreiv`; `/api/models/discover` sent `X-Provider-Api-Key` header without URL leak |

Screenshots:
- `/tmp/autoreiv-qa/card-709/card-709-web-and-ui-wiring-fixes-desktop-01-trigger-study-entry-from-chat-header-and-verify-.png`
- `/tmp/autoreiv-qa/card-709/card-709-web-and-ui-wiring-fixes-desktop-02-select-an-active-project-and-verify-chatactivepr.png`
- `/tmp/autoreiv-qa/card-709/card-709-web-and-ui-wiring-fixes-phone-03-verify-settings-studio-model-discovery-sends-api.png`

## Release note
- Fixed broken `#chatInput` study composer prefills, refreshed `WikiService` immediately when changing `wiki_path`, moved model-discovery API keys out of URL query strings, ran SSH host probes off the async event loop, and restored the active project pill for `AutoReiv` [CARD-709].
