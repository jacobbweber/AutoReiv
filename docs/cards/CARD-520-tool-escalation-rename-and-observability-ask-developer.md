---
id: CARD-520
title: "Rename the Teach/Observability remedy factory_escalation to tool_escalation, and replace Observability's always-failing Apply with Ask Developer"
status: In Review
created: 2026-09-26
branch: qa
related:
  - CARD-497
  - ADR-0060
  - CARD-472
  - CARD-354
  - CARD-503
  - CARD-504
  - CARD-525
  - CARD-526
labels:
  - type:product
  - area:observability
  - area:skills
  - P2
---

# [CARD-520] `tool_escalation`: one name for "this needs a tool", and a working Ask Developer in Observability

> **Status**: In Review (`build`, 2026-09-26 ~1:50 PM ET, D1-D12 accepted as recommended, D10 folds CARD-526). Branch `feat/card-520-tool-escalation` from local qa `5880e3b7`: failing tests `3de882ee` (+ `f4eb4b96` import fix), implementation `b702a304`. Serve runs the branch on 0.0.0.0:8000 with a live-test seed. Waiting for Jacob's live test, then `merge to qa`. Refined 2026-09-26 ~12:50 PM ET from `0f5cf9da`; split from CARD-497.
> **Related**: CARD-497 (Done: D3, D14 and the shared real-send path `chat/developer_intent.js`, REQ-497-016), ADR-0060 section 4.1, CARD-472 (Teach Ask Developer), CARD-354 (friction recommendations), CARD-503 (distill timeout, affects the Teach live test), CARD-504 (needs-tool card title reads both names), CARD-525 and CARD-526 (filed from this reproduction)
> **Labels**: `type:product`, `area:observability`, `area:skills`, `P2`

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code (this pass) |
| **`build`** | Build test-first on `feat/card-520-tool-escalation`, with the decisions as accepted |
| **`merge to qa`** | After In Review, and after the runbook passes on scratch and serve |

---

## 1. Four Beats

**Beat 1: What Jacob means.** When Teach or the Observability friction audit decides "this agent needs a tool, not a new rule", AutoReiv calls it a tool escalation, never a Factory escalation, and offers one action that works: **Ask Developer**. That button opens a Developer chat with the request and the reply starts right away, exactly like Ask Developer on a capability gap (CARD-497). The Observability card no longer shows an **Apply Patch** button that can only fail with HTTP 500. Old data that still says `factory_escalation` keeps working and is rewritten to the new name once.

**Beat 2: What AutoReiv does now.** Reproduced 2026-09-26 ~12:55 PM ET on a scratch server (port 8767, fresh data `scratch\c520_repro`, never Jacob's AppData). Script `scratch\c520_repro.py` (seeds one session with four 20,790-byte tool results, runs the audit, lists and applies every recommendation); UI capture `scratch\c520_obs.cjs` (desktop 1280x900 and phone 390x844, screenshots `scratch\c520_obs_{desktop,phone}_{before,apply}.png`); evidence `scratch\c520_repro_evidence.json`.

| Seeded tool result (20,790 bytes) | Recommendation | Apply (`POST .../recommendations/{id}/apply`) |
|---|---|---|
| `wiki_note_search` (pagination-aware) | `runbook_patch` on `packs/autoreiv/skills/wiki-knowledge/SKILL.md` | **200**, patch written |
| `wiki_note_read` (in skill `wiki_tasks`) | `factory_escalation`, "Escalate wiki_note_read to Factory Studio (unbounded payload)." | **500** "Failed to apply recommendation to 'packs/autoreiv/skills/wiki_tasks/SKILL.md'." |
| `c520_inventory_dump` (in no skill) | `factory_escalation`, `skill_path: null` | **500** "Failed to apply recommendation to 'None'." |
| `c520_other_dump` (in no skill) | **none**: 4 incidents gave 3 recommendations; the dedup key `(agent, skill_path, friction_type)` has no tool name (filed **CARD-525**) | |

- UI (desktop and phone): each escalation card shows the badge **"Factory Escalation"**, the summary "Escalate <tool> to Factory Studio ...", and the buttons **Apply Patch** and **Dismiss**. Clicking Apply Patch gives the toast **"Failed to apply patch: HTTP 500"**. No Ask Developer exists on this card.
- The friction section is hard to reach: **Skill Friction & Runbook Recommendations** is nested inside **Capability Catalog**, which is nested inside **Live System Logs** (the `<details>` at `index.html` L928 and L1143 are never closed). Collapsed by default, so the operator has to open Live System Logs, then Capability Catalog, then the friction section (filed **CARD-526**; D10 recommends folding it in).
- Teach: a needs-tool distill result is saved as a `skill_proposal` chat message whose JSON has `factory_escalation`; the proposal card carries `data-factory-escalation` and Ask Developer reads it (`teach_modal.js` L13). The distill prompt asks the model for `factory_escalation` (`distillation_service.py` L244).
- Stored old names on Jacob's serve data (read-only scan of every text column in `autoreiv.db`, plus `skills/_friction_recommendations.json` and the data folder): **0 rows, no ledger file, 0 files**. The migration is still needed for other installs and for any rows created before the build.

Full sweep (`rg -i "factory_escalation|factory-escalation|factoryEscalation|factory escalation"` over src, tests, platform-packs, docs, steering, scripts, CHANGELOG, README; 54 hits):

| Area | References |
|---|---|
| Backend writers | `distillation_service.py` L244 (prompt), L298, L314 (needs-tool result), L355, L397 (`None` in the skill and heuristic results); `tool_skill_resolver.py` L211-215 (text "Escalate ... to Factory Studio", remedy); `observability/models.py` L95 (field description) |
| Backend readers | `routers/observability.py` L317-371 (list), L374-444 (apply: any `False` becomes 500), L447-476 (dismiss); `telemetry_friction_auditor.py` L65 (auto-apply only for `runbook_patch`) |
| Frontend | `chat/render.js` L267 (`data-factory-escalation`); `chat/teach_modal.js` L13; `observability.js` L835-837 (badge), L839-848 (actions: always Apply Patch + Dismiss), L899-917 (apply handler) |
| Skills / platform packs | none |
| Unit tests | `test_tool_skill_resolver.py` L98-114; `test_card354_developer_simulations.py` L253; `test_skill_distillation_service.py` L138, L162-182; `test_skill_proposal_persistence.py` L152 |
| Vitest | `teach_distill_contract_500` L182; `chat_workbench_teach_wiring_472` L226; `card_496_retire_factory_ui` L232 (pins the old attribute); `skill_distillation_ui` L46 (title only) |
| Smoke | TC-34 fixture L1038, TC-36 fixture L1136 |
| ADR / steering | ADR-0060 L60 says "renamed `tool_escalation` (CARD-497)": change to CARD-520 |
| Cards (history, leave) | CARD-472, 495, 496, 497, 500, 504, 515; CARD-504 D2 already plans to read both names |
| Archive (leave) | `docs/archive_artifacts/specs/in-situ-skill-distillation/*` |
| CHANGELOG | L32 (CARD-496 history line, leave); the build adds a new line |

**Beat 3: What changes.**
- **One name.** Every writer uses `tool_escalation`: the distill prompt and result key, the Observability `remedy_kind`, the Teach card attribute `data-tool-escalation`. The badge reads **"Needs a tool"**. The text reads "Ask Developer to add pagination or a filter to <tool>: it returned N bytes (limit 8 KB)." No operator-visible "Factory".
- **Old data keeps working.** A one-time, idempotent startup migration rewrites stored values (skill-proposal messages, friction proposals, the ledger file). Readers also accept the old name for one release (D2).
- **Observability card.** A `tool_escalation` card shows **Ask Developer** and **Dismiss**, never Apply. Ask Developer builds a Tools Studio draft from the recommendation (`modify` the tool, D6), posts `/api/tools_studio/authoring/talk` and opens the Developer chat through the same `openDeveloperSession` / `sendDeveloperIntent` real-send path as CARD-497, so the reply starts immediately. The card then shows **"Asked Developer"** (D5).
- **Apply tells the truth.** The Apply route answers **409** with a plain reason for a tool escalation and for a runbook patch that has no skill to patch, **404** when the SKILL.md is gone, and 500 only for a real write error (D8).
- **Shared Ask Developer helper.** Gap, Teach and Observability build their draft differently but post and open the chat through one helper (D7).
- **Friction section reachable** at the top level of Observability (CARD-526, if D10 is accepted).

**Beat 4: Done when.** New distills and friction recommendations say `tool_escalation`; old stored ones are rewritten once and still render with Ask Developer; the Observability tool-escalation card has Ask Developer (the Developer reply starts with no further input) and Dismiss, never an Apply that fails; Apply never answers 500 for a recommendation that simply cannot be applied; no operator-visible text names the Factory; REQ-520-001..014 pass with tests written first; the runbook passes on scratch and serve (desktop and phone).

---

## 2. What must keep working (the regression fence)

- `runbook_patch` recommendations: audit, list, **Apply Patch** (200, idempotent bullet insert, path jail), Dismiss, and auto-apply for routines with `auto_apply`.
- Teach: distill, the skill proposal card, Adopt, Dismiss, `/learn`, and **Ask Developer to build this tool** (CARD-472, CARD-500), including history cards rendered from stored messages.
- Gap Ask Developer and Tools Studio Talk (CARD-497 REQ-497-016): one real send, no double send, no resend on reopen, busy chat puts the text in the composer.
- The friction list API shape (`GET /api/observability/friction/recommendations`) apart from the renamed value and the new optional fields; the `status` filter still works.
- The context compactor still drops `skill_proposal` messages (`context_compactor.py` L286).
- Smoke TC-32/TC-34/TC-36/TC-39/TC-44 and the CARD-497 Vitest suites.

---

## 3. Acceptance criteria (EARS)

- **REQ-520-001 (distill writer):** WHEN Teach distills a turn that needs a tool, THE result and the saved `skill_proposal` message SHALL carry the escalation under `tool_escalation` and SHALL NOT contain the key `factory_escalation`. The distill prompt SHALL ask for `tool_escalation`.
- **REQ-520-002 (distill reader of model output):** IF the model's JSON uses `factory_escalation`, THEN THE distill service SHALL treat it as `tool_escalation` (so an older prompt habit still yields a needs-tool card).
- **REQ-520-003 (friction writer):** WHEN the friction resolver recommends a tool change (payload bloat on a tool that is not pagination-aware), THE recommendation SHALL have `remedy_kind: "tool_escalation"`, `tool_name`, `payload_bytes`, the summary "<tool> needs pagination or a filter (unbounded payload)." and the text "Ask Developer to add pagination or a filter to <tool>: it returned <N> bytes (limit 8 KB)." It SHALL NOT mention the Factory.
- **REQ-520-004 (model reader):** `RunbookRecommendation` SHALL accept `remedy_kind: "factory_escalation"` and expose it as `tool_escalation`. WHERE `tool_name` is missing on an old record, THE list route SHALL derive it from the old text ("Escalate <tool> to ...") when it can.
- **REQ-520-005 (migration):** WHEN the app starts, THE system SHALL rewrite, once and idempotently: `skill_proposal` messages whose JSON has `factory_escalation` (key renamed, value kept), friction proposals whose payload has `remedy_kind: "factory_escalation"`, and the same field in `skills/_friction_recommendations.json`. It SHALL parse JSON (never a text replace), leave malformed rows untouched, log the counts, and change 0 rows on the next start.
- **REQ-520-006 (Teach attribute):** THE Teach proposal card SHALL carry `data-tool-escalation`. Ask Developer SHALL read it, and SHALL fall back to `data-factory-escalation` and the `factory_escalation` key for a card rendered from data the migration has not reached.
- **REQ-520-007 (Observability actions):** WHILE a recommendation is `tool_escalation` and pending, ITS card SHALL show **Ask Developer** and **Dismiss** and SHALL NOT show Apply Patch. THE badge SHALL read "Needs a tool". A `runbook_patch` card SHALL keep Apply Patch and Dismiss.
- **REQ-520-008 (Observability Ask Developer):** WHEN the operator clicks Ask Developer on a tool-escalation card, THE app SHALL post `/api/tools_studio/authoring/talk` with intent `modify` and a draft naming the tool and the limit, switch to chat and send the request through `openDeveloperSession` (CARD-497 REQ-497-016), so the Developer reply starts with no further input, once, never twice on a double click.
- **REQ-520-009 (escalated state):** WHEN that chat opens, THE recommendation SHALL be marked `escalated` (proposal status `approved`, payload and ledger `status: "escalated"`, `developer_session_id` stored) and ITS card SHALL show "Asked Developer" with no buttons; a later audit SHALL NOT recreate it. IF the talk call fails, THEN THE card SHALL stay pending and a toast SHALL say why.
- **REQ-520-010 (Apply statuses):** IF Apply is called for a `tool_escalation`, THEN THE route SHALL answer **409** "This recommendation needs a tool change, not a runbook patch. Use Ask Developer." IF a `runbook_patch` has no `skill_path`, THEN **409** "No skill lists <tool>, so there is nothing to patch." IF the SKILL.md is missing, THEN **404**. THE route SHALL answer 500 only for an unexpected write error. THE UI SHALL show the route's message, not "HTTP 500".
- **REQ-520-011 (shared helper):** Gap Ask Developer, Teach Ask Developer and Observability Ask Developer SHALL post the talk request and open the chat through one shared helper; Tools Studio Talk keeps its form flow but the same `openDeveloperSession`.
- **REQ-520-012 (no Factory words):** No operator-visible string in `observability.js`, `chat/render.js`, `chat/teach_modal.js`, `tool_skill_resolver.py` or the distill results SHALL contain "Factory". Outside the migration module and the named reader fallbacks, `src/` SHALL NOT contain `factory_escalation` or `data-factory-escalation` (sweep test with an allowlist).
- **REQ-520-013 (reachable section, if D10):** THE friction section SHALL be a top-level Observability section (not inside another `<details>`), and every Observability `<details class="obs-section">` SHALL be closed before the next one opens.
- **REQ-520-014 (docs):** ADR-0060 section 4.1 SHALL name CARD-520 for the rename; CHANGELOG SHALL describe the rename, the migration and the Apply statuses.

---

## 4. Decisions (recommendations in bold; waiting for `build`)

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | New name and label | `tool_escalation` / `needs_tool` / `developer_escalation` | **`tool_escalation`** (CARD-497 D3 already confirmed it; Teach already has a `needs_tool` boolean, so reusing that word as a remedy name would blur them). Badge **"Needs a tool"** |
| D2 | Old stored values | (a) readers accept both, no rewrite; (b) one-time startup migration plus reader fallback for one release; (c) rewrite only | **(b).** An idempotent startup step in the same style as CARD-497 D8 (`reset_stranded_training_gaps`), JSON-parsed, in one transaction per table, counts logged. Reader fallbacks stay until CARD-498's release and are removed there (note added to CARD-498 at build). Jacob's data has 0 old rows today, so the risk on serve is nil |
| D3 | Model output key | Ask for the new key only / ask for the new key and accept the old one | **Ask for `tool_escalation`, accept `factory_escalation`** from the model (REQ-520-002); costs one line and avoids a lost needs-tool card |
| D4 | Actions on an Observability tool-escalation card | Keep Apply and fix the 500 / Ask Developer + Dismiss / Ask Developer + Open in Tools Studio + Dismiss | **Ask Developer + Dismiss**, no Apply. Same as the gap card after CARD-497; Tools Studio stays reachable from the Developer chat and the fallback path |
| D5 | What happens to the recommendation after Ask Developer | Leave it pending / mark it applied / new `escalated` status | **New `escalated` status** (proposal `approved`, payload and ledger `status: "escalated"`, `developer_session_id` kept) through a small `POST .../recommendations/{id}/escalate` called after the talk call succeeds. Card shows "Asked Developer". Stops the same card being sent twice and keeps "applied" meaning "a file changed" |
| D6 | Draft sent to Developer from Observability | intent `create` / intent `modify` for the existing tool | **`modify`**, draft `{tool_name, behavior: "Add pagination or a filter (limit/offset or a query) so <tool> stays under 8 KB; it returned <N> bytes in session <id> (agent <agent>).", target_agent_id}`. The tool exists; Developer changes it. Needs `tool_name` and `payload_bytes` on the recommendation (REQ-520-003), with the old-text fallback for old records |
| D7 | Shared Ask Developer code | Copy the Teach code into Observability / one helper | **One helper**, e.g. `askDeveloperWithDraft(draft, {intent, callbacks, fetchFn, toastFn})` in `tools_studio_authoring.js`, used by `forge/tools.js askDeveloperAboutGap`, `chat/teach_modal.js askDeveloperToBuildTool` and Observability. It posts talk and calls `chat.openDeveloperSession` (real send). Observability gets `switchTab`/`getChatCtrl` from `sharedCallbacks` (`app.js` L321) |
| D8 | Apply route answers | Keep 500 / 409 for tool escalation only / full map | **Full map:** 409 for tool escalation, 409 for a runbook patch with no skill (the same always-500 bug for `runbook_patch` on a tool that no skill lists), 404 for a missing SKILL.md, 500 only for a raised write error. `apply_recommendation` returns a reason instead of a bare `False` |
| D9 | Wording | | **Summary** "<tool> needs pagination or a filter (unbounded payload)." **Text** "Ask Developer to add pagination or a filter to <tool>: it returned <N> bytes (limit 8 KB)." |
| D10 | Nested Observability sections (CARD-526) | Fold in / leave for CARD-526 | **Fold in.** Two missing `</details>` tags; without the fix the card this work changes is three clicks deep and collapsed, and the live test and smoke must open two unrelated sections first. CARD-526 closes with this card (as CARD-517 did with CARD-511) |
| D11 | Dedup drops a second tool without a skill (CARD-525) | Fold in / separate | **Separate (CARD-525, P3).** It is an auditor dedup rule, not part of the rename or the Apply fix. The runbook avoids it (first audit on serve, one tool per test) |
| D12 | `btn-escalate-developer` class, `needs_tool` flag, `propose_tool` | Rename too / leave | **Leave.** They do not say Factory and other code and tests depend on them |

---

## 5. Failing-tests-first plan

Write these first, confirm they fail on qa `0f5cf9da` (or the build base), commit, then build.

**Unit (pytest):**
1. `test_tool_skill_resolver.py`: payload bloat on a non-pagination tool gives `remedy_kind == "tool_escalation"`, `tool_name`, `payload_bytes`, the D9 wording, and no "Factory" in summary or patch (replaces L98-114). `test_card354_developer_simulations.py` L253 moves to the new value.
2. `RunbookRecommendation(remedy_kind="factory_escalation")` reads back as `tool_escalation`.
3. `apply_recommendation` returns a reason: tool escalation, no skill path, missing file, applied, already present.
4. Route (new `tests/unit/web/test_friction_recommendations_routes.py` on a temp store and data dir): Apply answers 409 / 409 / 404 / 200 per D8 with the REQ-520-010 messages; list derives `tool_name` for an old ledger record; `POST .../escalate` marks the proposal approved and the ledger `escalated` with `developer_session_id`; a second audit over the same session does not recreate an escalated recommendation.
5. `test_skill_distillation_service.py` L138-182: the needs-tool result has `tool_escalation` and no `factory_escalation`; the prompt contains `"tool_escalation"`; a model reply that uses `factory_escalation` still yields `tool_escalation` (REQ-520-002). `test_skill_proposal_persistence.py` L152 uses the new key.
6. Migration (new `tests/unit/core/test_card_520_tool_escalation_migration.py`): seeded `skill_proposal` message with the old key, a friction proposal and a ledger with the old `remedy_kind`, one malformed JSON row. After the migration all are rewritten, the malformed row is untouched, counts are returned; a second run changes 0.
7. Sweep (same file): no `factory_escalation` / `data-factory-escalation` in `src/` outside the allowlist (migration module, model validator, `teach_modal.js` fallback, distill reader); no "Factory" in the operator strings of the REQ-520-012 files.

**Vitest:**
8. `chat/render.js` renders `data-tool-escalation` from `tool_escalation` (update `card_496_retire_factory_ui` L232 and `teach_distill_contract_500` L182).
9. `teach_modal` Ask Developer reads `data-tool-escalation`, and falls back to `data-factory-escalation` (update `chat_workbench_teach_wiring_472` L226, add the fallback case).
10. `renderFrictionRecommendations`: a `tool_escalation` card and an old `factory_escalation` card both show "Needs a tool", **Ask Developer** and Dismiss, and no Apply; a `runbook_patch` card keeps Apply Patch; an `escalated` card shows "Asked Developer" and no buttons.
11. Observability Ask Developer (new `tests/unit/frontend/card_520_observability_ask_developer.test.js`): posts talk with intent `modify` and the D6 draft, calls `openDeveloperSession(sessionId, prompt)` once, then posts `/escalate`; a talk failure toasts and leaves the card pending; a double click sends once.
12. The shared helper is used by gap, Teach and Observability (source check, like `card_497_developer_intent_send`).
13. `index.html` (DOMParser): the friction `details` has no `details` ancestor, and no `details.obs-section` is nested in another (D10).
14. The Apply handler shows the route's `detail` message on 409/404.

**Smoke (Playwright, desktop and phone):**
15. New **TC-45**: route-mock `GET /api/observability/friction/recommendations` with one `tool_escalation` and one `runbook_patch`; open Observability and the friction section **without opening Logs or Capability Catalog**; the escalation card shows "Needs a tool", Ask Developer and Dismiss, no Apply; the patch card shows Apply Patch; click Ask Developer: talk is posted with intent `modify` (mocked), chat opens on Developer and one `/api/chat/stream` request with `agent_id: developer` is made with no further input (the stream held open, as in TC-44), and `/escalate` is posted.
16. Update TC-34 and TC-36 fixtures to `tool_escalation`; add one history card with the old key to TC-34 and assert Ask Developer still posts talk.

**Full suites at In Review:** unit, integration, Vitest, ESLint, ruff, then smoke on its own. Allowed failures: CARD-454 (linter, 4 Tutor errors), CARD-456 (3 Vitest), and the pre-existing ESLint (4 errors in education/study files) and ruff (7 errors in education files and tests) seen on qa `0f5cf9da`.

---

## 6. Runbook (live test on Jarvis, after build)

Scratch first (`powershell -ExecutionPolicy Bypass -File scratch\c505_run.ps1 -Data c520_live -Wipe -Tag c520l`, port 8767), then serve on 0.0.0.0:8000.

1. **Replay the reproduction (scratch):** point `scratch\c520_repro.py` at the new data folder and run it. Expect `tool_escalation` for `wiki_note_read` and `c520_inventory_dump` with the D9 wording, Apply **409** with the REQ-520-010 message for both, Apply **200** for the `wiki_note_search` patch.
2. **Migration (scratch):** stop the server, seed old data with a small script (one `skill_proposal` message with `factory_escalation`, one friction proposal and one ledger entry with `remedy_kind: "factory_escalation"`), start the server. The log shows the counts; the rows now say `tool_escalation`; the old Teach card still offers Ask Developer; the old friction card shows "Needs a tool". Restart: 0 rows changed.
3. **UI (scratch, desktop and phone):** Observability: **Skill Friction & Runbook Recommendations** is a top-level section. The escalation cards show "Needs a tool", **Ask Developer** and **Dismiss**, no Apply Patch; no "Factory" anywhere on the page.
4. **Serve (Jacob's data): make a tool-escalation remedy.**
   - *Primary, with the LLM:* in a Developer chat, ask "Use repo_file_read to read CHANGELOG.md in full, then tell me how many lines it has." `repo_file_read` returns up to a 24,000-character excerpt (`READ_EXCERPT_CHARS`), about three times the 8 KB limit, and it is not pagination-aware. Then Observability, **Skill Friction & Runbook Recommendations**, lookback **24h**, **Run Telemetry Audit**. A card "repo_file_read needs pagination or a filter" appears with Ask Developer.
   - *Fallback, no LLM needed:* run `scratch\c520_seed_serve.py` (written at build: creates one session "C520 live test" with a single 20 KB result from `c520_inventory_dump` in Jacob's DB, no other changes), then Run Telemetry Audit. Delete that session and its proposal after the test (cleanup step 8).
5. **Serve: Ask Developer from Observability.** Click Ask Developer on that card. The chat opens on Developer with the request as your message and the Developer reply starts streaming right away with no extra typing. Back in Observability the card reads "Asked Developer". Run the audit again: it is not recreated.
6. **Serve: Teach tool escalation.** In an AutoReiv chat: "What's the weather in Boston right now?" AutoReiv says it has no way to check. Teach on that reply with guidance "AutoReiv has no weather tool; it needs a tool that returns the current weather for a city." The proposal card shows "Needs a tool" and **Ask Developer to build this tool**; clicking it opens Developer and the reply starts at once. (If the distill falls back to the heuristic answer because of the 4.5 s timeout, CARD-503, retry once; the Teach path is also covered by smoke TC-34/TC-36.)
7. **Apply still works for patches (serve):** if the audit produced a `runbook_patch` card, Apply Patch returns success and the bullet appears in the SKILL.md under Jacob's data. Otherwise covered by step 1.
8. **Phone** (`http://192.168.1.99:8000`, Ctrl+F5 equivalent): repeat 3 and 5. **Cleanup:** delete the "C520 live test" session and its friction proposal and ledger entry if the fallback was used; leave Jacob's own Developer chats.
9. Restart serve (`scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`); health returns 200 on 127.0.0.1 and 192.168.1.99; app.js `?v=` bumped.

---

## 7. Definition of done

- REQ-520-001..014 pass; tests were written first and seen failing.
- Full suites pass apart from the known failures listed in section 5.
- The runbook passes on scratch and serve (desktop and phone).
- ADR-0060 L60 names CARD-520 (done in this refinement); CARD-504 and CARD-498 get a note (504 reads `tool_escalation` first; 498 removes the reader fallbacks).
- CARD-526 is closed with this card (if D10); CARD-525 stays Ready.
- The card is set to In Review with evidence, then Done at `merge to qa`.

## 8. Build evidence (2026-09-26, ET)

- **Tests first:** `3de882ee` committed 15 pytest tests (plus updates to 4 existing files), 11 Vitest tests and smoke TC-45 (desktop and phone); red confirmed (20 pytest, 13 Vitest, TC-45 x2). Ten of the Vitest failures were an import-resolution error (template-literal dynamic imports), so `f4eb4b96` switched to literal paths and a fuller fake DOM; that file was re-run against the `3de882ee` source in a temporary worktree: **9 red for the right reasons**, 2 guards pass on old code (patch keeps Apply; failed Talk does not escalate).
- **Implementation `b702a304`:** constants and a `remedy_kind` normalizer in `domain/observability/models.py`; resolver writes `tool_escalation`, `tool_name`, `payload_bytes`, `session_id` and the D9 wording, `apply_with_reason`; `update_proposal_payload`; router list normalization, Apply 409/409/404, new `/escalate`; distill prompt and result keys; startup migration `application/observability/tool_escalation_migration.py` (called from `app.py`); `tool_escalation.js`; `askDeveloperWithDraft` shared by gap, Teach and Observability; Observability cards (Needs a tool / Ask Developer / Dismiss / Asked Developer); two `</details>` (CARD-526); app.js `2.0.88`; CHANGELOG.
- **Preflight** (`scratch\full_suite.ps1 -Tag c520`, smoke last): unit 1984 passed / 11 skipped / 1 failed (CARD-454), was 1969 (+15 new); integration 103 passed; Vitest 913 passed / 3 failed (CARD-456), was 902 (+11 new); ESLint 4 errors + 5 warnings and ruff 7 errors (pre-existing baseline, no new files); smoke 71 passed, was 69 (+TC-45 x2).
- **Scratch (port 8767):** `scratch\c520_repro.py` replay: `wiki_note_read` and `c520_inventory_dump` are `tool_escalation` with the new wording, Apply 409 "needs a tool change ... Use Ask Developer" for both, the `wiki_note_search` patch applies (200). Startup migration: seeded one old `skill_proposal` message, one proposal and one ledger entry, restarted: all rewritten, and the list shows `tool_name`/`payload_bytes` derived from the old text (`old_tool` 30000); a second start changed nothing.
- **Serve (Jacob's data):** the migration ran at startup and changed nothing (read-only pre-scan: 0 old-name messages, 0 proposals, no ledger; re-run returns all zeros). Seed `scratch\c520_seed_serve.py` made "C520 live test" (autoreiv, `c520_inventory_dump`) and "C520 live test (dismiss)" (developer, `c520_catalog_dump`), then the audit staged 6 cards (2 seeded; 4 real from the last 24 h: `wiki_note_list` and `wiki_note_search` patches, `get_recent_errors` and `list_available_skills_and_tools` escalations). Read-only browser check (`scratch\c520_verify_serve.cjs`, desktop 127.0.0.1 and phone 192.168.1.99): no nested sections, friction opens with one click, escalations show Needs a tool + Ask Developer + Dismiss, patches show Apply Patch + Dismiss, no page errors. Undo: `scratch\c520_remove_seed.py`.
- **Filed:** CARD-527 (built-in tools get tool escalations the Developer cannot act on), CARD-528 (app log lines from `src.*` do not reach the serve log, so the migration counts are not visible).

## What stays out of scope

- The friction dedup rule (CARD-525) and the distill timeout (CARD-503).
- The needs-tool card title (CARD-504), apart from reading the new key first.
- Changing which tools count as pagination-aware, the 8 KB threshold, or making `repo_file_read` paginate (that is what Ask Developer is for).
- Renaming `btn-escalate-developer`, `needs_tool` or `propose_tool` (D12).
