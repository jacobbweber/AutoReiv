## [Unreleased]

### Added

- **CARD-450 Agent Studio platform defaults**: Platform agents get a **Platform defaults** section. It shows a plain-English badge only when the last platform update was skipped (edited system prompt) or partly applied (lists what was kept); up-to-date agents show no badge. One **Reset to platform defaults** button opens a confirm dialog listing Replaced (system prompt, shipped skill files, skill on/off list, platform tool list) vs Kept (max turns, model, provider and every other setting). It saves a backup, then resets. A per-agent **Backups** list (local time, ISO tooltip) offers **Restore** behind its own confirm dialog. Both actions re-read the agent, sync status and backups. When no newer platform version exists, the badge says the agent is customized, not that an update was skipped. When "Keep my agent customizations" is off, the section warns that edits reset on the next restart. Module: `src/web/static/modules/studios/forge/platform_defaults.js`. Contracts: `tests/unit/agent_packs/test_card_450_platform_reset.py`, `tests/unit/frontend/card_450_platform_defaults.test.js` ([CARD-450]).
- **CARD-451 Settings software updates via git**: System & Software Updates uses fixed `origin` (read-only URL). **Check for updates** = `git fetch --prune origin`. **Update now** = `git pull --ff-only` on the current branch with refusals for dirty / ahead / in-progress / detached / no-upstream (never reset/force/stash). Branch picker lists local+remote; switch creates tracking branches. After success: dependency-change detection (`pyproject.toml` / `uv.lock` / `requirements*.txt`) + `uv sync`, then injectable detached restart preserving host/port. Daily auto-update (default OFF) with busy deferral (chat streams, routines, Studio/Factory jobs). History in user-data settings. Contracts: `tests/unit/system/test_card451_software_updates.py`, router tests with `NoOpRestarter` ([CARD-451]).

### Changed

- **CARD-465 Chat composer grows on focus**: Clicking or typing in the Chat box opens it to the smaller of 8 lines and 40% of the visible chat column (limited by `visualViewport`, so a phone keyboard shrinks it); past the cap it scrolls inside. Unfocused it fits its text (up to the cap) and an empty box returns to one line; the auto-focus when Chat opens keeps it one line. The message list shrinks instead of being covered, stays scrollable, and stays pinned to the latest message when you were at the bottom (re-pinned on viewport/keyboard resize and when the Options drawer changes height); a click inside the composer area finishes before it shrinks. Jump to latest now sits on the list's bottom edge inside new `#chatMessagesViewport` (was a fixed `bottom-28`). One shared `setComposerText()` in `chat/composer.js` replaces every direct `promptInput.value =` write (Talk to Forge, new-agent authoring, Developer sessions, Tools Studio, lab monitor, Prompts, Projects pairing, send/`/learn` clears); `max-h-36`, the ad-hoc height reset and three dead `input` dispatches are gone. Contracts: `tests/unit/frontend/chat_composer_grow_465.test.js`, smoke TC-8 ([CARD-465]).
- **CARD-445 Global default turn budget 50**: Every agent now defaults to **50** turns per reply (was a hidden 10). One constant `DEFAULT_AGENT_MAX_TURNS` in `src/domain/kernel/models.py` feeds the profile model, guardrails, agents API, settings repository fallbacks, agent builder scaffold, handoff child-profile fallback, the `custom_agents` column default for new databases, and the Agent Studio Max Turns field. On startup (after platform pack promotion) a one-time upgrade raises any stored `max_turns` of exactly 10 to 50 and keeps every other value; it never touches `user_modified` (CARD-449) and records itself in settings key `agent_max_turns_default_50_applied` (`applied_at`, `raised`) so it runs once. Range stays 1-1000. flashcard-turn SKILL.md no longer states a numeric budget. Pack manifests still carry no `max_turns` (by design). Job / phase / handoff-envelope budgets are left to CARD-462. Contract: `tests/unit/agents/test_card445_global_turn_budget.py` ([CARD-445]).

### Fixed

- **CARD-472 Workbench, View Full Report and Teach wiring**: The Chat header Workbench button opens and closes the pane again (it was built from the chat state instead of the page elements after the CARD-397 split; `collectWorkbenchElements()` in `chat/workbench.js` now supplies the real template elements). A reply's Workbench button shows the reply with Preview/Raw, Copy (toast "Artifact copied to clipboard") and Save to Wiki; toast arguments were swapped. Every **View Full Report** card (history, live stream, Workbench preview) goes through one `openArtifactById()`: it fetches `/api/artifacts/{id}` once and opens it in the Workbench, or shows "Artifact not found" (before, depending on the path, the click did nothing useful or opened an empty Workbench). The header badge counts distinct artifacts again. The Teach modal moved to `chat/teach_modal.js`; its X button now closes it. A needs-tool skill proposal's button is now **Ask Developer to build this tool**: it opens a Developer chat pre-filled with the tool name, seed intent and objectives (`POST /api/tools_studio/authoring/talk`), and falls back to Tools Studio with a toast if that fails. A press in the message list now lands before the focused composer shrinks, so the first click on View Full Report or Workbench right after sending works on desktop (it was lost to the layout shift). On phones the Workbench pane now fills the chat area instead of sliding under the window title bar, so its back arrow works. `chat.js` 1,012 -> 1,004 lines. The training popup is left for CARD-496. Contracts: `tests/unit/frontend/chat_workbench_teach_wiring_472.test.js`, smoke TC-33/TC-34 desktop+phone ([CARD-472]).
- **CARD-488 Switching chats during your own reply shows the chat you picked**: Picking another chat, pressing New chat or switching agent while this tab was streaming a reply kept the old chat on screen, because rendering is skipped while streaming. It also hid Send, so Enter was ignored, and Stop then aborted the newly opened chat while the original reply kept running on the server. One flag, `state.isStreaming`, meant both "this tab is streaming" and "the open chat is streaming". Now:
  - New `chat/own_stream.js` (`createOwnStreamTracker`) tracks this tab's reply apart from the chat on screen.
  - Switching to a different chat detaches it. Only the browser request is cancelled and the server keeps going (CARD-154). Streaming is cleared, the stream bubble is removed, and Send comes back, so the picked chat renders and sends normally.
  - A detached turn can no longer write into the view (messages, notices, errors, button state).
  - Back on the first chat, the CARD-485 busy state shows while it is still running, and Stop aborts **that** chat. Stop always targets this tab's streaming chat, otherwise the open chat.
  - Switching agent mid-reply now opens that agent's chat: `loadSessions` no longer returns early while streaming.
  - Contracts: `tests/unit/frontend/chat_switch_during_reply_488.test.js`, smoke TC-30/31/32 ([CARD-488]).
- **CARD-486 Stop stops the reply on the server again**: The CARD-397 split dropped the server call from Stop. Pressing Stop only cut the browser off, so the model kept generating to the end (CARD-154 keeps work alive on disconnect), saved the whole reply, and held the only generation slot. The next message waited about 27 s in the scratch repro. Now:
  - New `chat/stop.js` (`createStopHandler`) cancels this tab's request, then sends one `POST /api/chat/stream/{id}/abort` for the open chat. It does this both for your own reply and for a reply running on another device (the CARD-485 busy state, where Stop used to do nothing). The abort cancels the model request and checkpoints a running phase so the job can resume (CARD-259). Extra presses while the abort is pending are ignored. It then stops the status watch, clears busy, restores Send, reloads the chat and shows **Stopped**. If the server can't be reached it shows a warning and still restores Send.
  - `GET /api/sessions/{id}/status` only reports running when a reply is in progress or a job phase is actually running. A stopped job (phase queued, resumable) or an approval that is waiting no longer reads as running, so busy clears after Stop in plan chats.
  - A waiting approval stays parked. The words shown before Stop disappear on reload, as before the split (keeping them is CARD-489).
  - Contracts: `tests/unit/frontend/chat_stop_486.test.js`, `tests/unit/web/test_card486_status_after_abort.py`, smoke TC-28/29 ([CARD-486]).
- **CARD-485 Picking a chat works like before the split again**: Since CARD-397, `selectSession` only loaded messages. Now:
  - New `chat/session_select.js` redraws Recent Chats with the picked chat highlighted, and closes the sessions drawer when you pick from it (desktop and phone; automatic selects on load and New chat leave the drawer alone).
  - It restores the chat's job strip and inline phase chips from `/api/chat/sessions/{id}/journey` (waiting-for-approval job first; a late reply for a chat you left is ignored), and refreshes the context badge when Options is open.
  - It asks `/api/sessions/{id}/status`. While the reply is still running elsewhere it shows Stop, hides Send, blocks sending and re-checks every 2 s (only while that chat is open and the page visible). When the reply finishes it restores Send and reloads the reply. Switching chats or starting your own reply stops the check.
  - Restoring the last chat on load goes through the same path. `hydrateJobPhaseStateFromJourney` moved into the module (still re-exported from `chat.js`). The stub `checkSessionBackgroundStatus` is replaced by `watchSessionStatus` for CARD-473. `chat.js` is down to 1,008 lines. Live replay of a running reply is CARD-487.
  - Contracts: `tests/unit/frontend/chat_session_select_485.test.js`, a behaviour test in `chat_hitl_journey_295.test.js`, smoke TC-24..TC-27 (desktop + phone) ([CARD-485]).
- **CARD-476 The first Chat message no longer fails with HTTP 422, and each device reopens its last chat**: Since the CARD-397 split, an agent with no chats had no session. The empty-list create in `chat/chrome.js` was never wired, and the send path had no guard, so the first message posted `session_id: null` and got a 422 ("Chat turn failed: Stream error: HTTP 422"). Sending before the chat list finished loading did the same. Now:
  - `chat.js` passes `createNewSessionFn` again, so an agent with no chats gets one on load and on agent switch. The new chat shows in the list right away.
  - New `chat/session_guard.js` `ensureActiveSession()` runs before every send and paperclip upload. It waits for any in-flight load (including an agent switch), creates at most one session (single-flight), and if that fails it doesn't send, shows "Couldn't start a new chat", and keeps the typed text. The backend stays strict (a null `session_id` is still 422).
  - On load, the chat saved in `autoreiv_active_session_id` (per device) reopens when it is in the current agent's list; otherwise the newest opens. The key was written but never read before.
  - `createNewSession` now treats a non-2xx reply as a failure.
  - Contracts: `tests/unit/frontend/chat_session_guard_476.test.js`, smoke TC-20..TC-23 (desktop + phone) ([CARD-476]).
- **CARD-475 An image no longer breaks a chat session**: Sending a screenshot to the default vLLM model (`nemotron-3.5-lightning`, text-only) made the Spark gateway answer HTTP 200 with a bare JSON error line (`... is not a multimodal model`). The stream parser skipped it and the kernel saved an empty assistant row. The adapters also re-read every `Local Path:` image in the whole history on every turn, so every later message in that chat failed the same way. Now:
  - The gateway (`src/application/gateway/attachment_images.py`) attaches image bytes only for the latest user message, and only when the model can view images. Earlier pictures are never re-sent, even to vision models (D3). The adapters no longer scan history. Chats that were stuck heal on the next message, with no data change (D5).
  - A text-only model gets a short note instead of the bytes, and the user sees an `attachment_notice` under the reply, worded exactly: "This model can't view images, so it only saw the file name `<name>`. Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures." (D1, D6).
  - Which models can view images (`src/application/gateway/model_capabilities.py`): your per-model **Can view images** checkbox (Settings > Providers > Refresh Models table, new `POST /api/settings/model-capabilities`), then provider metadata saved on Refresh Models (Ollama `capabilities`; a gateway description that says multimodal/vision/image/omni), then the model-name guess, otherwise text-only (D2). If the provider still refuses images, the turn is retried once without them, with the notice.
  - A provider error inside an HTTP 200 stream (bare JSON line, `data: {"error": ...}` frame, vLLM `{"object": "error"}`, Ollama `{"error": ...}` line) is now a real error. An empty reply (no text, no tool calls) sends an `error` event ("The model returned an empty reply.") and is never saved, in both `stream_turn` and `run_turn` (`EmptyModelReplyError`).
  - Empty assistant rows already in the database are skipped when history is replayed and hidden in the thread view (D4, no migration).

  Contracts: `tests/unit/gateway/test_model_capabilities_475.py`, `test_image_turn_gating_475.py`, `test_stream_error_frames_475.py`, `tests/unit/kernel/test_empty_reply_475.py`, `tests/integration/operator_contracts/test_oc475_image_turn_text_only_model.py`, `tests/unit/frontend/chat_attachment_notice_475.test.js`, `settings_model_vision_475.test.js`, smoke TC-19. The two CARD-144 adapter tests that required history scanning were replaced ([CARD-475]).
- **CARD-469 Chat composer wiring restored**: The CARD-397 split left three composer features silently unwired. `chat.js` called object-parameter helpers with positional arguments, and the Quick Prompts code looked up IDs that do not exist in the template. **Enter** now sends again on every device, phones included, and Shift+Enter adds a newline (decision D1). Enter that confirms an IME composition is ignored. Enter while a reply is streaming does nothing (no newline, no second turn), and the submit handler regained its `isStreaming` guard (D2). The **paperclip** opens the file picker, uploads to `/api/chat/upload`, stages the file and shows a chip. Staged attachments now live on `state.stagedAttachments` and are cleared in place after a send, so later uploads still show; the sent payload takes a copy. **Quick Prompts** opens the picker, filters, and on a pick inserts the prompt's `template_text` via `setComposerText` (the box resizes), then closes the picker and drawer. Manage opens the Prompts studio, and outside click or Escape closes the picker. New `chat/quick_prompts.js`, plus `wireComposer()` / `clearStagedAttachments()` in `chat/composer.js` and `closeChatOptionsDrawer()` in `chat/chrome.js`. The ghost `chatPromptCatalogBtn` / `chatClosePromptsModalBtn` / `chatPromptsModalList` lookups and the old `renderQuickPrompts` / `loadQuickPrompts` (which read `prompt`/`content`) are removed. `chat.js` shrank from 1,045 to 1,041 lines. The phone Enter-as-newline option is CARD-474. **Failed replies are shown again**: the split had also dropped the pre-split `error` SSE branch, and the finalize reload wiped the stream bubble, so a failed turn vanished. Seen live when a screenshot was sent to the text-only vLLM model, which returns 400 "not a multimodal model" (backend issue, CARD-475). `chat/stream.js` `trackStreamOutcome()` / `reportStreamOutcome()` now add a `.chat-stream-error` alert ("Reply failed: <reason>") after the reload, plus an error toast. Contract: `tests/unit/frontend/chat_stream_error_469.test.js`, smoke TC-13. Contracts: `tests/unit/frontend/chat_composer_wiring_469.test.js`, `tests/unit/frontend/chat_quick_prompts_469.test.js`, smoke TC-9..TC-12 ([CARD-469]).
- **CARD-467 Test runs never touch live AppData**: The Playwright smoke server used to pin only the DB and wiki, so its data root (packs, skills, agents, backups) still resolved to `%LOCALAPPDATA%\AutoReiv` via the env var, the live DB's `data_dir` setting or the platform default, and startup pack promotion could write the checked-out branch's pack files into live AppData. New `scripts/smoke_server.py` force-pins data dir / DB / wiki / backups (plus a fake `LOCALAPPDATA`) under `scratch/smoke_data`, wipes it each start, and refuses to start (exit 2, names each bad path) when anything resolves into live AppData or outside `scratch/`; `--check-only` prints the resolved paths. `playwright.config.js` runs the launcher with `reuseExistingServer: false`. `tests/conftest.py` now force-sets temp data paths (was `setdefault`, a no-op when the shell had the live value, so the import-time `src.web.app.app` bootstrapped against live packs) and aborts the run on live AppData. This absorbs CARD-455: `test_req_388_002` passes with the live Developer still named "Super Developer". Old `scratch/smoke_autoreiv.db` / `scratch/smoke_wiki` retired. Contracts: `tests/unit/scripts/test_card467_smoke_isolation.py` ([CARD-467], [CARD-455]).
- **CARD-450 Reset/restore correctness**: `POST /api/agents/{id}/accept-platform-seed` is now a true reset. It backs up, unlocks, clears that pack's turned-off-skills record and uses the CARD-449 force-reset path, so an edited system prompt is replaced (previously kept as `promoted_partial`); max turns and model stay. Single-pack promotions (reset/restore) merge into `platform_pack_sync_last_report` instead of wiping every other pack's status. Backup restore now also writes the operator override, which previously hid the restored prompt, and re-runs promotion for that pack so its skip status returns ([CARD-450]).
- **CARD-449 Pack lock granularity**: Scalar edits (`max_turns`, `model`, provider) no longer set `user_modified` / block platform-pack promotion. Prompt lock compares content to `platform_shipped_prompt_hashes`. Operator-disabled skills stay off while new platform skills are added. Automated additive grants / native packaging / Factory auto_pin no longer false-lock agents. One-time lock migration reports under sync-status `lock_migration`. Global setting `platform_pack_keep_customizations` (default true) force-resets pack content when false (after backup). Backups: `GET/POST /api/agents/{id}/pack-content-backups`. Settings toggle in Preferences (with System & Software Updates). Contract: `tests/unit/agent_packs/test_card_449_pack_lock_granularity.py` ([CARD-449]).


### Security

- **CARD-470 Chat Auto-run toggle no longer inverted**: Since the CARD-397 split (2026-09-20), `chat.js` sent `!approvalToggle.checked`, so with Auto-run **unchecked** (the default) every chat turn went out as `approval_mode: "run"`. That let tools that need approval (`cli_exec`, `execute_code`, wiki note writes, card/spec/project writes, `git_commit`, repo file writes, risky MCP tools, skill proposals) run without asking, and the mode carried into jobs and handoff child agents. Blocked tools stayed blocked. Unchecked now sends `"ask"` and checked sends `"run"`. New `chat/runtime_toggles.js` `setupRuntimeModeToggles()` restores the remembered choice (`autoreiv_approval_autorun`, default off/ask on a fresh install), saves changes, keeps `state.approvalAutoRun` / `state.verifyEnabled` in sync (Education follows the same choice), and shows the Self-Verify and Auto-run chips again. A saved `run` from before the fix is reset to `ask` once (marker `autoreiv_approval_autorun_reset_470`), because the UI had hidden that value. Tooltip now reads "Off: AutoReiv asks before write, shell and code tools. On: they run without asking. Blocked tools stay blocked." and the chip reads **Auto-run ON** in amber. No data fix for sessions run since 2026-09-20. Backend unchanged. Contracts: `tests/unit/frontend/chat_runtime_toggles_470.test.js`, smoke TC-14..TC-17 ([CARD-470]).
- **CARD-470 Approve/Reject cards restored**: Jacob's live test found that parked tools never showed an approval card, so a parked turn looked like "no reply, nothing saved". The backend had parked correctly. The CARD-397 split had broken both approval surfaces:
  - `setupPendingHitl` called `pendingApprovalsUrl(sessionId)` with shifted arguments, so it asked for `?agent_id=<session id>`.
  - It read `data.pending` from an API that returns a bare array.
  - It looked for `.hitl-approve-btn` buttons the card never renders, and rendered into the message list, which is wiped on the finalize reload, instead of the pinned `#pendingHitlHost` tray.
  - The inline card in the reply bubble had no button listeners and showed `tool` with no arguments.

  The fix restores the pre-split behaviour in `chat/hitl.js`:
  - `setupPendingHitl` queries by the open session, renders into `#pendingHitlHost`, dedupes by approval id and drops resolved rows.
  - New `wireHitlCardButtons()` posts the decision and resumes the turn when the backend did not.
  - New `renderInlineHitlCard()` builds the inline card and leaves `goal_plan_review` to the plan card.
  - `chat.js` refreshes the tray on park SSE events.
  - `setupComposerSizing` gained `pressRegions`, and chat passes `#pendingHitlHost`, so the first tap on Approve/Reject after typing is no longer lost when the composer shrinks on blur.

  `chat.js` is now 1,032 lines. Contracts: `tests/unit/frontend/chat_hitl_approval_card_470.test.js`, the new press-region case in `chat_composer_grow_465.test.js`, smoke TC-18 ([CARD-470]).

### Added

- **CARD-443 Platform pack → AppData promotion**: On startup and `POST /api/platform-packs/sync`, non-`user_modified` platform packs refresh AppData `pack.json` + `skills/*/SKILL.md` from `platform-packs/<id>/` and resync pack-owned SQLite fields (skills/tools; `system_prompt` only when still at shipped-prompt baseline). Preserves `max_turns`/`model`. `user_modified` packs return deterministic `skipped_user_modified` with resolution (`POST /api/agents/<id>/accept-platform-seed`). Status: `GET /api/platform-packs/sync-status`. Module: `src/infrastructure/skills/platform_pack_promotion.py`. Contract: `tests/unit/agent_packs/test_card_443_platform_pack_appdata_sync.py` ([CARD-443]). Follow-up: [CARD-449](docs/cards/CARD-449-scalar-operator-edits-max-turns-must-not-lock-platform-pack-promotion.md).


- **CARD-448 Education Studio flashcard / quiz / test players**: `#educationPlayersConsole` hosts interactive flashcard (front-then-reveal), quiz, and multi-item test players. Grades persist via `POST /api/education/quiz/grade` (with `quiz/next` / `mastery/due`); failures never fake pass. Uses Studio-active topic/course from CARD-447. Operator console kept; Tutor remains coach; Studio not retired. Contracts: `tests/unit/education/test_card448_education_studio_players.py`, `tests/unit/frontend/card_448_education_studio_players.test.js` ([CARD-448], [ADR-0059](docs/adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).

- **CARD-447 Education Studio operator strip + Tutor topic/course context**: Education Studio `#educationOperatorConsole` hosts Due / Progress / Wiki curate (same Learning OS APIs as CARD-439/440/441). Active topic/course persists via `PUT /api/education/selected` (`selected_education_context` settings key) + localStorage `autoreiv.educationStudio.activeContext.v1`. Tutor Study entry injects Studio-active context through `POST /api/education/tutor/context` (Projects selected parallel). Chat education-mode strip thins to a context indicator + Studio console deep-link. Players remain CARD-448. Contract: `tests/unit/education/test_card447_education_studio_selected_context.py`, `tests/unit/frontend/card_447_education_studio_operator.test.js` ([CARD-447], [ADR-0059](docs/adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).


### Changed

- **ADR-0059 amendment / Education Studio operator + players**: Education Studio is the education **operator surface + players** (topic/course selection saved in Studio; Due reviews; Progress; Wiki curate; flashcard/quiz/test players). Tutor stays coach with Studio topic/course context (Projects Studio ↔ Developer parallel). Chat education-mode strip is **not** the permanent operator UI — relocate under [CARD-447](docs/cards/CARD-447-education-studio-operator-strip-and-tutor-context.md). Parent [CARD-446](docs/cards/CARD-446-education-studio-flashcard-quiz-test-players.md); players [CARD-448](docs/cards/CARD-448-education-studio-flashcard-quiz-test-players.md). CARD-437..441 Done APIs stand; UI may relocate. [CARD-435](docs/cards/CARD-435-education-tutor-first-direction.md) + inventory pointers updated ([ADR-0059](docs/adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).
- **ADR-0059 / Education Studio product lock**: Education Studio is **not** retired. It is repurposed as the flashcard / quiz / test **player**. [CARD-442](docs/cards/CARD-442-retire-education-studio-landing.md) Superseded; [CARD-446](docs/cards/CARD-446-education-studio-flashcard-quiz-test-players.md) Ready (build last after 438 Done + 439/440/441 proof). [CARD-435](docs/cards/CARD-435-education-tutor-first-direction.md) amended. Tutor Learning OS skills remain ([ADR-0059](docs/adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).
- **CARD-438 Done**: Chat quiz/flashcard durable grading merged to qa; Studio kept; player card CARD-446 queued.

### Fixed

- **CARD-444 Flashcard-turn skill efficiency**: Tutor `flashcard-turn` runbook prefers `education_flashcard_next` / `education_flashcard_grade` (mastery due/upsert for empty-due seed only). Forbids mid-turn `wiki_note_create` / wiki curation / multi-note search loops; front-only then grade; honest failures. Pack skill tools drop `wiki_note_search` / `wiki_note_list`. Deterministic proof under default `max_turns` (10) without budget terminator. Prefer platform pack (AppData sync = CARD-443). Contract: `tests/unit/education/test_card444_flashcard_turn_skill_efficiency.py` ([CARD-444]).
lashcard-turn\ runbook prefers \ducation_flashcard_next\ / \ducation_flashcard_grade\ (mastery due/upsert for empty-due seed only). Forbids mid-turn \wiki_note_create\ / wiki curation / multi-note search loops; front-only then grade; honest failures. Pack skill tools drop \wiki_note_search\ / \wiki_note_list\. Deterministic proof under default \max_turns\ (10) without budget terminator. Prefer platform pack (AppData sync = CARD-443). Contract: \	ests/unit/education/test_card444_flashcard_turn_skill_efficiency.py\ ([CARD-444]).


- **CARD-438 hotfix datetime JSON on Tutor chat**: Live education-mode Tutor turns died with `Object of type datetime is not JSON serializable` when `get_session_info` returned raw `created_at`/`updated_at`. Shared `to_jsonable` now sanitizes every tool result at the kernel scrub boundary; `get_session_info` emits ISO strings; education tools reuse the shared helper. Contract: `tests/unit/kernel/test_json_safe_datetime.py` ([CARD-438]).

### Added

- **CARD-441 Progress you can trust (non-Studio)**: Tutor education-mode strip gains **Progress** panel (`#chatEducationModeProgressBtn`) sourced from `GET /api/education/progress` + Learning OS course/mastery/due ledgers. Tutor skill `progress-summary` gains `education_progress_summary|courses|mastery` tools. Failures return `mastery_pct=null` (never fake 100%). Education Studio course chrome stays (ADR-0059 / CARD-446 player). Contract: `tests/unit/education/test_card441_progress_you_can_trust_non_studio_surface.py`, `tests/unit/frontend/card_441_progress.test.js` ([CARD-441]).

- **CARD-440 Wiki curation from links / curriculum**: Tutor Learning OS skill `education-wiki-curation` gains durable path `POST /api/education/wiki/curate` + `education_wiki_curate_from_link|curriculum` / `education_wiki_template_catalog` tools (`src/application/education/wiki_curation.py`, `education_tools.py`). Notes stage via `wiki_note_create` into `00_Inbox/`; catalogued `education-*` templates when claimed; raw sources MAY omit education tags; fetch/write failures never claim library updated. Study education-mode strip adds **Wiki curate** panel. Education Studio wiki grounding stays. Contract: `tests/unit/education/test_card440_wiki_curation_from_links_curriculum.py` ([CARD-440]).

- **CARD-439 Due reviews in Tutor education mode**: Tutor Learning OS skill `due-review` gains `education_due_review_list|complete` + `education_retention_run` (`src/application/skills/education_tools.py`) sourced from `GET /api/education/mastery/due` and durable quiz-grade / retention APIs. Study education-mode strip adds **Due reviews** panel (`#chatEducationModeDueBtn`). Empty queue is honest; failures do not fake durable success. Education Studio due chrome stays. Contract: `tests/unit/education/test_card439_due_reviews_in_tutor_education_mode.py` ([CARD-439]).

- **CARD-438 Chat quiz / flashcard turns + durable grading**: Tutor Learning OS skills `quiz-turn` / `flashcard-turn` gain agent-callable tools `education_quiz_extract|next|grade`, `education_flashcard_next|grade`, `education_mastery_due|upsert` (`src/application/skills/education_tools.py`) that write binary grades into `education_mastery` (same path as `POST /api/education/quiz/grade`). Failures return `success=false` (no bubble theatre). Education Studio quiz UI stays. Contract: `tests/unit/education/test_card438_chat_quiz_flashcard_durable_grading.py` ([CARD-438]).
- **CARD-437 Study entry = Tutor education mode**: Sidebar `#btn-study-entry` and Chat header `#chatStudyEntryBtn` open Chat with Tutor selected, Learning OS skill `start-resume-topic`, and durable course bind via `POST /api/education/course/start` + `POST /api/education/tutor/context`. Education-mode rails strip `#chatEducationModeStrip` shows topic/course/skill (not freeform untitled chat). Education Studio (`#tab-education` / `#view-education`) stays. Module: `src/web/static/modules/studios/study_entry.js`. Contract: `tests/unit/frontend/card_437_study_entry.test.js` ([CARD-437]).
- **CARD-436 live Tutor seed honesty**: hash-gated platform seed apply now refreshes the AppData `packs/tutor/pack.json` skill projection (without wiping local extras) so Agent Studio `pack_skills` tracks SQLite `allowed_skill`; `serve --reload` also watches `platform-packs/` so Learning OS skill seed edits re-bootstrap without a manual kill.
- **CARD-436 Tutor Learning OS rails**: Inventory maps Education Studio chrome to Learning OS modules/APIs/Wiki templates/Tutor skill ids (`docs/education/tutor-learning-os-inventory.md`). Tutor pack gains named skills `start-resume-topic`, `quiz-turn`, `flashcard-turn`, `due-review`, `education-wiki-curation`, `progress-summary` (plus existing `socratic-tutoring`) under `platform-packs/tutor/skills/*/SKILL.md` with hard rails against open vibes. Education Studio chrome stays. Contract: `tests/unit/agent_packs/test_card_436_tutor_learning_os_skills.py` ([CARD-436]).

## [0.42.0] - 2026-09-23

### Added

- **CARD-429 Developer capability authoring**: The developer pack allowlist includes `capability-authoring`, `proposals`, and `build-agent-pack`. Chat with Developer can propose and commit skills and tools and scaffold an agent pack (`propose_skill`, `propose_tool`, `commit_skill_pack`, `list_available_skills_and_tools`, `scaffold_agent_pack`). `save_agent_specification` is not on the developer allowlist. A `user_modified` developer receives the new skill ids through the additive grant without a prompt rewrite. Runbook: `platform-packs/developer/skills/capability-authoring/SKILL.md` ([CARD-429], [ADR-0058](docs/adr/0058-retire-agent-builder-into-developer.md)).
- **CARD-428 Observability Journey Canvas**: Visual end-to-end operational execution trace across 4 architectural swimlanes (UI/Browser, API Gateway, Orchestrator ReAct Loop, Storage & Policy). Built directly into Observability Studio (`observe`) with a timeline scrubber, Play/Pause autoplay controls, synchronized Code Inspector with active line highlighting and IDE links, runtime state transition badges, and formatted Payload Inspector (`src/application/observability/journey_canvas.py`, `src/web/routers/observability.py`, `src/web/static/modules/observability/journey_canvas.js`, `src/web/templates/index.html` [CARD-428]).

### Changed

- **CARD-433 user-modified developer prompt**: When the developer profile is `user_modified` and the system prompt does not mention `scaffold_agent_pack`, pack sync appends one paragraph about propose, commit, and scaffold. The existing prompt text stays. The append is recorded once in `platform_user_modified_prompt_appends`, so a later deletion stays deleted. A developer that is not `user_modified` keeps the seed prompt. `save_agent_specification` stays off the allowlist (`src/infrastructure/skills/platform_packs.py` [CARD-433], [ADR-0056](docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md)).
- **CARD-432 historical agent-builder rows**: On boot, sessions, messages, jobs, and phases that still name `agent-builder` point at `developer`. Those rows are not deleted. Message text stays. A second boot does not rewrite rows that already say `developer`. No `agent-builder` profile is created (`src/infrastructure/memory/repositories/settings.py`, `src/infrastructure/agents/registry.py` [CARD-432], [ADR-0058](docs/adr/0058-retire-agent-builder-into-developer.md)).
- **CARD-430 Agent Studio one skill list**: Assigned Skills is one list. Each row keeps the allowlist toggle and Open in Skill Studio, and shows a home label (Platform, Operator, or Pack). Archived rows stay in that list and are marked Archived. The three boxes `#forgePlatformBox`, `#forgeOperatorBox`, and `#forgePackBox` are gone. Skill files are not moved between `$DATA_DIR/skills/` and `packs/<id>/skills/`. OS baseline chips stay (`src/web/static/modules/studios/forge/runbook.js`, `src/web/templates/index.html` [CARD-430]).
- **CARD-429 classification labels**: Skill Studio no longer shows the Advanced tier dropdown. Save still writes `tier: pack` and does not use tier to allow or deny a skill. Factory capabilities label shipped callables `Platform` in one group. Agent Studio always-on chips list all seven `REQUIRED_PLATFORM_TOOLS` (`recall_agent_memory`, `memorize_fact` included). The caption says Direct mounts none. `platform-packs/README.md` lists `autoreiv`, `direct`, `developer`, and `tutor` ([CARD-429]).
- **CARD-429 routines**: Paused routines `skill-eval-sleep` and `skill-curator` target `developer`. The plan engine no longer has an agent-builder-only prompt ([CARD-429]).

### Removed

- **CARD-431 `save_agent_specification`**: The tool is not registered and does not appear in the Tools Studio catalog (`GET /api/agent_training_factory/capabilities`). It is gone from the tool-policy `REQUIRE_CONFIRM` default and the HITL high-risk name list. The handler method is gone. `scaffold_agent_pack` stays registered, and a Developer turn that asks to scaffold an agent pack can still call it. `propose_skill`, `propose_tool`, and `propose_agent_specification` stay. `agent-builder` stays unregistered (`src/application/skills/agent_builder_tools.py`, `src/application/safety/tool_policy_gate.py`, `src/application/kernel/hitl_engine.py` [CARD-431], [ADR-0058](docs/adr/0058-retire-agent-builder-into-developer.md)).
- **CARD-429 agent-builder**: The hidden builtin profile is not registered. `get_agent("agent-builder")` is None. Boot deletes a leftover `custom_agents` / `agent_overrides` row for that id and does not recreate it. Historical sessions stay. Creating an agent with that id is rejected ([CARD-429], [ADR-0058](docs/adr/0058-retire-agent-builder-into-developer.md)).

### Fixed

- **CARD-428 pack runbooks in list_user_skill_packs**: `list_user_skill_packs` includes an allowlisted skill whose body lives at `packs/<agent>/skills/<id>/SKILL.md` when that folder is absent from `$DATA_DIR/skills/`. The row is the id, name, and description only. The call does not copy the runbook into `$DATA_DIR/skills/` and does not list an id that is not on the agent's allowlist. A developer chat turn that names the tool can call it (`src/application/skills/user_catalog.py`, `src/application/agent_packs/schema.py`, `src/application/kernel/agent_kernel.py` [CARD-428]).

- **CARD-427 developer chat pack skill open**: Developer chat `skill_view` opens an allowlisted pack runbook from `packs/<agent>/skills/<id>/SKILL.md` when `$DATA_DIR/skills/<id>/` is absent. The chat skill index lists that runbook's name and blurb. For `native-tool-engineering`, the tool result includes the CARD-426 legacy-loader warning. The open does not copy the file into `$DATA_DIR/skills/` and does not rewrite the developer prompt or other skill bodies (`src/application/skills/user_catalog.py`, `src/application/kernel/agent_kernel.py`, `src/application/agent_packs/schema.py` [CARD-427]).

## [0.41.0] - 2026-09-23

### Added

- **CARD-423 custom tool packaging**: Custom tools can be native or MCP-backed. Native tools register through `register_native_tool` or `POST /api/tools/native`, persist in the `native_custom_tools` setting, and run in the existing subprocess sandbox after ToolPolicyGate. They do not attach an MCP server. HITL defaults on; high risk cannot turn it off. MCP tools still attach through `/api/settings/mcp` or `/api/agents/{id}/mcp` and show in Tools Studio under that server name. Catalog badges read Platform, Native custom, or MCP · server. A folder path stays chat context (`plan_native_folder`); Tools Studio has no folder picker. The CARD-422 packaging dropdown stays a note. Developer runbooks: `platform-packs/developer/skills/native-tool-engineering/SKILL.md` and a dual-lane section in `mcp-engineering` (`src/application/tools/native_packaging.py`, `src/web/routers/native_tools.py`, `src/web/static/modules/studios/tools_studio_catalog.js` [CARD-423]).

- **CARD-422 Tools Studio tool intent**: Tools Studio has a create / modify / delete intent form (behavior, optional language and runtime hints, optional plain-text path, optional packaging note). There is no code editor. **Talk to developer** opens a new `developer` chat whose first message is that form. **Submit to developer** starts a standing job and runs one developer turn on that chat, or returns HTTP 503 and leaves the job failed or cancelled when the developer cannot run. A queued job is not reported as success. Packaging preference is stored on the packet only (`src/application/tools/developer_mediation.py`, `src/web/routers/tools_authoring.py`, `src/web/static/modules/studios/tools_studio.js`, `src/web/static/modules/studios/tools_studio_authoring.js`, `src/web/templates/index.html` [CARD-422]).

- **CARD-421 Tools Studio**: Agent Desktop dock window for the live tool catalog and MCP attach. Platform tools stay in their own groups. MCP tools group under the server that lists them. Search and source/status filters narrow the catalog. Platform attach uses `/api/settings/mcp*`. Agent attach uses `/api/agents/{id}/mcp*` with an agent picker. The catalog does not write `skill_tool_bindings` (`src/web/static/modules/studios/tools_studio.js`, `src/web/static/modules/studios/tools_studio_catalog.js`, `src/web/templates/index.html` [CARD-421]).

- **CARD-420 authoring module**: A versioned skill packet (`skill_studio_authoring_packet` v1) and `/api/skill_studio/authoring/*` can create or resume a queued standing job for `developer`, store proposals, and record accept or reject without writing the skill store. Skill Studio does not call this path. Agent Studio skill pills are unchanged (`src/application/skills/developer_authoring.py`, `src/web/routers/skill_authoring.py`, `src/web/static/modules/studios/skill_authoring.js` [CARD-420]).
- **CARD-420 Skill Studio chrome**: **Generate / Refine Runbook** is a quieter secondary control. External source context sits above the SKILL.md editor. **Delete skill** confirms, then uses the existing user-pack delete for an operator skill-store file that is not a bundled seed, and clears that skill’s pack copies and SQLite bindings. Protected seeds stay blocked (`src/application/skills/workshop.py`, `src/web/routers/skills.py`, `src/infrastructure/memory/repositories/skill_bindings.py` [CARD-420]).

- **CARD-418 Skill Studio**: Agent Desktop dock window labeled Skill Studio. It is the skill write surface: existing-skill picker, new skill, structured metadata, tool catalog, and save. Save writes the skill store and SQLite `skill_tool_bindings` the same way as CARD-411. A save with no agent id does not pin a pack or write tool rows into `pack.json` (`src/web/static/modules/studios/skill_studio.js`, `src/web/templates/index.html`, `src/web/static/modules/ui/agent-desktop.js` [CARD-418]).

### Changed

- **CARD-425 legacy pack tools**: `packs/<id>/tools/*.py` stays an in-process loader and is labeled **Legacy pack tool** (`origin=legacy_pack_tool`). It is not the CARD-423 native custom lane: it does not write `native_custom_tools`, does not use the sandbox worker, and is not catalogued as Native custom (`src/infrastructure/agents/legacy_pack_tools.py`, `src/web/static/modules/studios/tools_studio_catalog.js` [CARD-425]).

- **CARD-421 MCP attach cutover**: Settings keeps MCP hosting and a one-line platform attach status with **Open in Tools Studio**. Agent Studio keeps the mounted-count status and **Open in Tools Studio**. The full add/test/enable/delete form is only in Tools Studio (`src/web/static/modules/studios/settings.js`, `src/web/static/modules/studios/forge/tools.js` [CARD-421]).

- **Agent Studio operator skills**: Skills saved in the skill store show up as toggle pills under **Operator skills** in Agent Studio. The catalog field is `operator_skills` on `GET /api/skills/catalog`. Turning a pill on still writes only `allowed_skill`. Platform skills and pack skills stay in their own sections (`src/application/skills/workshop.py`, `src/web/routers/agents.py`, `src/web/static/modules/studios/forge/runbook.js`, `src/web/templates/index.html` [CARD-420]).

- **CARD-420 Skill Studio surface**: Skill Studio no longer shows **Ask developer**, the job id strip, or Accept/Reject, and it does not open Observe from that path. The operator surface is **Generate / Refine Runbook**, **Save skill**, **Delete skill**, and source context above the SKILL.md editor. Visible developer mediation waits until that job actually runs the developer (`src/web/static/modules/studios/skill_studio.js`, `src/web/templates/index.html` [CARD-420]).

- **CARD-419 Agent Studio skill toggle pills**: Agent Studio turns skills on and off with toggle pills. On adds the skill id to the agent's durable `allowed_skill` list; off removes it. Save still writes that list through the existing agent profile API. Clicking a pill does not open Skill Studio. Each skill row has **Open in Skill Studio**. Factory's allowed-skills strip is display-only and links to Skill Studio (`src/web/static/modules/studios/forge/skill_pills.js`, `src/web/static/modules/studios/forge/runbook.js`, `src/web/static/modules/studios/forge.js`, `src/web/static/modules/studios/factory/skill_scope.js`, `src/web/templates/index.html` [CARD-419]).

- **CARD-419 Agent Studio Inspect removed**: Agent Studio no longer has an Inspect button or an inline runbook viewer (`#studioRunbookEditor`). Viewing and editing a skill stays in Skill Studio (`src/web/static/modules/studios/forge/runbook.js`, `src/web/templates/index.html` [CARD-419]).

- **CARD-418 Factory cutover (thin shell)**: Factory keeps the agent brief and the display-only assigned-skills list, and links to Skill Studio. Forge **Open in Factory Workshop** and **Author skill in Factory** now open Skill Studio and load the selected skill by id (`src/web/static/modules/studios/factory.js`, `src/web/static/modules/studios/forge/runbook.js`, `src/application/skills/workshop.py`, `src/web/routers/agent_training_factory.py` [CARD-418]).

### Fixed

- **CARD-426 user-modified native-tool-engineering warning**: When the developer profile is `user_modified` and the live `packs/developer/skills/native-tool-engineering/SKILL.md` is missing the legacy-loader warning marker `<!-- autoreiv:native-tool-legacy-loader -->` and the heading `## Not the legacy pack loader`, pack sync appends only that seed warning section. Operator text in the file, the developer prompt, and other skill bodies stay. If the marker or the heading is already present, the file is left alone. Tools Studio **Legacy pack tool** labels do not read this file (`src/infrastructure/skills/platform_packs.py` [CARD-426]).

- **CARD-425 user-modified developer allowlist**: When the developer profile is `user_modified` and the seed includes `native-tool-engineering`, pack sync appends that skill id and `register_native_tool` / `plan_native_folder` to the allowlist. The existing prompt, other allowlist entries, and MCP servers stay. The grant is recorded once in `platform_user_modified_skill_grants`, so a later removal stays removed (`src/infrastructure/skills/platform_packs.py` [CARD-425]).

- **CARD-424 MCP disable unmounts**: Saving a platform or agent MCP server with `enabled: false` unmounts that server. Enable mounts it again. The save `mounted` flag and the list `is_mounted` / tool list match the live manager. Tools Studio shows **Disabled** after a successful disable, and **Disabled (still mounted, N tools)** only when unmount fails, with that failure shown to the operator (`src/web/mcp_mount_reconcile.py`, `src/web/routers/settings.py`, `src/web/routers/agents.py`, `src/web/static/modules/studios/tools_studio.js`, `src/web/static/modules/studios/tools_studio_catalog.js` [CARD-424]).

## [0.40.0] - 2026-09-22

### Added

- **CARD-411 Forge / Factory skill split**: Agent Studio inspects a skill runbook (name, description, tier, safety, required tools) and opens **Factory Workshop** for edits. Factory is the only writer: structured metadata and the tool picker update `requires_tools` with catalog tool ids, and save writes the skill body to the skill store plus tool bindings in operational SQLite (`skill_tool_bindings`). `pack.json` is not a live binding source. Forge no longer saves, archives, deletes, or creates runbooks (`src/application/skills/runbook_frontmatter.py`, `src/application/skills/workshop.py`, `src/infrastructure/memory/repositories/skill_bindings.py`, `src/web/static/modules/studios/forge/runbook.js`, `src/web/static/modules/studios/factory.js` [CARD-411]).

- **CARD-411 Factory layout UX**: Column 1 keeps Assigned Skills under Role Persona (agentΓåöskill scope only). Column 2 is the skill workshop with an Existing skill picker + **+ New Skill**. Column 3 stays tools/grounding. Tier sits behind a quiet advanced disclosure (legacy taxonomy). Safety checkboxes carry short operator help text (`src/web/templates/index.html`, `src/web/static/modules/studios/factory.js`, `src/web/static/modules/studios/factory/skill_scope.js` [CARD-411]).

- **CARD-411 Factory skill open**: The Existing skill list only includes runbooks the loader can open (skill store, agent pack `skills/`, platform-packs, bundled seeds). `GET /api/agent_training_factory/skills/{id}` keeps dotted and nested ids, so selecting a listed skill fills the workshop instead of `Skill not found` (`src/application/skills/workshop.py`, `src/web/routers/agent_training_factory.py`, `src/web/static/modules/studios/factory/skill_scope.js` [CARD-411]).

- **CARD-408 View Job shortcut**: Chat multi-phase job strip shows **View Job** beside Copy when a `job_id` is bound. Click opens or focuses Observe Studio, fills the standing-journey search, and loads the phase timeline. Unknown job ids show an error in the Observe viewer. Education "Open in Observe" uses the same path (`src/web/templates/index.html`, `src/web/static/modules/studios/chat/chrome.js`, `src/web/static/modules/studios/chat.js`, `src/web/static/modules/studios/observability.js`, `src/web/static/modules/ui/agent-desktop.js` [CARD-408]).

### Fixed

- **CARD-410 Browser refresh empty agent pickers**: Restored Agent Desktop studio windows fill Chat, Agent Studio, Factory, Routines, and Observe agent dropdowns after F5 without closing and reopening. `/api/agents` publishes `agents:loaded` (late subscribers replay the roster). The selected agent is kept (`autoreiv_active_agent_id`, plus forge/factory/routines/observe keys). Agent Studio is loaded when its window was restored before the dynamic import finished (`src/web/static/modules/studios/agent_picker.js`, `src/web/static/modules/ui/agent_desktop/agent_hydration.js`, `app.js`, `forge.js`, `chat.js`, `factory.js`, `routines.js`, `observability.js` [CARD-410]).

- **CARD-415 Chat Studio transcript durability (live == refresh)**: Persist assistant `reasoning` on `ChatMessage` ΓåÆ SQLite `messages.reasoning` ΓåÆ `GET /api/sessions/{id}/messages`; hydrate Thinking Process drawer; post-turn `loadMessages` finalizes stream bubbles onto the same action-row path as refresh (Copy / Save to Wiki / Teach Agent / Workbench); wire `exportSessionToWiki` (full thread ΓåÆ Wiki Inbox) and pass `exportMessageToWikiFn` into hydrate render; align tool activity via durable `role=tool` re-fetch after turn (`src/domain/gateway/models.py`, `src/infrastructure/memory/schema.py`, `src/infrastructure/memory/connection.py`, `src/infrastructure/memory/repositories/sessions.py`, `src/application/kernel/agent_kernel.py`, `src/web/routers/chat.py`, `src/web/static/modules/studios/chat.js`, `chat/render.js`, `chat/chrome.js`, `wiki/export.js`, `src/web/static/app.js` [CARD-415]).

- **CARD-416 Wiki 01_Notes empty scrub**: Idempotent `WikiStore.scrub_empty_seed_taxonomy()` removes leftover empty pre-CARD-406 seed taxonomy dirs under `01_Notes` (`computer_science/artificial_intelligence`, `general/notes`, `operations/diagnostics`, `operations/worklog`, `systems_engineering/observability` + empty parents) from `scaffold` / Settings confirm. Never deletes non-empty note paths; does not reintroduce domain mkdir lists. Vanilla seeding asserts `01_Notes` has zero children; regression plants five empty dirs then verifies scrub (`src/domain/wiki/store.py`, `tests/unit/wiki/test_vanilla_wiki_seeding.py` [CARD-416]).

- **CARD-414 / ADR-0056 Hybrid C+ cutover (vertical slice)**: SQLite sole writer for agent profiles + tool/skill bindings with `user_modified` + seed hash/version provenance; platform pack sync is hash-gated and never prunes operator skill dirs or re-adds removed tools when `user_modified`; `pack.json` treated as export projection. Wiki: local explicit path (no suggestion) via Settings + `/api/settings/wiki-path`; Docker/daemon hard-fail start when `AUTOREIV_WIKI_PATH` unset/unreadable (`AUTOREIV_DEPLOY_MODE=docker|daemon`). Backup writes `backup-manifest.json` (DBs, wiki URI, digests, packs, provenance). Compose requires wiki env+volume. Operator contracts OC-S1..S6 under `tests/integration/operator_contracts/`.

- ADR-0056 **Accepted** (Hybrid C+ durable runtime registry) and CARD-414 Ready implementation scaffold (`docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md`, `docs/cards/CARD-414-implement-hybrid-c-plus-durable-runtime-registry-and-deployment-mode-wiki.md`, `docs/cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md` [CARD-413]/CARD-414]): Docker/daemon hard-fail if wiki missing; local explicit wiki path with no suggestion; CARD-411 remains deferred.

- ADR-0056 Proposed: Docker/daemon hard-fail start when wiki path/volume missing (docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md [CARD-413]).

- ADR-0056 Proposed refinement: deployment-mode wiki config (`docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md` [CARD-413]): Windows/Linux local require explicit wiki path with no suggestion; Docker Compose/daemon require wiki via env + volume mount; no silent fallback vault.

- ADR-0056 Proposed: Hybrid C+ durable runtime registry (`docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md`, `docs/cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md` [CARD-413]): SQLite-canonical control plane; filesystem wiki + pack interchange; versioned reconcile with `user_modified`; wiki first-run picker with no suggested path; CARD-411 deferred until Accept.

- CARD-413 ownership audit and recommended Hybrid C+ architecture (docs/design/CARD-413-ownership-audit-and-recommended-architecture.md, docs/cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md [CARD-413]): deep current-state ownership map; intent synthesis; one recommended architecture (pending Jacob); CARD-411 defer until ADR; no product code.

- CARD-412 Phase 1+2 build (	ests/integration/operator_contracts/, src/web/static/modules/studios/settings.js, src/application/settings/settings_service.py, src/web/routers/observability.py, src/domain/wiki/frontmatter.py [CARD-412]):
  - **OC-1**: Save Provider also persists default_context_window via /api/settings/matrix; settings dump uses JSON mode.
  - **OC-2**: Observe session-metrics export fail-closed on empty markdown/read-back; wiki frontmatter uses model_dump for Pydantic metas.
  - **OC-3**: Wiki note create single-lever operator contract.
  - **Prune**: Removed 8 brittle frontend vitest whitebox files (Bucket C theater).

- Operator-contract testing strategy and suite hygiene footing (docs/adr/0055-operator-contract-testing-and-suite-hygiene.md, .agents/rules/operator-contract-testing.md, .agents/rules/tdd-invariants.md, .agents/rules/definition-of-done.md, docs/cards/CARD-412-test-suite-hygiene-obsolete-test-pruning-and-consolidation-audit.md, AGENTS.md [CARD-412]):
  - **ADR-0055 Accepted**: Prefer operator contracts + Bucket A invariants + thin honesty/smoke over broad unit-TDD theater and Playwright volume.
  - **Always-on rule**: .agents/rules/operator-contract-testing.md defines OC-1 (context-window persist), OC-2 (observe metrics non-empty inbox), OC-3 (wiki note create single-lever).
  - **CARD-412 Ready**: Phase 0 governance landed; Phase 1 prune + Phase 2 contracts await **build**.
## [0.39.0] - 2026-09-21

- Wiki Architecture Overhaul, Single-Lever Wiki Tools, wiki_tasks Runbook, Granular Skills Split, RAG Grounding Poisoning Fix, and Goal Phase Dedup (`platform-packs/autoreiv/pack.json`, `platform-packs/autoreiv/skills/wiki_tasks/SKILL.md`, `platform-packs/autoreiv/skills/wiki-knowledge/SKILL.md`, `platform-packs/autoreiv/skills/wiki-inbox/SKILL.md`, `platform-packs/autoreiv/skills/wiki-curation/SKILL.md`, `src/application/skills/wiki_tools.py`, `src/application/skills/manifest.py`, `src/application/agent_packs/schema.py`, `src/application/orchestration/wiki_thin_grounding.py`, `src/domain/wiki/store.py`, `src/domain/wiki/frontmatter.py`, `src/application/routines/wiki_curator.py`, `src/infrastructure/memory/repositories/capability_catalog.py`, `src/application/capabilities/seeder.py`, `src/application/orchestration/phase_llm_resilience.py`, `src/web/app.py`, `src/web/routers/chat.py`, `tests/unit/skills/test_wiki_tasks.py`, `tests/unit/wiki/test_wiki_archive.py`, `tests/unit/orchestration/test_wiki_thin_grounding_creation_intent.py`, `tests/unit/orchestration/test_chat_multiphase_deliverable_dedup.py`, `tests/unit/capabilities/test_capability_seeder_407.py` [CARD-409]):
  - **Single Lever Note Creation**: Enforced exactly one note-creation tool across the platform (`wiki_note_create`). Completely pruned the 5 bespoke weekly tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`) from the codebase, manifests, and test suites.
  - **Capability Catalog Stopword Immunity & Underscore Tokenization Fix**: Resolved capability scoring inversion in `CapabilityCatalogResolver` where verbose tools accumulated points on English stopwords (`the`, `and`, `to`, `in`, `is`, `when`). Implemented `ENGLISH_STOPWORDS` filtering, compound match bonuses, and underscore-splitting tokenization (`_TOKEN_RE`) so snake_case tool names match prompt intent words (`wiki_note_create` matches `wiki`, `inspect_system_health` matches `health`). Enriched canonical synonyms (`save`, `write`, `check`, `app`, `report`) in `seeder.py` so standard human phrasing accurately surfaces required tools in the top matched capabilities.
  - **Chat Studio + Options Button Toggle Fix**: Fixed argument mismatch in `toggleChatOptionsDrawer` in `src/web/static/modules/studios/chat/chrome.js`. Supported both `(boolean, options)` and `({ open: boolean, ... })` call signatures, correctly passed `chatOptionsToggleBtn`, and wired `loadChatSessionContextFn`, resolving the non-responsive `+ Options` drawer click behavior.
  - **Capability Catalog Pruning & Zombie Elimination**: Added `delete_entry()` to `CapabilityCatalogRepository` and updated `seed_builtin_capabilities()` to automatically reconcile and prune obsolete `source="builtin"` capabilities and retired tool names (`RETIRED_TOOL_NAMES`) from `capability_index`. Eliminates dead weekly tool injection into planning prompts.
  - **Dotenv Loading on FastAPI App & Phase Timeout Resolution**: Wired `load_repo_dotenv()` into `create_app()` in `src/web/app.py` and `resolve_standing_phase_llm_timeout()` in `phase_llm_resilience.py`, ensuring configured `.env` timeouts (e.g. `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800`) are respected under Uvicorn servers rather than falling back to the 300s kill.
  - **SOP Runbook-Driven Task Management (`wiki_tasks`)**: Replaced hardcoded procedural weekly tools with a declarative SOP runbook (`wiki_tasks`) that drives weekly work journaling, Markdown checklists (`- [ ]`), and task rollover using canonical wiki tools (`wiki_note_read`, `wiki_note_create`, `wiki_note_update`, `wiki_template_read`).
  - **Granular Skills Split**: Decomposed the monolithic `wiki` and `tasks` skills into 4 cohesive, verb-noun scoped skills: `wiki_tasks` (task tracking), `wiki-knowledge` (vault search and read), `wiki-inbox` (one-door note creation drop-zone), and `wiki-curation` (deep grooming, template management, merging, and archiving).
  - **Single Primary Companion (No Separate Wiki Agent)**: Retained AutoReiv as the single primary companion holding wiki and task capabilities, avoiding context fragmentation and agent routing confusion.
  - **RAG Grounding Poisoning Fix**: Enhanced `WikiThinGrounding` with `is_wiki_create_ask()` so creation/staging prompts (e.g., *"save that note to the wiki"*) bypass restrictive path constraints and never falsely fail-closed with ungrounded path claims.
  - **Honesty Gate Safety Expanded**: Broadened `_PROVENANCE_TOOLS` in `wiki_thin_grounding.py` to recognize all legitimate note/template creation, update, and archival tools as provenanced paths.
  - **Multi-Phase Deliverable Dedup**: Resolved the chat router deliverable stutter in `src/web/routers/chat.py`, preventing intermediate phase deliverables from being joined with repetitive `---` dividers.
  - **Archive Lever & Version Preservation**: Implemented `archive_note()` in `WikiStore` and exposed `wiki_note_archive`. Automatically snapshots prior note versions to `03_Archive/` before major updates or deduplication merges in `curate_inbox`.
  - **Single Lever Naming & Pruning**: Excised shadow tool aliases `list_wiki_templates` and `get_wiki_template`, standardizing strictly on `wiki_template_list` and `wiki_template_read`.

- Capability Catalog Startup Seeding, Tool Policy Gate Empty Fallback, and AutoReiv Pack Alignment (`src/application/safety/tool_policy_gate.py`, `src/application/capabilities/seeder.py`, `src/application/agent_packs/schema.py`, `src/web/app.py`, `platform-packs/autoreiv/pack.json`, `platform-packs/autoreiv/skills/platform-health/SKILL.md`, `tests/unit/safety/test_tool_policy_gate.py`, `tests/unit/capabilities/test_capability_seeder_407.py`, `tests/unit/agents/test_autoreiv_pack_alignment_407.py`, `tests/unit/agents/test_builtin_profiles.py`, `tests/unit/agent_packs/test_card_126_platform_packs.py`, `tests/unit/agent_packs/test_card_127_platform_skills_layout.py`, `tests/unit/agent_packs/test_card_181_developer_agent.py`, `tests/unit/agent_packs/test_fleet_packs.py`, `tests/unit/kernel/test_card_121_tools.py`, `tests/unit/skills/test_sysadmin_descriptions.py`, `tests/unit/skills/test_sysadmin_network_info.py`, `tests/unit/skills/test_system_agent_tools.py`, `tests/unit/skills/test_skill_linter_consolidation.py`, `tests/unit/routines/test_routine_executor.py`, `tests/unit/observability/test_card354_developer_simulations.py`, `tests/unit/web/test_wiki_vault_seeding_and_resilience.py`, `docs/cards/CARD-407-fix-capability-catalog-seeding-tool-policy-gate-empty-fallback-and-autoreiv-pack-health-tools.md` [CARD-407]):
  - **Tool Policy Gate Non-Blocking Fallback**: Fixed `ToolPolicyGate._capability_tool_names()` in `tool_policy_gate.py` so that empty matched capability sequences or sequences containing only non-tool capabilities return `None` rather than `set()`. Eliminates the fail-closed paralysis bug where jobs with unseeded or non-tool matched subsets blocked 100% of all tool executions with `"out of matched capability subset ([])"`.
  - **Durable Capability Catalog Startup Seeding**: Implemented `seed_builtin_capabilities()` in `src/application/capabilities/seeder.py`, integrated into `src/web/app.py` startup lifespan. Automatically indexes all built-in tools (`kind=CapabilityKind.TOOL`), agent profiles (`kind=CapabilityKind.AGENT`), and pack skills (`kind=CapabilityKind.SKILL`) into SQLite `capability_index` with `TrustTier.TRUSTED`, ensuring `CapabilityCatalogResolver.resolve(..., trusted_only=True)` matches indexed platform capabilities.
  - **AutoReiv Role Boundary & Shell Tool Exclusion**: Pruned `cli_exec` from `platform-health` and `pack_tool_names` in `platform-packs/autoreiv/pack.json`, `src/application/agent_packs/schema.py`, and `SKILL.md`. Synchronized updated definition to user data `%LOCALAPPDATA%\AutoReiv\packs\autoreiv\`. AutoReiv relies strictly on application/database telemetry (`inspect_system_health`, `get_tool_health_matrix`, `get_recent_errors`, `get_system_logs`, `system_info`) and delegates host CLI/terminal execution exclusively to `developer` via `handoff_to_agent`.
  - **Single Lever SDLC Engineering Cleanup**: Excised duplicate `sdlc-engineering` skill and project manipulation tools (`read_project_file`, `write_project_file`, `list_project_dir`, `execute_code`) from `autoreiv/pack.json` and deleted `platform-packs/autoreiv/skills/sdlc-engineering/`. Full-lifecycle SDLC engineering is now strictly owned by the dedicated `developer` specialist pack.
  - **Max Turns Ceiling Expansion (1ΓÇô1000) & Agent Studio Persistence**: Raised `max_turns` upper bound from 50 to 1000 across `AgentProfile` (`src/domain/kernel/models.py`), `AgentProfileGuardrail` (`src/domain/agents/guardrails.py`), and Agent Studio UI inputs (`src/web/templates/index.html`). Updated `update_agent` in `src/web/routers/agents.py` to synchronize `max_turns`, `tone`, and `history_retention_days` directly to `user_data/packs/<agent_id>/pack.json`. Improved UI error formatting in `forge.js` to unpack FastAPI 422 validation detail arrays into human-readable toast messages.
  - **Defensive Wiki Tag Coercion**: Implemented `coerce_string_or_list_of_strings()` in `src/domain/wiki/frontmatter.py` and attached mode="before" field validators to `WikiInboxNoteMeta` and `WikiNoteMeta` (and list sanitization in `create_wiki_note` in `wiki_tools.py`). Automatically deserializes stringified JSON arrays (`'["tag"]'`) and comma-delimited strings into valid `list[str]`, preventing ReAct tool error loops and turn budget exhaustion.
  - **Test-Locked Delivery & Anti-Regression Invariants**: Authored unit test suites in `test_capability_seeder_407.py`, `test_autoreiv_pack_alignment_407.py`, and `test_max_turns_api_persistence_407.py`, plus tag coercion tests in `test_wiki_frontmatter.py`. All unit tests, 110 frontend test suites (642 tests), boundary check, and lint checks pass with 0 errors.

  - **Chat User Input Bubble Render Fix**: Resolved argument mismatch between `appendMessageBubbleDirect` caller in `chat.js` and `appendMessageBubble` in `render.js`. Added polymorphic resolution for `messagesContainer` as either positional argument 3 or property inside the options object, preventing premature bailouts and guaranteeing the user prompt bubble renders immediately upon submission.
  - **Vanilla Wiki Structure Restoration**: Cleaned `scaffold()` in `src/domain/wiki/store.py` to enforce the strict numbered vault structure (`00_Inbox`, `01_Notes`, `02_Resources/operating_manuals`, `02_Resources/_Templates`, `03_Archive`). Pruned legacy unnumbered folder creation (`notes/`, `01_Notes/general/notes`).
  - **Elimination of Mock Starter Notes**: Neutralized `_seed_starter_notes_if_empty()` to prevent auto-populating arbitrary domain notes into `00_Inbox` or `01_Notes` on fresh installs.
  - **Weekly Notes Tools Vault Alignment & Mock Data Pruning**: Updated `WeeklyNotesTools` to write to `01_Notes/weekly/{week}.md` and read templates from `02_Resources/_Templates/weekly_notes.md`. Removed mock company projects (*Server Currency*, *AQS Migration*, *Leaders Life*) from both default templates and vault cleanup routines.
  - **Cold-Boot Cron Routine Execution Suppression**: Fixed `ScheduleMatcher.is_routine_due()` and `ScheduleMatcher.compute_next_run()` in `matcher.py` so CRON routines (such as `weekly-note-rollover`) calculate next execution via cron ETA instead of firing immediately upon server boot when `last_run_at is None`. Updated startup seeding routines across `scheduler.py`, `app.py`, and `cli/main.py` to populate `next_run_at`.
  - **Test-Locked Delivery**: Authored frontend tests in `chat_user_input_bubble_render_406.test.js`, vanilla wiki seeding assertions in `test_vanilla_wiki_seeding.py`, and cron cold-boot tests in `test_schedule_matcher.py`. All 110 frontend test suites (642 tests), all 117 wiki/skills/routines tests, and static linting passed with 0 errors.

- Agent Cognitive Memory System Verification, Stress Audit, and Forge Brain Drawer Wiring (`src/web/routers/agents.py`, `src/web/routers/chat.py`, `src/web/static/modules/studios/forge/config.js`, `src/web/static/modules/studios/forge.js`, `src/application/memory/extractor.py`, `src/application/memory/agent_memory_tools.py`, `src/application/kernel/agent_kernel.py`, `src/application/kernel/tool_registry.py`, `src/application/safety/tool_policy_gate.py`, `src/infrastructure/agents/registry.py`, `platform-packs/developer/pack.json`, `tests/integration/test_agent_memory_universal_readiness.py`, `tests/integration/test_agent_memory_lifecycle_walkthrough.py`, `tests/unit/frontend/agent_memory_ui.test.js`, `tests/unit/skills/test_agent_memory_tools.py`, `scripts/test_live_dev_memory.py`, `scripts/test_live_tutor_memory.py` [CARD-405]):
  - **Universal Cognitive Memory Readiness Across All Agents**: Implemented universal cognitive memory authorization and awareness for all agents (`autoreiv`, `tutor`, `developer`, and dynamically created custom agents) where `memory_enabled=True`. Direct agent (`id="direct"`) remains a strict zero-tool, zero-memory pass-through.
  - **Tool Policy & Execution Authorization**: Added `recall_agent_memory` and `memorize_fact` to `_DEFAULT_SAFE` and `_effective_allowed_tools()` in `src/application/safety/tool_policy_gate.py` and authorized them in `ScopedToolRegistry.execute()` in `src/application/kernel/tool_registry.py`. Eliminates the previous authorization failure where agents other than Developer were rejected by policy gates.
  - **Cold-Start Brain Awareness & Capability Preamble**: Enhanced `AgentKernel._build_effective_system_message` in `src/application/kernel/agent_kernel.py` to always inject a foundational `[Agent Brain - Cognitive Memory System]` capability preamble for all memory-enabled agents even on cold start (0 facts stored), ensuring agents never deny having memory on Turn 1.
  - **Multi-Phase Goal Job Memory Compilation**: Added asynchronous `_background_extract_turn_memory` execution at the conclusion of `execute_goal_job_phases()` in `src/web/routers/chat.py`, ensuring long-running multi-phase deliverables automatically compile milestones and durable facts into `<agent_id>_memory.db`.
  - **Agent Forge Studio UI Alignment**: Updated `src/web/static/modules/studios/forge.js` to automatically derive `recall_agent_memory` and `memorize_fact` into allowed tools whenever `forgeMemoryEnabled` is checked.
  - **Prune List Cleanup**: Completely pruned the temporary `"memory"` pseudo-skill declaration and tool names from `platform-packs/developer/pack.json`. Memory is now a first-class agent core capability rather than a faux skill.
  - **Live Cognitive Memory Pipeline & Developer Brain Wiring**: Resolved cognitive memory pipeline connecting chat streaming with post-turn fact compilation. Updated `MemoryExtractorService.process_turn` to complete requests via `MultiProviderGateway.complete(CompletionRequest(...))`, and wired `AgentMemoryTools` (`recall_agent_memory`, `memorize_fact`) to dynamically resolve caller agent identity via tool context.
  - **Background Post-Turn Compilation**: Added asynchronous non-blocking background turn compilation (`_background_extract_turn_memory`) in `src/web/routers/chat.py` executing after short turns complete, extracting durable facts and generating session milestone summaries into `<agent_id>_memory.db`.
  - **Broad Query Recall Fallback**: Enriched `AgentMemoryTools.recall_agent_memory` with fallback to `list_semantic_facts(limit=limit)` when broad wildcard queries (e.g. "all stored facts", "preferences", "memories") return empty under strict FTS5 BM25 match rules.
  - **Live Multi-Agent Automated Verification**: Created `scripts/test_live_dev_memory.py` and `scripts/test_live_tutor_memory.py` executing live multi-turn tests against Developer and Tutor on the running control plane. Verified fact ingestion, background compilation in ~5s, multi-session recall, and self-awareness across both agents.
  - **Strict Physical Per-Agent Isolation**: Verified and enforced physical partition of cognitive memory brains into separate `<agent_id>_memory.db` files. Proven zero cross-agent fact contamination between Developer and Tutor agents and verified that purging an agent's memory leaves other agents completely unaffected.
  - **Dynamic Multi-Tier Context Assembly**: Validated memory token budgeting across Tight ($\le 8\text{k}$ context, ~350 tokens, max 3 facts, 0 summaries), Standard ($8\text{k}-32\text{k}$, ~800 tokens, max 6 facts, 1 summary), and Broad ($>32\text{k}$, ~2000 tokens, max 15 facts, 3 summaries) budget tiers.
  - **Atomic Conflict Resolution & Trivial Turn Bypass**: Tested atomic compilation engine across `ADD` (new facts), `BUMP` (access count increment on identical facts), `UPDATE` (in-place modification for revised values), and `DELETE` (soft-deletion). Confirmed trivial pleasantries ("thanks", "ok", "hello") bypass LLM extraction with zero spurious facts or LLM cycles.
  - **FTS5 BM25 Relevance & Decay Physics**: Verified SQLite FTS5 full-text search integrated with half-life exponential decay and logarithmic access reinforcement, ensuring frequently accessed knowledge stays buoyant while stale facts decay.
  - **Forge Brain Drawer Dual-Key Compatibility & Purge Alignment**: Enriched backend `GET /api/agents/{agent_id}/memory` to return dual-key formats (`facts` + `semantic_facts` with formatted `fact_text`, and `summaries` + `session_summaries` with `summary_text`). Added route alias `@router.post("/api/agents/{agent_id}/memory/purge")` and aligned frontend `config.js` to trigger `DELETE` for purging.
  - **End-to-End Test Suite**: Authored comprehensive universal readiness integration tests in `tests/integration/test_agent_memory_universal_readiness.py`, lifecycle tests in `tests/integration/test_agent_memory_lifecycle_walkthrough.py`, unit tests in `tests/unit/skills/test_agent_memory_tools.py`, and 5 Vitest tests in `tests/unit/frontend/agent_memory_ui.test.js`. All 78 memory tests, 109 Vitest test suites (638 tests), and preflight lint/type checks pass with 0 errors.

- Automated Scheduled Backups, Retention Policy, and Configurable Backup Directory (`src/infrastructure/data/resolver.py`, `src/infrastructure/data/backup.py`, `src/infrastructure/data/migrate.py`, `src/application/system/backup_scheduler.py`, `src/web/app.py`, `src/web/routers/settings.py`, `src/web/templates/index.html`, `src/web/static/modules/studios/settings.js`, `tests/unit/data/test_backup_retention_and_schedule.py`, `tests/unit/web/test_backup_management_api.py`, `tests/unit/frontend/settings_backups.test.js` [CARD-404]):
  - **Configurable Backup Destination**: Added `ENV_BACKUP_DIR = "AUTOREIV_BACKUP_DIR"` and `BACKUP_DIR_SETTING_KEY = "backup_dir"` to `DataDirResolver` and `DataDirPaths.backups_path`. Supported custom backup destinations across external drives, secondary disks, or Docker volumes, persisted to repo `.env` for Docker Compose volume alignment. Added checkout hygiene validation (`is_checkout_live_tree_path`) refusing backup directories within the git checkout outside `scratch/`.
  - **Automated Scheduler & Cadence Execution**: Implemented `DataDirBackupScheduler` in `src/application/system/backup_scheduler.py`, integrated into `src/web/app.py` lifespan loop. Periodically evaluates schedule rules (`disabled`, `hourly`, `daily`, `weekly`, custom intervals) and executes backup creation and retention pruning without blocking active web server operations.
  - **Retention Policy Pruning & Negative Assertions**: Enhanced `DataDirBackupService.prune_backups` to inspect archive history and enforce strict retention caps by deleting older `autoreiv-data-*.zip` files. Added negative assertions ensuring retention pruning never deletes `pre-restore-*.zip` safety archives, never touches database files or sqlite sidecars, and never deletes unrelated files in the backup folder.
  - **Comprehensive Backup Catalog REST API**: Implemented endpoints `GET /api/data-dir/backups` (catalog listing and schedule metadata), `POST /api/data-dir/backups/run` (immediate backup trigger with retention pruning), `GET /api/data-dir/backups/{filename}/download` (archive download stream), `DELETE /api/data-dir/backups/{filename}` (archive deletion with path traversal prevention), `POST /api/data-dir/backups/{filename}/restore` (server-side restore from existing catalog), and `GET`/`PUT /api/data-dir/backup-config` (schedule, retention, and path management).
  - **Settings Studio UI**: Enriched Settings Studio Data section in `index.html` and `settings.js` with backup destination input, schedule dropdown, retention count field, immediate backup creation button, and live backup archive history table with download, restore, and delete actions.

- Agent Desktop Window Manager Monolith Decomposition and Submodule Refactoring (`src/web/static/modules/ui/agent-desktop.js`, `src/web/static/modules/ui/agent_desktop/chrome.js`, `src/web/static/modules/ui/agent_desktop/dock.js`, `src/web/static/modules/ui/agent_desktop/layout.js`, `src/web/static/modules/ui/agent_desktop/prefs.js`, `src/web/static/modules/ui/agent_desktop/presets.js`, `src/web/static/modules/ui/agent_desktop/window.js`, `tests/unit/frontend/desktop_monolith_decomposition_403.test.js` [CARD-403]):
  - **Monolith Decomposition**: Decomposed the 1,894-line monolith `src/web/static/modules/ui/agent-desktop.js` into 6 cohesive single-responsibility submodules under `src/web/static/modules/ui/agent_desktop/`: `layout.js` (grid constants, window stack z-indices, geometry clamping, tile/cascade/columns/mobile rect calculators), `prefs.js` (localStorage preferences load/save, open tabs tracking, sessions scrubbing), `chrome.js` (desktop wallpaper and window layer DOM scaffolding, HITL dialog enhancement, system clock ticker), `dock.js` (dock launcher rendering, open/minimized state indicators, horizontal scroll buttons and stepper controls), `presets.js` (canvas presets, preset saving/applying/deletion, organize menu UI and click handlers), and `window.js` (window shell DOM creation, pointer drag & resize handlers, focus and z-index elevation, maximize/minimize/close transitions, mobile responsive window stacking).
  - **800-Line Size Caps Enforced**: Every single decomposed submodule under `src/web/static/modules/ui/agent_desktop/*.js` is strictly under 800 lines of code (109 to 769 lines). The root coordinator `agent-desktop.js` was reduced from 1,894 lines down to 649 lines (<1,000 lines), maintaining zero duplicate code paths and strict single-source-of-truth architectures.
  - **Complete Backward Compatibility**: Retained and re-exported all 24 public APIs and constants directly from `agent-desktop.js` (`DOCK_LAUNCHERS`, `VIEW_BY_TAB`, `RESIZE_EDGES`, `initAgentDesktop`, `GRID_SIZE`, `DESKTOP_DOCK_Z`, `DESKTOP_MODAL_Z`, `DESKTOP_WINDOW_Z_CAP`, `nextDesktopStackZ`, `PREFS_KEY`, `scrubSessionsFromDesktopPrefs`, `collectAgentsFromDom`, `loadDesktopPrefs`, `saveDesktopPrefs`, and all layout math functions) ensuring 100% drop-in compatibility across caller studios (`app.js`, `chat.js`, `factory.js`, etc.) and all existing Vitest suites.
  - **Contract & Regression Verification**: Authored contract test suite `tests/unit/frontend/desktop_monolith_decomposition_403.test.js` asserting file line counts (<1,000 for root coordinator, <800 for all submodules) and verifying all exported APIs and layout calculators. All 108 Vitest suites (632 tests) and all 1,873 Python backend tests pass with 0 errors and zero warnings.

- Chat Studio SSE Stream Event Parsing and Message Load Rendering Fix (`src/web/static/modules/studios/chat/stream.js`, `src/web/static/modules/studios/chat/render.js`, `src/web/static/modules/studios/chat.js`, `src/web/routers/chat.py`, `tests/unit/frontend/chat_stream_sse_parsing.test.js` [CARD-401]):
  - **Stateful SSE Event Parsing**: Enhanced `consumeChatStream` in `src/web/static/modules/studios/chat/stream.js` to statefully parse multi-line Server-Sent Events headers (`event: token`, `event: reasoning`), mapping `eventType = ev.type || ev.event || currentEvent || 'message'` and extracting text via `ev.text ?? ev.content ?? ev.data ?? ''`. Guarantees `onToken` and `onReasoning` callbacks fire predictably during streaming even when event headers precede data payloads.
  - **Conversation History Loading & Render Options Compatibility**: Corrected `loadMessages` in `src/web/static/modules/studios/chat.js` to handle direct JSON array responses from `GET /api/sessions/{id}/messages` without defaulting to empty arrays. Updated `renderMessages` in `src/web/static/modules/studios/chat/render.js` to accept both options object (`{ messagesContainer, messages, ... }`) and legacy positional signatures, preserving rendering of message bubbles and full Markdown styling upon session load.
  - **Stream Markdown Finalization**: Ensured `executeChatTurn` in `chat.js` calls `renderMarkdown` on completion so reasoning drawers, code blocks, tables, and LaTeX math render cleanly once streaming ends.
  - **Defense-in-Depth SSE Payload Types**: Added explicit `"type": "token"` and `"type": "reasoning"` attributes inside JSON SSE payloads emitted by `_forward_kernel_event` in `src/web/routers/chat.py`.
  - **Test-Locked Delivery & Negative Assertion**: Authored `tests/unit/frontend/chat_stream_sse_parsing.test.js` covering multi-line SSE chunking, history array rendering, and negative assertion `[REQ-401-004]` verifying `onToken` is never dropped on header-separated SSE streams.


- Wiki Studio Monolith Decomposition and Submodule Refactoring (`src/web/static/modules/studios/wiki.js`, `src/web/static/modules/studios/wiki/export.js`, `src/web/static/modules/studios/wiki/folder.js`, `src/web/static/modules/studios/wiki/mindmap.js`, `src/web/static/modules/studios/wiki/note.js`, `src/web/static/modules/studios/wiki/templates.js`, `src/web/static/modules/studios/wiki/tree.js`, `tests/unit/frontend/wiki_monolith_decomposition_399.test.js` [CARD-399]):
  - **Monolith Decomposition**: Decomposed the 1,701-line monolith `src/web/static/modules/studios/wiki.js` into 6 single-responsibility submodules under `src/web/static/modules/studios/wiki/`: `export.js` (chat turn export to Wiki Inbox), `folder.js` (folder selection, folder overview card grid, folder deletion), `mindmap.js` (Obsidian-style force-directed mind map canvas, physics simulation runner, zoom, pan, tooltip interactions), `note.js` (note content loading, markdown preview vs textarea editor view mode switching, note save/delete, collapsible YAML frontmatter inspector), `templates.js` (structured wiki templates discovery, new note modal, body prefilling, rule-based inbox graduation), and `tree.js` (vault tree hierarchy loading, collapsible sections across Inbox, Notes warehouse, Resources, and Archive).
  - **800-Line Size Caps Enforced**: Every single decomposed submodule under `src/web/static/modules/studios/wiki/*.js` is strictly under 800 lines of code (39 to 590 lines). The root coordinator `wiki.js` was reduced from 1,701 lines down to 124 lines (<1,000 lines), maintaining zero duplicate code paths and strict single-source-of-truth architectures.
  - **Complete Backward Compatibility**: Re-exported all decomposed submodule symbols directly from `wiki.js` ensuring 100% drop-in backward compatibility for all public exported APIs (`initWikiStudio`, `exportMessageToWiki`) and existing Vitest suites.
  - **Contract & Regression Verification**: Created contract test suite `tests/unit/frontend/wiki_monolith_decomposition_399.test.js` asserting file line counts (<1,000 for root coordinator, <800 for each submodule) and verifying exported APIs. All 106 Vitest suites (622 tests), 1,817 Python backend tests, and all 7 Playwright multi-studio smoke tests pass with 0 errors and zero warnings.

- Agent Forge Studio Monolith Decomposition and Submodule Refactoring (`src/web/static/modules/studios/forge.js`, `src/web/static/modules/studios/forge/config.js`, `src/web/static/modules/studios/forge/lab_monitor.js`, `src/web/static/modules/studios/forge/proposals.js`, `src/web/static/modules/studios/forge/runbook.js`, `src/web/static/modules/studios/forge/scaffold.js`, `src/web/static/modules/studios/forge/tools.js`, `tests/unit/frontend/forge_monolith_decomposition_398.test.js` [CARD-398]):
  - **Monolith Decomposition**: Decomposed the 3,505-line monolith `src/web/static/modules/studios/forge.js` into 6 cohesive single-responsibility submodules under `src/web/static/modules/studios/forge/`: `config.js` (per-agent LLM providers, model discovery, avatar preview, routines, telemetry, brain drawer, tones), `lab_monitor.js` (autonomous factory training monitor drawer, packet telemetry, live activity feeds, artifact preview, retry modal), `proposals.js` (architectural governance proposals inbox, category badges, remedy execution, autonomic synthesis), `runbook.js` (runbook markdown authoring, char counter, mechanical capability linting, platform/pack skills hierarchy), `scaffold.js` (quick presets `FORGE_QUICK_PRESETS`, quick scaffold modal, candidate queue, same-job origin resumption), and `tools.js` (OS baseline tools, capability gaps backlog, remote MCP server management, credential grants).
  - **800-Line Size Caps Enforced**: Every single decomposed submodule under `src/web/static/modules/studios/forge/*.js` is strictly under 800 lines of code (254 to 728 lines). The root coordinator `forge.js` was reduced from 3,505 lines down to 699 lines (<1,000 lines), maintaining zero duplicate code paths and strict single-source-of-truth architectures.
  - **Complete Backward Compatibility**: Re-exported all decomposed submodule exports directly from `forge.js` ensuring 100% drop-in backward compatibility for all public exported APIs and caller studios (`app.js`, `factory.js`, etc.).
  - **Contract & Regression Verification**: Authored contract test suite `tests/unit/frontend/forge_monolith_decomposition_398.test.js` asserting file line counts (<1,000 for root coordinator, <800 for all submodules) and verifying all exported APIs. All 105 Vitest suites (619 tests), 1,817 Python backend tests, and all 7 Playwright multi-studio smoke tests pass with 0 errors and zero warnings.

- Chat Studio Monolith Decomposition and Submodule Refactoring (`src/web/static/modules/studios/chat.js`, `src/web/static/modules/studios/chat/chrome.js`, `src/web/static/modules/studios/chat/composer.js`, `src/web/static/modules/studios/chat/hitl.js`, `src/web/static/modules/studios/chat/job_chrome.js`, `src/web/static/modules/studios/chat/journey.js`, `src/web/static/modules/studios/chat/render.js`, `src/web/static/modules/studios/chat/scroll.js`, `src/web/static/modules/studios/chat/stream.js`, `src/web/static/modules/studios/chat/train_modal.js`, `src/web/static/modules/studios/chat/training.js`, `src/web/static/modules/studios/chat/workbench.js`, `tests/unit/frontend/chat_monolith_decomposition_397.test.js` [CARD-397]):
  - **Monolith Decomposition**: Decomposed the legacy 4,118-line monolith `src/web/static/modules/studios/chat.js` into 11 single-responsibility submodules under `src/web/static/modules/studios/chat/`: `chrome.js` (sessions drawer, session persistence, title renaming, quick prompts picker, options drawer), `composer.js` (attachments preview, file drop/paste/upload, auto-resize textarea, send/stop controls, `/learn` command handler), `hitl.js` (pending approvals polling and HITL card interactions), `job_chrome.js` (multi-phase inline job chrome models, HTML templates, phase rows, plan steps, and reflexion badges), `journey.js` (journey timeline and tool execution spans), `render.js` (markdown and mermaid rendering, artifact modal, message bubbles, proposal cards, and click delegation), `scroll.js` (smart autoscroll, follow-tail calculations, jump-to-latest button, and sessions drawer toggling), `stream.js` (SSE stream consumption, turn events, agent handoff cards), `train_modal.js` (training handshake and teach agent skill distillation modals), `training.js` (training payload builder and live indicators), and `workbench.js` (Dual-Pane Workbench canvas, tabs, artifact badge, and clipboard copy).
  - **800-Line Size Caps Enforced**: All 11 decomposed submodules are strictly under 800 lines of code (139 to 785 lines). The root coordinator `chat.js` was reduced from 4,118 lines down to 975 lines (<1,000 lines), maintaining zero duplicate code paths and strict single-source-of-truth architectures.
  - **Complete Backward Compatibility**: Re-exported all decomposed submodule exports directly from `chat.js` ensuring full drop-in compatibility across all caller studios (`app.js`, `education.js`, `wiki.js`, `agent-desktop.js`).
  - **Contract & Regression Verification**: Created contract test suite `tests/unit/frontend/chat_monolith_decomposition_397.test.js` asserting file line counts (<1,000 for root, <800 for each submodule) and verifying exported APIs. All 104 Vitest suites (616 tests), 4 Python job phase UI tests, and all 7 Playwright multi-studio smoke tests pass with 0 errors and zero warnings.

- Modular CSS Extraction and Index Template Hygiene (`src/web/templates/index.html`, `src/web/static/css/base.css`, `src/web/static/css/components.css`, `src/web/static/css/desktop.css`, `src/web/static/css/studios.css`, `tests/unit/frontend/template_helper.js`, `tests/unit/frontend/css_extraction_396.test.js`, `tests/unit/web/test_static_css_396.py` [CARD-396]):
  - **Modular CSS Extraction**: Extracted 1,324 lines of inline CSS from the `<style>` tag in `src/web/templates/index.html` into four modular, cacheable stylesheets under `src/web/static/css/`: `base.css` (variables, base resets, mobile inset locks), `components.css` (scrollbars, badges, buttons, drawers), `desktop.css` (radical agent desktop windowing, dock launcher, drag/resize handles, claymorphism), and `studios.css` (studio-specific layouts and collapse details).
  - **Mobile Dock Launcher Alignment Fix**: Replaced `justify-content: center` with `justify-content: flex-start` on `.desktop-dock-apps` (with `has-overflow` and `@media (max-width: 767px)` locks) to eliminate CSS flexbox negative coordinate occlusion that trapped leading studio launcher buttons (Chat, Wiki, Projects) behind the left scroll indicator on mobile viewports.
  - **Index Template Hygiene**: Linked all four stylesheets in `src/web/templates/index.html` via `<link rel="stylesheet">` tags with asset cache busting query string `?v=2.0.82`, trimming `index.html` from 5,998 lines down to 4,676 lines (-1,322 lines).
  - **Test-Locked Delivery**: Authored frontend contract suite `tests/unit/frontend/css_extraction_396.test.js` asserting `<link>` tags exist, zero inline `<style>` tags exceed 50 lines, and all four modular stylesheets are non-empty. Added backend FastAPI integration test `tests/unit/web/test_static_css_396.py` verifying HTTP 200 and `text/css` MIME type for each stylesheet. Created `tests/unit/frontend/template_helper.js` (`loadPageHtml()`) ensuring existing Vitest suites validate DOM markup and modular CSS together.

- Dead Code Scavenger, Orphaned Workflows Pruning, and Git Hygiene (`src/web/static/modules/studios/skills.js`, `src/web/routers/workflows.py`, `src/application/orchestration/workflow_service.py`, `src/infrastructure/memory/repositories/workflows.py`, `src/domain/orchestration/workflow.py`, `src/web/routers/chat.py`, `src/web/app.py`, `src/application/agent_packs/service.py`, `.gitignore` [CARD-395]):
  - **Pruned Dead Standalone Studio File**: Deleted orphaned `src/web/static/modules/studios/skills.js` (367 lines, retired since CARD-118, zero importers, dead DOM IDs).
  - **Excised Orphaned Workflows Subsystem**: Removed legacy `workflows` router, service, repository, and domain models (`src/web/routers/workflows.py`, `workflow_service.py`, `repositories/workflows.py`, `workflow.py`). Unmounted `workflows_router` from `src/web/app.py` and excised obsolete workflow copy routines from `AgentPackService`.
  - **Retired Deprecated Chat Goal Endpoint**: Excised `POST /api/chat/goal` and `GoalChatRequest` from `src/web/routers/chat.py`, locking all multi-step chat execution through the standing `POST /api/chat/stream` orchestrator.
  - **Fixed Git-Ignore Masking & Restored Hidden Tests**: Anchored `.gitignore` rule `/core` to prevent matching `tests/unit/core/`, tracking the previously ignored regression suite `test_dead_code_shims_scavenger_385.py` and adding `test_dead_code_scavenger_395.py` with negative assertions for all excised files and endpoints.

## [0.38.0] - 2026-09-20

- Enterprise MCP Server Development and Docker Deployment Skill Pack (`src/application/skills/mcp_engineering_tools.py`, `src/infrastructure/tools/mcp_engineering.py`, `src/infrastructure/skills/seeds/mcp-engineering/SKILL.md`, `platform-packs/developer/skills/mcp-engineering/SKILL.md`, `platform-packs/developer/pack.json`, `src/infrastructure/agents/registry.py`, `src/web/app.py` [CARD-394]):
  - **`mcp-engineering` Platform Skill Pack**: Equipped AutoReiv Developer agent and engineering specialists with end-to-end capabilities to scaffold FastMCP projects, execute AST syntax and JSON-RPC 2.0 schema tests, containerize with multi-stage non-root Dockerfiles, and automatically register endpoints into AutoReiv.
  - **FastMCP Scaffolding (`scaffold_mcp_server`)**: Generates canonical FastMCP project trees with typed Pydantic parameter schemas, automatic `health()` endpoint, multi-stage non-root `Dockerfile`, `pyproject.toml`, and comprehensive `README.md`.
  - **Protocol & Schema Verification (`test_mcp_server`)**: Validates AST Python syntax, validates tool docstrings and typed parameters, runs simulated JSON-RPC 2.0 `initialize` and `tools/list` handshakes, and executes contract checks with remediation diagnostics `[REQ-394-003]`.
  - **Docker Container Deployment with Health Checks (`deploy_mcp_container`)**: Builds and launches Docker containers with mandatory `HEALTHCHECK` validation `[REQ-394-004]`; includes graceful fallback to local `stdio` subprocess mode when Docker CLI or daemon is unavailable. Rejects deployments missing healthcheck endpoints `[REQ-394-005]`.
  - **Single Lever Invariant for MCP Mounting (`register_mcp_service`)**: Agent tool writes to the exact same canonical SQLite state store (`store.set_setting("mcp_servers")`) and invokes the exact same `MCPClientManager.mount_server` pipeline as Settings Studio manual additions (`#addMcpServerBtn`). Discovered tools automatically generate Matt Pocock compliant companion runbooks (`$DATA_DIR/skills/mcp-<name>/SKILL.md`).
  - **Test-Locked Delivery**: Unit tests in `tests/unit/skills/test_mcp_engineering_tools.py` and integration lifecycle suite in `tests/integration/mcp/test_mcp_dev_deploy_lifecycle.py` verifying scaffolding, negative syntax rejection, missing healthcheck rejection, stdio fallback, and canonical single-lever persistence.

- AutoReiv Hosted MCP Server and Cross-Instance Federation (`src/web/routers/mcp_server.py`, `src/web/routers/settings.py`, `src/infrastructure/mcp/companion_author.py`, `src/web/templates/index.html`, `src/web/app.py` [CARD-392]):
  - **FastAPI Hosted MCP Server (`/api/mcp/sse`, `/api/mcp/messages`, `/api/mcp/status`)**: Implemented official Model Context Protocol (MCP) HTTP/SSE transport on port 8000. `GET /api/mcp/sse` handles Server-Sent Events stream handshake and session initialization; `POST /api/mcp/messages` and `POST /api/mcp/sse` process JSON-RPC 2.0 requests (`initialize`, `ping`, `tools/list`, `tools/call`). `GET /api/mcp/status` reports live host metrics and published capability counts.
  - **Agent-Mediated Capability Publishing (Zero Naked Tool Leakage)**: `tools/list` publishes chat-visible autonomous agents as high-level dispatcher tools (`ask_autoreiv`, `ask_developer`, `ask_tutor`, etc.) and safe passive lookups (`search_wiki`, `read_wiki_document`, `get_system_health`). Raw internal tools and retired or non-autonomous engines (`direct`, `coding`, `agent-builder`, `assistant`) are strictly excluded. When invoked, `tools/call` executes the agent's turn via `AgentKernel.run_turn` with server-side governance and returns the final scrubbed output.
  - **Cross-Instance Federation & Companion SKILL.md Authoring**: When connecting to a peer AutoReiv instance via Settings Studio or `MCPClientManager`, discovered tools are automatically mounted and a Matt Pocock compliant companion runbook (`$DATA_DIR/skills/mcp-<server>/SKILL.md`) is authored, preserving strict SOP governance across physical network boundaries.
  - **Token Authentication & Settings Studio Banner**: Inbound requests can be protected with API Bearer tokens or `x-api-key`. Added Hosted MCP Server status banner in Settings Studio displaying active HTTP/SSE endpoints and port 8000 metrics.
  - **Strict In-Process Invariant & Test-Locked Delivery**: Authoritative unit tests in `tests/unit/mcp/test_hosted_mcp_server.py` and end-to-end integration test `tests/integration/test_autoreiv_federation_e2e.py` verifying full JSON-RPC handshake, agent dispatching, companion skill authoring, and negative assertion `[REQ-392-005]` proving local turns execute tools in-process without network hops to `/api/mcp/sse`.

- Developer Agent and Projects Studio Workspace Integration (`src/application/kernel/agent_kernel.py`, `src/web/templates/index.html`, `src/web/static/modules/studios/projects.js`, `src/web/static/modules/studios/chat.js` [CARD-391]):
  - **Pair with Developer Direct Bridge**: Added `[ ≡ƒÆ╗ Pair with Developer ]` button (`#projectsPairDeveloperBtn`) in Projects Studio header adjacent to the active project badge. Clicking navigates directly to Chat Studio, selects Developer (`#agentSelect`), and initializes a paired engineering session pre-grounded with the active project workspace greeting.
  - **Chat Studio Active Project Indicator & Round-Trip Navigation**: Added `#chatActiveProjectPill` and `#chatActiveProjectName` to Chat Studio header. When Developer is the active agent, the pill dynamically reflects the active project name from `/api/projects/selected` with a tooltip. Clicking the pill instantly routes back to Projects Studio.
  - **Skill-Gated Dynamic Workspace Grounding in AgentKernel**: Enriched `AgentKernel._build_effective_system_message` to automatically detect the selected project root, its `AGENTS.md` governance constitution, and active work cards (`docs/cards/CARD-*.md`), injecting them directly into Developer's system prompt. Strictly skill-gates injection so non-project agents (e.g. Tutor) maintain 100% clean context windows without workspace noise, and tailors guidance text based on read-only vs. read/write tool availability.
  - **Project Tool Scoping & Boundary Jail**: Verified Developer's tools (`ProjectFileTools`, `GitTools`, `CardTools`, `SysadminTools`) resolve paths dynamically relative to the active project root, with strict negative assertion verification (`[REQ-391-004]`) ensuring path traversal attempts outside project boundaries are rejected with `ProjectPathError`.
  - **Test-Locked Delivery & Single Lever Invariant**: Authored Python unit test suite `tests/unit/agents/test_developer_project_grounding.py` (6 tests including negative assertion for non-project agents and read-only guidance) and frontend Vitest suite `tests/unit/frontend/developer_projects_integration.test.js` (8 tests), maintaining zero duplicate indicators and zero hardcoded fallback paths.

- Integrated Runbook Editor and Mechanical Capability Linter (`src/web/routers/skills.py`, `src/web/static/modules/studios/forge.js`, `src/web/templates/index.html` [CARD-390]):
  - **Mechanical Capability Linter Endpoint**: `POST /api/skills/lint` compiles draft runbook text or form fields against ADR-0054 capability contracts without disk writes, verifying Rule of 7 tool budget (`CAP-001`), mandatory testable verification / Done-When criteria (`CAP-002`), security boundary collisions (`CAP-003`), runbook body budget $\le 8000$ chars (`CAP-004`), and YAML syntax (`SYN-001`).
  - **Integrated Agent Studio Runbook Workbench**: Embedded on-demand capability validation into `#studioRunbookEditor` via `#studioRunbookValidateBtn` and `#studioRunbookLintStatus`, displaying live diagnostic badges (PASS / WARN / FAIL) and granular violation messages.
  - **Context Budget Tracking**: Live `#studioRunbookCharCount` tracking runbook body length against the 8,000 character limit with visual threshold cues.
  - **Pre-fill Canonical Blueprint**: New runbook creation (`#studioNewRunbookBtn`) pre-populates the canonical Matt Pocock operational blueprint (`## Operating Principles`, `## Available Tools`, `## Done-When`), eliminating blank-page syndrome and preventing `CAP-002` violations.
  - **Pre-Save Violation Guard**: Saving an invalid runbook via `#studioRunbookSaveBtn` invokes the capability linter, displaying detected contract violations and requiring operator confirmation before persisting draft state.
  - **Test-Locked Delivery & Single Lever Invariant**: Added `tests/unit/web/test_skill_lint_api.py` and `tests/unit/frontend/forge_runbook_linter.test.js`, maintaining the permanent retirement of standalone `#view-skills` / `#tab-skills` and ensuring exactly one canonical runbook editor exists in Agent Studio.

- Uniform Skill-First Capability Architecture and Agent Forge Realignment (`src/infrastructure/skills/seeds/sqlite-storage/SKILL.md`, `src/infrastructure/skills/seed.py`, `src/application/agent_packs/schema.py`, `src/domain/settings/models.py`, `src/infrastructure/agents/registry.py`, `src/web/routers/agents.py`, `src/web/static/modules/studios/forge.js`, `src/web/templates/index.html` [CARD-389]):
  - **Uniform Skill-First Capabilities (Zero Naked Tools)**: In Agent Forge Studio, completely replaced the raw tool checkboxes grid (`#forgeToolsSection`, `#forgeToolsGrid`, `#selectAllToolsBtn`, etc.) with the Assigned Skills section (`#forgeSkillsSection`), which renders declared tools as read-only chips with required badges. Agents configure capabilities strictly through `SKILL.md` runbooks ("Brain & SOPs") which mount their declared tools ("Hands").
  - **Display Name Customization with Immutable Identity Slug**: Operators can customize `agent.name` for any agent (including seeded agents like `autoreiv`, `developer`, `tutor`) via `#forgeNameInput`. The underlying slug `agent.id` is strictly `readonly` to protect database and filesystem integrity. Changes persist to `agent_overrides` SQLite table and user-data `packs/<id>/pack.json`.
  - **Specialty SQLite Storage Database Toggle**: Checking `[x] Dedicated Storage Database (<slug>_storage.db)` (`#forgeStorageEnabled`) automatically binds the Tier 1 `sqlite-storage` skill runbook (`query_agent_database`, `execute_agent_database`) via `AgentProfileGuardrail`.
  - **Locked OS Baseline Primitives**: Preserved uncheckable reference chips for the 5 fundamental platform tools (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`) in `#forgeBaselineBox`.
  - **Test-Locked Delivery & Negative Assertions**: Authoritative regression tests in `tests/unit/agent_packs/test_card_389_skill_first_architecture.py`, `tests/unit/frontend/forge_decoupled_tools_skills_350.test.js`, and `tests/unit/frontend/forge_allowlist.test.js` ensuring 0 naked tools can be bound without a skill runbook and display names cleanly update without mutating slugs.

- Restore Developer and Tutor as Unified Agent Packs (`platform-packs/`, `src/application/agent_packs/schema.py`, `src/infrastructure/skills/platform_packs.py`, `src/domain/agents/profiles.py`, `src/web/templates/index.html`, `src/web/static/modules/studios/chat.js` [CARD-388]):
  - **Restored Factory Seed Packs**: Added `platform-packs/developer/` with `sdlc-engineering` skill and full SDLC tooling (`read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, `propose_followup`), and `platform-packs/tutor/` with `socratic-tutoring` skill and educational wiki tools. Both packs strictly adhere to the Rule-of-7 tool budget with zero naked tools.
  - **Eliminated Retired Status and Aliases**: Removed `developer` and `tutor` from `RETIRED_PLATFORM_PACK_IDS` and `LEGACY_AGENT_ALIASES`, restoring them to `PLATFORM_PACK_IDS` and `CHAT_SHOWN_BY_ID` so queries resolve canonically without redirecting to `autoreiv`.
  - **Dynamic Multi-Agent Chat Studio Header**: Upgraded `#chatEngineSelector` from a binary toggle to dynamic selectable pills for all chat-visible agents (`AutoReiv`, `Developer`, `Tutor`, `Direct`, and user packs) displaying `agent.name`, supporting independent session contexts and model routing.
  - **Test-Locked Delivery & Negative Assertions**: Authoritative regression tests asserting that `developer` and `tutor` are not redirected to `autoreiv`, not deleted during startup reconciliation, and render interactive selector pills.

- Factory Scaffolder UX Top Action Banner, Auto Slug, and Tool Batch Actions (`src/web/templates/index.html`, `src/web/static/modules/studios/factory.js` [CARD-387]):
  - **Horizontal Top Action Banner**: Elevated `[Γ£¿ Generate / Refine Runbook]` and `[≡ƒÆ¼ Talk it out with Forge]` to `#factoryTopActionBar` above the 3-column workshop, establishing a natural left-to-right, top-to-bottom sequence across desktop and mobile.
  - **Automated `snake_case` Agent Slug**: Agent ID (`#factoryAgentIdInput`) is now marked `readonly` when creating new agents and auto-formats from Display Name into lowercase alphanumeric `snake_case`.
  - **Pruned Redundant Model Dropdown**: Completely deleted `#factoryAgentModelSelect` and the stranded footer from Column 1, delegating model routing canonically to Agent Studio and Settings Studio.
  - **Tool Batch Selection & Intent Auto-Suggest**: Added `[Select All]` (`#factorySelectAllToolsBtn`) and `[Clear]` (`#factoryClearAllToolsBtn`) to quickly check/uncheck filtered capabilities in Column 3, alongside an `[≡ƒ¬ä Suggest]` button (`#factoryAutoSuggestToolsBtn`) that scans the catalog for tools matching skill trigger and intent keywords.

- 3-Column Agent & Skill Scaffolder and Capabilities Workshop (`src/web/routers/agent_training_factory.py`, `src/web/static/modules/studios/factory.js`, `src/web/templates/index.html` [CARD-386]):
  - **Column 1: Target Agent Brief**: Target specialist dropdown with support for both existing agents and net-new agent scaffolding (`+ Create New Agent`), role persona / system instructions, and model routing.
  - **Column 2: Skills & Runbook**: Matt Pocock standard `SKILL.md` authoring workbench with concise trigger description ($\le 60$ chars), operator intent notes, LLM procedural runbook generator (`POST /api/agent_training_factory/scaffold/runbook`), live Markdown editor, and auto-pinning on save (`POST /api/agent_training_factory/scaffold/save`).
  - **Column 3: Capabilities & Grounding**: Live capabilities inspector (`GET /api/agent_training_factory/capabilities`) exposing dormant platform tools and connected MCP servers (e.g. Blender MCP with 24 tools) grouped by namespace, paired with an external reference notes textarea for API documentation and cheat sheets.
  - **Dynamic Pack-Declared Tool Mounting**: Updated `resolve_scoped_tools` and `ScopedToolRegistry.get_tools_for_agent` so agent packs declaring tools in their `skills` definitions automatically mount and resolve them when active.
  - **Deterministic Test-Locked Delivery**: Added comprehensive unit test suite (`tests/unit/agent_training_factory/test_scaffolder_endpoints.py`) and end-to-end integration lifecycle test (`tests/integration/factory/test_scaffolder_lifecycle.py`), with all 99 Vitest test files passing green.


- Orphaned Shims & Dead Compatibility Aliases (`src/web/routers/`, `src/application/orchestration/`, `src/application/agent_training_factory/` [CARD-385]):
  - **Excised Unused Router Shims**: Deleted unreferenced shim `src/web/routers/_card313_import_data_dir_migrate.py` and obsolete router alias `src/web/routers/factory.py`, ensuring all factory endpoints route canonically through `agent_training_factory.py`.
  - **Excised FactoryRunner Compatibility Shims**: Deleted `src/application/orchestration/factory_runner.py`, pruned `FactoryRunner = FactoryOrchestrator` export alias from `orchestrator.py`, and cleaned `app.state.factory_runner` and `gaps.py` fallbacks.
  - **Stale Root Bytecode Cleanup**: Purged historical compiled bytecode from root `__pycache__`.
  - **Negative Assertion Regression Suite**: Added `tests/unit/core/test_dead_code_shims_scavenger_385.py` asserting that excised shims cannot be imported and obsolete aliases remain absent.

### Removed

- Completely excised naked-tool checkboxes grid (`#forgeToolsSection`, `#forgeToolsGrid`, `#forgeToolSearchInput`, `#selectAllToolsBtn`, `#clearAllToolsBtn`) and associated shadow helpers (`toolCheckboxHtml()`, `selectRecommendedToolsForSkill()`, `renderAllowedTools()`, `applyToolChecks()`) from Agent Forge Studio in favor of Assigned Skills architecture [CARD-389].
- Excised `is_builtin` restriction in `src/web/routers/agents.py` that previously prevented display name customization for seeded agents [CARD-389].

- Excised horizontal button-scroll agent picker and button pills (`#engineBtnCore`, `#engineBtnDeveloper`, `#engineBtnTutor`, `#engineBtnDirect`, `renderEngineSelectorPills`) in Chat Studio header in favor of canonical `#agentSelect` dropdown [CARD-388].
- Pruned binary dual-engine lock in Chat Studio header (`#engineBtnCore` / `#engineBtnDirect` exclusivity) and hardcoded 2-agent chat restrictions [CARD-388].
- Excised `developer` and `tutor` entries from `RETIRED_PLATFORM_PACK_IDS` and `LEGACY_AGENT_ALIASES` [CARD-388].
- Pruned `(Platform)` and `(Custom)` labels from Agent Studio dropdowns and select options [CARD-388].
- Excised origin-based pack purging in `DeclarativePackReconciler` [CARD-388].

- Subtractive Pruning of Legacy 8-Phase Factory Compiler & Sub-Views (`src/web/templates/index.html`, `src/web/static/modules/studios/factory.js`, `src/web/static/modules/ui/agent-desktop.js` [CARD-386]):
  - **Excised Obsolete Factory Sub-Views**: Completely deleted the dead 8-phase pipeline view (`#factoryPipelineView`), the training runs & live monitor two-pane view (`#factoryRunsView`), and the sub-tab bar (`#factoryTabIntakeBtn`, `#factoryTabRunsBtn`, `#factoryTabPipelineBtn`).
  - **Excised Obsolete Deliverable Inspector Modal**: Removed the legacy HITL deliverable modal (`#factoryDeliverableModal`) and its diff tabs (`#factoryTabDiffBtn`, `#factoryTabToolBtn`, `#factoryTabRunbookBtn`) in favor of direct, in-place Matt Pocock `SKILL.md` runbook authoring in Column 2.
  - **Relocated Capability Gap Backlog**: Preserved the Needs Training Backlog (`#agentTrainingBacklogCard`) in Agent Studio (`view-agents`), where it is canonically updated by `forge.js` during agent inspection.
  - **Pruned Dead CSS & Event Listeners**: Excised orphaned CSS rules for `#factoryRunsView` and `#factoryPipelineView`, pruned `switchSubView` and tab-switching event handlers, and removed dead modal enhancement hooks from `agent-desktop.js`.

### Changed

- Unify Agent Packs & Drop Platform vs Custom Primitive (`src/domain/kernel/models.py`, `src/domain/agents/guardrails.py`, `src/infrastructure/skills/reconciler.py`, `src/infrastructure/memory/repositories/settings.py`, `src/web/routers/agents.py`, `src/web/static/modules/studios/forge.js`, `src/web/static/modules/studios/factory.js`, `src/web/static/modules/studios/chat.js` [CARD-388]):
  - **Unified Agent Pack Model**: Replaced artificial "Platform" vs "Custom" distinction with a single cohesive `Agent Pack` primitive (`AgentOrigin.PACK = "pack"`). Seeding from `platform-packs/` initializes factory defaults into user data, after which all agent packs share sovereign status and capabilities.
  - **Clean Display Naming**: Pruned `(Platform)` and `(Custom)` tags from `formatAgentSelectOption` across all Studio dropdowns and simplified `#factoryAgentSelect` label to `'All Agents'`.
  - **Unified Studio Badging**: Replaced `Platform Agent Pack` / `Custom Agent` badges with a single `Agent Pack` badge (reserving `System Baseline` exclusively for internal engine `agent-builder`).
  - **Refined Deletion Protection**: Restricted deletion protection strictly to core system orchestration identities (`autoreiv` and `agent-builder`). Operators can freely delete or manage any other agent pack (`developer`, `tutor`, or custom packs).
  - **Sovereign User Pack Reconciliation**: Pruned origin-based purging from `DeclarativePackReconciler`; reconciler now strictly purges explicitly retired packs (`RETIRED_PLATFORM_PACK_IDS`), never touching user packs in `$DATA_DIR/packs/`.
  - **Self-Healing Legacy Purpose**: Added automated normalization in `AgentProfileGuardrail` and `install_platform_agent_packs` converting legacy `"purpose": "code"` to `"task_execution"`, resolving unhandled validation errors and ensuring Developer imports reliably.

- Single Lever Audit & Shadow Function Deduplication (`src/web/static/modules/`, `src/web/routers/` [CARD-384]):
  - **Canonical HTML Escaping Single Lever**: Unified HTML escaping across desktop and studio interfaces to use canonical `escapeHtml` from `dom.js` (re-exported from `formatters.js`); pruned local duplicate `escapeHtml` in `projects.js` and shadow helper `escapeHtmlLite` in `agent-desktop.js`.
  - **Canonical Mobile Viewport Invariant**: Exported canonical `isMobile()` helper (`window.innerWidth < 768`) from `dom.js` and replaced 11 open-coded viewport width checks and 2 local duplicate functions across `agent-desktop.js`, `prompts.js`, `app.js`, `chat.js`, `wiki.js`, `skills.js`, and `projects.js`.
  - **Unified Safe Clipboard Operations**: Replaced raw unhandled `navigator.clipboard.writeText` and inconsistent inline `execCommand` fallbacks in `factory.js`, `forge.js`, `projects.js`, and `wiki.js` with centralized `copyToClipboard()` from `utils/clipboard.js`.
  - **Canonical Toast Dispatch**: Standardized toast notification paths across `factory.js`, `skills.js`, and `projects.js` to dispatch via `../ui/toast.js` (`showToast`) when callbacks are omitted.
  - **Single Backend Data Directory Resolver**: Eliminated duplicate `_data_dir_paths` implementation in `src/web/routers/data_dir_migrate.py`, cleanly importing the canonical helper from `settings.py`.
  - **Negative Assertion Regression Suite**: Added `tests/unit/frontend/single_lever_dedup_384.test.js` verifying the absence of shadow functions and asserting positive `isMobile` boundary behaviors.

- Eliminate Hardcoded Agent Names, Aliases, and Fragmented Routing (`src/domain/agents/`, `src/application/orchestration/`, `src/application/kernel/`, `src/infrastructure/agents/`, `src/web/` [CARD-383]):
  - **Schema-Driven Chat Visibility**: Replaced legacy 7-string chained comparison blocklist in `chat.js` with declarative schema properties (`show_in_chat !== false`, `origin !== 'system'`, and `id !== 'agent-builder'`).
  - **Canonical Agent Resolution Single Source**: Unified alias mapping via `canonical_agent_id()` and `DEFAULT_PLATFORM_AGENT_ID = "autoreiv"` in `src/domain/agents/profiles.py`; excised duplicate ad-hoc `alias_map` dictionaries in `handoff_engine.py` and `supervisor_orchestrator.py`.
  - **Clean Specialist & Capability Dispatch**: Pruned hardcoded tuple checks for legacy agents (`developer`, `coding`, `wiki`, `tutor`) in `job_phase_orchestrator.py`, delegating all resolution to canonical profiles and capabilities.
  - **Education Router Defaults**: Replaced legacy `agent_id: str = "tutor"` defaults across 50 API endpoints in `education.py` with canonical `"autoreiv"`.
  - **Routines Studio Fallback**: Replaced obsolete `'system-agent'` fallback in `routines.js` with active selection fallback to `'autoreiv'`.
  - **Negative Assertion Regression Suite**: Added `test_canonical_agent_resolution_383.py` ensuring zero duplicate alias dictionaries or legacy tuple checks can recur.

### Added

- Desktop Canvas Multi-Window Layout Presets, Custom Layout Pinning, and Sticky Auto-Restore (`src/web/static/modules/ui/agent-desktop.js`, `src/web/templates/index.html` [CARD-279]):
  - **Canvas Presets Geometry Engine**: Implemented pure layout math for 3-window configurations (Left Stacked 50/50 + Right Full 100%, and Left Full 100% + Right Stacked 50/50), 2-column equal split (50/50), and 3-column equal split (33/33/33), complete with grid alignment and dock height clearance.
  - **Organize Menu Redesign**: Upgraded the desktop dock Organize menu (`#desktopOrganizeMenu`) from a flat 6-button list into categorized sections: Canvas Presets, Window Actions, and Saved Layouts.
  - **Custom Layout Pinning & Saving**: Added interactive "Save Current Layout..." prompt to capture open studios, window geometries (`x, y, w, h`), and stacking order into named presets stored in `localStorage[autoreiv_desktop_prefs_v1]`.
  - **Preset Loading & Deletion**: One-click preset activation automatically closes/parks non-member windows and sizes/positions member windows; individual presets can be deleted directly from the Organize menu.
  - **Session Sticky Auto-Restore**: Preserves open studio windows and coordinates across browser reloads when `autoRestore` is active on desktop viewports (>=768px). Mobile layouts (<768px) remain strictly single-window.


## [0.37.0] - 2026-09-19

### Added

- Dogfooding Telemetry Friction & God Agent Threshold Detectors (`tests/integration/observability/test_dogfood_architectural_governance.py` [CARD-375]):
  - Authored comprehensive end-to-end integration test validating the closed-loop architectural governance lifecycle across all 5 God-Agent thresholds: Tool Bloat (>8 tools), Context Tax (>4000 characters), Lifecycle Mismatch (unattended polling loops), Security Boundary Collision (untrusted ingestion + mutating tools without HITL), and Cognitive Conflict (mutations without verification).
  - Validated on-demand scanning (`POST /api/observability/architectural/scan`), typed alert filtering, proposal generation (`POST /api/observability/architectural/proposals/generate`), one-click background Routine promotion (`POST /api/observability/architectural/proposals/{id}/apply`), and proposal dismissal (`POST /api/observability/architectural/proposals/{id}/dismiss`).
  - Idempotent re-scanning and deduplication with checkout boundary hygiene verification.

### Changed

- Enhanced Work Card Query & Inspection Skill (`.agents/skills/card-status/`, `.agents/skills/sdd-workflow/`):
  - Token-Efficient Default Filtering (`list_card_status.py`): Defaults to displaying only active/actionable cards (`Ready`, `In Review`, `In Progress`) rather than dumping hundreds of historical `Done` cards into conversation context, reducing default output from ~400 lines to ~10 lines.
  - Granular Search & Inspection Modes: Added `--search` / `-q` (search across titles, IDs, labels, ADRs, intent), `--label` / `--tag`, `--recent [N]` / `--latest [N]` (latest worked cards), `--card <ID>` (single-card detail inspector), `--parked`, and `--done`.
  - Native YAML Frontmatter & Markdown Blockquote Support (`list_card_status.py`, `new_card.py`): Fully parses both YAML frontmatter and standard blockquotes, and upgraded `new_card.py` to generate structured YAML frontmatter alongside the Four Beats template.
  - Automated Skill Test Suite (`tests/unit/skills/test_list_card_status.py`): Added unit test verifying parsing, granular searching, filtering, and inspector modes.

### Fixed

- Per-Agent Provider Model Resolution & Platform Leakage (`src/application/kernel/agent_kernel.py` [CARD-214]):
  - Resolved cascade defect in `_resolve_model()` where an agent configured with an explicit provider (e.g. `ollama`) and model `default` fell through to the platform provider (e.g. Gemini).
  - Enforced 2-tier resolution: explicit agent provider settings route strictly to that provider (using provider-configured defaults or adapter defaults), while agents with `provider="default"` cleanly inherit system defaults from Settings Studio.
- Transparent Rate Limit & Quota Exhaustion Surfacing Across All Providers (`src/application/kernel/agent_kernel.py`, `src/infrastructure/gateway/` [CARD-214]):
  - Caught `RateLimitError` during streaming and non-streaming turns across all providers, formatted a plain-language notification in chat, and persisted it into session message history without crashing or triggering hidden model swaps.
  - Added `is_permanent_quota_exhaustion()` to `openai_adapter.py`, `openai_stream_tool_calls.py`, and `anthropic_adapter.py`, immediately failing fast on HTTP 429 quota exhaustion (`RESOURCE_EXHAUSTED`, `Quota exceeded`) instead of hanging in futile 14-second backoff sleep loops.
- Dynamic Credential Vault Loading on Server Boot (`src/web/app.py` [CARD-214]):
  - Updated LLM gateway startup loop to respect custom `vault_cred_id` fields configured in provider settings rather than hardcoding `llm-provider-{p_id}`.
- Architectural Proposal Deduplication for Dismissed Proposals (`src/application/observability/architectural_proposals.py` [CARD-375]):
  - Fixed proposal generator to include `ArchitecturalProposalStatus.DISMISSED` in `existing_keys`, preventing previously dismissed proposals from continually respawning on subsequent background scans.

## [0.36.0] - 2026-09-19

### Added

- Developer Audit Skills Suite (`.agents/skills/`):
  - `lifecycle-audit` (`.agents/skills/lifecycle-audit/SKILL.md`): Protocol for auditing state mutation, database persistence, and post-reboot survival to prevent factory re-seeding clobbering user customizations.
  - `boundary-audit` (`.agents/skills/boundary-audit/SKILL.md`, `scripts/boundary_check.py`): Automated scanner and verification checklist to ensure zero runtime databases, live packs, or wiki folders leak into the git checkout outside `scratch/`, flagging un-resolved relative `data/` paths.
  - `single-lever-audit` (`.agents/skills/single-lever-audit/SKILL.md`): Protocol for auditing duplicate DOM listeners, competing REST endpoints, and shadow functions to enforce the Single Lever Invariant.
  - `regression-sentinel` (`.agents/skills/regression-sentinel/SKILL.md`): Standardized protocol for authoring negative assertion unit/integration tests to permanently lock fixed defects against recurrence.
- Work Cards Scaffolded:
  - `CARD-381`: Preserve Platform Pack MCP Tools Across Server Reststarts (`docs/cards/CARD-381-preserve-platform-pack-mcp-tools-across-server-restarts.md`).
  - `CARD-382`: Hardened WikiStore Data Resolver and Checkout Working-Tree Hygiene (`docs/cards/CARD-382-hardened-wikistore-data-resolver-and-checkout-working-tree-hygiene.md`).

### Changed

- Developer Skill Consolidation & RTM-Sync Retirement:
  - Retired Obsolete `rtm-sync` Skill: Completely removed `.agents/skills/rtm-sync/`, moved `verify_rtm.py` to `docs/archive_artifacts/scripts/verify_rtm.py`.
  - Unified Preflight Script Relocation (`package.json`, `.agents/skills/preflight/`): Relocated `preflight.py` to `.agents/skills/preflight/scripts/preflight.py` and updated `npm run preflight` script in `package.json`.
  - TDD Cycle Modernization (`.agents/skills/tdd-cycle/SKILL.md`): Replaced legacy references to `tasks.md` and `[REQ-xxx]` with active work cards (`docs/cards/CARD-xxx.md`), EARS criteria, and card checklist verification.
- Retirement and Archival of 3-File Feature Specs and Requirements Traceability Matrix (RTM):
  - Spec & RTM Archival (`docs/archive_artifacts/`): Relocated all historical 3-file specifications (`docs/specs/` -> `docs/archive_artifacts/specs/`) and machine-readable RTM files (`docs/rtm.json`, `docs/rtm.schema.json` -> `docs/archive_artifacts/`) to preserve history while cleanly eliminating active maintenance friction.
  - Pragmatic Triad Architecture (`AGENTS.md`, `steering/structure.md`, `steering/tech.md`): Formally adopted the Pragmatic TriadΓÇöLiving Steering (`steering/`), Active Work Cards (`docs/cards/CARD-xxx.md`), and Architecture Decisions (`docs/adr/`) backed by automated tests and git history.
  - Unified Preflight Gate Decoupling (`.agents/skills/rtm-sync/scripts/preflight.py`, `package.json`, `.agents/skills/preflight/SKILL.md`): Decoupled the unified preflight quality runner (`npm run preflight`) from RTM schema and file checking, running pure static, unit, integration, honesty smoke, and browser smoke gates.
  - SDD & Intake Modernization (`.agents/skills/sdd-workflow/`, `.agents/rules/sdd-ears.md`): Pruned `new_spec.py` and updated `new_card.py` and `sdd-workflow` to operate exclusively on the single work card contract with Four Beats, EARS acceptance criteria, and Socratic discovery.
  - Governance & Issue Templates (`.agents/rules/`, `.github/`): Updated `architecture.md`, `definition-of-done.md`, `git-workflow.md`, `card.yml`, `story.yml`, `bug.yml`, and `PULL_REQUEST_TEMPLATE.md` to reference the Card and ADRs rather than retired specs.
- Agentic Governance & Code Hygiene Modernization:
  - Four Beats Protocol (`AGENTS.md`, `.agents/rules/human-engagement.md`): Upgraded the Three Beats to Four Beats by introducing Beat 4 ("What dies today / The Prune List"), requiring every refactor and feature change to explicitly declare and eliminate superseded code, obsolete variables, and dead flags before code generation.
  - Code Hygiene, Anti-Duplication & Single Lever Invariant (`.agents/rules/code-hygiene-and-pruning.md`): Introduced a hard invariant that every user capability, UI interaction, or internal state machine transition must have exactly one canonical code path (zero duplicate functions, shadow listeners, or dual entry points).
  - Test-Locked Delivery Standard (`AGENTS.md`, `.agents/rules/tdd-invariants.md`, `.agents/rules/definition-of-done.md`): Replaced dogmatic TDD red-phase commits with outcome-driven Test-Locked Delivery, permitting exploratory root-cause analysis while strictly requiring passing unit, integration, and Playwright tests with negative regression guards before any slice can move to review.
  - Retired Active RTM Maintenance Barrier (`AGENTS.md`, `.agents/rules/definition-of-done.md`, `.agents/rules/sdd-ears.md`): Retired mandatory `docs/rtm.json` editing and verification on routine cards, replacing high-friction JSON maintenance with Card-level acceptance criteria, automated test suites, and git traceability.
  - Scavenger Pass & Monolith Decomposition (`.agents/rules/code-hygiene-and-pruning.md`, `.agents/rules/definition-of-done.md`): Enforced post-green caller audits via ripgrep to ensure zero orphaned symbols remain, and added guidelines to decompose monolithic studio files exceeding 800 lines into focused submodules.
  - Rules Streamlining & Brand Neutrality (`AGENTS.md`, `.agents/rules/`): Streamlined governance and rules files by removing vendor/brand name references in favor of universal roles, harmonizing the Git commit cadence with Test-Locked Delivery, establishing a clear two-tier Card-First vs Spec-First hierarchy in `sdd-ears.md`, de-duplicating frontend verification into the canonical DoD gate, and replacing conversational essays in `ui-ux-design.md` with an actionable Diagnostic Gate.
  - Markdown & YAML Frontmatter Linting Pass (`AGENTS.md`, `.agents/rules/`, `.agents/skills/`): Fixed invalid YAML frontmatter across rule files, eliminated unanchored text before main headings, resolved code-block and list spacing issues, and ran Prettier formatting across all 21 rules and skills to achieve 0 markdown mistakes and 0 linter warnings.

### Fixed

- CARD-382: Hardened WikiStore Data Resolver and Checkout Working-Tree Hygiene ΓÇö Eliminated stray runtime checkout directories (`00_Inbox`, `01_Notes`, `03_Archive`), defaulted WikiStore and related tools to the canonical platform user-data root, and enforced checkout boundary protections:
  - Canonical Data Resolver Default (`src/domain/wiki/store.py`, `src/application/skills/wiki_tools.py`, `src/application/wiki/service.py`, `src/application/skills/weekly_notes_tools.py`): Updated `WikiStore`, `WikiTools`, `WeeklyNotesTools`, and `WikiService` constructors to accept `None` for root paths, resolving dynamically via `DataDirResolver().resolve().wiki_path` instead of relative `"data/wiki"`.
  - Working-Tree Checkout Boundary Enforcement (`src/domain/wiki/store.py`): Enforced `ensure_live_data_root()` on the resolved wiki root directory during store initialization and scaffolding, refusing live paths placed directly inside the git checkout root.
  - Checkout Hygiene Cleanup & Audit Lock (`tests/unit/wiki/test_wiki_checkout_hygiene.py`, `.agents/skills/boundary-audit/scripts/boundary_check.py`): Pruned stray `00_Inbox/`, `01_Notes/`, and `03_Archive/` directories from the repository root, added automated regression tests ensuring default store operations never pollute the checkout, and verified `boundary_check.py` clean working tree with 0 file leaks.
- CARD-381: Preserve Platform Pack MCP Tools Across Server Restarts ΓÇö Fixed platform pack boot reconciliation wiping operator-granted MCP and custom tools, ensured non-destructive pack.json updates, and synchronized user pack configurations:
  - Non-Destructive Boot Reconciliation (`src/infrastructure/skills/platform_packs.py`): Updated `install_platform_agent_packs()` to union new factory platform tools into `allowed_tool_names` while preserving operator-added MCP and custom tool selections, and updated live user `pack.json` in-place rather than unconditionally overwriting with repo factory seeds.
  - User Pack & Override Synchronization (`src/web/routers/agents.py`): In `PUT /api/agents/{agent_id}`, synchronized operator tool selections and configurations to `$DATA_DIR/packs/{agent_id}/pack.json` and mirrored customizations into SQLite `agent_overrides`.
  - Dynamic MCP Tool Guardrail Exemption (`src/domain/agents/guardrails.py`): Permitted dynamic `mcp_*` tools during profile validation even when external MCP servers are unmounted or offline.
- CARD-380: Fix Chat Stream Bubble Removal and Preserve Error State ΓÇö Resolved chat stream bubble disappearing during turns, ensured backend stream errors persist to SQLite, and protected error states in the chat thread:
  - Stream Bubble Immunity (`src/web/static/modules/studios/chat.js`): In `paintInlineJobChrome()` and `resetInlineJobChrome()`, added checks for `data-stream-bubble="true"`. When non-multiphase ambient events (such as `react_state: "THINKING"`) arrive, embedded `.job-chrome-phases` are hidden rather than removing the entire active assistant stream container from the DOM [REQ-CHAT-017].
  - Backend Unhandled Stream Error Persistence (`src/web/routers/chat.py`): Enhanced the `worker()` exception handler in `chat_stream` to record an honest assistant error message (`store.save_message(ChatMessage(role=Role.ASSISTANT, content=f"ΓÜá∩╕Å **Error**: {e}"))`) before sending SSE error events, ensuring errors survive stream interruptions and thread reloads [REQ-CHAT-018].
  - Stream Failure UI Protection (`src/web/static/modules/studios/chat.js`): Tracked stream errors via `hasStreamError` and guarded `loadMessages()` in `executeChatTurn()`'s `finally` block to ensure that failed turns without saved responses retain their rendered error banner instead of being wiped to a blank screen [REQ-CHAT-019].
  - Reasoning Drawer Live Duration (`src/web/static/modules/studios/chat.js`): Ensured `event: reasoning` streaming properly reveals the thought drawer and increments elapsed thinking duration in real time [REQ-CHAT-020].
  - Cache Busted App Asset (`src/web/templates/index.html`): Bumped `app.js?v=2.0.80` to `app.js?v=2.0.81`.
- CARD-379: Bump LLM Gateway Adapter Read Timeout to 200s for Cold Starts ΓÇö Increased default HTTP client read timeout from 60.0s to 200.0s across `OpenAIProviderAdapter` and `AnthropicProviderAdapter`, updated `GATEWAY_DEFAULT_TIMEOUT_SECONDS` in `factory.py` to 200.0s, and ensured dynamic provider registration inherits the 200s runway. Prevents premature HTTP client timeout errors when local GPU nodes (such as the Spark host) require 70+ seconds for cold-start weights loading and dynamic model swapping.
- CARD-378: Multi-Phase Stream Chrome Deduplication and Prior Phase Deliverable Preservation ΓÇö Fixed chat streaming duplicate bubble rendering, preserved prior phase deliverables across failures and stream reloads, pruned stale developer specialist routing, and gated branching option plans for operator selection:
  - Pruned Stale Specialist Routing (`src/application/orchestration/job_phase_orchestrator.py`): Removed legacy hardcoded routing of coding capabilities to the retired `developer` agent, defaulting execution phases to `default_agent_id` or `autoreiv` and eliminating 5-minute timeouts against obsolete Ollama endpoints [REQ-ORCH-044].
  - Prior Deliverable Preservation (`src/web/routers/chat.py`): Enhanced `execute_goal_job_phases()` to track and accumulate `completed_deliverables`. When subsequent phases fail or park, earlier deliverables (e.g. Formulate plans) are combined with the phase status summary and persisted into `store.save_message()`, ensuring `loadMessages()` preserves the user's plan [REQ-CHAT-016].
  - Interactive Option Park Gating (`src/web/routers/chat.py`): Added `is_plan_awaiting_operator_choice()` to detect multi-branch plans (Option A vs Option B) generated during Formulate. When detected, the job parks with status `waiting_approval` instead of blindly executing an unchosen option [REQ-ORCH-045].
  - Stream Bubble Deduplication (`src/web/static/modules/studios/chat.js`): Added `data-stream-bubble="true"` and embedded `.job-chrome-phases` inside `streamBubble`. Updated `ensureInlineJobChromeBubble()` and `paintInlineJobChrome()` to reuse the active stream bubble, eliminating duplicate bubbles and duplicate streaming headers during multi-phase runs [REQ-CHAT-015].
  - Clean Truncated Milestone Goal Headers (`src/web/static/modules/studios/chat.js`): Introduced `formatMilestoneGoalTitle()` to sanitize raw attachment file paths and truncate goal headers to at most 80 characters with an ellipsis [REQ-CHAT-015].
  - Cache Busted App Asset (`src/web/templates/index.html`): Bumped `app.js?v=2.0.79` to `app.js?v=2.0.80`.
- CARD-372: Dogfood Overnight Skill Improvement Harvest Routine ΓÇö Validated and hardened the end-to-end overnight skill improvement loop (`skill-eval-sleep`) across the full harvest, mining, gating, proposal draft, operator approval, runbook update, and snapshot rollback lifecycle:
  - Preserved Pack Frontmatter & Appended Learnings: Enhanced `commit_skill_pack` (`src/application/orchestration/skill_proposals.py`) for `ace_delta` proposals targeting existing packs to preserve the pack's canonical name, description, and existing instructions, cleanly appending operational learnings under `## Operational Learnings` without corrupting YAML frontmatter or erasing declared tools.
  - End-to-End Integration Dogfooding Suite: Created `tests/integration/routines/test_dogfood_skill_eval_sleep.py` validating synthetic telemetry harvest within the 72h lookback window, gap clustering into bounded insights ($\le 400$ chars), safety gate enforcement (`harvest_gate` failing closed on python source rewrites and missing pack IDs), uncommitted draft creation in SQLite with pre-change snapshot, operator approval, clean SKILL.md update passing `CapabilityLinter`, and bit-for-bit snapshot restoration via `catalog.rollback_pack`.
- CARD-376: Audit and Clean Platform Skills and Tools ΓÇö Conducted systematic audit of all platform skills and registered tools, pruning dead and vestigial tools, fixing YAML syntax validation, and consolidating duplicate runbook aliases:
  - Pruned Dead Tools & Unhooked Modules: Deleted unreferenced `src/application/skills/opentofu_tools.py` (509 lines). Removed legacy unhooked tools `check_port` and `manage_opentofu_hyperv` from `src/application/skills/manifest.py`. Unregistered retired fleet delegation tools `delegate_to_fleet_agent` and `lookup_homelab_docs` from `ScopedToolRegistry`, `manifest.py`, and `PLATFORM_SKILL_TOOLS["coordination"]`.
  - Skill Runbook Hygiene & YAML Syntax Validation: Fixed YAML syntax error in `platform-packs/autoreiv/skills/agent-authoring/SKILL.md` (quoted description containing unescaped colon). Fixed missing `## Done-when` verification contract in `src/infrastructure/skills/seeds/wiki-templates/SKILL.md`. Enhanced `CapabilityLinter` (`src/application/skills/linter.py`) with `SYN-001` error emission on YAML parsing failures so invalid frontmatter cannot silently pass validation.
  - Consolidated Tool Runbook Aliases: Streamlined `platform-packs/autoreiv/skills/wiki-templates/SKILL.md` and seed to reference the 4 canonical tools (`wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update`), eliminating duplicate alias clutter.
  - Automated Tool & Skill Audit Suite: Added `tests/unit/skills/test_tool_and_skill_audit.py` to assert that all 88 active registered tools have valid schemas/callables, all manifest and platform skill tools are registered, pruned tools remain barred from the registry, and all platform and seed skills pass `CapabilityLinter` with zero errors.
- CARD-371: Routines Studio Delete Routine 404 Disambiguation ΓÇö Disambiguated failure cases in Routines Studio deletion (`src/web/routers/routines.py`):
  - Honest 404 on Missing Routine: Added pre-deletion existence check in `DELETE /api/routines/{routine_id}` via `store.get_routine(routine_id)`, returning HTTP 404 Not Found instead of generic HTTP 400 Bad Request when the target routine does not exist.
  - Automated Regression Tests: Updated `tests/unit/web/test_routine_management_api.py` to assert HTTP 404 with "not found" detail when attempting to delete nonexistent routines.
- CARD-370: Factory Studio Phase Instructions State Resolution and Step Job 404 Honesty ΓÇö Fixed two API reliability and contract honesty issues in Factory Studio (`src/web/routers/agent_training_factory.py`):
  - State Database Path Resolution: Resolved `paths = getattr(request.app.state, "data_dir_paths", None)` (with fallback to `request.app.state.store.db_path`) in `list_phase_instructions`, `update_phase_instruction`, and `delete_phase_instruction`, eliminating unhandled HTTP 500 errors caused by querying the nonexistent `data_paths` state attribute.
  - Nonexistent Step Job Contract Honesty: Added verification check in `POST /api/agent_training_factory/jobs/{job_id}/step` to query the job repository prior to stepping, returning HTTP 404 Not Found instead of false HTTP 200 OK with null job when the job does not exist.
  - Automated Regression Tests: Added unit tests in `tests/unit/web/test_agent_training_factory_router.py` verifying successful phase instruction customization, reset, and 404 rejection on nonexistent job stepping.

### Added

- CARD-377: MCP Lifecycle Handshake, Standard Client Compliance & Dynamic Demand Paging ΓÇö Implemented standard Model Context Protocol (MCP) initialization handshake, unified transport parity, and dynamic capability demand paging for MCP tool families:
  - Protocol Lifecycle Handshake (`src/infrastructure/mcp/client_adapter.py`): Implemented mandatory `initialize` handshake with `protocolVersion: "2024-11-05"`, `capabilities`, and `clientInfo`, followed by `notifications/initialized` before subsequent JSON-RPC requests (`tools/list`, `tools/call`), compliant with standard FastMCP and Blender Lab MCP servers.
  - Fallback Tolerance (`src/infrastructure/mcp/client_adapter.py`): Added error tolerance for legacy or simple servers rejecting `initialize`, preserving graceful tool discovery without connection termination.
  - Global Settings Studio Parity (`src/web/routers/settings.py`, `src/web/templates/index.html`, `src/web/static/modules/studios/settings.js`): Added transport selector (`stdio` vs `HTTP / SSE`), remote URL, and custom header inputs to Global Settings Studio's Add MCP Server form, passing transport parameters to `mcp_manager.mount_server` and `MCPClientAdapter`.
  - Dynamic System Message Capability Index (`src/application/kernel/agent_kernel.py`): Replaced the static 4-item capability list with dynamic capability discovery that lists all mounted MCP servers (e.g. `blender` with 26 tools) and instructions to use `activate_skill` or query directly.
  - Fast-Path Intent Matching & Demand-Paged Skill Activation (`src/application/kernel/agent_kernel.py`, `src/application/skills/platform_primitives.py`): Enabled Layer 1 fast-path intent matching for active MCP server names, and enhanced `activate_skill()` to recognize and mount external MCP tool families (e.g. `activate_skill(["blender"])`).
  - Scoping & Rule of 7 Intelligent Prioritization (`src/application/kernel/tool_registry.py`, `src/application/kernel/agent_kernel.py`): Authorized active MCP skills on `autoreiv` and custom specialist agents, prioritizing query-relevant tools within the 8-tool entropy budget ceiling.
  - Agent Forge Studio Bulk Selection (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`): Added functional "Select All" and "Clear All" action buttons in both the section header and the search filter toolbar, disambiguating DOM element IDs, reliably filtering visible `.forge-tool-card:not(.hidden)`, programmatically dispatching `change` events, and presenting feedback toasts on selection counts.
  - Automated & Live Verification: Added `tests/unit/mcp/test_mcp_client_handshake.py`, `tests/unit/kernel/test_mcp_demand_paging.py`, and `tests/integration/test_settings_mcp_endpoints.py`, and verified live tool discovery and execution with the Blender MCP server.
- CARD-374: Dogfood Capability Gap Closed Loop Lifecycle ΓÇö Implemented an end-to-end integration dogfooding suite (`tests/integration/capabilities/test_dogfood_capability_gap_loop.py`) verifying the complete capability gap journey from turn-time detection to Factory promotion:
  - Kernel Gap Capture: Updated `AgentKernel.run_turn` and `run_stream` to pass session context (`session_id`) into `capability_gap_repo.create_gap` upon missing tool detection, persisting structured gaps to SQLite.
  - Backlog Surfacing & API Exposure: Added `GET /api/agent_training_factory/gaps` in `src/web/routers/agent_training_factory.py` to complement `GET /api/agents/gaps`, surfacing pending backlog items with agent ID, session ID, turn text, and suggested tool names.
  - Job Seeding with Gap Association: Added `capability_gap_id` to `CreateFactoryJobRequest` in `POST /api/agent_training_factory/jobs`, automatically encoding the gap objective (`gap_id=<id>`) and transitioning gap status from `pending` to `training`.
  - Promotion & Resolution Sync: Verified that `_sync_linked_gap_status` transitions the linked gap to `trained` upon operator approval, writes the pack to user data `packs/<slug>/`, registers the custom agent in `BuiltinAgentRegistry`, and removes the item from pending backlog views.
  - Honest Rejection & Cant Handling: Validated that promotion rejection transitions gap status to `failed`, unverified promotion attempts (zero sandbox files) fail with HTTP 422 transitioning gap status to `cant`, and dismissal deletes or marks the gap `dismissed`.
- CARD-373: Dogfood Factory Eight Phase Tool Training Pipeline ΓÇö Implemented an end-to-end integration dogfooding suite (`tests/integration/factory/test_dogfood_factory_pipeline.py`) validating the full 8-phase tool creation pipeline (`intent_distill` -> `ground` -> `blueprint` -> `author` -> `scenario_verify` -> `verify` -> `optimize` -> `promote`):
  - Multi-Phase Integration Validation: Verified that a realistic capability training job advances sequentially across all 8 phases, generating clean Python tool modules and Matt Pocock compliant `SKILL.md` runbooks adhering to standard frontmatter and deterministic verification contracts (`## Done-when`).
  - AST Verification & Syntax Error Catching: Validated that `VerifyPhase` AST inspection and sandbox battery catch syntax errors before promotion, properly triggering rinse cycles back to `author`.
  - Tool Collision Guard & Deduplication: Fixed `PromotePhase` tool deduplication across historical packets and validated that collision detection catches duplicate callable names and conflicts against existing disk packs, rejecting unauthorized overwrites with HTTP 409 while permitting approved replacements.
  - User-Data Isolation & Registry Dynamic Loading: Verified that `UserPackFinalizer` writes promoted agent packs exclusively to user-data `packs/<slug>/` with zero checkout tree pollution, tags promoted profiles with `origin="custom"`, and guarantees dynamic discovery and execution by `BuiltinAgentRegistry` and `AgentKernel`.
- CARD-369: Audit and Prune Dead UI Controls and Vestiges Across Studios ΓÇö Systematically audited all 11 studios and the outer shell, pruning unhooked dialogs, obsolete navigation rails, and misleading controls left behind after architectural evolutions:
  - Pruned Dead Mermaid Zoom Inspector Modal (`src/web/templates/index.html`, `src/web/static/app.js`, `src/web/static/modules/ui/modal.js`, `src/web/static/modules/studios/chat.js`): Removed 65 lines of unimplemented modal DOM (`#mermaidZoomModal` and child zoom/fullscreen buttons), removed its registration in `allModals` and close selectors, and eliminated misleading "Inspect & Zoom" overlay buttons from rendered Mermaid diagrams in Chat Studio, replacing them with clean inline diagrams and responsive horizontal overflow.
  - Pruned Superseded Pre-Desktop Navigation Rail (`src/web/templates/index.html`, `src/web/static/app.js`): Removed `<nav id="appRail">` and child buttons (`#railBtnChat`, `#railBtnVault`, `#railBtnFleet`, `#railBtnFactory`, `#railBtnSettings`) previously suppressed by CSS since the Agent Desktop dock (`#dockBar`) became primary navigation. Cleaned up `railBtns` and `updateRailSurfaces` from `app.js`.
  - Pruned Orphaned Desktop Sidebar Positioning (`src/web/static/modules/ui/agent-desktop.js`): Deleted obsolete coordinate calculation code for `#sidebar` from a nonexistent `sessions` window, preserving the in-studio `#chatSessionsDrawer` toggle.
  - Preserved All Active Studio Controls: Confirmed and preserved all 167 input/select/textarea controls and active buttons (`#promptsEditorSaveBtn`, `#saveToneBtn`, `#educationAmpWatchLuminaBtn`, `#wikiMobileDrawerBtn`).
  - Traceability & Verification: Added comprehensive frontend test suite `tests/unit/frontend/dom_audit.test.js` to lock in pruned state and prevent regressions; updated legacy tests in `workbench_shell.test.js` and `factory_studio.test.js`. All 7 preflight verification gates passed cleanly.
- CARD-368: Retire Autonomous Training Checkbox and In-Flight JIT Synthesis ΓÇö Pruned vestigial in-flight tool synthesis controls and streamlined capability gap routing to Factory Studio's backlog:
  - Agent Studio UI Pruning (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`): Removed `#forgeAutoTrainCheckbox` ("Allow Autonomous Training") and `#forgeMaxTrainRetriesInput` ("Max Auto-Train Retries") from Agent Studio while preserving the honest Agent Training Optimization backlog card.
  - Direct Capability Gap Factory Backlog Routing (`src/application/kernel/agent_kernel.py`): Simplified capability gap handling in `run_turn` and `stream_turn` so all missing capability detections route directly and reliably to `capability_gap_repo.create_gap` (surfacing in Factory Studio Backlog) without attempting unverified in-flight JIT tool code generation or emitting progress noise during live conversations.
  - Backward Compatibility Preservation (`src/domain/kernel/models.py`, `src/domain/settings/models.py`): Kept backward-compatible defaults on `AgentProfile` and `AgentCustomization` so existing database rows and schemas remain stable.
  - Traceability & Verification: Registered requirements `REQ-PRUNE-AUTO-001` through `REQ-PRUNE-AUTO-004` in `docs/rtm.json`. Updated frontend unit tests in `tests/unit/frontend/auto_train_backlog.test.js` and kernel tests in `tests/unit/kernel/test_in_flight_synthesis.py`.
- CARD-367: Declarative Agent Pack Lifecycle Reconciliation and Origin Tracking ΓÇö Permanently resolved stale agent artifacts, ghost pack resurrections, and origin ambiguity across disk and database:
  - Agent Origin Taxonomy (`src/domain/kernel/models.py`, `src/domain/settings/models.py`, `src/domain/agents/profiles.py`): Introduced typed `AgentOrigin` enum (`PLATFORM`, `SYSTEM`, `CUSTOM`) on `AgentProfile` (default: `CUSTOM`) and `AgentCustomization`. Tagged platform agents (`autoreiv`, `direct`) as `AgentOrigin.PLATFORM` and system agent (`agent-builder`) as `AgentOrigin.SYSTEM`.
  - Database Schema & Migrations (`src/infrastructure/memory/schema.py`, `src/infrastructure/memory/connection.py`, `src/infrastructure/memory/repositories/settings.py`): Added `origin TEXT NOT NULL DEFAULT 'custom'` to `custom_agents` and `agent_overrides` tables with seamless forward migrations. Updated settings repository to persist and load origin.
  - Declarative Pack Reconciler (`src/infrastructure/skills/reconciler.py`): Built `DeclarativePackReconciler` comparing desired `PLATFORM_PACK_IDS` against actual AppData state on boot. Automatically purges retired platform packs (`developer`, `tutor`, `forge`, `homelab`, `finance`) from both disk and SQLite custom agent tables, while strictly preserving user-created custom agents (`origin == AgentOrigin.CUSTOM`).
  - Ghost Import Loop Elimination (`src/infrastructure/skills/platform_packs.py`, `src/infrastructure/agents/registry.py`): Hooked reconciler into boot lifecycle and updated `install_platform_agent_packs()` so abandoned or retired directories are never re-imported as custom agents.
  - API Origin Surfacing & Deletion Protection (`src/web/routers/agents.py`, `src/web/static/modules/studios/forge.js`): Surfaced `origin` in `/api/agents` responses and guarded `DELETE /api/agents/{id}` to prevent accidental deletion of platform and system agents with HTTP 400. Updated Agent Studio to display origin-aware badges and disable delete controls for protected agents.
  - Traceability & Verification: Registered requirements `REQ-RECON-001` through `REQ-RECON-005` in `docs/rtm.json`. Added comprehensive unit tests in `tests/unit/agents/test_agent_origin_taxonomy.py`, `tests/unit/skills/test_declarative_pack_reconciler.py`, and `tests/unit/web/test_agent_origin_api.py`.
- CARD-366: Consolidate Personas into AutoReiv Skills and Purge Deprecated Profiles ΓÇö Consolidated specialized persona agents into modular skill runbooks and completed the transition to the Single-Brain / Autonomic OS model (ADR-0054):
  - Modular Skill Runbooks (`platform-packs/autoreiv/skills/`): Created `sdlc-engineering/SKILL.md` (absorbing `developer`), `agent-authoring/SKILL.md` (absorbing `forge`), and `socratic-tutoring/SKILL.md` (absorbing `tutor`). Enforced Rule of 7 tool budget ceilings (<= 6 tools each) and deterministic completion verification contracts.
  - Platform Seed Pack Consolidation (`platform-packs/`): Retired standalone seed packs `developer`, `forge`, and `tutor`. Restricted active `PLATFORM_PACK_IDS` to `("autoreiv", "direct")`. Added retired personas to `RETIRED_PLATFORM_PACK_IDS` and configured `cleanup_orphaned_platform_packs()` to cleanly remove legacy folders from user data on startup.
  - Transparent Legacy Agent Aliasing (`src/domain/agents/profiles.py`): Mapped `developer`, `tutor`, and `forge` in `LEGACY_AGENT_ALIASES` so any incoming requests or historic sessions automatically route to `autoreiv` Core.
  - Deprecated Profiles & Legacy Recipes Purge: Purged `HOMELAB_*` fleet profiles from `profiles.py`, deleted obsolete `homelab_domain_recipe.py` and `homelab_outcome_smoke.py`, and removed legacy `homelab` and `finance` integration/unit test suites.
  - Capability Linter Fix (`src/application/skills/linter.py`): Updated `resolve_data_dir` to `DataDirResolver().resolve().root` ensuring `autoreiv lint-skills` validates all platform skills cleanly.
  - Traceability & Verification: Registered requirements `REQ-CONSOL-001` through `REQ-CONSOL-006` in `docs/rtm.json`. Authored unit tests in `tests/unit/skills/test_skill_linter_consolidation.py` and `test_platform_packs_lifecycle.py`, with 100% green test suite across Python, ESLint, Vitest, and Playwright smoke gates.
- CARD-365: Architectural Proposal Inbox in Agent Forge Studio ΓÇö Closed the autonomic loop for ADR-0054 (Milestone 18), providing an interactive operator inbox and one-click execution engine for architectural evolutions:
  - Architectural Proposal Domain Models (`src/domain/observability/models.py`): Added `ArchitecturalProposalType` (`PROMOTION_ROUTINE`, `SKILL_DECOMPOSITION`, `TOOL_PRUNING`, `SECURITY_ISOLATION`, `CONTRACT_REINFORCEMENT`), `ArchitecturalProposalStatus` (`PENDING`, `APPLIED`, `DISMISSED`), and the `ArchitecturalProposal` domain model.
  - Autonomic Proposal Generator & Application Service (`src/application/observability/architectural_proposals.py`): Implemented `ArchitecturalProposalGenerator` and `ArchitecturalProposalService` synthesizing concrete proposals from God-Agent threshold alerts, maintaining a durable JSON ledger at `$DATA_DIR/telemetry/architectural_proposals.json`, and executing one-click remedies (e.g., registering scheduled daemon `Routine` models in SQLite database, reinforcing verification contracts, and pruning high-entropy tools).
  - REST API Endpoints (`src/web/routers/observability.py`): Added `GET /api/observability/architectural/proposals`, `POST /api/observability/architectural/proposals/generate`, `POST /api/observability/architectural/proposals/{id}/apply`, and `POST /api/observability/architectural/proposals/{id}/dismiss`.
  - Agent Studio UI (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`): Added the Architectural Governance & Proposal Inbox section (`#forgeArchitecturalSection`) in Agent Studio with dynamic card rendering, threshold tags, severity indicators, impact summaries, and interactive "Apply Remedy" and "Dismiss" buttons.
  - Observability Studio Cross-Linking (`src/web/templates/index.html`, `src/web/static/modules/studios/observability.js`): Added `#obsArchitecturalInboxBtn` header badge and deep navigation jumping directly to Agent Studio's Architectural Inbox.
  - Traceability & Verification: Registered requirements `REQ-ARCH-008` through `REQ-ARCH-014` in `docs/rtm.json`. Authored comprehensive unit tests across domain models, generator logic, application service execution, REST APIs, and Vitest frontend UI tests.
- CARD-364: Architectural Telemetry & Threshold Detectors ΓÇö Implemented runtime God-Agent threshold monitoring and architectural breach detection grounded in ADR-0054:
  - Architectural Domain Models (`src/domain/observability/models.py`): Defined `ArchitecturalThresholdType`, `ArchitecturalAlert`, and `ArchitecturalScanReport` representing runtime alerts across the 5 God-Agent thresholds (`TOOL_BLOAT`, `CONTEXT_TAX`, `SECURITY_COLLISION`, `LIFECYCLE_MISMATCH`, and `COGNITIVE_CONFLICT`).
  - Pure Domain Detector (`src/domain/observability/architectural_detector.py`): Implemented `ArchitecturalThresholdDetector` auditing telemetry spans and session message transcripts for tool entropy limit violations (>8 tools), prompt schema tax (>4,000 chars), untrusted input co-mingling with mutating host levers without HITL gating, chat sessions executing unattended automated polling loops (>5 automated turns), and mutations completed without mechanical verification.
  - Architectural Evaluator Service (`src/application/observability/architectural_evaluator.py`): Implemented `ArchitecturalEvaluatorService` to query historical sessions and spans, deduplicate alerts, calculate threshold breakdowns, and persist alert ledgers.
  - REST API Endpoints (`src/web/routers/observability.py`): Added `POST /api/observability/architectural/scan` for on-demand audits and `GET /api/observability/architectural/alerts` supporting severity and threshold filtering.
  - CLI Subcommand `autoreiv scan-architecture` (`src/cli/main.py`): Added `scan-architecture [--days N] [--json] [--strict]` displaying diagnostic summaries and machine-readable JSON reports.
  - Traceability & Verification: Registered requirements `REQ-ARCH-001` through `REQ-ARCH-007` in `docs/rtm.json`. Authored comprehensive unit tests in `tests/unit/observability/test_architectural_detector.py`, `test_architectural_evaluator.py`, and `test_architectural_api_and_cli.py`.
- CARD-363: Mechanical Capability Linter & Contract Compiler ΓÇö Established mechanical governance and static contract compilation for `SKILL.md` runbooks grounded in ADR-0054:
  - Skill Contract Domain Models (`src/domain/skills/contract.py`): Defined `SkillContract`, `VerificationContract`, `VerificationKind`, `SafetyContract`, `LintSeverity`, `LintViolation`, and `LintReport` models representing typed capability runbook contracts.
  - Mechanical Capability Linter & AST Compiler (`src/application/skills/linter.py`): Implemented `SkillContractCompiler` and `CapabilityLinter` enforcing rules: `CAP-001` (tool budget ceiling clamping `len(requires_tools) <= 6`), `CAP-002` (mandatory deterministic verification via `command`, `exit_code`, `assertion`, `file_exists`, or `## Done-when` section), `CAP-003` (security boundary collision guard preventing untrusted external inputs from pairing with mutating tools without `requires_hitl: true`), and `CAP-004` (runbook body length budget <= 8,000 characters).
  - CLI Subcommand `autoreiv lint-skills` (`src/cli/main.py`): Added `lint-skills [paths...]` supporting directory scanning, human-readable terminal summaries, machine-readable `--json` output, and `--strict` warning enforcement.
  - REST API Endpoint `POST /api/skills/lint` (`src/web/routers/skills.py`): Added endpoint returning structured validation verdicts, parsed contracts, and diagnostic violation lists for Agent Forge.
  - Shipped Seed Packs Refactored: Refactored platform seed runbooks across `platform-packs/` (`coding`, `diagnostics`, `tasks`, `wiki`, `wiki-templates`, `tutoring`) to ensure 100% compliance with 0 errors and 0 warnings.
  - Traceability & Verification: Registered requirements `REQ-CAP-LINT-001` through `REQ-CAP-LINT-005` in `docs/rtm.json`. Added comprehensive unit test suite in `tests/unit/skills/test_capability_linter.py` covering AST compilation, mechanical rules, platform seed compliance, CLI output formats, and REST validation.
- CARD-362: Demand-Paged Capability Engine & Progressive Tool Mounting ΓÇö Implemented demand-paged capabilities and Rule of 7 entropy budget capping grounded in ADR-0054:
  - Rule of 7 Entropy Budget Cap (`src/application/kernel/agent_kernel.py`): Enforced `MAX_ACTIVE_TOOLS_PER_TURN = 8` in `AgentKernel._resolve_active_tools()` across all agent profiles, clamping prompt payloads to at most 8 tool definitions. Implemented deterministic priority ranking preserving active skill tools first (Priority 0), baseline coordination tools second (Priority 1), and unactivated generic tools third (Priority 2).
  - Lean Baseline & Compact Capability Index (`src/application/kernel/agent_kernel.py`): AutoReiv Core defaults to 5 lean platform coordination primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`) and injects a compact 1-line capability index into system prompts (<500 tokens) pointing to on-demand skill activation.
  - Demand-Paged Dynamic Mounting & Phase Boundary Scoping (`src/application/kernel/agent_kernel.py`): Paged tools dynamically when skills are activated via intent matching or orchestrator phase checkpoints (`_matched_capability_ids_for_job`). Transitioning between phase boundaries automatically evicts out-of-scope tools from prior phases and mounts new phase tools.
  - Telemetry Overhead Tracking (`src/application/kernel/agent_kernel.py`): Enriched turn telemetry spans to measure and persist `active_tool_count` and `tool_schema_chars`, proving baseline pre-fill schema overhead reduction from 16k tokens to under 1,500 characters (~400 tokens).
  - Traceability & Verification: Registered requirements `REQ-CAP-PAGE-001` through `REQ-CAP-PAGE-005` in `docs/rtm.json`. Authored comprehensive unit test suite in `tests/unit/kernel/test_demand_paged_tools.py` and updated `tests/unit/kernel/test_resolve_active_tools.py`.
- CARD-361: Dual-Engine Front Door (AutoReiv Core & Direct Mode) ΓÇö Established a clean dual-engine front door in Chat Studio grounded in ADR-0054, retiring persona dropdowns and roundtable selectors:
  - Dual-Engine Front Door Controls (`src/web/templates/index.html`, `src/web/static/modules/studios/chat.js`): Replaced Chat Studio's top bar dropdown roster with a segmented front-door toggle (`#chatEngineSelector`) featuring `[ ΓÜí AutoReiv Core | ≡ƒÆ¼ Direct Mode ]` (`#engineBtnCore` and `#engineBtnDirect`). Synchronized state bidirectionally with `#agentSelect` to maintain full backward compatibility with automated Playwright end-to-end tests and unit tests.
  - Direct Mode Fast-Path Bypass (`src/web/routers/chat.py`): Added dedicated zero-overhead execution pass-through for turns submitted under Direct Mode (`agent_id == 'direct'`). Directly streams provider tokens with `tools=None` (zero tool schema prompt tax), completely bypassing `JobPhaseOrchestrator`, database job/phase record minting, and catalog capability resolution.
  - Core Orchestration Preservation: Preserved full state-machine orchestration (`JobPhaseOrchestrator`) for AutoReiv Core turns (`agent_id == 'autoreiv'`), including phase tracking, capability resolution, and verification gates.
  - Scoped Session Isolation & Chrome Suppression (`src/web/static/modules/studios/chat.js`, `src/web/static/modules/studios/chat/stream.js`): Filtered Chat Studio session drawer and agent rosters strictly to the active engine channel (`dualEngineAgentsVisibleInChat`), suppressed `#jobPhaseStatusStrip` and inline job chrome during Direct Mode, and updated active engine badges and stream bubbles.
  - Traceability & Verification: Registered requirements `REQ-CHAT-DUAL-001` through `REQ-CHAT-DUAL-005` in `docs/rtm.json`. Authored comprehensive unit tests in `tests/unit/web/test_chat_direct_mode.py` and `tests/unit/frontend/chat_dual_engine_front_door_361.test.js`.

## [0.35.0] - 2026-09-18

### Added

- CARD-354: Autonomous Telemetry Auditor: Overnight Skill Friction Detection & Runbook Optimizer Routine ΓÇö Built an autonomous background routine and interactive Observability Studio workbench that audits session traces for execution friction and proposes surgical `SKILL.md` runbook patches:
  - Telemetry Friction Analyzer (`src/domain/observability/friction_analyzer.py`): Pure domain service evaluating message transcripts and telemetry spans against three Day-1 friction heuristics: Redundant Verification loops (successful mutations immediately followed by read/list of the same entity), Payload Bloat (>8 KB output payloads), and Search Thrashing (3+ consecutive search tool calls in a turn without reading any item).
  - Tool Span Payload Byte Attribution (`src/application/kernel/agent_kernel.py`): Enriched tool telemetry spans to persist `payload_bytes` and tool call arguments in metadata for rapid trace auditing.
  - User-Data Tool-to-Skill Resolver (`src/domain/observability/tool_skill_resolver.py`): Maps offending tools to their user-data `SKILL.md` runbook path (`$DATA_DIR/packs/<agent_id>/skills/` or `$DATA_DIR/skills/`), strictly honoring checkout hygiene. Synthesizes surgical rules targeting `## Common Pitfalls & Forbidden Paths` or escalates missing tool pagination to Factory Studio. Provides safe patch application restricted to user-data bounds.
  - Autonomous Telemetry Auditor Routine (`src/application/routines/telemetry_friction_auditor.py`, `src/domain/routines/manifests.py`, `src/application/routines/executor.py`): Registered `telemetry-friction-auditor` (weekday 21:00 America/New_York, seeded paused by default to respect GPU load). Stages recommendations in SQLite `proposals` table (`auto_apply: false` default).
  - Observability Studio REST API & UI (`src/web/routers/observability.py`, `src/web/templates/index.html`, `src/web/static/modules/studios/observability.js`): Added `/api/observability/friction/audit`, `/recommendations`, `/apply`, and `/dismiss`. Added "Skill Friction & Runbook Recommendations" collapsible section in Observability Studio featuring lookback window selector, "Run Telemetry Audit" button, markdown diff preview, and 1-click Apply/Dismiss actions. Bumped frontend cache-buster to `app.js?v=2.0.76`.
  - Traceability & Verification: Comprehensive unit test suites across friction analyzer, tool-to-skill resolver, routine execution, API endpoints, and frontend integration.

### Fixed

- CARD-360: Prevent Duplicate Streaming Tile in Chat Studio ΓÇö Eliminated visual defect where Chat Studio rendered two identical streaming tiles on turn start:
  - Streaming Lifecycle Guard (`src/web/static/modules/studios/chat.js`): Added `shouldMountInlineJobChrome(model)` to verify whether `inlineJobChromeModel` contains active phases (`phaseOrder.length > 0`) or plan steps (`steps.length > 0`). Guarded `paintInlineJobChrome()` so it returns `null` and cleans up empty elements if called on ambient turn events (such as `react_state: "THINKING"`), ensuring single-turn runs display only the primary `streamBubble`.
  - Multiphase Preservation: Preserved automatic mounting of `[data-job-chrome="inline"]` for multi-phase standing jobs and formulated plans as soon as phases or steps are populated.
  - Cache Buster & Automated Test Proof: Bumped frontend cache-buster to `app.js?v=2.0.75`. Added unit tests in `tests/unit/frontend/chat_inline_chrome_guard_360.test.js` verifying the predicate and lifecycle guard against regressions.

## [0.34.0] - 2026-09-18

### Added

- CARD-359: Restore Developer Platform Agent to Chat and Studio Pickers ΓÇö Restored the `developer` platform agent to client-facing pickers across AutoReiv:
  - Chat Studio Agent Visibility (`src/web/static/modules/studios/chat.js`, `src/web/static/modules/studios/chat/stream.js`): Removed `developer` from `isAgentVisibleInChat` exclusion conditions, allowing Developer to be selected in `#agentSelect` and the `#trainAgentTargetSelect` modal.
  - Agent Forge Studio Roster (`src/web/static/modules/studios/forge.js`): Removed `developer` from the retired agent exclusion list in `isStudioAgentVisible`, allowing Developer to appear in `#forgeAgentSelect`.
  - Frontend Test Alignment: Updated `tests/unit/frontend/agent_packs.test.js` and `tests/unit/frontend/forge_agent_select.test.js` to assert `developer` is visible in Chat Studio and Agent Forge. Bumped frontend cache-buster to `app.js?v=2.0.73`.

- CARD-358: Persistent Skill Proposal Cards in Chat History ΓÇö Transformed distilled skill proposals into first-class, persistent artifacts in the conversation stream:
  - Model & Database Persistence (`src/domain/gateway/models.py`, `src/infrastructure/memory/repositories/sessions.py`): Added `Role.SKILL_PROPOSAL` (`"skill_proposal"`). Implemented `update_message` and `get_message` in `SessionRepositoryMixin` to allow updating message contents (e.g. `adoption_state: "adopted"`) in the SQLite database.
  - Distillation Service & Adoption Router Integration (`src/application/skills/distillation_service.py`, `src/web/routers/skills.py`): Updated `distill_turn` to save a `ChatMessage(role=Role.SKILL_PROPOSAL)` in the active session's transcript and return `message_id`. Updated `POST /api/skills/adopt` to update the persisted proposal record's `adoption_state` and `adopted_at` timestamp.
  - LLM Gateway Safety (`src/application/kernel/context_compactor.py`): Automatically filtered out `Role.SKILL_PROPOSAL` messages in `ContextCompactor.compact` so LLM provider completion requests (OpenAI, Ollama, Anthropic) never receive non-standard roles.
  - Chat Studio Stream Hydration (`src/web/static/modules/studios/chat.js`): Added native handling for `role === 'skill_proposal'` in `renderMessageItem(msg)`. Rendered interactive `.skill-proposal-card` elements during normal message loop hydration, preserving proposals across window focus, tab switching, and page reloads. Re-rendered adopted proposals with the persistent green receipt badge. Bumped frontend cache-buster to `app.js?v=2.0.72`.
  - Traceability & Verification: Registered `REQ-SKIL-015` and `REQ-SKIL-016` in `docs/rtm.json`. Added comprehensive automated tests in `tests/unit/skills/test_skill_proposal_persistence.py`, `tests/unit/web/test_skills_distill_router.py`, and `tests/unit/frontend/skill_proposal_persistence_ui.test.js` (all 1,700+ Python tests and 543 frontend tests passing, full pre-flight verified).

- CARD-357: Homelab Admin Deepening and Multi-Capability Factory Evolution ΓÇö Evolved the Agent Training Factory into a multi-capability, non-destructive pack expansion engine and deepened `homelab-admin` with direct Hyper-V VM lifecycle and switch management:
  - Active Project Auto-Resolution (`src/application/skills/factory_dispatch_tools.py`): Enhanced `FactoryDispatchTools.launch_factory_training` to auto-resolve `target_directory` from the active workspace project or store settings when omitted by Forge or the operator (`REQ-FACT-070`).
  - Dynamic Script-Aware Tool Synthesis & Action Augmentation (`src/application/orchestration/tool_synthesizer.py`): Detected PowerShell Hyper-V driver scripts (`HyperVDriver.psm1`, `LabManager.ps1`) and unattend ISO generators (`New-UnattendIso.ps1`) in environment manifests. Synthesized discrete action handlers (`list_vms`, `start_vms`, `stop_vms`, `deploy_lab`, `destroy_lab`, `build_image`, `build_iso`, `test_prereqs`). When an existing tool exists on disk, preserved all previous valid actions (`tofu_plan`, `tofu_apply`, `ansible_playbook`, `checkpoint_lab`) and augmented the dispatcher with newly requested capabilities (`REQ-FACT-071`, `REQ-FACT-072`).
  - Author Phase Existing Code Grounding (`src/application/agent_training_factory/phases/author.py`): Grounded authoring prompts on existing tool implementations loaded from user data packs, passing `existing_tool_code` to the LLM and `ToolSynthesizer` to prevent capability regression (`REQ-FACT-072`).
  - Companion Skill Scaffolding (`src/application/agent_training_factory/phases/blueprint.py`): Formulated focused companion skill runbooks (e.g. `skills/hyperv-vm-lifecycle/SKILL.md`) when deepening existing packs with distinct operational capabilities, preventing destructive overwrite of prior skills like `manage-opentofu-hyperv` and registering both skills in `pack.json` (`REQ-FACT-073`).
  - End-to-End Certified Training & Live Smoke: Executed factory training run `fjob_aad9ceb8ea3d` for `homelab-admin` targeting `D:\Projects\Exprimentation\Homelab`, successfully passing all 8 phases (`intent_distill`, `ground`, `blueprint`, `author`, `scenario_verify`, `verify`, `optimize`, `promote`). Promoted pack to `%LOCALAPPDATA%\AutoReiv\packs\homelab-admin` with dual skills (`manage-opentofu-hyperv` and `hyperv-vm-lifecycle`), verified both old and new actions via dry-run and live execution.
  - Traceability & Test Coverage: Registered `REQ-FACT-070` through `REQ-FACT-073` in `docs/rtm.json`. Authored unit tests in `tests/unit/skills/test_factory_dispatch_tools.py`, `tests/unit/orchestration/test_tool_synthesizer.py`, `tests/unit/agent_training_factory/test_author_phase.py`, and `tests/unit/agent_training_factory/test_card186_pack_aware_blueprinting.py` (all 28 unit tests passing, full pre-flight verified).

- CARD-356: Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification ΓÇö Transformed the Agent Training Factory into a truly domain-agnostic, project-grounded capability manufacturing pipeline:
  - Domain-Agnostic Blueprint Synthesis (`src/application/agent_training_factory/phases/blueprint.py`, `src/application/orchestration/tool_synthesizer.py`): Grounded blueprints on discovered project assets (`tofu`, `ansible`, `powershell`). Guarded legacy Hyper-V single-concern overrides on `not has_grounded_project`, enabling project-tailored tools and skills. Synthesized 5-section Matt Pocock compliant `SKILL.md` runbooks and operational dispatcher tools.
  - Decoupled Resilient Authoring (`src/application/agent_training_factory/phases/author.py`): Decoupled authoring into two focused sequential LLM calls (Tool Call: max 2200 tokens, 120s; Skill Call: max 1500 tokens, 90s), eliminating 180s hangs caused by monolithic 3,500-token JSON generations. Added progress honesty error diagnostics to packets.
  - Universal Verification Battery Harmonization (`src/application/orchestration/verification_battery.py`, `src/application/agent_training_factory/phases/scenario_verify.py`): Harmonized heading acceptance (`## Overview` / `## Purpose`), relaxed rigid legacy Hyper-V single-concern whitelists when project-grounded, and separated fast status checks from long-running network TCP socket probes in synthesized tools so deterministic functional verification executes in milliseconds.
  - Traceability & Verification: Registered requirements `REQ-FACT-064` through `REQ-FACT-069` in `docs/rtm.json`. Added comprehensive unit test suites in `tests/unit/agent_training_factory/test_ground_phase.py`, `tests/unit/agent_training_factory/test_author_phase.py`, `tests/unit/orchestration/test_tool_synthesizer.py`, and `tests/unit/orchestration/test_verification_battery.py` (all 449 unit tests green, full pre-flight verified). Verified end-to-end live training run `fjob_989bb20516a6` for `homelab-admin` targeting `D:\Projects\Exprimentation\Homelab`, certifying and promoting pack to `%LOCALAPPDATA%\AutoReiv\packs\homelab-admin`.
- CARD-352: In-Situ Skill Workshop: /learn Distillation from Chat ΓÇö Implemented an in-situ skill distillation and adoption loop in Chat Studio that converts turn corrections into standardized `SKILL.md` runbooks or escalates tool gaps to Factory Studio:
  - Application Distillation Service (`src/application/skills/distillation_service.py`): Built `SkillDistillationService` to analyze conversation turns, diagnose procedural friction vs. missing native code tools (`needs_tool`), synthesize standardized Matt Pocock 5-section `SKILL.md` runbooks (<60 char description), and adopt skills directly into user data agent packs (`$DATA_DIR/packs/<agent>/skills/<slug>/SKILL.md`) with automatic `pack.json` synchronization and directory traversal guards.
  - Web API Endpoints (`src/web/routers/skills.py`): Added `POST /api/skills/distill` and `POST /api/skills/adopt` with Pydantic request/response validation (`DistillSkillRequest`, `AdoptSkillRequest`).
  - Chat Studio Teaching Trigger & Guidance Modal (`src/web/templates/index.html`, `src/web/static/modules/studios/chat.js`): Added `[ ≡ƒÆí Teach Agent ]` action button (`.msg-teach-agent-btn`) to assistant message action rows, lightweight modal (`#teachAgentModal`) with target agent pill and optional guidance input, and `/learn [guidance]` slash command handling in the chat composer.
  - Inline Skill Proposal Card (`src/web/static/modules/studios/chat.js`): Rendered interactive `.skill-proposal-card` inline in the active chat stream featuring plain-language summary (Observed Slip and Remedy), collapsible accordion preview of raw `SKILL.md`, one-click `[ Γ£à Adopt Skill to <Agent> ]`, and one-click `[ ≡ƒÜÇ Send to Factory Studio ]` pre-filling the Capability Intake Workbench when `needs_tool` is true. Bumped frontend cache-buster to `app.js?v=2.0.71`.
  - Traceability & Verification: Registered requirements `REQ-SKIL-010` through `REQ-SKIL-014` in `docs/rtm.json`. Added comprehensive unit test suites in `tests/unit/skills/test_skill_distillation_service.py`, `tests/unit/web/test_skills_distill_router.py`, and `tests/unit/frontend/skill_distillation_ui.test.js` (all 1671 Python tests and 538 frontend unit tests passing, full pre-flight verified).
- CARD-355: Forge Platform Specialist: Conversational Intake Partner for Factory Studio ΓÇö Provided a dedicated core platform specialist agent (**Forge**) in Chat Studio who acts as a conversational requirement discovery partner for Factory Studio:
  - Core Platform Specialist Pack (`platform-packs/forge/pack.json`): Authored Schema 1.1 platform pack definition for Forge (`id="forge"`, `avatar_icon="hammer"`, `tone="socratic"`, `purpose="reasoning"`). Configured with a rigorous Socratic capability-architect system prompt, domain boundaries prohibiting raw unverified file generation directly into packs, and an execution protocol for eliciting requirements, checking APIs, and selecting deliverable taxonomy. Seeded automatically into user data `$DATA_DIR/packs/forge/` on startup.
  - Platform Seeding Integration (`src/application/agent_packs/schema.py`, `src/infrastructure/skills/platform_packs.py`): Added `"forge"` to `PLATFORM_PACK_IDS` and `CHAT_SHOWN_BY_ID`.
  - Platform Capability Dispatch Tools (`src/application/skills/factory_dispatch_tools.py`, `src/infrastructure/agents/registry.py`): Implemented and registered `inspect_agent_pack` (inspects a target agent's identity, active tools, skills, and pack paths) and `launch_factory_training` (validates inputs, creates a `FactoryJob` and initial `WorkPacket`, and kicks the 8-phase factory runner tick).
  - Factory Studio On-Canvas Conversational Bridge (`src/web/templates/index.html`, `src/web/static/modules/studios/factory.js`, `src/web/static/app.js`): Added `#factoryIntakeTalkToForgeBtn` (`[ ≡ƒÆ¼ Talk it out with Forge ]`) to the Capability Intake Workbench. Clicking switches directly to Chat Studio, selects agent `forge`, and pre-seeds the prompt with the active target agent context. Bumped cache-buster to `app.js?v=2.0.70`.
  - Traceability & Automated Tests: Registered requirements `REQ-FACT-060` through `REQ-FACT-063` in `docs/rtm.json`. Authored unit tests in `tests/unit/skills/test_factory_dispatch_tools.py`, `tests/unit/agent_packs/test_card_126_platform_packs.py`, and `tests/unit/frontend/factory_studio.test.js`.
- CARD-351: Factory Studio: Intake & Training Steering Workbench ΓÇö Transformed Factory Studio from a developer-focused phase prompt editor into an operator-first Capability Intake & Training Steering Workbench:

  - Capability Intake Workbench Default Landing Canvas (`src/web/templates/index.html`, `src/web/static/modules/studios/factory.js`): Set `#factoryIntakeView` as the default landing view of Factory Studio. Rendered Target Agent Identity Card (`#factoryIntakeAgentCard`), Training Goal & Intent full-width textarea (`#factoryIntakeIntentInput`), Starter Objectives checklist (`#factoryIntakeObjectivesInput`), Reference Materials & Context attachment area (`#factoryIntakeContextInput`), and Deliverable Architecture selector (`#factoryIntakeDeliverableType`).
  - 3-Surface Sub-View Navigation: Reorganized Factory Studio header into 3 explicit tabs: `[ ≡ƒ¢á∩╕Å Capability Intake ]` (`#factoryTabIntakeBtn`), `[ ≡ƒôè Training Runs & Live Monitor ]` (`#factoryTabRunsBtn`), and `[ ΓÜÖ∩╕Å Pipeline Prompts ]` (`#factoryTabPipelineBtn`), relocating the 8-phase system prompt editor to the advanced Pipeline Prompts tab.
  - In-Page Direct Job Dispatch: Added prominent `[ ≡ƒÜÇ Launch Capability Manufacturing ]` button (`#factoryIntakeLaunchBtn`) that validates required inputs, dispatches `POST /api/agent_training_factory/jobs`, resets the form, and immediately switches to the live monitor tab tracking telemetry packets. Updated header `New Training Run` to switch to the intake workbench directly.
  - Backlog & Chat Friction Pre-Fill Bridge: Added `#factoryIntakePreFillSelect` dropdown to one-click populate Target Agent, Training Intent, and Starter Objectives directly from queued capability gaps.
  - Traceability & Verification: Registered `REQ-FACT-056` through `REQ-FACT-059` in `docs/rtm.json`. Added and passed unit test suite in `tests/unit/frontend/factory_studio.test.js` (89 test files / 531 frontend unit tests green, full preflight passing).

- CARD-350: Agent Forge: Decoupled Tools and Skills UI & Scoping ΓÇö Separated tools ("hands") and skills ("brain") into two distinct, full-width peer sections:
  - Allowed Skills ("Brain") Section (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`): Stacked full-width section containing Platform Skills and Custom Agent Pack Skills runbooks. Removed nested tool accordions (`.forge-skill-tools`, `.forge-skill-expand`). Added a subtle skill-to-tool helper affordance (`.forge-skill-recommend-tools-btn`) to quickly select recommended tools without coupling or locking.
  - Allowed Tools ("Hands") Section (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`): Stacked full-width section featuring an always-active locked chip badge group for the 4 mandatory platform primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `get_session_info`), real-time tool search filtering (`#forgeToolSearchInput`), Select All / Clear tool actions, and flat tool cards (`.forge-tool-card`) with independent permission checkboxes (`.forge-tool-checkbox`).
  - Decoupled Persistence: Removed legacy logic in `saveAgentBtn` that discarded checked tools if their parent skill was unchecked, ensuring tool permissions are persisted and enforced independently.
  - Traceability & Test Coverage: Registered `REQ-FORGE-010` in `docs/rtm.json` and added comprehensive unit test suite `tests/unit/frontend/forge_decoupled_tools_skills_350.test.js` (89 test files / 527 tests green).
- CARD-353: Wiki Search & Catalog Optimization (Metadata Filtering and Payload Trimming) ΓÇö Reduced LLM context bloat and enhanced search precision:
  - Trimmed `list_templates()` (`src/domain/wiki/store.py`): Stripped `content` and `raw_template` from default listing, dropping payload size from >50 KB to <2.5 KB (<315 bytes/template index).
  - Targeted Template Read (`src/domain/wiki/store.py`, `src/application/skills/wiki_tools.py`): Added `get_template()` and registered `wiki_template_read` (alias `get_wiki_template`) for retrieving full template contents on demand. Added to `PLATFORM_SKILL_TOOLS["wiki"]`, `DYNAMIC_SKILL_TOOLS["wiki"]`, and `autoreiv` pack manifest.
  - Focused Search with Structured Filters (`src/domain/wiki/store.py`, `src/application/skills/wiki_tools.py`): Extended `search_notes()` and `wiki_note_search` with structured filters (`tags`, `domain`, `topic`, `document_type`, `limit`). Search results return compact metadata summaries with truncated 200-char excerpts instead of full document bodies.
  - Runbook Anti-Pattern Guards (`platform-packs/autoreiv/skills/wiki-templates/SKILL.md`, seed runbook): Added explicit guidance prohibiting redundant verification turns after a successful template creation and guiding agents toward focused metadata queries.
  - Requirements & Test Coverage: Registered `REQ-WIKI-038` in `docs/rtm.json` and added unit test suite `tests/unit/wiki/test_card353_wiki_search_and_catalog_optimization.py` (13 passing tests, 58/58 wiki unit tests green).
- CARD-349: Wiki Templates Native Create Tool and Seed Runbook ΓÇö Implemented native tools and runbook for structured wiki note templates, resolving the issue where agents created templates under `notes/resources/`:
  - Domain Storage (`src/domain/wiki/store.py`): Added `create_template` and `update_template` methods to `WikiStore`. Enforces canonical storage under `02_Resources/_Templates/<slug>.md` (aliased as `resources/templates/<slug>.md`). `create_template` strictly fails closed if a slug exists. Injects YAML frontmatter with `type: template`, `title`, `description`, and `tags`.
  - Application Tool Handlers (`src/application/skills/wiki_tools.py`): Implemented `create_wiki_template` and `update_wiki_template`, registered in `ScopedToolRegistry` as `wiki_template_create` and `wiki_template_update`.
  - Schema & Dynamic Scoping (`src/application/agent_packs/schema.py`, `platform-packs/autoreiv/pack.json`): Added both tools to `PLATFORM_SKILL_TOOLS["wiki"]` and `DYNAMIC_SKILL_TOOLS["wiki"]`.
  - Platform Skill Runbook (`platform-packs/autoreiv/skills/wiki-templates/SKILL.md` & `src/infrastructure/skills/seeds/wiki-templates/SKILL.md`): Authored standardized runbook instructing agents on template authoring, discovery, and prohibiting note tools for templates.
  - Automated Tests (`tests/unit/wiki/test_wiki_templates.py`): Added unit tests verifying create, collision refusal, update, missing refusal, and tool registration (13 passing tests).

### Fixed

- E2E Smoke Suite UI Drift: Modernized `tests/e2e/smoke.spec.js` to match current v0.33.0 UI architecture (replaced retired `#chatTopBarAgentSelect` with `#agentSelect`, expanded Settings preferences section for theme switcher tests, and navigated via Chat Studio drawer instead of retired `#dock-sessions`).
- CARD-348: Studio Window Box Content Containment ΓÇö Fixed desktop studio windows (notably Factory Studio and Lumina Cinema) where studio content spilled outside the bottom of the window box instead of remaining enclosed within the window frame:
  - Decoupled Hosted View Roots: In `src/web/templates/index.html`, removed `#view-factory.desktop-view-hosted` and `#view-lumina.desktop-view-hosted` from selectors that set `height: 100% !important; max-height: 100% !important;`, allowing `.tab-view.desktop-view-hosted` to enforce strict window-bounded height (`height: var(--dw-h, 30rem) !important;`).
  - Preserved Internal Full-Height Scrolling: Kept `height: 100% !important; min-height: 0 !important; overflow: hidden !important;` on inner wrappers (`#factoryStudio`, `#luminaStudio`), allowing `#factoryPipelineView` and `#luminaComposeView` to scroll cleanly inside the window chrome.
  - Narrow-Screen Media Query Guard: Scoped `#view-education` under `@media (max-width: 1023px)` to `:not(.desktop-view-hosted)` so mobile/tablet media queries do not leak `height: 100% !important` into hosted desktop windows.
  - Cache-Buster Bump: Bumped `app.js?v=2.0.67` in `index.html`.
  - Automated Coverage: Added test suite `tests/unit/frontend/studio_window_containment_348.test.js` verifying CSS rules and preventing viewport containment regressions (88 files / 522 tests green).

## [0.33.0] - 2026-09-17

### Added

- CARD-346: Frontend Architecture Refactoring (SOLID, DRY & Componentization) ΓÇö Comprehensive architectural refactoring of the AutoReiv web frontend applying SOLID, DRY, and industry-standard modern web design patterns:
  - Decoupled Pub/Sub EventBus (`src/web/static/modules/events/event-bus.js`): Introduced a singleton `EventBus` (`on`, `off`, `emit`, `once`, `clear`) with standard typed events (`AGENT_SAVED`, `AGENT_DELETED`, `AGENTS_RELOAD`, `TAB_SWITCH`, `TOAST_SHOW`, `STATE_CHANGE`), removing tight cross-controller coupling (`getChatCtrl()`, `getObsCtrl()`).
  - Polymorphic Studio Lifecycle Registry (`src/web/static/modules/studios/registry.js`): Standardized studio registration with `mount()`, `activate()`, and `deactivate()` lifecycle hooks, replacing the monolithic 11-branch switch in `app.js` with polymorphic dispatch (`studioRegistry.activate(tabName)`).
  - Centralized Modal Manager (`src/web/static/modules/ui/modal.js`): Replaced ad-hoc modal toggles and repetitive Escape key handlers with a centralized LIFO modal stack manager conforming to `REQ-DOM-001`.
  - Enhanced REST API Client (`src/web/static/modules/services/api.js`): Extended `api.js` with standard HTTP verbs (`get`, `post`, `put`, `delete`), query serialization (`buildQueryString`), and domain namespaces (`api.agents`, `api.sessions`, `api.routines`) with 100% backward compatibility.
  - Decomposed Chat Submodules (`src/web/static/modules/studios/chat/`): Decomposed the ~4,400 line `chat.js` monolith into cohesive, single-responsibility submodules: `hitl.js` (HITL formatting and decision submission), `training.js` (training handshake and options), `scroll.js` (autoscroll and jump-to-latest calculations), and `stream.js` (stream payload and context budgeting). Retained canonical job phase rendering in `chat.js` to adhere to Python AST contract invariants. Preserved 100% backward-compatible exports.
  - Pruned Redundancies & Dead Code: Cleaned up redundant Escape key DOM traversals across studios in favor of `modal.js`, pruned dead retired elements (`#goalToggle`, `#hostTestResultAlert`, `#forgeFleetBox`), eliminated double-execution of studio tab loaders in `app.js`, and removed dead functions (`_renderList`, `_rerenderFiltered`, `_selectAgent`).
  - Linter Hygiene: Resolved all ESLint unused variable warnings across `chat.js`, `forge.js`, `projects.js`, `routines.js`, `settings.js`, and `agent-desktop.js`, achieving a completely clean linter gate (0 errors, 0 warnings).
  - Test Suite: Added 33 unit tests across 5 new test suites (`event_bus.test.js`, `studio_registry.test.js`, `modal_manager.test.js`, `api_service_extended.test.js`, `chat_decomposed_modules.test.js`), bringing total frontend tests to 87 files / 517 tests passing with 0 regressions.
- CARD-345: Claymorphism Theme Prototype ΓÇö Implemented an interactive Claymorphism visual prototype for the AutoReiv desktop environment:
  - Theme Engine Preset & Dynamic Attribute: Added `claymorphism` preset configuration to `PRESET_THEMES` in `theme-engine.js` with tactile coral brand accent (`#fb7185`) and charcoal clay surface tokens. Configured `applyTheme` to toggle `data-theme="claymorphism"` on `document.documentElement` dynamically when selected, and cleanly remove it when standard flat themes are active.
  - Settings Studio Swatch: Added a dedicated Claymorphism preset button to `#themePresetsList` in Settings Studio (`index.html`) with a 3D tactile pill swatch indicator.
  - Scoped Tactile Desktop Styling: Implemented scoped CSS rules under `[data-theme="claymorphism"]` in `index.html` featuring:
    - Desktop Dock: Rounded 18px pill buttons with compound inner bevel shadows (`inset 2px 2px 4px rgba(255,255,255,0.18), inset -2px -2px 5px rgba(0,0,0,0.45)`) and realistic tactile click depression on `:active` (`scale(0.95) translateY(2px)`).
    - Desktop Windows: 18px rounded window corners, extruded perimeter clay elevation, cushioned titlebar gradient, and 3D tactile window control buttons (minimize, maximize, close).
    - Primary Action Buttons: Tactile 3D buttons that depress smoothly upon activation.
  - Verified via Vitest unit suite (`tests/unit/frontend/theme_claymorphism_preset_345.test.js`).

## [0.32.0] - 2026-09-17

### Fixed

- CARD-344: Routines Edit Modal Z-Order Stacking and Dock Clearance ΓÇö Resolved window stacking and dock cutoff issues when creating or editing autonomous routines in Routines Studio on the desktop:
  - Document Root Dialog Relocation: Moved `<div id="routineModal">` out from inside `<section id="view-routines">` to the global document root, liberating the dialog from the studio's lower stacking context (`win.z + 1`) which previously caused the window frame (`win.z + 2`) to render on top of the modal.
  - Desktop Modal Z-Order Superiority: Exported `DESKTOP_MODAL_Z = 11000` in `agent-desktop.js` and updated the desktop CSS rule for `.desktop-dialog-host, [aria-modal="true"]` from `120 !important` to `11000 !important`, ensuring all modal dialogs sit in front of both open desktop windows (`DESKTOP_WINDOW_Z_CAP = 9000`) and the bottom dock (`DESKTOP_DOCK_Z = 10000`).
  - Pinned Dialog Footer & Dock Clearance: Restructured `#routineModal` into a 3-part layout with a pinned header (`flex-shrink-0`), scrollable form body (`flex-1 min-h-0 overflow-y-auto overscroll-contain`), and a pinned action footer (`flex-shrink-0 border-t bg-[#0e1015]/95`). The "Cancel" and "Save Routine" buttons remain pinned and visible at all times, with `pb-20 md:pb-24` and `max-h-[calc(100vh-6.5rem)]` preventing the card from being cut off behind the dock.
- CARD-343: Real-Time Live Stream HITL Approval Card Surfacing ΓÇö Fixed an issue where Human-in-the-Loop (HITL) approval prompts did not appear in real time during live chat turns and were only visible after refreshing the browser:
  - Reordered Stream Bubble DOM: Moved `.hitl-approval-card` in `streamBubble.innerHTML` to the bottom of the message container (after `.reasoning-drawer` and `.stream-content`), preventing expandable thought drawers and streaming text from scrolling the card off the screen on mobile devices.
  - Reliable Pinned Tray Surfacing: Introduced `shouldSkipPendingHitlCard` in `chat.js` and relaxed mutual exclusion in `renderPendingHitlCards` so that multi-phase child phases, routines, and non-streaming parked states always mount the interactive Approve/Reject prompt directly into `#pendingHitlHost` above the chat composer without requiring a browser reload.
  - Real-Time Scroll on Approval: Triggered `scrollIntoView` and `maybeAutoscrollMessages()` on `approval_required` SSE events so the prompt is immediately visible when the agent pauses.
  - Multi-Phase Park Status Honesty: Updated `_run_multi_phase_job` in `src/web/routers/chat.py` to recognize `outcome == "parked"` cleanly, eliminating false "FAILED during Formulate: parked" claims and `job_failed: True` flags when an agent simply pauses for operator confirmation.
- CARD-342: Mobile Chat Sessions Drawer Button Portrait Visibility ΓÇö Removed `hidden md:flex` from the in-studio sessions drawer button (`#toggleSidebarBtn`) in `index.html` so it is visible and touch-accessible on mobile devices in vertical portrait orientation (< 768px). Refined button padding and agent selector max-width for 360px-wide portrait viewports.
- CARD-338: Chat Job ID resolution & Phase strip hygiene ΓÇö Suppressed the `#jobPhaseStatusStrip` during plain conversation turns so "Job unknown" is never displayed. Hardened `humanizeJobStatus` and `formatJobPhaseStrip` to never synthesize "Job unknown". Ensured the strip only renders when bound to an active standing job ID, displaying the real job_id with a working copy button.

### Added

- CARD-341: Platform Agent Decoupling: Assistant & Wiki Retirement, Tutor Education Pinning & Roster Consolidation ΓÇö Solidified the 4-agent platform roster (`autoreiv`, `developer`, `tutor`, `direct`), decoupled backend subsystems from legacy hardcoded defaults, retired and deleted `assistant` and `wiki` agent packs from disk, migrated all daily task tracking and wiki curation capabilities into `autoreiv`, and pinned Education Studio to `tutor`:
  - Platform Roster Solidified: Established the 4 canonical platform agent packs: (1) `autoreiv` as primary companion, SRE, daily task coordinator, and wiki vault curator; (2) `developer` as dedicated software engineering specialist for Projects Studio and TDD coding jobs; (3) `tutor` as dedicated education specialist for Education Studio; (4) `direct` as the zero-tool raw model baseline (`PLATFORM_PACK_IDS = {"autoreiv", "developer", "tutor", "direct"}`).
  - Capability Migration to AutoReiv: Fully declared weekly note tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`) and wiki curation tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_note_organize`, `list_wiki_templates`, `wiki_overview`, `wiki_graph`, `promote_artifact_to_wiki`) in `platform-packs/autoreiv/pack.json`. Added `tasks` and `wiki` runbooks to `platform-packs/autoreiv/skills/` and dynamic mappings in `DYNAMIC_SKILL_TOOLS`.
  - Subsystem Decoupling & Alias Resolution: Updated Education router (`src/web/routers/education.py` and `education_priming.py`) from defaulting `agent_id="assistant"` to `agent_id="tutor"`, isolating course mastery and spaced repetition in `tutor_memory.db`. Updated CLI (`src/cli/main.py`), Wiki domain defaults (`frontmatter.py`, `store.py`), and routine manifests (`manifests.py`) to default to `autoreiv`. Added canonical alias resolution mapping `assistant` and `wiki` to `autoreiv` to preserve backward compatibility for legacy session lookups.
  - Working Tree & User Data Cleanup: Permanently deleted `platform-packs/assistant` and `platform-packs/wiki` from git checkout. Implemented startup auto-cleanup in `platform_packs.py` that purges orphaned `$DATA_DIR/packs/assistant` and `$DATA_DIR/packs/wiki` from user data.

- CARD-339: Skill and Tool Architecture, Dynamic Scoping Strategy & Specialist Delegation ΓÇö Resolved the 16k harness tax, eliminated specialist delegation deadlocks, and hardened kernel execution:
  - ADR-0052 Architectural Standard: Established formal contracts separating atomic callable tools ("hands") from procedural Markdown skills ("brain"), specifying a minimal OS baseline and dynamic execution-time tool scoping.
  - Lean OS Baseline: Pruned `REQUIRED_PLATFORM_TOOLS` down to 5 essential coordination and context primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`) in `src/application/skills/platform_primitives.py`.
  - Dynamic Execution Scoping: Implemented execution-time tool resolution in `AgentKernel` via `resolve_scoped_tools(agent, active_skills)`. Cold conversation turns mount only the 5 platform primitives plus agent-specific storage tools (slashing prompt tool schema overhead from 40 tools / 16,164 tokens down to 7 tools / 608 tokens ΓÇö a 96.2% harness tax reduction). Specialized tools mount progressively on-demand when their owning skill is activated.
  - Specialist Intake Dispatch (CARD-336 Resolution): Resolved the single-agent graph deadlock by updating `create_job_from_catalog_resolve` in `JobPhaseOrchestrator` to automatically assign the `Execute` phase to the matching specialist pack (e.g. `wiki`, `homelab`, `developer`) rather than locking all phases to the front-of-house agent.
  - Platform Agent Consolidation: Consolidated front-of-house pickers across Chat Studio (`#agentSelect`) and Agent Studio (`#forgeAgentSelect`) down to the primary companion `autoreiv` and zero-tool baseline `direct` (`CHAT_SHOWN_BY_ID = {"autoreiv", "direct"}`). Deprecated `assistant`, `developer`, and `wiki` from front-of-house companion dropdowns (`CHAT_HIDDEN_BY_ID`), while preserving their underlying pack manifests, databases, and specialist dispatch roles for standing jobs and routines.
  - Kernel Hardening: Added oscillation and argument-churn loop detection (`StreamingCycleDetector`), 70/30 head/tail tool output compaction with scratch disk artifact offloading (`ContextCompactor`), and ephemeral git worktree isolation under `scratch/worktrees/` (`repo_create_worktree` and `repo_remove_worktree`).
- CARD-337: Granular Telemetry Attribution & Observe Studio Performance Audit ΓÇö Implemented discrete token and timing telemetry attribution, a pure model baseline agent, and deterministic performance auditing across AutoReiv:
  - Platform Direct Agent: Added `direct` as a built-in platform agent (`platform-packs/direct/pack.json`) with zero tools and zero skills for raw model benchmarking and pure, low-latency chat.
  - Granular Telemetry Attribution: Instrumented `AgentKernel` (`run_turn` and `stream_turn`) and `telemetry_attribution.py` to calculate exact token consumption across User Prompt, Agent Persona, Tool Schemas, Progressive Skills, Episodic Memory, Compacted History, Tool Results Injected, Completion, and Reasoning (<think>), along with latency stages (Harness Prep, TTFT, Generation TPS, Inter-step Latency) recorded inside `telemetry_spans.metadata_json`.
  - Deterministic Performance Audit Service: Implemented `AuditService` (`src/application/observability/audit_service.py`) aggregating metrics across jobs, sessions, or time windows, computing Scaffold Ratio ("Harness Tax") and dollar costs, and raising tool bloat warnings (>50%).
  - Observe Studio Telemetry Audit & Inbox Export: Integrated an agent-to-session dynamic history browser (`#observeSessionSelect`, `#observeAuditContainer`) into Observe Studio, displaying live KPI cards (Scaffold Ratio, Prompt/Completion, Est Cost, Avg TTFT, TPS), bloat alerts, and component token attribution breakdown table. Added one-click "Generate Report to Inbox" (`#observeGenerateReportBtn`) via `POST /api/observability/audit/export` and `wiki_service.create_note`, filing formatted markdown reports directly into `00_Inbox/` with initial YAML frontmatter ($0.00 LLM inference cost, zero inference delay, honoring the One-Door Policy). Eliminated unnecessary LLM agent tools and routines.
- CARD-329: Capability-gap smoke ΓÇö Implemented an operator-executable capability gap proof loop proving the gap -> candidate -> approve/reject cycle with zero UI theatre. Forced missing tool or skill calls persist durable rows in both `agent_capability_gaps` and `scaffold_spine` records (`force_missing_capability_gap`). Approving a candidate promotes the capability entry to `trusted` in `CapabilityCatalogRepository` and marks the underlying gap status as `trained`. Rejecting a candidate transitions the record to `rejected`, records the operator reason, marks the gap `dismissed`, and mathematically guarantees that the trusted capability inventory is completely unchanged. Added REST endpoints `POST /api/capabilities/smoke/force-gap`, `POST /api/capabilities/scaffold/{record_id}/reject`, and `POST /api/capabilities/smoke/gap-candidate-loop`. Verified via unit and API test suites (`tests/unit/capabilities/test_card329_capability_gap_smoke.py`) and live smoke testing on Jarvis.
- CARD-334: Education knowledge-type anchors ΓÇö Specialized teaching artifacts across four distinct knowledge types (`concept`, `tool`, `method`, `problem`) rather than a single generic course step shape. Implemented `src/application/education/knowledge_types.py` with 4 tailored shape kinds (`concept_brief`, `tool_reference`, `method_runbook`, `problem_scenario`) requiring specific pedagogical sections. Registered corresponding Wiki templates (`education-concept`, `education-tool`, `education-method`, `education-problem`) in `EDUCATION_TEMPLATES`. Specialized course steps by default knowledge type (`resolve_step_knowledge_type`) while supporting explicit caller overrides. Added REST endpoints `GET /api/education/knowledge-types` and `POST /api/education/knowledge-artifact`. Surfaced `knowledge_type` and `available_knowledge_types` in `course_chrome_snapshot` and added `#educationKnowledgeAnchorBar` (with `data-card="334"`), `#educationKnowledgeTypeBadge`, and `#educationKnowledgeTypeSelect` in Education Studio. Kept strictly separate from CARD-324 Construction/Application graded lab pressure. Verified via unit test suites (`tests/unit/education/test_card334_knowledge_type_anchors.py` and `tests/unit/frontend/education_studio.test.js`) and live smoke on Jarvis.
- CARD-333: Education delivery profiles ΓÇö Implemented dedicated presentation delivery profile toolbar (`#educationDeliveryProfileToolbar` with `data-card="333"`) in Education Studio, visually separated from the sky-blue academic depth chrome (CARD-327). Features emerald styling, live active presentation badge (`#educationActiveDeliveryProfileBadge`), primary delivery profile selector (`#educationPrimaryDeliveryProfileSelect`), and Apply button (`#educationApplyDeliveryProfileBtn`) synchronized with the backend study environment. Enforces strict architectural separation: selecting presentation profiles (`default`, `calm_focus`, `adhd_bite`, `pomodoro`) adjusts pacing, chunk size, and timers without mutating academic depth ladders, mastery ledger rows, or spaced repetition intervals. Integrated `delivery_profile` into `course_chrome_snapshot`. Verified via unit test suites (`tests/unit/education/test_card333_education_delivery_profiles.py` and `tests/unit/frontend/education_studio.test.js`).
- CARD-332: Assistant constitution Wiki scrub ΓÇö Scrubbed Wiki-specific operating instructions and duplicate Wiki skills out of the `assistant` platform pack (`platform-packs/assistant/pack.json`). Removed redundant `platform-packs/assistant/skills/wiki/` folder, scrubbed 9 `wiki_*` tools from Assistant's pack manifest, and removed default Wiki vault restrictions from `src/domain/agents/good_agent_instructions.py`. Clarified domain boundaries so Assistant acts strictly as a daily workflow coordinator, task manager, and day-to-day helper, delegating deep Wiki curation requests to the dedicated `wiki` platform pack (`platform-packs/wiki/`) via `handoff_to_agent`. Verified via unit tests (`tests/unit/agents/test_card332_assistant_wiki_scrub.py`).

- CARD-328: Education Learning OS ΓÇö Amplifiers & Lumina Studio integration ΓÇö Integrated the multimodal concept cinema and visual layout engine into AutoReiv as a native Lumina Studio (`#luminaStudio`) in the navigation rail and sidebar. Implemented pure ES Module SVG layout engine (`src/web/static/modules/lumina/visual.js`) rendering 14 geometric archetypes (`flow`, `cycle`, `compare`, `orbit`, `stack`, `split`, `wave`, `network`, `scale`, `balance`, `grow`, `transform`, `pipeline`, `system`) with animated packet motion (`<animateMotion>`), glow filters, and pulsating node cards. Added Lumina Stage Player with synchronized timeline scrubber, subtitle/whisper HUD, browser speech narration, and starter lessons. Elevated step 9 (`amplifiers`) of the durable `education_course` pipeline to generate structured visual schemas, save templated Wiki notes (`00_Inbox/`), and anchor mastery rows in `assistant_memory.db`. Added bidirectional bridge: "Send to Education Course" from Lumina Studio, and "Watch in Lumina" (`#educationAmpWatchLuminaBtn`) from Education Studio. Added REST endpoints `GET /api/lumina/starters`, `GET /api/lumina/lesson/{id}`, `POST /api/lumina/compose`, and `POST /api/lumina/send-to-course`. Fixed ESM export/import in `toast.js` and `lumina.js`, enabled hosted desktop `pointer-events: auto` for Lumina inputs, added form submission handler for mobile keyboards, and ensured robust touch-scroll flow on mobile. Verified via unit test suites (`tests/unit/education/test_card328_lumina_amplifiers.py` and `tests/unit/frontend/lumina_studio.test.js`).
- CARD-327: Education Learning OS ΓÇö Adaptive depth + mastery chrome + Studio usability ΓÇö Implemented a durable, adaptive 5-rung mastery depth ladder (Level 0: Explorer [Kindergarten] ΓåÆ Level 1: Foundational [Elementary] ΓåÆ Level 2: Practitioner [High School] ΓåÆ Level 3: Expert [Undergraduate] ΓåÆ Level 4: Master [Masters]) anchored in `memory.db` (`education_depth` semantic facts and `education_mastery` pass rate evaluation). Added Wiki growth portfolio generator (`education-portfolio` template in `00_Inbox/`) anchoring `course_growth_portfolio` facts and mastery items. Elevated Education Studio course chrome with live mastery badge (`#educationMasteryBadge`), academic rank (`#educationAcademicRank`), progress bar (`#educationMasteryProgressBar`), next milestone description (`#educationNextMilestone`), and one-click Growth Portfolio button (`#educationGrowthPortfolioBtn`). Added human-friendly step labels across the course pipeline and REST endpoints `GET /api/education/course/depth` and `POST /api/education/course/portfolio/create`. Verified via unit test suite (`tests/unit/education/test_card327_adaptive_depth_chrome.py`) and frontend tests.
- CARD-325: Education Learning OS ΓÇö Environment framing + AnalysisΓåÆRetention handoff ΓÇö Elevated Environment framing and AnalysisΓåÆRetention handoff into robust, kill/resume-safe course steps in the durable `education_course` pipeline. Environment framing establishes runtime boundaries and active delivery profiles without touching or rewriting SRS interval rules, writing templated `education-priming` notes (`00_Inbox/`), anchoring `education_mastery` and learner semantic facts (`course_step_environment`) in `memory.db`. Hardened Analysis step and `execute_analysis_retention_handoff` to automatically schedule missing `next_due` timestamps across all course mastery items via 1-3-7-30 SRS and record durable `course_handoff_retention` semantic facts, guaranteeing zero lost schedule or step progression across process restart/kill. Added REST endpoints `POST /api/education/course/environment/preview`, `POST /api/education/course/environment/complete`, and `POST /api/education/course/analysis/handoff`. Integrated Education Studio with `#educationAnalysisHandoffBtn` and `#educationEnvironmentCompleteBtn`.
- CARD-324: Education Learning OS ΓÇö Construction / Application labs with graded pressure ΓÇö Elevated Construction and Application labs into ordered course steps (`ORDERED_COURSE_STEPS`) with objective invariant-based graded pressure evaluation. Passing labs generate templated Wiki artifacts using `education-lab` (`00_Inbox/`), update `education_mastery` (`grade="pass"`), append learner semantic facts in `memory.db`, and advance the course step honestly. Failed or incomplete lab submissions record `grade="miss"` via `record_education_grade`, schedule retention reviews (`next_due`), record learner weakness facts, and halt course progression without faking mastery. Added `POST /api/education/course/lab/preview` and `POST /api/education/course/lab/grade` endpoints. Enhanced Education Studio with dedicated Construction and Application lab panels, objective/invariant inspection, solution submission textareas, and verified receipt feedback.
- CARD-323: Education Learning OS ΓÇö Elaboration course step ΓÇö Added Elaboration (explain-in-own-words / Feynman technique) as an ordered step (`ORDERED_COURSE_STEPS`) in the durable `education_course` pipeline, situated between `retrieval` and `construction`. Completing the step writes a structured Wiki artifact with the learner's explanation and key concept anchors using the `education-elaboration` template, updates `education_mastery` (`course_{slug}_elaboration`), and records a learner semantic fact (`course_step_elaboration`) in `memory.db`. Added `POST /api/education/course/elaboration/preview` and `POST /api/education/course/elaboration/complete` endpoints. Integrated Education Studio with an interactive Elaboration Player panel (`#educationElaborationSection`) with prompt, textarea, Preview button, and Complete Step button.
- CARD-322: Education Learning OS ΓÇö Wiki templates for every Education artifact ΓÇö Registered structured Wiki templates catalog covering all Education artifacts (`education-priming`, `education-dual-coding`, `education-elaboration`, `education-quiz`, `education-flashcard`, `education-lab`, `education-score`). Scaffolds templates into `02_Resources/_Templates/` and discovers them via `WikiStore.list_templates()`. Enforces `template_id` requirement across all Education write-back and course step paths (`create_priming_note`, `create_study_artifact_note`, `_write_step_artifact`), recording authorized `template: <id>` in note YAML front matter and rejecting freeform un-templated dumps (`assert_education_template_required`).
- CARD-321: Education Learning OS ΓÇö Dual Coding as real course step ΓÇö Elevated Dual Coding into a first-class ordered course step (`ORDERED_COURSE_STEPS`) in the durable `education_course` pipeline, situated between `priming` and `retrieval`. Completing the step writes a structured Wiki artifact with verbal prose, fenced Mermaid diagram, and step-through breakdown, while anchoring concept items in `education_mastery` and learner semantic facts (`course_step_dual_coding`) in `memory.db`. Added `POST /api/education/course/dual-coding/preview` endpoint and wired an interactive Dual Coding Player panel into Education Studio with prose display, Mermaid diagram canvas, and step completion action.
- CARD-326: Education Learning OS ΓÇö Tutor agent (Wiki + ledger aware) ΓÇö Added `tutor` as the 5th Platform Agent Pack (`platform-packs/tutor/`) with a dedicated Socratic tutoring runbook (`skills/tutoring/SKILL.md`). Enforces the strict single-brain invariant (`_verify_memory_repo_invariants`): grounds the Socratic context in the active topic's Wiki artifacts and existing `memory.db` mastery ledger (`education_mastery`, `learner_facts`), explicitly forbidding secondary `storage.db` creation. Added `POST /api/education/tutor/context` endpoint. Integrated Education Studio with a primary "Discuss with Tutor" button (`#educationDiscussTutorBtn`) with graduation-cap icon to preload Socratic topic context and launch into interactive chat under the `tutor` agent.
- CARD-335: Dynamic Tool Output Budget Scaling ΓÇö Scaled `max_tool_chars` in `ContextCompactor` proportionally with the resolved model context limit (`resolve_max_tool_chars`) from an 8,000 character floor up to a 120,000 character ceiling (~30,000 tokens). Eliminates artificial truncation warnings and agent anxiety when reading large documents or wiki notes on modern 32kΓÇô131k+ models while preserving runaway safety caps. Wired into both sync `run_turn` and streaming `stream_turn` kernel execution loops.
- CARD-293: Wiki Skill, Tools, Template Enforcement & Dedicated Wiki Agent ΓÇö Enforced mandatory structured templates on note creation (defaulting to `zettelkasten-atomic` when omitted; recorded as `template: <id>` in YAML front matter). Added `concept-comparison.md` core template for comparative study analysis. Registered `list_wiki_templates` / `wiki_template_list` across tool registry and AutoReiv OS Baseline. Enforced canonical vault grounding with explicit `vault_root` and `relative_path` in return envelopes, paired with strict prompt instructions forbidding filesystem searching for wiki vaults. Provided truncation-safe reads (`total_length`, `truncated: False`) and seeded `wiki` (Wiki Librarian) as a 4th Platform Agent Pack with dedicated `wiki-curation` runbook and tools, visible in Agent Studio and Chat.
- CARD-330: Platform skill tiers & mount-time tool scoping ΓÇö Enforced 3-tier model: Tier 1 Enforced Platform Required (coordination and wiki read), Tier 2 Platform Optional (sandbox, proposals, worker, etc.), Tier 3 Dedicated Agent Pack (`pack_tool_names`). `PlatformSkillMountError` fails honestly on missing required platform skills at mount time. `ToolRegistry.get_tools_for_agent` strictly filters tools to scoped authority, eliminating prompt bloat during LLM turns. Agent Studio (`#view-forge`) organizes capabilities into 3 distinct visual sections: AutoReiv OS Baseline (with uncheckable reference cards and locked indicators), Platform Skills & Tools, and Custom Agent Pack Skills & Tools.
- CARD-320: Education Course + Mastery model ΓÇö durable `education_course` in agent `*_memory.db` (topic_id, ordered Learning OS steps JSON, current_step, status); course pipeline DEFAULT Ask path; mode-picker = jump-to-step; step complete ΓåÆ Wiki artifact + ledger anchors; mastery gate = binary external (`grade_answer_binary`) with miss ΓåÆ Retention `next_due`; restart-safe TDD (`tests/unit/education/test_card320_course_mastery_model.py`); no Dual Coding chrome

## [0.31.0] - 2026-09-14

Learning OS prove-and-harden (CARD-316ΓÇô319) + Education Studio continuity + UI marathon already on qa.

### Fixed

- CARD-319: Education Retention RoutineΓåÆJob prove-and-harden - respect routine.enabled (pause ΓåÆ no mint; resume ΓåÆ mint); due ledger next_due ΓåÆ standing Job; restart-safe (`tests/unit/education/test_card319_retention_routine_job.py`)

### Added

- CARD-318: Education Retrieval binary external grade prove-and-harden - Priming-seeded (or upsert) practice ΓåÆ `grade_answer_binary` / `grader: binary_external` ΓåÆ durable item├ùmastery pass/fail in memory.db; miss sets `next_due` stage0=+1d (1-3-7-30); quiz selection prefers Priming unseen; empty expected_answer ΓåÆ 422; restart-safe TDD (`tests/unit/education/test_card318_retrieval_binary_grade.py`)

### Added

- CARD-317: Education Priming write-back - Ask Priming / priming_writeback lands Wiki schema/outline note (catalog wiki_note_* only) **and** memory.db ledger anchors (education_mastery + learner priming_topic); unregistered/forbidden wiki tools soft-fail without blocking note write-back ( ests/unit/education/test_card317_priming_writeback.py)

### Fixed

- CARD-316: Education learner ledger prove-and-harden - `record_education_grade` no longer swallows learner-fact sync; TDD pins for memory.db path, missΓåÆ1-3-7-30 `next_due`, binary external grade, restart-safe reopen + weakness facts (`tests/unit/education/test_card316_learner_ledger.py`)

### Added

- CARD-313: Settings collapsed sections (Providers / Data / Preferences / Connections) + honest `POST /api/data-dir/migrate` (copy, validate, `*_backup_<ts>`, persist `AUTOREIV_DATA_DIR`)

### Fixed

- CARD-314:
- CARD-315: Education Learning OS panels collapsed on load (`details.edu-section`); expand scrolls; Ask keeps journey/HITL on origin Education session Train Specialist modal scrolls (max-h + body overflow); Factory studio min-h-0 + full desktop window (not toast); Agents deep-link still scopes agent queue
- CARD-312: Observe expand sections scroll with the studio panel (phone + desktop)

- CARD-311: Observe collapsible sections + agent KPI select from real `/api/observability/kpi`; journey chips from traces; serve `0.0.0.0 --reload`

### Added

- CARD-310: Routines structured schedule (schedule_rule) + full agent pickers

### Added

- **Chat picker / sessions drawer / Jump to latest [CARD-296]**: Single left `agentSelect` (Show in Chat); remove top Chat agent dropdown. Sessions = in-studio left drawer (New Conversation + recent only, no Active Agent; select loads + auto-collapses). Smart autoscroll + Jump to latest. Dock Sessions launcher removed. Journey/Debug stay under Chat. Wiki labels both **Save to Wiki**; remove Chat **Train in Lab** button; keep Workbench (Save to Wiki path) and durable Train Agent checkbox.

### Fixed

- **Routines filters + schedule builder [CARD-309]**: Agent/status/last-ran/search filters; Active = scheduler enabled; exact cron preview + calendar presets.
- **Wiki Graduate Inbox pass/fail [CARD-308]**: Incomplete notes stay in Inbox with `graduate_errors`; complete notes graduate/merge.
- **Journey/Debug under + Options [CARD-307]**: Moved Chat Journey and Debug into Options; quieter top chrome.
- **Chat Train keep-one [CARD-306]**: Hide Chat Train Agent option; remove Forge Train in Lab; keep Factory + Workbench with honest empty state.
- **Sessions off dock [CARD-305]**: Sessions is Chat drawer only; scrub prefs and refuse desktop Sessions windows.
- **Agents Constitution + Training Optimization [CARD-304]**: Constitution last under Identity; queue renamed/moved under Capabilities; sections default collapsed; Open Training Factory control.
- **Projects Manager / Explorer flip [CARD-303]**: Two full studio modes instead of overlay drawer; default Artifact Explorer for Active project.
- **Projects live context + drift [CARD-302]**: Versioned path manifest; Set Active reloads disk tree; structure-only drift (red missing) + Align; drawer paints above explorer.
- **Chat duplicate agent picker [CARD-301]**: Remove Agent Desktop titlebar agent dropdown; only `#agentSelect` (Show in Chat) remains.
- **Projects folder tree [CARD-300]**: Folder-only browse under projects_root with Up/Root; Set Active from tree selection (no huge flat-only list).
- **Agents Studio create + collapse [CARD-299]**: One New Agent path (Quick Scaffold toolbar removed); Identity / Agent Preferences / Overrides / Capabilities collapsibles; Custom Agent Pack Skills & Tools header.
- **Wiki Studio tighten [CARD-298]**: Single Wiki-based Document Repository identity; drop Expand keep Meta; Curate Inbox relabeled Graduate Inbox (honest rule-based fast-file, not agent review).
- **Desktop Organize Windows always on top [CARD-297]**: Dock z-index 10000; window stack capped at 9000 so Organize never sits under open studio windows.
- **Chat journey + HITL stay intact without refresh [CARD-295]**: Live Chat SSE drives full job chrome through park; park events and stream-end call refreshPendingHitl; session select rehydrates journey; approval_required SSE includes type.

## [0.30.0] - 2026-09-13

- **CARD-294 cards home**: Move work cards `.github/cards/` ╬ô├Ñ├å `docs/cards/`; CardTools/paths prefer `docs/cards` (legacy fallbacks kept); add `.agents/skills/card-status`.
- **CARD-294 agentic artifacts realign**: Slim `AGENTS.md` to governance; Antigravity `trigger`/`globs` on `.agents/rules`; always-on checkout-hygiene / agents-vs-packs / single-card; skills `preflight`, `serve-hygiene`, `honesty-smoke-gate`; product-only `steering/` (serve runbook removed from `tech.md`).
- **CARD-294 single AGENTS + tight steering**: Folded serve hygiene into `steering/tech.md` and honesty merge gate into `AGENTS.md` DoD; deleted standalone steering one-offs; removed root `GEMINI.md` and `PROJECT.md` (stale/duplicate) so coding assistants use **one** `AGENTS.md`.
- **CARD-294 docs/skills tidy**: Removed `docs/audit/`, `docs/architecture/` runbooks; moved serve-orphan + honesty-smoke into `steering/` (not `.agents/`, not packs); moved `docs/agent-packs.md` ╬ô├Ñ├å `docs/specs/agent-packs.md`; wiped local `notes/` + `hyperv_unattend/`; locked `.agents/` vs pack skills boundary in AGENTS.md.

### Changed

- **Repo + user-data hygiene [CARD-294]**: Platform seed only `assistant` / `autoreiv` / `developer` (`developer` is id and display name; coding/coder obsolete). Homelab packs removed from `platform-packs/` and seed lists ╬ô├ç├╢ AppData user packs untouched. Untracked scratch: `notes/`, `packs/finance/`, `skills/opentofu-hyperv/`, radical demo doc; removed empty `agent-packs/`. `AUTOREIV_DATA_DIR` unchanged.
- **CARD-294 working-tree hygiene**: Refuse live data roots inside the git checkout (`ensure_live_data_root`); add `scratch/` (+ ignore); AGENTS.md hard rule; remove checkout `./data` fallbacks for attachments/skills/factory; wipe leftover checkout `packs/`/`data/`/`*.db` (AppData untouched).
- **CARD-294 follow-up**: Explicit gitignore exceptions so platform-packs/developer/skills/build/ ships; SQLite/update defaults use user-data database/ (not checkout ./data/ or repo-root db); install never treats repo platform-packs/ as the live pack dest; homelab unit tests assert seed exclusion.

### Added

- **CARD-291**: Studio UI overhaul, consolidation, high-signal design system, and Education Studio refinement ╬ô├ç├╢ applied dark void palette (`#08090C`/`#0E1015`), hairline borders, and concentric radii across all 10 studios and modals; consolidated Agent Studio by separating LLM provider discovery to Settings Studio; elevated Education Studio into an Adaptive Learning Cockpit with spaced retrieval telemetry and clean pedagogical panels; streamlined Chat Studio with ReAct monospace execution traces; unified signal hierarchy across windows. All 375 frontend unit tests pass.

### Fixed

- **CARD-291**: Fixed desktop window shell occluding hosted studio views by ensuring `.desktop-window` frame background is transparent (preventing higher z-index window chrome from covering hosted studio content).

## [0.29.0] - 2026-09-12

### Added

- **CARD-275╬ô├ç├┤289**: Capture Track B (UI marathon) + Track D (horizon) backlog as Ready cards (scaffold only; no build).
- **CARD-273**: Repo hygiene, test alignment to standing runtime, and release v0.29.0 ╬ô├ç├╢ cleaned 578 root scratch/test residue files; aligned legacy test suites to standing runtime contracts with 100% green tests (1,479 pytest, 370 vitest); fast-forwarded `qa` to `grok` tip, cut release `v0.29.0`, promoted to `main`, and safely retired `grok`.
- **CARD-272**: Install / Compose / update truth ╬ô├ç├╢ compose persists /data, Windows+systemd installers exist, live /api/system/version matches git HEAD, Settings wires version/check; no live apply.

### Added

- **CARD-271**: ReAct vs Job spine truth ╬ô├ç├╢ short chitchat stays SHORT_REACT (no Job); outcome-shaped Ask mints durable job_id with Observe standing-journey 200. Live
  otes/marathon-card271-live-smoke.json.

### Fixed

- **CARD-290**: Settings Refresh Models uses live provider inventory only ╬ô├ç├╢ no ghost Custom/Saved defaults when id is off-endpoint.

- **CARD-274**: OpenAI/vLLM streaming tool calls merge argument fragments by index before kernel execution (fixes empty wiki_note_create args under Nemotron/vLLM).
- **CARD-270**: Training Factory truth ╬ô├ç├╢ gap `train` sets `training` (not premature `trained`); promote without sandbox pack files is honest **can't** (422, no ToolSynthesizer invent); promote reject/approve sync linked gap status; `_repo` accepts `factory_repo` override.

### Added

- **CARD-269**: Shared good-agent Instructions template (`src/domain/agents/good_agent_instructions.py`) with IDENTITY / DOMAIN / EXECUTION / SAFETY / TOOLS / PROVENANCE / OUTPUT sections; backfill Assistant, AutoReiv (System-to-be), and Finance pack `system_prompt`s; Forge scaffold + pack-sync refresh overrides so live Chat uses the new contract.

### Added

- **Foundation honesty re-smoke [CARD-268]**: Tip re-proof of bones 1╬ô├ç├┤5 under qwen ╬ô├ç├╢ honesty pack + Observe receipt + Chat/Observe operator UI + kill/resume same `job_╬ô├ç┬¬` + Forge same-job + HITL Approve/Deny. Artifact `notes/marathon-card268-live-smoke.json`.

### Fixed

- **Observe finished-job receipt [CARD-266 / REQ-OBSREC-001..005]**: Canonical `GET /api/observe/jobs/{job_id}` (alias `GET /api/jobs/{job_id}`) returns the standing journey when the Job exists and a real HTTP 404 when it does not. Standing-journey query uses the same existence rule (no 200-empty for unknown ids). Live `notes/marathon-card266-live-smoke.json`.

### Added

- **Specialist A2A same-job handoff [CARD-265 / REQ-A2ASAME-001..005]**: Default specialist A2A binds/resumes the **same** standing `job_id` (parent park ╬ô├Ñ├å specialist work ╬ô├Ñ├å parent continues one Observe tree). Privilege never widens ╬ô├ç├╢ effective matched IDs stay the parent subset (skip allowlist escalation). CARD-224 linked `child_job_id` remains opt-in via `linked_child_job=true`. Supervisor pick (234) uses same-job bind. Live `notes/marathon-card265-live-smoke.json`.

### Added

- **Scoped repo write/patch under HITL [CARD-264 / REQ-RWHITL-001..005]**: Catalog `repo_file_write` / `repo_file_patch` / `repo_file_rollback` jailed under checkout (CARD-262 sandbox). Write/patch = REQUIRE_CONFIRM (CARD-221); Deny leaves tree unchanged; rollback restores prior or deletes created file. Homelab + Assistant packs. Live `notes/marathon-card264-live-smoke.json`.

### Added

- **Homelab-class outcome smoke [CARD-263]**: One Homelab-class Ask uses Wiki grounding + repo_file_* reads on the same job_id; Journey DONE; provenance-only claims. Live job_1080eb9f4ab4. Script notes/scripts/homelab_outcome_smoke_263.py.
- **Repo/code capability path [CARD-262 / REQ-REPO-001..005]**: Catalog-registered read-only `repo_file_list` / `repo_file_read` jailed under AutoReiv checkout (`AUTOREIV_CHECKOUT_ROOT` or detect) with sensitive denylist ╬ô├ç├╢ no FS escape. CARD-221 SAFE (no write tools in this card). Standing Chat injects repo grounding constraint for code-aware asks; claim guard + honest-fail when no successful read (Homelab-class: never invent AGENTS.md/source). Homelab + Assistant packs gain tools. Live `notes/marathon-card262-live-smoke.json`.

### Added

- **Standing honesty/smoke pack tip merge gate [CARD-261 / REQ-HSP-001..005]**: Freeze stress classes `timeout|gate|tool|honesty|kill_resume|pass` as a standing tip merge gate. Classifier + `notes/scripts/honesty_smoke_pack_261.py` (`--validate` / `--live`) exit non-zero on red Done-on-FAILED / honesty theatre / silent SSE death. Wired into unified preflight; runbook `steering/honesty-smoke-merge-gate.md`. Live `notes/marathon-card261-live-smoke.json`.

### Fixed

- **Wiki-thin fail-closed grounding [CARD-260 / REQ-WIKITHIN-001..004]**: Empty/thin vault topics no longer invent Okta-class Wiki paths/titles. Standing Chat probes the vault before Formulate; source-dependent thin asks HITL-park with **need sources**; create-shaped thin asks proceed **grounded_only** (paths only from `wiki_note_create`/`wiki_note_read`). Chat turn claims that cite paths outside tool provenance **and** this Job vault grounding hit/read allow-list are honesty-rewritten (not Done theatre); ellipsis table paths are ignored. Live `notes/marathon-card260-live-smoke.json`.

- **Kill/resume mid-LLM same job_id [CARD-259 / REQ-KILLR-001..005]**: Operator abort during standing Formulate/Execute no longer `fail_phase` / cancel the Job (live other `job_9836e6ddd4a2`). Abort writes a durable checkpoint (`operator_kill_mid_llm`), re-queues the RUNNING phase, stops the worker (no orphan after SSE death), and `resume: true` continues the **same** `job_id` to DONE or honest park. Never Done-on-FAILED. Live `notes/marathon-card259-live-smoke.json`.

- **Phase LLM longer budget + retries [CARD-258 / REQ-PLLM-001..005]**: Standing Formulate/Execute/Research no longer die at the import-time 120s default (live FAIL `job_cbf0a330fc5c`). Default budget 300s for qwen KV fill; timeout/retries resolve at **call time** from env; CLI serve + `restart_serve` load repo `.env` (do not overwrite process env). 1╬ô├ç├┤2 retries on `phase_llm_timeout` / connection stall before `fail_phase`; exhausted reason includes `retries_exhausted` + CARD-257 honesty (never Done / invent a note). Live `notes/marathon-card258-live-smoke.json`; stress pack `notes/marathon-card258-stress-pack.json`.

- **Research gate skip-or-continue + Chat status honesty [CARD-257 / REQ-RGATE-001..005]**: Matched tools covering the outcome (`outcome_covered_by_matched`) skip Research even when `count < 2` ╬ô├ç├╢ never hard-fail on `below_threshold` alone. Standing Research with side-effects already at mint **auto-completes without LLM** (Chat + routine executor) so thin Research cannot `phase_llm_timeout` ╬ô├Ñ├å `fail_phase` kill Formulate/Execute. On Job/phase FAILED, Chat emits honest `turn_done` (job_id + phase + reason) instead of leaving streamed "Done╬ô├ç┬¬" / invented notes as the claim. `derive_success_rule` prefers colon-form `Done-when:`. Live `notes/marathon-card257-live-smoke.json`.

### Added

- **Self-scaffold queue E2E [CARD-255 / REQ-SSQ-001..005]**: Education gap Ask -> Forge candidate -> sandbox/HITL Approve (251 same job_id) -> trusted; next Job trusted-only resolve can use the skill; rollback restores prior trusted; standing catalog resolve never auto-trusts candidates. Live `notes/marathon-card255-live-smoke.json`.
- **Verifier / replan harden [CARD-254 / REQ-VRH-001..005]**: Binary external verify only (LLM self-critique never standing pass); `apply_forced_fail_verify_gate` forces fail -> CARD-232 replan <=3 -> HITL park (no infinite loop); Chat standing checker-fail uses `apply_phase_complete_verify_gate` (not `fail_phase` dead-end); handoff != replan. Live `notes/marathon-card254-live-smoke.json`.
- **Long-run context / working-set holds N╬ô├Ñ├åN+1 [CARD-253 / REQ-LRCTX-001..005]**: Phase-scoped working set (228 progressive skill + 229 working set) survives kill/resume; phase N+1 rebuilds from ledger/`memory.db` facts + durable notes ╬ô├ç├╢ full Chat transcript dumps rejected as memory theatre. `rebuild_working_set_after_resume` + Chat resume wire; live `notes/marathon-card253-live-smoke.json` (qwen SAW_LEDGER).
- **Frozen operator eval pack [CARD-252 / REQ-EVAL-PACK-001..004]**: 3-5 frozen asks (Chat outcome Job, Education Ask/quiz, Wiki Job, Forge Approve same job_id) with Observe `job_id` checklist; CI-scriptable runner `notes/scripts/frozen_eval_pack_252.py` + `tests/unit/eval/test_frozen_eval_pack_252.py`; live `notes/marathon-card252-live-smoke.json`.
- **Serve / orphan process hygiene [CARD-256 / REQ-SERVE-HYG-001..004]**: Documented Jarvis restart runbook (`steering/serve-orphan-hygiene.md`); `scripts/restart_serve.py` (+ `.ps1`) finds/kills :8000 orphans, starts one tip serve, prints tip SHA + `app.js?v=` from `index.html`; unit tests lock version parse + dry-run; live smoke `notes/marathon-card256-live-smoke.json`. Prevents stale-serve / stale-chrome false fails.
- **Education Studio viewport layout [CARD-250 / REQ-EDU-VP-001..004]**: Learning OS pedagogy panels (Quiz╬ô├Ñ├åAmplifiers) wrap/stack inside `#educationPedagogyColumns` with in-panel `overflow-y` and `overflow-x: hidden` so Studio fits one viewport ╬ô├ç├╢ no sideways peek / forever-horizontal overflow; CARD-242..249 engines untouched; Lumina out of scope.
- **Education Visual Amplifiers / Mermaid + step-through on Retrieval [CARD-249 / REQ-EDU-VA-001..004]**: Dual Coding Mermaid and ordered step-through attach to quiz/mastery Retrieval items only; visuals-only / missing ledger path refused (edutainment guard); video/film player OUT of P0; Education Studio Amplifiers panel + `/api/education/amplifiers/*`; quiz/next surfaces amplifiers without rewriting `next_due`.
- **Education Environment / study-session delivery profiles [CARD-248 / REQ-EDU-ENV-001..004]**: Named delivery profiles (tone + timer / ADHD bite-size) shape Ask and quiz _presentation_ only; mastery ledger + Routine->Job SRS remain sole due/resurface source; Education Studio Environment panel + `/api/education/environment/*`; quiz/next returns delivery metadata without rewriting `next_due`.
- **Education Analysis / error log + metacog [CARD-247 / REQ-EDU-AN-001..004]**: On miss/fail, deterministic `miss_reason` taxonomy writes durable error_log + metacog facts into agent `memory.db` (never `storage.db`); `/api/education/quiz/next` prefers miss-reason pressured weak items (feeds CARD-243); Wiki + memory write-back; Education Studio Analysis panel + `/api/education/analysis/*`.
- **Education Application / Exercise Job + binary verify [CARD-246 / REQ-EDU-APP-001..004]**: Application exercises from Wiki `## Application`/`## Exercise`; binary external grade (reference/concepts ╬ô├ç├╢ never LLM self-score); prefer standing Exercise Job mint; fail ╬ô├Ñ├å bounded replan or HITL park (CARD-232) + mastery miss/resurface; pass advances mastery; Wiki + memory.db write-back; Education Studio Application panel + `/api/education/application/*`.
- **Education Construction / generative study artifacts [CARD-245 / REQ-EDU-CONST-001..004]**: Deterministic Construction engine builds schema + dual-code + quiz/elaboration study notes and stages them to Wiki `00_Inbox/` via catalog-matched `wiki_note_*` only (CARD-241 allowlist; fail-soft search/read; never `wiki_overview`). Seed `education-construction`, Ask mode chip, Education Studio Generate panel, `/api/education/construction/generate`.
- **Education Elaboration / explain-it-back [CARD-244 / REQ-EDU-ELAB-001..004]**: Binary external grade (reference token containment or required-concepts rubric ╬ô├ç├╢ never LLM self-score); miss updates mastery ledger + 1-3-7-30 and can Routine╬ô├Ñ├åstanding Job resurface (reuse CARD-242); Wiki + memory.db write-back of elaboration outcomes; Education Studio Elaboration panel + `/api/education/elaboration/*` endpoints.
- **Education Learner Model [CARD-243 / REQ-EDU-LM-001..004]**: Quiz grades write durable strengths/weaknesses/patterns into agent `memory.db` semantic facts (adjacent to the CARD-242 mastery ledger ╬ô├ç├╢ never `storage.db`); `/api/education/quiz/next` prefers due/weak/missed over random; Education Ask + Studio Next Quiz / Pressure Ask pressure known misses; kill/resume serve still prefers the known miss from `memory.db` (no second tutor runtime).
- **Education Retrieval + Retention [CARD-242 / REQ-EDU-RR-001..005]**: Quiz engine over Wiki Priming/Dual notes with binary external grade (not LLM self-score); thin mastery ledger in agent \memory.db\ (item id, topic/path, grade, next_due); miss schedules fixed 1-3-7-30; \ducation-retrieval-retention\ Routine mints standing Jobs for due reviews (chat toast is not Done); Education Studio Quiz/Due operator path + \/api/education/*\ endpoints.

### Fixed

- **P0 empty-rail / blank Chat [CARD-251 syntax]**: `7ca3f9d` stripped template-literal backticks in `forge.js` (`SyntaxError: Invalid regular expression flags`). Static `import` of Forge prevented `initApp` (CARD-237 class: chrome loads, rail+Chat dead). Restored templates + `$()` lookups; Forge is now dynamic-import so one studio parse failure cannot blank Chat. Live `notes/marathon-card255-spa-rail-fix-smoke.json`.
- **Forge Approve resumes same job_id [CARD-251 / REQ-FORGE-RESUME-001..004]**: Parked mid-job HITL Forge Approve promotes via 218 spine then unparks/`start_phase` on the **same** `job_id` / origin session (no orphan mint, no soft-delete). Forge UI resumes origin Chat + Observe one tree; Chat standing mint refuses orphan while `waiting_approval`. Live smoke `notes/marathon-card251-live-smoke.json`.
- **Education Priming/Dual Coding Wiki allowlist [CARD-241 / REQ-EDU-WIKI-001..003]**: Skills + Ask shaping only call catalog-matched `wiki_note_*` (never bare `wiki_overview`). Unregistered / out-of-matched-subset tool calls fail soft / skip so Execute can still land an Inbox note; Education skill matches expand to the `wiki_note_*` allowlist; job-bound turns stop offering `wiki_overview` to the model.

### Fixed

- **Unified Job phase chrome on Education origin [CARD-240 / REQ-JOB-CHROME-001..003]**: Education Ask forwards SSE phase events into Chat's grape-vine inline Job chrome (`updateJobChromeFromEvent` -> Formulate/Execute bars + `plan-steps`) and the shared strip; replays after `selectSession` so origin is not prompt-only. No Education-only progress UI.

### Added

- **Learning OS 1╬ô├ç├┤2**: Education Priming + Dual Coding skill seeds and Education Ask mode chips (Wiki schema / prose+Mermaid write-back via standing Jobs) [CARD-238].

### Fixed

- **HITL origin cohesion**: Education Ask keeps SSE after `job_created`, opens origin Chat for phase Approve, and Education Jobs show Needs approval / Approve in Chat [CARD-239 / REQ-HITL-ORIGIN-001..003].

### Fixed

- **Education Ask mint**: always create a fresh Education session (do not reuse Chat/phase `activeSessionId`); return on `job_created` so Ask cannot hang disabled [CARD-237 / REQ-EDU-SHELL-002a].

### Fixed

- **Education Studio P0**: stray brace in `app.js` tab loader blanked SPA (rail/dock never init); Education now dynamic-imported so one studio cannot take down `initApp` [CARD-237 / REQ-EDU-SHELL-005].

### Added

- **Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]**: New Education Studio in SPA nav + desktop dock. Wiki-backed ask (topic + how-to-teach + optional Wiki note search) mints a standing Job via the CARD-236 Chat `/api/chat/stream` path with outcome-shaped `done-when` / `success_rule`, shows copyable `job_id`, and lists Education Jobs with Open in Chat / Open in Observe. Shell + Job mint only ╬ô├ç├╢ no quiz/SRS/concept-player depth.

### Fixed

- **Chat Job strip + Journey show copyable `job_id` [CARD-236 / REQ-JOBMINT-005]**: When a standing Job is bound, the Chat Job strip and Journey header render the full `job_╬ô├ç┬¬` string (monospace chip) with one-click Copy so operators can paste into Observe without us supplying the id.
- **Chat outcome ask always mints standing Job [CARD-236]**: Wiki-write / done-when outcome-shaped Chat asks (incl. hyphenated `done-when:`) always create a durable Job via `create_job_from_catalog_resolve` before phase 1 ╬ô├ç├╢ never silent ReAct with `jobs=[]` after a successful outcome reply. Classifier covers create/write/save/author wiki|note deliverables; `derive_success_rule` extracts hyphenated done-when clauses. Chat fail-closes when orchestrator unavailable instead of ReAct-bypass theatre. Short chitchat stays plain ReAct. Observability standing-journey by `job_id` shows intake ╬ô├Ñ├å phases.

### Fixed

- **Chat composer hit-testing [CARD-235]**: Incomplete CARD-215 Goal-theatre cleanup left orphan Enable/dismiss buttons and a stray `</div>` that closed the composer `pointer-events-auto` wrapper early, so **+ Options** (and the rest of the form) sat under `#chatInputWrapper.pointer-events-none` and could not receive clicks. Removed the orphan controls, restored nesting, set `pointer-events: auto` on `#chatForm` / Options, and disabled maximized window resize hit-targets so they cannot cover the composer. Dock chrome remains PE-none with PE-auto only on `.desktop-dock-shell`.

### Added

- **Supervisor specialist pick from matched catalog [CARD-234]**: `JobPhaseOrchestrator.supervisor_pick_specialist` picks handoff targets **only** from matched catalog agent/pack IDs (working set) ╬ô├ç├╢ not free-form role theatre. Reuses CARD-224 standing child job (never-widen + linked `child_job_id` + checkpoint). Out-of-catalog handoff rejected; no specialty match => park/scaffold (233) or fail-closed (never invent). Observability journey `standing.supervisor_pick` + Chat strip parent╬ô├Ñ├╢child link. Closes wave 2 (230╬ô├ç├┤234).

- **Mid-job self-scaffold via 218 spine [CARD-233]**: When a running Job hits a capability gap (tool/skill missing for `success_rule` / phase), standing runtime opens a **candidate** draft via `SelfScaffoldSpine` ╬ô├ç├╢ never writes trusted from a live phase. Path: draft ╬ô├Ñ├å sandbox ╬ô├Ñ├å version ╬ô├Ñ├å HITL approve ╬ô├Ñ├å trusted ╬ô├Ñ├å catalog re-resolve (updates matched IDs on checkpoint). Until HITL promotes, Job parks (or continues with remaining matched only) ╬ô├ç├╢ no silent candidate-as-trusted. Observability journey shows `standing.scaffold_candidate` + `standing.scaffold_hitl` + `standing.catalog_reresolve`; Forge candidate queue is the operator path. Rejects unscoped trusted write mid-phase. Extends 215╬ô├ç├┤232 + 218 only.

- **Bounded auto-replan on verifier failed [CARD-232]**: On standing verifier `failed`, Job auto-replans remaining phases against the same `success_rule` + matched capability IDs (never silent advance). Cap `MAX_REPLAN_ATTEMPTS=3` (durable `replan_count` on checkpoint); 4th fail => HITL park with `last_fail_reason` (not infinite loop, not auto-success). `skipped_no_checker` still does not replan and never counts as verified advance (216). Observability standing journey shows `standing.replan` + `standing.replan_park` spans. Extends 215-231 only.

- **Standing research-before-plan on capability gap [CARD-231]**: After intake catalog resolve, thin/gap matches (empty IDs, below threshold <2, or missing critical roles implied by `success_rule`) insert a **Research** phase before Formulate/Execute. Sufficient matches skip research (Formulate/Execute only ╬ô├ç├╢ no latency tax). Research writes facts into `<agent>_memory.db` and may propose catalog gaps; never writes trusted skills/tools (218/233). Checkpoint persists `research_inserted` + reason; Observability standing journey shows `standing.research` span. Extends 215╬ô├ç├┤230 only.

### Added

- **Outcome intake ╬ô├Ñ├å durable Job + success_rule [CARD-230]**: Outcome-shaped Chat asks (multi-step / goal / deliverable language) create a standing Job with a **testable** `success_rule` stop condition and catalog-resolved `matched_capability_ids` before phase 1. Vibes-only rules (`"looks good"`) reject at intake. Agent picker is preference only ╬ô├ç├╢ matched IDs remain capability authority. Fail-closed phase-1 gate when either field is missing. Extends 215╬ô├ç├┤229 standing path only (no second orchestrator).

### Added

- **Phase-scoped working-set context [CARD-229]**: Each standing Job/Phase turn carries phase goal + matched capability metadata + **bound** skill body only + this-phase `memory.db` facts. Prior phases distill to short durable notes (tool dumps / unbound skill bodies stripped; M12 ContextCompactor truncation aligned). Wired into Chat standing + crash-resume and Routines standing path. AGENTS.md invariant: Chat still lists ticked tools every turn.

### Added

- **Progressive SKILL.md disclosure [CARD-228]**: Catalog/resolve returns skill metadata only (`id`, `title`, `risk`, HITL flags) ╬ô├ç├╢ never full `SKILL.md` bodies (qwen context tax / theatre). Standing Job/Phase `bind_skill_for_phase` loads one runbook body on phase bind/select (`skill_bound` journey event + SSE). `POST /api/capabilities/bind-skill`. Chat still mounts that agent's ticked tool schemas every turn (AGENTS.md / CARD-117/121 invariant).
- **Observability standing journey timeline [CARD-227]**: One `job_id`-correlated standing path replay (`GET /api/observability/standing-journey`) with OpenTelemetry-style GenAI agent span tree. Includes Job/Phase steps, catalog matches, verifier statuses, CARD-221 policy decisions (MCP BLOCKs), durable A2A `child_job_id` links, and `resumed_from_checkpoint` events. Observability Studio filter UI closes scattered-panel theatre.

### Added

- **Job/Phase cross-phase memory.db recall [CARD-226]**: Standing Job/Phase path persists phase reflections/facts into per-agent `<slug>_memory.db` via CARD-116 `AgentMemoryRepository` (never `<slug>_storage.db`). Checkpoints stamp accumulating `memory_fact_ids`. Kill/resume rebuilds prior from memory.db for phase N+1 (`memory_recalled` SSE + `GET /api/observability/job-phase-memory`). Closes ephemeral-prior theatre on resume.

### Added

- **MCP tools through matched-subset + CARD-221 gate [CARD-225]**: MCP ools/list / mount is transport only (listing ╬ô├½├í authorization). Mounted mcp_<server>_<tool> calls hit matched capability subset (when job-bound) and ToolPolicyGate ALLOW / REQUIRE_CONFIRM / BLOCK before executor. Outside-subset / unknown MCP ╬ô├Ñ├å BLOCK (never runs). Dangerous MCP names ╬ô├Ñ├å REQUIRE_CONFIRM ╬ô├Ñ├å existing HITL. Extends MCPClientAdapter / ScopedToolRegistry / ToolPolicyGate ╬ô├ç├╢ no parallel auth.

### Fixed

- Standing Job/Phase LLM hang no longer leaves orphan RUNNING phases: routine and Chat standing turns bound by `STANDING_PHASE_LLM_TIMEOUT_SECONDS` and call `fail_phase` with checkpoint on timeout/cancel/error [CARD-222 reliability].

### Added

- **A2A handoff inherits standing Job/Phase path [CARD-224]**: Linked `child_job_id` inherits parent matched capability IDs (no cold re-resolve / no tool widen). `HandoffResult` stamps `parent_job_id`/`child_job_id`; child has own checkpoint; CARD-221 BLOCK/REQUIRE_CONFIRM preserved; kill╬ô├Ñ├åresume same child `job_id`. `/api/agents/delegate` prefers `HandoffIsolationEngine`; `handoff_to_agent` stamps `parent_job_id` from tool context; child `stream_turn` bound to `job_id`; kernel resolves matched IDs for the tool policy gate when job-bound. Lazy `ToolPolicyGate` import breaks kernel╬ô├Ñ├╢policy circular import.
- Marathon scorecard `notes/marathon-scorecard-standing-job-graph.md` (cards 215╬ô├ç├┤224).

- **Routines join standing Job/Phase path [CARD-222]**: Cron/scheduler remains trigger-only. Multi-step `RoutineExecutor` calls `JobPhaseOrchestrator.create_job_from_catalog_resolve` (same catalog R/H/E + matched IDs + verifier gate + CARD-221 policy/HITL as Chat). Durable `job_id` on `RoutineRun` / routine metadata; crash-resume same `job_id`. Short prompts stay plain ReAct. Special curator/skill-eval jobs unchanged. Trigger/run API returns durable job_id.
- **Steering truth sync [CARD-223]**: Roadmap M15╬ô├ç├┤17 marked Done/Superseded (MCP, external verifier/Reflexion, Job-Graph superseding Goal-mode). `steering/product.md` no longer claims a shipped Docs Studio (`docs.js` absent). FastAPI OpenAPI version aligned to package `0.28.0`. `PROJECT.md` labeled stale audit brief.
- **Tool policy gate [CARD-221]**: Every tool call gets durable `ALLOW` / `REQUIRE_CONFIRM` / `BLOCK` via `ToolPolicyGate` before the executor (registry listing ╬ô├½├í authorization). `REQUIRE_CONFIRM` parks through existing HITL; `BLOCK` fail-closed. Decision log + `GET /api/observability/tool-policy-decisions`. Extends DangerousCommandFilter / HITL ╬ô├ç├╢ no parallel HITL.
- **Chat standing path uses catalog resolve [CARD-220 anti-theatre]**: `/api/chat/stream` multi-step now calls `JobPhaseOrchestrator.create_job_from_catalog_resolve` (Research/Handoff/Execute + matched capability IDs); emits `catalog_resolved`. App wires `capability_resolver` into the orchestrator. Short turns stay plain ReAct.

### Added

- **Catalog Resolve into JobPhaseOrchestrator [CARD-220]**: Standing Capability Catalog C runtime ╬ô├ç├╢ `JobPhaseOrchestrator.create_job_from_catalog_resolve` maps `intent ╬ô├Ñ├å matched subset ╬ô├Ñ├å Research / Handoff / Execute`. Matched capability IDs persist on `job_phase_checkpoints` (extend CARD-219); `resume_after_crash` reuses the same subset (no cold re-resolve drift). Advance rules: only `verified` advances Execute; `failed` ╬ô├º├å park + `needs_replan`; `skipped_no_checker` never counts as verified advance (Research/Handoff may continue on honest skip). Out of scope: UI polish, new Studios.

- **Job/Phase Crash-Resume Checkpoints [CARD-219]**: Durable `job_phase_checkpoints` rows after each phase commit (`job_id`, phase index, verifier status `verified|skipped_no_checker|failed`, HITL park state). `JobPhaseOrchestrator.resume_after_crash` continues the same `job_id` after mid-phase process kill (LangGraph-style); replan-from-zero only when checkpoint is corrupt/missing. Chat SSE + Job/Phase strip + Observability surface `resumed_from_checkpoint`. Extends existing SQLite Job/Phase persistence ╬ô├ç├╢ no second graph engine.
- **Self-Scaffold Spine [CARD-218]**: New skill/tool always lands **candidate** (never trusted by default). Durable `scaffold_spine` path draft ╬ô├Ñ├å sandbox_exec ╬ô├Ñ├å version ╬ô├Ñ├å HITL approve ╬ô├Ñ├å trusted. Run gate rejects unsandboxed candidates; unscoped write to trusted is rejected; rollback restores prior trusted via UserSkillCatalog snapshots. Agent Forge candidate queue + `/api/capabilities/scaffold/*`. Extends propose_skill/HITL/catalog (no second product). Cite SoK Agentic Skills arXiv 2602.20867. Out of scope: crash-resume (CARD-219).

- **Capability Catalog C (match-only) [CARD-217]**: Progressive capability index over `agent|skill|tool|pack|routine` with trust tiers (`candidate`╬ô├Ñ├å`reviewed`╬ô├Ñ├å`trusted`), risk + HITL flags, SQLite `capability_index`, and `POST /api/capabilities/resolve` returning a matched **subset only**. Operator `GET /api/capabilities/registry` is capped and marked `prompt_dump_forbidden`. No dump-all-for-prompt path. Out of scope: self-scaffold write spine.

- **Standing External Verifier Policy [CARD-216]**: Reflexion/retry only when a named binary checker is present (pytest/schema/health/tool). Missing checker yields durable `skipped_no_checker` (never same-model pass). Wired via `external_verifier_policy` phase-complete gate + `run_verified_turn`; Chat/Observability surface `verified` / `skipped_no_checker` / `failed`. Cites Shinn Reflexion 2023; Panickssery 2024 same-model judges.

- CARD-215 In Review (`AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre` - CARD-215):
  - **Standing Job-Graph Runtime**: Multi-step Chat outcomes formulate/advance durable Job+Phase rows via `JobPhaseOrchestrator` without requiring `goal_mode=true`. Short turns stay plain `AgentKernel` ReAct.
  - **Retire Goal-mode theatre**: Removed Chat UI Goal toggle and Goal suggestion chip; `goal_mode` on `/api/chat/stream` is ignored for routing. `POST /api/chat/goal` is deprecated to formulate-into-Job/Phase only (no `execute_plan` bypass).
  - **PlanAndExecuteEngine formulator-only**: Kept as no-tool phase formulator writing into Job/Phase; `execute_plan` marked retired as parallel execute authority.
  - **Honest verify**: `self_verify` / Reflexion runs only with a named external checker; missing checker yields honest skip (no same-model-only success).
  - **Replan**: `JobPhaseOrchestrator.replan_job` replaces queued remaining phases while preserving DONE history.

## [0.28.0] - 2026-09-10

- CARD-213 Done (`AutoReiv.Gateway`, `AutoReiv.Settings`, `AutoReiv.Chat` - CARD-213):
  - **Google Gemini Provider Compatibility & Tool Message Sanitization**: Fixed silent hanging and HTTP 400 errors when using Google Gemini as the LLM provider in Chat Studio (`#view-chat`).
  - **Orphan Tool Call Sanitization**: In `OpenAIProviderAdapter._format_messages()`, unlinked or orphan `role: "tool"` messages without a matching `tool_call_id` in the immediately preceding assistant turn (from past provider runs, approval pauses, or handoffs) are automatically transformed into clean user context notes (`[Tool Output: <name>]: <content>`), preserving full conversational history while preventing Google Gemini's OpenAI endpoint from rejecting calls with `HTTP 400: function_response.name: Name cannot be empty`.
  - **Verified Model Recommendations**: Updated Gemini model catalog in `presets.py` to verified, low-latency models (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.1-flash-lite-preview`), deprecating non-existent models (`gemini-3.8-flash`, `gemini-3.5-flash`).
  - **Automatic Obsolete Model Normalization**: Added automatic migration in `src/web/routers/settings.py` and `OpenAIProviderAdapter._format_model_name()` that normalizes dead Gemini model names in stored provider configurations to `gemini-3.6-flash` / `gemini-3.7-flash`.

- CARD-212 Done (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Web` - CARD-212):
  - **LLM Provider Hybrid Credential Vault Picker**: Added a hybrid credential source selector (`#provVaultCredSelect`) in Settings Studio allowing operators to link any provider directly to an existing Credential Vault secret or type a direct key.
  - **Direct & Linked Vault Modes**: Selecting an existing Vault credential disables the input field and displays a linked badge (`Linked: <name>`), preventing secret duplication and ensuring single-source-of-truth credential management. Selecting "Direct Secret Input (Auto-Vault)" re-enables direct input to auto-encrypt secrets to `llm-provider-{pid}`.
  - **Live Vault Synchronization**: The credential picker dynamically refreshes when secrets are added, edited, or deleted in the Credential Vault table below.
  - **Dynamic Gateway & Model Discovery Binding**: Backend `POST /api/settings/providers` persists `vault_cred_id`, while `/api/settings` and `/api/models/discover` resolve keys dynamically from the linked Vault credential.

- CARD-211 Done (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Gateway` - CARD-211):
  - **Per-Provider LLM Credentials & Vault Persistence**: Updated `provider_settings` to persist configurations as an independent per-provider map (`gemini`, `openai`, `anthropic`, `ollama`, etc.), ensuring swapping between providers never clears or overwrites saved API keys.
  - **AES-256-GCM Vault Encryption**: Integrated LLM provider secrets with AutoReiv's Credential Vault (`credentials` table). API keys are encrypted at rest with zero plaintext secrets exposed in SQLite settings.
  - **Automatic Legacy Key Migration**: On boot and first load, existing legacy plaintext keys (including active Google Gemini keys) are automatically migrated into encrypted Vault records.
  - **Settings Studio Vault Hydration & Masking**: Changing the Provider Preset dropdown dynamically restores the provider's saved host URL, displays an "Encrypted in Vault" badge (`#provKeyVaultBadge`), and masks saved credentials (`╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│`) to prevent accidental key exposure while allowing one-click overrides.
  - **Vault-Aware Model Discovery**: Updated `/api/models/discover` to dynamically resolve provider keys directly from the Credential Vault when omitted from client query parameters.

## [0.27.0] - 2026-09-10

- CARD-210 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-210):
  - **Enterprise Neutral Chrome & Restrained Theme Accents**: Window shells and focused borders use neutral white/alpha borders (`rgba(255, 255, 255, 0.10)`) and elevation shadows without brand halos. Window titlebar icons retain clean slate chrome (`#94a3b8`).
  - **Enterprise Palette Presets**: Recalibrated preset color models for professional enterprise workstations: Indigo, Slate Graphite, Violet, Warm Sand, and Teal.
  - **Storage Key Upgrade**: Upgraded client theme persistence to `autoreiv.theme.v2` to prevent legacy neon/high-saturation test settings from sticking across browser sessions.

- CARD-209 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-209):
  - **Dynamic Stage Wallpaper Theming**: Routed `.desktop-wallpaper` radial gradients and backgrounds through `--theme-brand-glow`, `--theme-bg-surface`, and `--theme-bg-base`, allowing the background desktop stage to transform organically with active themes.
  - **Deep Studio Card & Panel Skinning**: Mapped hosted studio cards, panels, and containers (`.bg-slate-900`, `.bg-slate-950`, `.card-nested`, and border dividers) to `--theme-bg-surface` and `--theme-border`, extending palette colors deeply across all windows (Settings, Observability, Routines, Chat).
  - **Primary Buttons & Metric Highlights**: Mapped primary action buttons (`button.bg-brand-600`, `button.bg-indigo-600`, `.btn-primary`) and text highlights (`.text-indigo-400`, `.text-brand-400`) to `--theme-brand` with calculated high-contrast text (`--theme-brand-contrast`).
  - **Rich Palette Tuning**: Enhanced prebuilt presets with distinctly calibrated dark base and surface tones for Amber Phosphor, Emerald Matrix, Orbital Monochrome, and Obsidian Slate.

- CARD-208 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Settings` - CARD-208):
  - **Theme Customizer and Color Palette Presets**: Added an interactive theme customizer to Settings Studio (`#view-settings` -> `#settingsThemeCard`) with 5 prebuilt themes: AutoReiv Indigo, Orbital Monochrome, Obsidian Slate, Amber Phosphor, and Emerald Matrix.
  - **Slider-Style Custom Palette Tuner**: Implemented custom palette controls with Hue (0-360Γö¼Γûæ), Saturation (0-100%), and Background Tone (0-30%) range sliders allowing real-time color adjustments, dynamic hex display tags, and instant window preview.
  - **CSS Variable Architecture**: Routed desktop window shells, titlebars, dock buttons, and active borders through dynamic CSS custom properties (`--theme-brand`, `--theme-brand-hover`, `--theme-brand-glow`, `--theme-bg-base`, `--theme-bg-surface`, `--theme-border`), providing seamless real-time theme switching without DOM recreation.
  - **Persistence & Reset**: Added browser local storage caching under `autoreiv.theme.v1` with automatic boot restoration and a one-click Reset button to restore defaults.

- CARD-207 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Desktop` - CARD-207):
  - **Sessions Window Studio Cleanup**: Hid the redundant "All Studios" navigation grid (`#sidebarNav`) and close button when opening the Sessions drawer/window in desktop mode, giving the recent conversation history list (`#sessionList`) full vertical space to display and scroll.
  - **Studio Page Vertical Scrolling**: Updated `.tab-view.desktop-view-hosted` layout rules so page-style studio views╬ô├ç├╢including Settings (`#view-settings`), Routines (`#view-routines`), Observability (`#view-observability`), and any scrollable tab views╬ô├ç├╢allow smooth vertical scrolling without clipping content on both desktop floating windows and mobile viewports.
  - **Desktop Window Resize Layer & Corner Handles**: Changed `#desktopWindowLayer` to `display: contents` and elevated window shells and 8-directional resize handles to `win.z + 2` above hosted views (`win.z + 1`), completely eliminating stacking context traps that prevented corner clicks. Attached pointer drag/resize handlers to `window` on interaction to prevent event drop during rapid cursor movements.
  - **Dynamic Sessions Window Stacking & Alignment**: Removed hardcoded `z-index: 50 !important` and replaced `inset: auto` with explicit bounds on `#sidebar`, ensuring conversations embed directly into the draggable `#desktopWin-sessions` window shell. Hid the redundant internal drawer header (`#sidebarDrawerHeader`), leaving a single unified window titlebar with smooth dragging and corner resizing.
  - **Window Clarity & Sharp Text Rendering**: Removed `backdrop-filter: blur(10px)` from `.desktop-window` shell overlay, resolving blur artifacts that softened text and UI elements across all floating windows.

- CARD-206 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-206):
  - **Online ACE Proposal Deduplication & Approval Filter**: Hardened `ace_online.py` and `agent_kernel.py` so standard HITL `approval_required:` tool execution pauses are never misclassified as tool execution errors, completely eliminating runaway and duplicate draft skill proposals during agent execution loops (`[REQ-HOMELAB-005]`).
  - **OpenTofu Compiler Diagnostic Extraction**: Added `extract_hcl_diagnostics` to `opentofu_tools.py` parsing both structured JSON and human-readable CLI compiler errors (`tofu validate` and `tofu plan`) into actionable `{file, line, summary, detail, severity}` records, empowering the Homelab Engineer to self-correct HCL syntax errors autonomously (`[REQ-HOMELAB-004]`).
  - **Domain Topology HCL Generator & Network Isolation Invariants**: Implemented `generate_domain_topology_hcl` in `homelab_domain_recipe.py` enforcing strict safety invariants: private isolated `Internal` virtual switch (`DomainSwitch`), 10.10.10.0/24 subnet, and 3 Gen2 VMs (`DC01`, `DC02`, and `FS01`) with static memory and zero modifications or exposure to physical host network adapters (`[REQ-HOMELAB-002]`, `[REQ-HOMELAB-003]`).
  - **Multi-Agent Homelab Domain Workflow Recipe**: Defined the reusable 4-chapter relay recipe `homelab-domain-deployment` (`homelab-admin` -> `homelab-architect` -> `homelab-engineer` -> `homelab-admin`) with strict per-phase success criteria (`[REQ-HOMELAB-001]`, `[REQ-HOMELAB-006]`).
  - **OpenTofu Hyper-V Skill Runbook**: Authored canonical `skills/opentofu-hyperv/SKILL.md` runbook codifying Hyper-V provider syntax, Gen2 VM configurations, compiler-guided self-correction protocols, and dry-run safety gates. Equipped `homelab-engineer` pack with `opentofu-hyperv` (`[REQ-HOMELAB-004]`).

- CARD-205 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Factory` - CARD-205):
  - **Multi-Window Agent Desktop Adoption**: Formally adopted the OS-style Agent Desktop environment (`#desktopStage`, `#desktopDock`, `#desktopWindowLayer`) on `qa`. Dock launchers open Chat, Wiki, Projects, Agents, Factory, Routines, Observability, Settings, Prompts, and Sessions as draggable, resizable, stackable floating windows.
  - **Factory Orchestrator Constructor Fix**: Assigned `self.store = store` in `FactoryOrchestrator.__init__`, resolving an `AttributeError` that impacted Agent Training Factory background advancement and verification battery phases.
  - **Defensive DOM Architecture Compliance**: Replaced raw `document.getElementById` lookup in `agent-desktop.js` with defensive `$` query helper from `dom.js` satisfying `REQ-DOM-001`. Added `id="${d.id}"` attributes to dock buttons for explicit DOM element targeting.
  - **Modal Layer Elevation**: Elevated all modal dialogs (`aria-modal="true"`) to `z-index: 120 !important` so modal cancellation and confirmation buttons are never intercepted by the bottom application dock.
  - **Automated Smoke Test Modernization**: Modernized Playwright E2E smoke suite (`smoke.spec.js`) to test the desktop dock launchers and multi-window interface across all studios with zero console errors.

## [0.26.0] - 2026-09-09

- CARD-204 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-204):
  - **Pure Chat Runtime Promotion**: Decoupled Goal and Self-Verify execution entirely from agent platform tool schemas. Multi-phase jobs and reflexion critic loops operate strictly as server-side runtimes triggered by Chat Studio toggles (`goalMode`, `selfVerify`).
  - **Retired Planning & Verification from Platform Skills**: Removed `planning` ("Goal Planning Engine") and `verification` ("Logic Verification (Critic)") from `PLATFORM_SKILL_TOOLS`, `PLATFORM_SKILL_METADATA`, and `BUILTIN_TOOL_GROUPS`. Platform skills in Agent Studio Box 1 are strictly the 5 active tool suites (`wiki`, `coordination`, `proposals`, `worker`, `sandbox`).
  - **Pruned Skill Seeds**: Removed `planning` and `verification` from `BUNDLED_PACK_IDS` and deleted their bundled runbooks from `src/infrastructure/skills/seeds/`. Added both to `BLED_AGENT_SKILL_IDS` to ensure automatic pruning from `$DATA_DIR/skills/`.
  - **Prompt Token Savings**: Removed dead tool schemas (`formulate_plan`, `get_active_plan`, `append_plan_step`, `mark_plan_step_completed`, `assert_json_schema`, `validate_metric_bounds`) from agent turn payloads.

- CARD-203 Done (`AutoReiv.Skills`, `AutoReiv.Packs`, `AutoReiv.Data` - CARD-203):
  - **Zero Skill Bleed on Inbound Pack Import**: Removed `_copy_skills_in` from `AgentPackService._import_folder`. Agent pack skills stay strictly isolated under `packs/<agent_id>/skills/` and are never copied into `$DATA_DIR/skills/`.
  - **Pack-Aware Skill Export**: Updated `_copy_skills_out` to read from the agent's dedicated `packs/<agent_id>/skills/` folder first, preventing false dependencies on the platform skills directory.
  - **Platform Skills Isolation**: Hardened `forge.js` `loadPlatformSkills()` to render exclusively the verified `platform_skills` from `/api/skills/catalog`, eliminating fallback polling of `$DATA_DIR/skills/`.
  - **Automated Data Pruning in Resolver**: Added `prune_bled_platform_skills` and `prune_orphan_databases` to `bootstrap_data_dir` to automatically remove historical bled agent skills from `$DATA_DIR/skills/` and unlink 0-byte orphan state/storage database files.
  - **Purged Retired Personas**: Deleted retired persona directories (`coder/`, `critic/`, `inspector/`, `sandbox_runner/`) from `platform-packs/` and cleaned obsolete `fleet.json` and `shared_skills/` discovery logic from `agents.py` and `user_catalog.py`.

## [0.25.0] - 2026-09-09

- CARD-202 Done (`AutoReiv.Web`, `AutoReiv.UI` - CARD-202):
  - **Flat Alphabetized Agent Studio Picker**: Removed `<optgroup>` categorizations ("Primary Specialists" and "Internal / Fleet Workers") from Agent Studio (`#forgeAgentSelect`). All agents are rendered in a single, clean list sorted alphabetically from A to Z.
  - **Simplified Platform vs. Custom Tagging**: Options in the Agent Studio dropdown display only `${name} (Platform)` (for built-in and platform agents) or `${name} (Custom)`, eliminating `[fleet]` and `(Internal)` badge clutter.

- CARD-201 Done (`AutoReiv.Web`, `AutoReiv.Skills`, `AutoReiv.Fleet` - CARD-201):
  - **Strict Platform Primitives in Box 1**: Locked `/api/skills/catalog` `platform_skills` strictly to the 7 core platform primitives (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`), preventing user skills or domain runbooks from ever polluting Box 1.
  - **Platform Skills Leakage Guard in Box 2**: Hardened `AgentPackManifest.derive_compat_lists`, `AgentPackService`, and `_pack_skills_payload` so platform capability IDs (`wiki`, `coordination`) ticked in `allowed_skill` are never synthesized into pack skills or rendered in Box 2 (**Agent Pack Skills & Tools**).
  - **Permanent Platform Skills (Zero Dynamic Filtering)**: Eliminated `pack_owned` filtering in `/api/skills/catalog` and `packOwnedIds` filtering in `forge.js`. All 7 core platform skill primitives are permanently visible in Box 1 (**Platform Skills & Tools**) for every agent.
  - **Strict Two-Box UI**: Removed `#forgeFleetBox` entirely from Agent Studio (`index.html` and `forge.js`). Restored the clean two-tier layout: Box 1 (Platform Skills & Tools) and Box 2 (Agent Pack Skills & Tools).
  - **1:1 Agent to Agent Pack on Disk**: Flattened the nested `platform-packs/homelab/` suite into 5 standard, top-level 1:1 agent pack folders: `homelab/`, `homelab-architect/`, `homelab-engineer/`, `homelab-admin/`, and `homelab-janitor/`. Removed `fleet.json`, `shared_skills/`, and nested `agents/` directories.
  - **Standard Platform Levers**: Homelab coordinator and architect agents leverage standard platform `wiki` tools (`wiki_note_read`, `wiki_note_search`, `wiki_note_create`) and platform `coordination` tools (`delegate_to_fleet_agent`, `lookup_agents`, `handoff_to_agent`), eliminating custom duplicate tools.
  - **Automated Platform Pack Seeding & Sync**: Updated `ALL_PLATFORM_PACK_IDS` and `install_platform_agent_packs` in `platform_packs.py` to automatically seed and synchronize all 5 homelab agents directly into the registry alongside platform core agents.

- CARD-200 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-200):
  - **Inline Skill Runbook Editor Placement**: Updated Agent Studio so clicking "Edit" mounts `#studioRunbookEditor` directly adjacent to the clicked skill row rather than rendering below remote MCP servers and credential cards.
  - **Platform Primitive Seed Runbooks**: Authored canonical Matt Pocock 5-section seed runbooks for `sandbox`, `coordination`, `worker`, `planning`, and `verification` in `src/infrastructure/skills/seeds/` and registered them in `BUNDLED_PACK_IDS`.
  - **Multi-Source Catalog Resolution**: Enhanced `UserSkillCatalog.resolve_pack_scoped_skill_md` to seamlessly resolve platform seeds, fleet shared skills (`shared_skills/`), and nested fleet agents.
  - **Accurate Not-Found Error Reporting**: Fixed `get_user_pack` endpoint so unarchived missing packs report `Pack '<id>' not found.` instead of misleading `Archived pack` text.

- CARD-199 Done (`AutoReiv.Fleet`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-199):
  - **Platform Wiki Skill Restoration & Visibility**: Fixed metadata conflict in `homelab-architect` and hardened the backend catalog endpoint so "Wiki & Knowledge Vault" (`wiki`) is consistently visible and functional in the Platform Skills & Tools container (`[REQ-FLEET-010]`).
  - **Unpolluted Core Platform Skills & Tools**: Removed domain-specific homelab infrastructure tools (`manage-opentofu-hyperv`, `lookup-network-spec`, `lookup-host-spec`) from `PLATFORM_SKILL_TOOLS`, keeping AutoReiv platform core strictly isolated (`[REQ-FLEET-011]`).
  - **Consolidated Multi-Agent Fleet Suite Layout**: Unified the 5 homelab specialist packs and their 3 shared skills under a canonical fleet suite format (`platform-packs/homelab/`) with `fleet.json`, `shared_skills/`, and `agents/` (`[REQ-FLEET-012]`).
  - **Agent Studio Three-Tier Skill Architecture**: Introduced `#forgeFleetBox` ("Fleet Shared Skills & Tools") between Platform Skills and Agent Pack Skills in Agent Studio, displaying fleet-wide shared runbooks and tools with batch select/clear actions (`[REQ-FLEET-013]`).
  - **Contextual Fleet Container Visibility**: Configured `#forgeFleetBox` to automatically appear when inspecting an agent belonging to a fleet and gracefully hide for standalone agents (`[REQ-FLEET-014]`).
  - **Consolidated Fleet Suite Single-Door Import & Export**: Updated `AgentPackService` to detect fleet manifests and seamlessly import and export multi-agent suites and their shared runbooks in one unified operation (`[REQ-FLEET-015]`).
  - **Redundant Wiki Toggle Deprecation**: Removed standalone `[x] Allow Wiki Access` toggle in Agent Studio Card 3 (`#forgeAllowWikiAccessCheckbox`), establishing the Platform Skills & Tools checkboxes as the single source of truth for agent Wiki grants.

## [0.24.0] - 2026-09-09

- CARD-196 Done (`AutoReiv.System`, `AutoReiv.Web`, `AutoReiv.SettingsStudio` - CARD-196):
  - **Installed Version & Runtime Environment Inspection**: Added dynamic version resolution, git commit hash, active branch name, and runtime deployment mode detection (`Git Clone`, `Docker Container`, `Systemd Service`, `Windows Service`, `Standalone`) surfaced in Settings Studio (`[REQ-UPD-001]`).
  - **Configurable Upstream Repository & Tracked Branch**: Implemented SQLite persistence and REST API endpoints (`GET/PUT /api/system/updates/config`) to allow operators to track private forks or mirrors (`[REQ-UPD-002]`).
  - **Automated Upstream Update Check & Changelog Preview**: Created `check_for_updates` endpoint querying upstream GitHub REST API or git remotes with commit distance comparison, release notes, and status indicators (`[REQ-UPD-003]`).
  - **Safe In-App Update Apply with Database Snapshotting**: Built one-click update apply with pre-flight dirty tree guard (`git status --porcelain`), timestamped SQLite backup (`autoreiv.db.bak-<timestamp>`), and fast-forward pull (`git pull --ff-only`) (`[REQ-UPD-004]`).
  - **Non-Git Deployment Guidance and Guardrails**: Added copyable upgrade commands (`docker compose pull && docker compose up -d`) for containerized deployments and abort protections on merge conflicts (`[REQ-UPD-005]`).

- CARD-198 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-198):
  - **Agent Visibility & Fleet Grouping**: Added `visibility` (`"public"` vs `"internal"`) and `fleet` metadata to `AgentProfile` and `AgentPackManifest`. Chat Studio filters out internal specialist workers while Agent Studio groups them under dedicated fleet sections (`[REQ-FLEET-001]`).
  - **Monolithic Hyper-V Deprecation**: Decoupled the legacy monolithic hyperv agent in favor of modular fleet capabilities and exempted it from chat selectors (`[REQ-FLEET-002]`).
  - **Enterprise IT Homelab Documentation Framework**: Populated standard IT documentation hierarchy (`00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`, `templates`) strictly under `notes/homelab/` with zero impact to the existing Wiki engine (`[REQ-FLEET-003]`).
  - **Homelab Fleet Roles & Starter Profiles**: Established starter profiles and platform packs for 5 homelab roles (`homelab` Coordinator, `homelab-architect`, `homelab-engineer`, `homelab-admin`, `homelab-janitor`) adhering to the 6-section system prompt blueprint (`[REQ-FLEET-004]`).
  - **Scoped Domain Lookup & Delegation Protocol**: Implemented `lookup_homelab_docs` and `delegate_to_fleet_agent` in `fleet_coordinator.py`, allowing the lead coordinator to inject note context and delegate directives to internal specialists (`[REQ-FLEET-005]`).
  - **OpenTofu Hyper-V Capability & Safe Tool Execution**: Created `manage_opentofu_hyperv` tool supporting plan, apply, destroy, validate, inspect_host, and get_vm_status with safe dry-run simulation mode (`[REQ-FLEET-006]`).
  - **Homelab Fleet Skills & Runbooks**: Authored runbook skills (`lookup-network-spec`, `lookup-host-spec`, `manage-opentofu-hyperv`) adhering strictly to Matt Pocock's 5-section layout and YAML frontmatter (`[REQ-FLEET-007]`).
  - **8-Stage Training Factory Dogfooding**: Programmatically executed AutoReiv's 8-stage Training Factory pipeline on `homelab-engineer`, verifying duration tracking, self-healing loop, and deliverable quality gates end-to-end (`[REQ-FLEET-008]`).

- CARD-197 Done (`AutoReiv.Agents`, `AutoReiv.Factory`, `AutoReiv.Web`, `AutoReiv.Orchestration` - CARD-197):
  - **Socratic Agent Pack Creation Directive**: Upgraded `build-agent-pack` skill and prompt directives with Socratic discovery, asking 3-4 targeted questions (specialization, host environment, safety/approval boundaries, tools needed) and instilling the 6-section system prompt architectural blueprint (`[IDENTITY & ROLE]`, `[DOMAIN BOUNDARIES & REFUSALS]`, `[EXECUTION PROTOCOL]`, `[SAFETY & APPROVALS]`, `[TOOL USAGE RULES]`, `[OUTPUT FORMAT]`) (`[REQ-FACT-046]`).
  - **Specialist Agent Quick-Scaffold Modal**: Added `#forgeNewAgentModal` with manual inputs for ID, display name, role, description, purpose slot, and safety requirements in Factory and Agent Studios, enabling rapid agent definition without conversational overhead (`[REQ-FACT-047]`).
  - **Post-Creation Agent Training Handoff Card**: Implemented an immediate post-creation card in Chat Studio (`[ Γëí╞Æ├£├ç Launch Training in Factory ]` and `[ ╬ô├£├ûΓê⌐Γòò├à Open in Studio ]`) enabling seamless one-click routing to Factory Studio pre-scoped with the newly created agent (`[REQ-FACT-048]`).
  - **8-Stage Factory Prompt Registry Refinement**: Upgraded default system prompts across all 8 pipeline stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) with agentic constraints, few-shot schema enforcement, and explicit context tokens (`[REQ-FACT-049]`).
  - **Self-Healing Verification Loop**: Added automatic repair edge (`retry_author`) and execution traceback forwarding from Verify to Author phase, enabling automatic self-healing (up to 2 attempts) before failing a training job (`[REQ-FACT-050]`).
  - **Per-Phase Execution Duration Tracking**: Recorded `duration_ms` on phase packets and rendered duration badges on visual flowchart stepper nodes in Factory Studio (`[REQ-FACT-051]`).
  - **Progressive Disclosure Runbook Standard**: Enforced 5-section progressive disclosure runbook layout (`## Overview`, `## Tools`, `## Order`, `## Pitfalls`, `## Done-when`) with YAML frontmatter in synthesized `SKILL.md` runbooks while preserving backward compatibility (`[REQ-FACT-052]`).
  - **Standardized Tool Return Envelope & Google-Style Docstrings**: Standardized synthesized tools to include Google-style docstrings (`Args:`, `Returns:`, `Raises:`) and structured dictionary return envelopes (`{"status": "success" | "error", "data": ..., "error": ...}`) (`[REQ-FACT-053]`).
  - **Tool Name Collision Guard in Promotion**: Added callable name inspection in promote phase and REST API to prevent duplicate callable names and cross-pack tool name collisions, supporting `allow_overwrite` flag for intentional updates (`[REQ-FACT-054]`).
  - **Tabbed HITL Promotion Deliverable Inspector**: Built tabbed deliverable inspection modal (`#factoryDeliverableModal`) with tabs for Runbook preview, Python tool code, and manifest diff (`pack.json`) for operator pre-promotion verification (`[REQ-FACT-055]`).
  - **Comprehensive Automated Verification**: All 1,048 Python backend tests and 284 frontend unit tests passing cleanly with zero lint errors.

## [0.23.0] - 2026-09-08

- CARD-195 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration` - CARD-195):
  - **Dedicated Agent Training Factory Studio**: Elevated the Agent Training Factory into a first-class, top-level Studio workspace (`#view-factory` / `#factoryStudio`) accessible via the navigation bar (`#navFactory`) and desktop app rail (`#railBtnFactory`).
  - **Single Hub Agent Context Dropdown**: Integrated `<select id="factoryAgentSelect">` directly in the Factory Studio header, dynamically populated from `/api/agents` with `All Agents (Platform View)` and all loaded specialist agents, strictly filtering out internal system agents (`agent_builder`, `agent-builder`) (`[REQ-FACT-040]`).
  - **Agent-Scoped Telemetry & Pre-Scoped Launcher**: Selecting an agent automatically filters historical and active runs, updates status filter counters and active run badges, filters the capability backlog, and turns the primary launch action into `[ Γëí╞Æ├£├ç Train <agent_name> ]` pre-scoped with target ID and starter objectives (`[REQ-FACT-041]`).
  - **Retirement of Agent Studio Training Buttons**: Removed `[Train in Lab]` (`#forgeTrainAgentBtn`) and `[Lab Monitor]` (`#forgeLabMonitorBtn`) from Agent Studio (`#view-forge`), consolidating all training lifecycle, monitoring, and HITL approvals exclusively within Factory Studio (`[REQ-FACT-042]`).
  - **Single-Pick Target Lock & Live Pack Verification in Training Launcher**: Streamlined `#trainAgentHandshakeModal` by removing redundant `<select id="trainAgentTargetSelect">` and `#trainAgentNameGroup`. The launcher directly locks to the selected agent from `#factoryAgentSelect`, rendering an on-disk inspection banner (`Target: <Agent>` with `packs/<agent_id>/`, existing skill count, and registered tool count) to guarantee training augments the target pack without duplicate definitions. In Platform View (`All Agents`), attempting to launch training prompts the operator to pick an agent first (`[REQ-FACT-043]`).
  - **Conversational New Agent Creator in Factory Studio**: Added `[ + New Agent ]` button (`#factoryNewAgentBtn`) directly in the Factory Studio top bar, which smoothly transitions the operator to Chat Studio to converse with AutoReiv to define the new agent's brief, instructions, identity, and tone prior to any capability training (`[REQ-FACT-044]`).
  - **Factory Studio Capability Gap Backlog Consolidation**: Relocated the "Needs Training" capability gap backlog (`#agentTrainingBacklogCard`) from Agent Studio into Factory Studio's Runs & Monitor view, dynamically rendering queued gaps for the selected agent (or all pending gaps in Platform View) with one-click training launch (`[REQ-FACT-045]`).
  - **Pipeline & Phase Prompts Sub-View**: Built visual 8-stage interactive flowchart canvas and Phase Prompt Inspector with read-only runtime context variable tokens (click-to-insert `{{seed_intent}}`, `{{objectives}}`, etc.), live prompt editing, platform-level SQLite persistence via REST API, and built-in default resetting.
  - **Training Runs & Live Monitor Sub-View**: Implemented a responsive two-pane layout with search filtering, status tabs (All, In Progress, Needs Review, Completed, Failed), an 8-stage visual progress stepper, HITL human-in-the-loop deployment gate with approved tools promotion, artifact preview modal triggers, and streaming packet activity feed with copy-to-clipboard.
  - **Mobile & Desktop Responsive Design**: Designed with mobile-first breakpoint adaptations, including an intuitive back-to-runs navigation button (`#factoryMobileBackToRunsBtn`) for small screens and sticky controls.
  - **Full Automated Verification & Zero Quality Gaps**: Added and verified comprehensive test suites in `tests/unit/frontend/factory_studio.test.js`, `tests/unit/frontend/train_agent_handshake.test.js`, and `tests/unit/frontend/auto_train_backlog.test.js` (276 frontend tests passing 100%), full Python test suites (107 tests passing 100%), zero eslint errors, zero ruff errors, and full RTM validation for `[REQ-FACT-034]` through `[REQ-FACT-045]`.

- CARD-175 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.HITL` - CARD-175):
  - **Agent Training Factory Instruction Registry & Dynamic Resolution**: Implemented backend system prompt registry and runtime customization for all 8 training phases (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`).
  - **SQLite Prompt Persistence & REST API**: Created `src/application/agent_training_factory/prompt_registry.py` managing `factory_phase_instructions` table in SQLite, and REST endpoints `GET`, `PUT`, `DELETE` at `/api/agent_training_factory/phases/instructions` and `/api/agent_training_factory/phases/{phase_id}/instructions`.
  - **Dynamic Phase Runner Integration**: Updated factory phase runners (`intent_distill.py`, `ground.py`, `blueprint.py`, `author.py`, `optimize.py`) to query dynamic system prompts via `get_phase_system_prompt(phase_id, db_path)`.
  - **Drawer Streamlining & Studio Path**: Kept the Lab Monitor drawer focused strictly on real-time activity and HITL deployment, delegating the dedicated visual prompt inspector and flowchart canvas to the dedicated Factory Studio (`CARD-195`).
  - **Agent Studio Action Hygiene**: Removed redundant `[Train New]` button from the Agent Studio header per operator direction, keeping `[Train in Lab]` on active agents.
  - **Full Automated Verification**: Added Python registry tests and REST API router tests, passing 100% with zero linter errors.

- CARD-122 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-122):
  - **Three Beats Alignment Protocol Embedded in Developer Agent**: Formally closed CARD-122, validating that the Three Beats working agreement is operationalized directly in the Developer Agent's `plan` runbook (`platform-packs/developer/skills/plan/SKILL.md`), canonical card templates (`card.template.md`), and the Master Constitution (`AGENTS.md` & `GEMINI.md`). Preserved strictly within the Developer Agent and SDLC workflow with zero external skill bloat.

- CARD-155 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-155):
  - **Open Standards Constitution & Rules Adoption**: Adopted the canonical DotAgents Protocol (`.agents/`) and `AGENTS.md` open standard for project constitutions and agentic rules under CARD-190, formally closing CARD-155. Intentionally excluded vendor-specific instruction files in favor of unified, vendor-neutral open standards for the Platform Developer Agent.

- CARD-149 Done (`AutoReiv.Agents`, `AutoReiv.Packs`, `AutoReiv.Memory` - CARD-149):
  - **Finance Specialist Agent Pack with Transaction Tracking**: Verified Personal Finance Lead user pack (`packs/finance`) with dedicated SQLite storage (`finance_storage.db`), `personal_finance` runbook, and tools for transaction ingestion (`log_transactions`), category budgeting (`manage_budget`), savings targets (`set_savings_goal`), and financial health reporting (`summarize_finances`).
  - **Isolated Storage & Automated Proof**: Confirmed 100% test pass in `tests/unit/orchestration/test_finance_agent_e2e.py` validating that personal ledger data remains fully isolated in `$DATA_DIR/packs/finance/` without modifying core `autoreiv.db`. Per operator direction, maintained as private user agent state external to git.

- CARD-193 Done (`AutoReiv.Deploy`, `AutoReiv.Docker` - CARD-193):
  - **Linux Systemd Service Uninstaller**: Created `deploy/systemd/uninstall_systemd.sh` providing clean automated uninstallation that stops and disables `autoreiv.service`, cleans up service unit files, removes `/opt/autoreiv`, and preserves `/var/lib/autoreiv` persistent storage by default unless `--purge-data` is explicitly passed.
  - **Linux Systemd Service & Installer Alignment**: Modernized `deploy/systemd/autoreiv.service` to declare single canonical `Environment="AUTOREIV_DATA_DIR=/var/lib/autoreiv"`. Updated `deploy/systemd/install_systemd.sh` to initialize directory layout and sync `templates/` into the installation tree.
  - **Windows Service Uninstaller**: Created `deploy/windows/uninstall_windows_service.ps1` with Administrator privilege checking to safely stop and unregister `AutoReivService` via NSSM with fallback to `sc.exe delete`, preserving local app data.
  - **Docker & Docker Compose Modernization**: Updated `Dockerfile` to copy `templates/` into `/app/templates/` with `autoreiv:autoreiv` ownership for Developer Agent project scaffolding, and provisioned `/data` subdirectories. Modernized `docker-compose.yml` by removing obsolete top-level `version: '3.8'` and verifying persistent volume mounts.
  - **Deploy Suite Documentation & Verification**: Added comprehensive operator manual in `deploy/README.md` and automated test suite in `tests/unit/deploy/test_deploy_suite.py`.

- CARD-189 Done (`AutoReiv.Skills`, `AutoReiv.PlatformPacks`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-189):
  - **Retirement of `propose_workflow` Tool**: Removed obsolete `propose_workflow` tool registration and handler from `AgentBuilderTools` (`agent_builder_tools.py`) and `skill_proposals.py`. Removed `propose_workflow` from Platform skill `proposals` in `schema.py`, builtin tool groups in `manifest.py`, and allowed tool lists on `AGENT_BUILDER_PROFILE` (`profiles.py`), `platform-packs/assistant/pack.json`, and `platform-packs/autoreiv/pack.json`.
  - **Unified Capability Proposals Platform Skill**: Collapsed the duplicate `recommend-capability` runbook and `proposals` tools container into a single unified Platform Skill: `proposals` ("Capability Proposals & Discovery"). Relocated the seed runbook to `src/infrastructure/skills/seeds/proposals/SKILL.md` and updated `BUNDLED_PACK_IDS`. Added automatic cleanup of legacy `recommend-capability` folders during startup seeding, eliminating the redundant empty skill row from Agent Studio and connecting the 7 proposal tools directly to their operating runbook.

- CARD-192 Done (`AutoReiv.SDLC`, `AutoReiv.Developer`, `AutoReiv.Skills` - CARD-192):
  - **Developer Agent End-to-End Verification**: Supervised the Developer agent across a complete 10-feature real-world project (`SentinelPulse`) built inside `agentic-test` with zero external wheel dependencies (`[REQ-DEVVER-001]` - `[REQ-DEVVER-012]`).
  - **Strict TDD & SOLID Verification**: Followed red-green-refactor TDD on all 10 vertical slices (`models.py`, `storage.py`, `probes.py`, `rules.py`, `alerts.py`, `remediation.py`, `circuit_breaker.py`, `diagnostics.py`, `reporter.py`, `cli.py`), achieving 35/35 passing automated tests and zero ruff lint errors (`[REQ-DEVVER-012]`).
  - **Project Scaffolding .gitignore & Git Repository Initialization**: Enhanced `ProjectsService.create_project` to automatically initialize git repository (`git init -b main`) on project scaffolding and added standard `.gitignore` to `REQUIRED_SCAFFOLD` and `templates/sdlc-project/` to prevent bytecode and cache clutter (`[REQ-DEVVER-001]`).
  - **GitTools Conventional Commit Message Alias**: Updated `GitTools.git_commit` to accept `message` as an alias for `subject`, preventing unexpected keyword argument runtime exceptions when agents invoke git commit tools (`[REQ-DEVVER-011]`).

- CARD-191 Done (`AutoReiv.Web`, `AutoReiv.Projects` - CARD-191):
  - **Active Project State & Explicit Selection**: Upgraded Projects Studio project rows with an explicit "Set as Active" action button and persistent `[Active Project]` green indicator badge (`[REQ-PROJ-010]`).
  - **Two-Pane Workspace Layout**: Expanded Projects Studio from a simple list into a full dual-pane web workspace with Directory Explorer on the left and Artifact Viewer on the right (`[REQ-PROJ-011]`).
  - **Directory Tree Navigation & Quick Filters**: Implemented collapsible folder navigation with file-type iconography and quick category filter buttons for **All**, **Cards** (`.agents/cards/`), **Specs** (`.agents/specs/`), **Steering** (`.agents/steering/`), and **ADRs** (`.agents/adr/`), plus real-time search filtering (`[REQ-PROJ-012]`).
  - **Artifact & File Viewer**: Added rich viewer rendering formatted Markdown via `marked` for cards/specs and styled monospace views for code scripts (`.py`, `.ps1`, `.json`, etc.) with file path breadcrumbs, character counts, and one-click path copying (`[REQ-PROJ-013]`).
  - **Mobile Responsive Reading & Touch Scrolling**: Clamped directory tree height on mobile (`max-h-48`) with independent touch scrolling, added mobile tree collapse/expand toggle controls, and auto-focused the reading pane with full-height scrolling on file selection (`[REQ-PROJ-011]`, `[REQ-PROJ-013]`).
  - **Jailed Project File API Endpoints**: Implemented secure `GET /api/projects/files/list` and `GET /api/projects/files/read` endpoints strictly clamped inside the active project root, filtering out `.git`, `__pycache__`, and `node_modules` (`[REQ-PROJ-014]`).

- CARD-190 Done (`AutoReiv.SDLC`, `AutoReiv.Skills` - CARD-190):
  - **DotAgents Protocol Directory Standardization**: Adopted the open DotAgents Protocol (`.agents/`) as the canonical project-level directory convention, eliminating artifact fragmentation (`[REQ-SDLC-060]`).
  - **Dual-Path SDLC Resolution**: Enhanced `CardTools` with dual-path resolution to prioritize `.agents/cards/`, `.agents/specs/`, and `.agents/steering/` while seamlessly falling back to legacy `docs/cards/` and `docs/specs/` (`[REQ-SDLC-061]`).
  - **AWS Kiro Steering & 3-File Specs**: Integrated AWS Kiro persistent steering (`product.md`, `tech.md`, `structure.md`, `roadmap.md`) and 3-file specifications (`requirements.md`, `design.md`, `tasks.md`) under `.agents/` (`[REQ-SDLC-060]`).
  - **Standardized Artifact Templates with Three Beats**: Created standard templates in `templates/sdlc-project/.agents/templates/` embedding the Three Beats operating instructions (`card.template.md`, `requirements.template.md`, `design.template.md`, `tasks.template.md`, `adr.template.md`) (`[REQ-SDLC-062]`).
  - **Constitution & SDLC Invariants**: Updated `AGENTS.md` and `GEMINI.md` to document the canonical `.agents/` directory standard and AWS Kiro framework (`[REQ-SDLC-063]`).

- CARD-181 Done (`AutoReiv.Agents`, `AutoReiv.PlatformPacks`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-181):
  - **Shipped Platform Developer Agent**: Created `platform-packs/developer` (Schema 1.1) equipped with modular `plan`, `build`, and `test` skills, automatically seeded into `$DATA_DIR/packs/developer/` on launch (`[REQ-DEV-001]`, `[REQ-DEV-003]`).
  - **Unified Multi-Language Engineering Toolset**: Equipped Developer with full engineering tools (`read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, git tools, card tools), enabling shell execution for PowerShell Pester/PSScriptAnalyzer, Python pytest/ruff, and TypeScript vitest (`[REQ-DEV-002]`).
  - **Agent Studio & Chat Presentation**: Configured Developer to display with `[Platform]` badge and enabled chat visibility (`show_in_chat=true`) (`[REQ-DEV-004]`).
  - **Retirement of SDLC Trio**: Retired `conductor`, `coding`, and `review` from active catalog and hid them from chat pickers (`[REQ-DEV-005]`).
  - **Active Selected Project Root Resolution**: Bound `SysadminTools` (`cli_exec`) to `ProjectsService.resolve_root` with optional `cwd` parameter, and injected active project context into `AgentKernel` prompt assembly, ensuring scripts and CLI commands execute directly within the active project directory selected in Projects Studio.

- CARD-188 Done (`AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings` - CARD-188):
  - **Operator Credential Secret Reveal Endpoint**: Added `GET /api/vault/credentials/{cred_id}/reveal` endpoint returning decrypted secrets for operator verification (`[REQ-VAULT-006]`).
  - **Settings Studio Credential Edit Flow**: Added row edit button pre-populating the credential modal form and supporting retention of existing encrypted secrets when updating metadata (`[REQ-VAULT-007]`).
  - **Settings Studio Sensitive Field Unmask Controls**: Added eye toggle buttons to reveal and re-mask secrets in the table and toggle password visibility in the input form (`[REQ-VAULT-008]`).
  - **Settings Studio Remote Host Edit Flow**: Added row edit button pre-populating the remote host modal form and enabling full modification of host parameters (`[REQ-REMOTE-006]`).

- CARD-160 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings` - CARD-160):
  - **Remote Host Profile Persistence**: Added SQLite `remote_hosts` repository and migrations linking remote SSH endpoints directly into the encrypted Credential Vault (`[REQ-REMOTE-001]`).
  - **REST API for Remote Host Management & Probes**: Built `/api/remote_hosts` endpoints (`GET`, `POST`, `DELETE`, and `POST /{id}/test`) supporting connection configuration and in-memory connection latency probes (`[REQ-REMOTE-002]`).
  - **Settings Studio Remote Hosts UI**: Added dedicated Remote Hosts management card and modal in Settings Studio, complete with host listings, connection handshake testing, and deletion controls (`[REQ-REMOTE-003]`).
  - **Platform Remote Execution & Inspection Tools**: Implemented `ssh_exec_command`, `ssh_read_file`, and `ssh_inspect_environment` platform tools for remote machine management without writing temporary private keys to disk (`[REQ-REMOTE-004]`).
  - **Security Guardrails & Access Control**: Enforced agent credential grant verification (`allowed_credentials`), dangerous command blocking via filter checks, and full compatibility with human-in-the-loop approval cards (`[REQ-REMOTE-005]`).

- CARD-168 Done (`AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-168):
  - **Encrypted Local Credential Storage**: Built AES-256-GCM encrypted `CredentialVault` domain engine and SQLite `credentials` repository, automatically creating and storing a 256-bit local master key under `$DATA_DIR/.vault_key` (`[REQ-VAULT-001]`).
  - **REST API for Credential Management**: Added `/api/vault/credentials` endpoints (`GET`, `POST`, `DELETE`) with strict secret masking on read (`****...abcd`) (`[REQ-VAULT-002]`).
  - **Agent Studio Credential Grants**: Added Credential Vault management UI in Settings Studio and per-agent direct credential grants list with live counter badge in Agent Studio, persisted into agent profiles and `pack.json` under `allowed_credentials` (`[REQ-VAULT-003]`).
  - **JIT Tool Execution Injection**: Extended `ScopedToolRegistry.execute()` to dynamically resolve authorized secrets for the active agent, injecting them into tool context (`_tool_context["credentials"]`) and ephemeral environment variables (`AUTOREIV_CRED_<KEY>`), popping them in a `finally` block (`[REQ-VAULT-004]`).
  - **Real-Time Secret Output Scrubbing**: Added `TranscriptScrubber` integrated into `AgentKernel` (`execute_and_scrub_tool`), scanning and masking all plaintext secret occurrences with `***MASKED***` across tool stdout/stderr, message histories, and LLM payloads (`[REQ-VAULT-005]`).

- CARD-187 Done (`AutoReiv.Chat`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-187):
  - **Human-Readable HITL Code & Command Preview**: Added `formatHitlArgs` in `src/web/static/modules/studios/chat.js` to extract primary script and command arguments (`code`, `command`, `CommandLine`, `script`, `sql`, `query`, `prompt`), rendering them as unescaped, formatted multiline text with metadata neatly listed above, replacing raw JSON stringification with escaped `\n` (`[REQ-HITL-050]`).
  - **Direct Standard Output Display**: Added `formatHitlOutput` in `chat.js` and updated `submitHitlDecision` to extract `stdout` / `stderr` directly. Formats terminal outputs and automatically pretty-prints embedded JSON strings with indentation and real line breaks, eliminating `\r\n` escaping (`[REQ-HITL-051]`).
  - **Routine API Built-in Flag Parity**: Updated `GET /api/routines` in `src/web/routers/routines.py` to check `BUILTIN_ROUTINES` and return `is_builtin: boolean` on each routine (`[REQ-ROUTINE-050]`).
  - **Universal Routine Deletion & Toast Feedback**: Rendered functional Delete button on all routine cards in `src/web/static/modules/studios/routines.js`. Added confirmation dialog checks, direct `DELETE /api/routines/{id}` invocation, grid refresh, and floating toast feedback (`showToast`) (`[REQ-ROUTINE-051]`, `[REQ-ROUTINE-053]`).
  - **Unrestricted Database Routine Deletion & Startup Seeding Guard**: Removed artificial `builtin_ids` deletion rejection from `src/infrastructure/memory/repositories/routines.py`, allowing operators to delete any routine from SQLite storage. Updated `src/web/app.py` and `scheduler.py` to seed default routines once on initial setup so deleted routines stay deleted across restarts (`[REQ-ROUTINE-052]`).

- CARD-179 Done (`AutoReiv.Chat`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web` - CARD-179):
  - **Smart Goal & Verify Checkbox Coupling**: Checking the Goal checkbox in Chat Studio now automatically pairs with and enables Self-Verify (`#verifyToggle`), ensuring multi-phase execution plans default to active critic verification while preserving operator choice to explicitly untick it (`[REQ-REF-001]`).
  - **Live Reflexion SSE Streaming**: Extended `_apply_verify_gate` in `src/web/routers/chat.py` to stream `reflexion_attempt` and `reflexion_critique` events to the chat SSE queue when running named tool checkers, giving real-time visibility into verification attempts and discrepancy critiques before final resolution (`[REQ-REF-002]`).
  - **Collapsible Reflexion Status Badges**: Unified chat stream reflexion badge rendering with `renderReflexionBadge` in `chat.js`, providing expandable/collapsible details (`.reflexion-badge-toggle` and `.reflexion-details`) for inspection of critic verdicts, checkers, and discrepancy logs (`[REQ-REF-003]`).
  - **Autonomous Mode Suggestion for Multi-Step Prompts**: Added prompt heuristic `isComplexMultiStepPrompt` in `chat.js` and suggestion chip `#chatGoalSuggestionChip` in `src/web/templates/index.html`. Prompts with numbered lists, explicit step markers, or multi-action sequential phrases offer a 1-click upgrade to Goal & Self-Verify mode (`[REQ-REF-004]`).

- CARD-180 Done (`AutoReiv.Chat`, `AutoReiv.Web`, `AutoReiv.Agents` - CARD-180):
  - **Chat Options Drawer Workflow Picker Retirement**: Removed `#workflowPicker` and its loading logic from `chat.js` and `index.html`. The chat options drawer now focuses strictly on execution modes, context budget, and loaded tools (`[REQ-CLEAN-001]`).
  - **Completed Job "Save as workflow" Retirement**: Removed `#saveAsWorkflowBtn` and modal triggers from `chat.js` and `index.html` (`[REQ-CLEAN-002]`).
  - **Chat Stream Endpoint Simplification**: Removed `workflow_id` parameter from `ChatStreamRequest` and stripped workflow recipe instantiation branching from `src/web/routers/chat.py` (`[REQ-CLEAN-003]`).
  - **Agent Studio Workflows Card Retirement**: Removed `#studioWorkflowsList` ("Workflows: Saved multi-step plans") box from `index.html` and deleted `loadAgentWorkflows`, chapter editing, saving, and deletion methods from `src/web/static/modules/studios/forge.js` (`[REQ-CLEAN-004]`).

- CARD-186 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-186):
  - **Visible Training Goal & Intent Input**: Added `#trainSeedIntentInput` field to `#trainAgentHandshakeModal` in `src/web/templates/index.html` and wired in `chat.js` and `forge.js`. If left blank, intent derives cleanly from the first objective rather than injecting generic `"Train capabilities for <slug>"` strings (`[AC-1]`).
  - **Pack-Aware Blueprinting**: Extended `BlueprintPhase` with `_load_existing_pack_info` to inspect `pack.json` when targeting existing agents. Passes existing skills, tools, and SQLite storage into the LLM context and heuristic fallback, anchoring new tools to existing skills and guarding against duplicate `{agent_id}` skills or `manage_{agent_id}` dummy dispatchers (`[AC-2]`, `[AC-3]`).
  - **Data & Analytics Tool Synthesis**: Added data query and analytics actions (`query`, `analyze`, `forecast`, `summary`, `report`) to `_synthesize_generic_python_tool` in `src/application/orchestration/tool_synthesizer.py` for agents with SQLite storage or reporting objectives (`[AC-3]`).
  - **Private Pack Skill Isolation**: Restricted `AgentPackService._import_folder()` skill copying to platform pack IDs, keeping private agent pack skills isolated inside `packs/<agent_id>/skills/` without leaking into the global `$DATA_DIR/skills/` catalog (`[AC-4]`).
  - **Pack-Scoped Runbook Editing**: Updated `UserSkillCatalog` with `resolve_pack_scoped_skill_md` allowing the runbook editor (`GET/PUT /api/skills/user-packs/{pack_id}`) to directly read and write private pack-scoped runbooks (`[AC-5]`).

- CARD-185 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Skills` - CARD-185):
  - **Deliverable Auto-Detection & Existing Pack Expansion**: Enhanced `classify_deliverable_type` in `src/application/agent_training_factory/phases/blueprint.py` to inspect target agent packs (`pack.json`, `mcp/`, `tools/`) when deliverable architecture is set to `"auto"`. Automatically maintains and expands existing MCP servers or native tools rather than guessing from scratch (`[AC-2]`).
  - **Procedural Skill Runbook Only Deliverable**: Added first-class support for `"skill"` deliverable architecture in `BlueprintPhase`, `AuthorPhase`, and `VerifyPhase`, authoring pure operational `SKILL.md` runbooks with zero tools or MCP files (`[AC-1]`).
  - **Distinct Multi-Skill Titles & Content Alignment**: Fixed title and content bleed in `AuthorPhase` where all skills previously inherited the first skill's title and dumped raw user prompt paragraphs. Each skill now generates its own unique title (e.g. `# Hyper-V Unattend Templates` vs `# Hyper-V Checkpoint Lifecycle`) and clean operational SOP objectives (`[AC-3]`, `[AC-4]`).
  - **All-Tools Verification Battery Logging**: Updated `VerifyPhase` battery logging and packet outcomes to enumerate all verified authored tools rather than truncating to the first tool (`[AC-5]`).
  - **MCP Container Rebuild Guidance**: Added container rebuild instructions (`docker build -t autoreiv-<slug>-mcp:latest packs/<slug>/mcp`) to `PromotePhase` gate messages, promote API responses, and promotion packets for operator visibility (`[AC-2]`).

- CARD-184 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Docker` - CARD-184):
  - **Remote MCP Server Pack Scaffolding**: Configured Agent Training Factory `AuthorPhase` to generate a self-contained, zero-internal-dependency MCP package under `mcp/` consisting of dual-mode stdio/HTTP `server.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `run.ps1`, `run.sh`, and `README.md` (`[REQ-MCP-SCAFF-001]`).
  - **Strict No-Loose-Tools Invariant**: Enforced strict deliverable boundary in `AuthorPhase`, `ScenarioVerifyPhase`, `VerifyPhase`, and `PromotePhase` ensuring that selecting MCP deliverable architecture strictly generates only `mcp/` artifacts and declarative skill runbooks (`skills/`), completely omitting loose `tools/` ad-hoc scripts (`[REQ-MCP-SCAFF-002]`).
  - **Docker Container Execution & Verification**: Built and ran the scaffolded Hyper-V MCP server container (`autoreiv-hyperv-mcp:latest`) on port 8080 over HTTP/SSE, successfully executing remote JSON-RPC 2.0 tool calls and discovering tools over network boundaries (`[REQ-MCP-SCAFF-003]`).
  - **Per-Agent MCP On-Demand Mount Endpoint & UI Control**: Added `POST /api/agents/{agent_id}/mcp/{server_name}/mount` and Agent Studio Inspector "Connect" control to dynamically mount running remote MCP containers into AutoReiv's `ScopedToolRegistry` without restarting the application (`[REQ-MCP-SCAFF-004]`).
  - **Pack Manifest Import & Upsert Parity**: Updated `AgentPackService._upsert_agent` to seamlessly map `mcp_servers` from `pack.json` into `AgentProfile`, ensuring custom and built-in agents automatically retain their configured MCP servers across restarts and reloads (`[REQ-MCP-SCAFF-005]`).

- CARD-183 Done (`AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Infrastructure`, `AutoReiv.Packs` - CARD-183):
  - **Per-Agent Remote MCP Server Architecture**: Scoped Model Context Protocol (MCP) servers directly to individual agent profiles and pack manifests (`pack.json`) instead of global-only settings, establishing external microservices as the primary target (`[REQ-MCP-AGENT-001]`).
  - **Remote HTTP/SSE Client Adapter**: Enhanced `MCPClientAdapter` in `src/infrastructure/mcp/client_adapter.py` with HTTP/SSE transport (`transport="sse"`), remote URL endpoints, custom authorization headers, and JSON-RPC 2.0 dispatch over HTTP without requiring local subprocesses (`[REQ-MCP-AGENT-002]`).
  - **Agent Studio MCP Inspector**: Added `#forgeMcpServersCard` in Agent Studio with live server badges, mount status indicators, tool counts, "Add Remote MCP Server" form supporting both remote SSE and stdio modes, and single-click connection probe testing (`[REQ-MCP-AGENT-003]`).
  - **Agent MCP Management Endpoints**: Created endpoints `GET /api/agents/{agent_id}/mcp`, `POST /api/agents/{agent_id}/mcp`, `DELETE /api/agents/{agent_id}/mcp/{server_name}`, and `POST /api/agents/{agent_id}/mcp/test` with SQLite state store and pack manifest synchronization (`[REQ-MCP-AGENT-003]`).

- CARD-182 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-182):
  - **Lab Monitor Retry Training Attempt**: Added `#labRetryJobBtn` ("Retry Training") to the Lab Training Monitor drawer run selector row, allowing operators to immediately re-launch a training run with all prior inputs preserved (agent name, seed intent/objectives, deliverable architecture, constraints, prerequisites, reference docs, and target location) into `#trainAgentHandshakeModal` (`[REQ-LAB-002]`).
  - **Structured Job Inputs Endpoint**: Enhanced `GET /api/agent_training_factory/jobs/{job_id}` in `src/web/routers/agent_training_factory.py` to extract and expose structured `inputs` parsed from the initial orchestrator work packet (`[REQ-LAB-003]`).
  - **Copy Activity Feed Control**: Added `#labCopyFeedBtn` to the Live Activity Feed box header in the Lab Training Monitor drawer, enabling single-click copying of the complete timestamped terminal trace to system clipboard with visual "Copied!" feedback (`[REQ-LAB-001]`).

- CARD-176 Done (`AutoReiv.Orchestration`, `AutoReiv.Infrastructure`, `AutoReiv.Web`, `AutoReiv.Packs` - CARD-176):
  - **Capability Architecture Taxonomy**: Established clear architectural separation between external service Model Context Protocol (MCP) servers, local atomic tools, and procedural skill runbooks (`[REQ-DELIV-001]`).
  - **Reusable Pack MCP Server Micro-Framework**: Implemented zero-dependency `PackMCPServer` in `src/infrastructure/mcp/pack_server.py` with standard JSON-RPC 2.0 stdio transport, `@server.tool` decorator, automatic type annotation introspection, and schema derivation (`[REQ-DELIV-002]`).
  - **Socratic Train Agent Modal Deliverable Inputs**: Added `#trainDeliverableType` selector ("Auto-detect", "Model Context Protocol", "Native Atomic Tool", "Procedural Skill Runbook Only") and collapsible `#trainAdvancedReqsAccordion` with constraints, prerequisites, and reference docs inputs in `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js` (`[REQ-DELIV-003]`).
  - **Agent Studio Badges**: Rendered distinct indigo `[MCP Server]` and slate `[Native Tool]` badges next to capability tools in `src/web/static/modules/studios/forge.js` (`[REQ-DELIV-003]`).
  - **Pack Manifest MCP Server Specification**: Extended `AgentPackManifest` in `src/application/agent_packs/schema.py` with `mcp_server: Optional[PackMCPServerConfig]` and dynamic lifecycle mounting in `src/infrastructure/mcp/client_adapter.py` (`[REQ-DELIV-004]`).
  - **Author Phase Dual Scaffolding**: Integrated deliverable classification in `BlueprintPhase` and scaffolded `mcp/server.py` in `AuthorPhase`, pairing with agentskills.io YAML frontmatter and 5-section imperative SOP skill runbooks (`[REQ-DELIV-005]`).
  - **Verification Battery MCP Subprocess Gate**: Implemented `run_mcp_battery()` in `VerificationBatteryService` and integrated into `VerifyPhase`, validating MCP servers across deterministic stdio execution, invariant safety, idempotency stress replay, and SRE Critic AST audit (`[REQ-DELIV-006]`).
  - **Windows SelectorEventLoop Compatibility**: Refactored `MCPClientAdapter` from `asyncio.create_subprocess_exec` to `subprocess.Popen` in a thread executor with an async lock, resolving the `NotImplementedError` that occurred when running inside Uvicorn on Windows, and improved `critic_notes` error formatting so exceptions never evaluate to blank (`[REQ-DELIV-006]`).
  - **Promote Phase Pack Manifest Persistence**: Saved `mcp_server` configuration to `pack.json` upon job promotion and mounted pack server into `MCPClientManager` (`[REQ-DELIV-007]`).

- CARD-174 Done (`AutoReiv.Architecture`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-174):
  - **Execution Primitives Taxonomy**: Formalized the AutoReiv agentic execution stack (CoT -> ReAct -> Plan & Execute -> Reflexion -> Multi-Agent -> Graphs).
  - **Platform vs. User Pack Boundaries**: Locked platform-owned core anchors (Assistant, Developer, AutoReiv) vs modular User Agent Packs (`$DATA_DIR/packs/`).
  - **Derived Card Scaffolding**: Spawned CARD-179 (Smart Goal & Verify Coupling), CARD-180 (Retire Chat Workflow Picker), and CARD-181 (Platform Core Developer Agent).

- CARD-169 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Architecture` - CARD-169):
  - **Nomenclature Lock**: Locked standard name as **Agent Training Factory** (ATF) and Lab Monitor across all documentation, UI, and code.
  - **Location Semantics Clarification**: Formally defined the path field as strictly an optional read-only reference codebase directory, never writing generated pack files to the project root.

## [0.22.0] - 2026-09-07

- CARD-178 Done (`AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-178):
  - **Structured Note Templates**: Added 6 canonical templates (`feynman-technique.md`, `concept-map-system-hub.md`, `dikw-pyramid-of-insight.md`, `zettelkasten-atomic.md`, `sop-runbook.md`, `adr-decision.md`) seeded in `02_Resources/_Templates/` with standard YAML frontmatter and clear step-by-step markdown sections.
  - **Template Endpoints**: Added `GET /api/wiki/templates` and `GET /api/wiki/template?slug=...` REST API endpoints to list and fetch structured template skeletons.
  - **Optional Directive System**: Kept freeform topic synthesis untouched as the default. Templates are strictly optional directives that can be requested naturally in chat or selected from the UI.
  - **New Note Modal Integration**: Added `#newNoteTemplateSelect` dropdown to `#wikiNewNoteModal` defaulting to "None (Freeform Topic Synthesis)". Selecting a template dynamically pre-fills the body textarea with the chosen skeleton.
  - **Agent Tool Support**: Added `wiki_template_list` tool and `template` parameter to `wiki_note_create` for assistants to inspect templates and apply structured frameworks when explicitly requested.

- CARD-177 Done (`AutoReiv.Wiki`, `AutoReiv.Web` - CARD-177):
  - **Collapsible Folders Default Closed**: All top-level sections (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) and nested domain/topic subfolders start collapsed on initial page load and vault reload, with toggle persistence and search-driven auto-expansion.
  - **Select-Then-Delete Navigation Flow**: Clicking a folder row selects it, updates `#activeWikiTitle` and `#activeWikiPath`, renders a Folder Overview card with item count and note links, and activates `#wikiFolderActionsGroup` with `#wikiDeleteFolderBtn` in the main header bar.
  - **Subfolder Deletion (`DELETE /api/wiki/folder`)**: Enabled deleting subfolders directly from the Wiki Studio header toolbar, folder overview card, or tree hover buttons with confirmation prompts and reactive editor cleanup.
  - **Guarded Root Invariant**: Explicitly prohibited deleting foundation root folders (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) across both the UI (displaying a `#wikiRootFolderBadge` `[Γëí╞Æ├╢├å Protected Root]`) and backend validator.

- CARD-173 Done (`AutoReiv.Wiki`, `AutoReiv.Routines`, `AutoReiv.Web`, `AutoReiv.Kernel` - CARD-173):
  - **Platform-Owned PARA-Wiki Standard**: Enforced Jacob's single PARA-Wiki vault layout (`00_Inbox/`, `01_Notes/<domain>/<topic>/`, `02_Resources/_Templates/`, `03_Archive/`) with transparent backwards-compatible path aliasing.
  - **Single-Door Inbox Filing**: All new notes land in `00_Inbox/` with a lightweight 10-field staging YAML frontmatter schema.
  - **Pre-Write Fluff Scrubber**: Added `clean_note_content()` purging conversational AI greetings, sign-offs, and filler while protecting code blocks and technical content verbatim.
  - **Tag Authority Registry**: Seeded `02_Resources/_Templates/tag-authority.md` with check-first normalization and novel tag self-registration.
  - **Wiki Curation Routine**: Autonomous scheduled background routine (`wiki-curation`) and on-demand `[╬ô├£├¡ Curate Inbox Now]` toolbar button to scrub fluff, validate metadata, check/register tags, deduplicate notes, and graduate notes to `01_Notes/`.
  - **Per-Agent Wiki Access Gate**: Added `[x] Allow Wiki Access` toggle in Agent Studio, controlling RBAC access to wiki tools in `ScopedToolRegistry`.
  - **One-Door Policy Hardening for Agent Tools**: Enforced that `wiki_note_create` and the UI new note modal strictly stage new captures into `00_Inbox/`, preventing agent bypasses into `01_Notes/` and ensuring all notes pass through staging and the autonomous curation routine.

## [0.21.0] - 2026-09-06

- CARD-171/172 Factory domain-taint cleanup (`AutoReiv.Orchestration`, `AutoReiv.Web`):
  - Restored domain-agnostic Scenario Verify, Blueprint, Author, Ground, and Optimize phases (gated Hyper-V bleed and tool fragment rules strictly to Hyper-V domains).
  - Restored promotion file selection to cleanly prefer latest Author files map.
  - Fixed `_latest_blueprint` packet lookup order in Author phase.
  - Fixed 14 ruff lint errors and 5 test regressions across unit and web test suites.

- CARD-171/172 Factory quality harden (AutoReiv.Orchestration):
  - **Checkpoint focus** bucket: Checkpoint-VM / Get-VMSnapshot / Restore / Remove only (no New-VM/switch/unattend bleed).
  - **Scenario Verify** fails on out-of-focus action branches / banned tokens (not prose-only; ignores `no oscdimg` constraint echo).
  - **Intent Distill + Ground** generic SOP rubric (purpose / steps / verify / rollback); reject vacuous brief-echo.
  - Author seed-only + re-filter for any `manage_hyperv_*` tool (narrow trains stay narrow).
  - **Negation scrub** so `no switch/NIC` / `No New-VM` do not widen focus; Scenario Verify flags out-of-scope tool files.

- CARD-172 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Frontend` - CARD-172):
  - **Intent Distill** phase (question battery -> structured answers) before Ground.
  - **Scenario Verify** phase (Blueprint capability done-whens) before Code Verify.
  - **Inner rinse** (implementation) -> Author; **outer rinse** (sop/how) -> Intent Distill + Ground with Reflexion lessons; caps `max_verify_rinses` / `max_outer_rinses`.
  - Lab Monitor 8-stage stepper + feed lines for inner/outer rinse reasons.
  - Persist `outer_rinse_count`, `max_outer_rinses`, `failure_class`, `scenario_matrix_json` on FactoryJob.

- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Verify multi-skill tool selection**: battery loads exact `tools/<primary>.py` (no sibling overwrite ImportError).
  - **Author seed-only fast path** for Hyper-V multi-skill blueprints (avoid 4x LLM hangs).
  - **Docstring path sanitize** so `D:\` in seed intent does not break generated tool AST.

- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Multi-skill Hyper-V blueprints**: Blueprint keeps VM lifecycle / networking / unattend-templates / template-maintenance skills (no single fat manage_hyperv collapse). Author emits all blueprint tools+skills. Promote merges skills/<id>/SKILL.md. Focus synthesizer builders emit real Hyper-V\ cmdlets (New-VMSwitch, Set-VMDvdDrive, Autounattend ISO, template maintenance).
  - **Synthesizer/Author hardeness**: sanitize seed docstring paths (D:/...); Author rejects LLM tool_code that fails st.parse and restores synthesizer seed.

- CARD-171 Done follow-up (`AutoReiv.Orchestration` - CARD-171):
  - **Non-Hyper-V CLI synthesizer path**: Windows services/sysadmin briefs synthesize `Get-Service` tools + matching SKILL actions (no Hyper-V `Get-VM` costume bleed).
  - **Author domain-bleed gate**: If LLM returns Hyper-V `Get-VM` tool/skill for a Windows services brief, restore synthesizer `Get-Service` seed (CARD-171).
  - **Promote/Optimize files_map preference**: Latest Author `files_map` wins over stale Optimize snapshots so rinsed Get-Service packs are not clobbered by earlier Hyper-V copies.
  - **Safe OBJECTIVES literals**: Generated tool `OBJECTIVES` lists use `json.dumps` so apostrophes in objectives no longer SyntaxError the sandbox battery.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-171):
  - **Max verify rinses**: `FactoryJob.verify_rinse_count` / `max_verify_rinses` (default 3); Verify fail increments; at max, job status `failed` with packet `critic_notes` (no infinite Author╬ô├Ñ├╢Verify loop).
  - **Fail reasons visible**: Verify packet messages include rinse progress + short reason; Lab Monitor live feed shows a `Reason:` line from `critic_notes` via `formatLabPacketFeedLines`.
  - **Path false-positive fix**: Stage-2 preflight no longer bans `"C:\`; uses real `..` traversal / sensitive Unix-path checks so `D:\Archive\...\2022.ISO` and `C:\Users\...` are allowed.
  - **Author adapts**: Latest Verify `critic_notes` injected into Author LLM user context as `LAST VERIFY FAILURE`.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Live-test grounding/author/verify fix**: Persist `objectives` on `FactoryJob` (SQLite `objectives_json`); create-job copies payload objectives; PhaseContext merges job objectives with orchestrator work-packet facts.
  - **Ground heuristics**: Match `hyperv` (no hyphen), `unattend`/`autounattend`/`iso`/`vhdx`/`template`; force cli + Hyper-V module when keywords match; rich operating manual includes full seed, objectives, and ISO paths (no costume computation/`{slug}-cli` when intent is Hyper-V).
  - **Author quality gate**: Pass objectives into LLM; reject stub `Agent for managing ... tasks` / missing Purpose+Objectives / missing unattend-ISO keywords; enrich SKILL with seed brief.
  - **Verify shallow-stub gate**: `is_shallow_stub_artifact` fails battery when skill/tool ignore seed objective keywords.
  - **Lab Monitor artifact preview**: Clickable `#labArtifactPills` open `#labArtifactPreviewModal` with packet content, pre-promote note, and expected `%LOCALAPPDATA%\AutoReiv\packs\<agent_id>\...` paths.

- CARD-171 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Agent Training Factory Orchestrator**: Replaced costume `FactoryRunner` (deterministic ToolSynthesizer walker + five persona packs) with `FactoryOrchestrator` under `src/application/agent_training_factory/` ╬ô├ç├╢ thin phase registry (Ground -> Blueprint -> Author -> Verify -> Optimize -> Promote), rinse edges (Verify fail -> Author), real gateway LLM phase context, Wiki grounding with front-matter contract v1 (`type=factory-grounding`, `agent_id`, `medium`; optional `factory_job_id`/`status`).
  - **Consistent rename**: API prefix `/api/agent_training_factory`, package/modules/UI copy use Agent Training Factory / `agent_training_factory`. Lab Monitor shows six phases (not personas). FE fetch URLs updated.
  - **Persona packs retired from Factory**: `FACTORY_PACK_IDS` emptied; former `{conductor,inspector,coder,sandbox_runner,critic}` recorded as `RETIRED_FACTORY_PERSONA_PACK_IDS` and no longer presented as Factory runtime. Assistant/AutoReiv and unrelated user packs untouched. SQLite `factory_*` tables kept (legacy names documented in code).
  - Surfaces kept: Train Agent, Lab Monitor, Needs Training backlog, auto-train, promote/HITL. Done after review and live test.

## [0.20.0] - 2026-09-05

- CARD-167 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Skills` - CARD-167):
  - **Agent Studio Skill Runbook Editor Close & Cancel Controls**: Added top-right close `x` button (`#studioRunbookCloseBtn`) and bottom `[Cancel]` button (`#studioRunbookCancelBtn`) to the skill runbook editor in Agent Studio (`#studioRunbookEditor`), wired to `hideRunbookEditor()` in `forge.js` to dismiss the editor, clear form inputs, and return the operator to the skills list [REQ-DATA-019, REQ-DATA-020].

- CARD-166 Done (`AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.Kernel` - CARD-166):
  - **Module-Qualified Host Cmdlet Tool Synthesis**: Updated `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and live agent packs to fully qualify all virtualization cmdlets (`Hyper-V\Get-VM`, `Hyper-V\New-VM`, `Hyper-V\Start-VM`, `Hyper-V\Stop-VM`, `Hyper-V\Restart-VM`, `Hyper-V\Checkpoint-VM`, `Hyper-V\Get-VMSnapshot`, `Hyper-V\Remove-VM`, `Hyper-V\Get-VMSwitch`, `Hyper-V\New-VHD`, `Hyper-V\Add-VMHardDiskDrive`) and explicitly import `Import-Module Hyper-V -ErrorAction SilentlyContinue;`, eliminating command lookup shadowing and ambient namespace collisions on the host [REQ-FACT-029, REQ-FACT-030, REQ-FACT-031].
  - **Domain-Agnostic Purpose-Grounded Environment Discovery**: Grounded `_step_discovery_probe` in `factory_runner.py` directly in the agent's purpose, intent, and objectives, dynamically detecting target execution medium (CLI, API, Database, Filesystem, Computation) and inspecting module availability and namespace isolation rules rather than returning static mocks [REQ-FACT-032].
  - **Verification Battery Command Collision Guardrail**: Enhanced the 4-stage verification battery in `verification_battery.py` and `generate_verification_test` to actively detect foreign module command collisions and unhandled subsystem interception signatures in runtime stderr, failing Stage 2 safety with actionable diagnostics before any code is approved for deployment [REQ-FACT-033].

- CARD-164 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.HITL` - CARD-164):
  - **Autonomous Background Factory Runner**: Implemented `FactoryRunner` background worker loop in `src/application/orchestration/factory_runner.py` started in `app.py` lifespan to automatically advance queued and active training jobs across all graph nodes to `hitl_deploy_gate_node` without manual intervention during sandbox testing.
  - **AutoReiv Platform Chat Anchoring**: Anchored all training jobs and HITL promotion milestone notifications to the `autoreiv` platform agent's session, guaranteeing that new or headless agents (`show_in_chat: false`) never orphan deployment approval cards.
  - **Lab Monitor Slide-Over Drawer in Agent Studio**: Added `#forgeLabMonitorBtn` with dynamic active runs badge (`#forgeLabRunsBadge`) and a full slide-over `#labMonitorDrawer` featuring an active run selector, a 5-stage visual stepper (Discovery, Blueprint, Toolmaker, Sandbox QA, Deploy Gate), a live packet activity feed, and direct **Approve & Deploy** and **Reject** buttons.
  - **Lab Monitor Drawer Visibility & Handshake Input Alignment**: Fixed DOM nesting in `index.html` by properly closing `agentBrainDrawer` tags so `#labMonitorDrawer` is an independent sibling and slides open immediately when clicked, added auto-open on job launch, added `autocomplete="off"` and input resets to prevent browser pre-filling `admin`, marked project path as optional with OS/hypervisor hints, and added dedicated `#trainAgentNameInput` for training brand new agents from scratch.
  - **Pack Tool Persistence & Registry Mount**: Fixed `promote_factory_job` to extract authored tool files and runbooks from packet payloads, persist `tools/<tool>.py` and `skills/<agent>/SKILL.md` into `$DATA_DIR/packs/<agent_id>/`, register tools under `pack_tool_names` and `allowed_tool_names` in `pack.json`, and register tool dispatch handlers directly in `ScopedToolRegistry` and `master_tool_registry` so promoted agents immediately possess callable tools.
  - **Chat Studio Lab Monitor Link**: Added a direct "View in Lab Monitor &rarr;" trigger inside the Chat Studio training launch bubble, allowing instant transition from chat to the live monitor drawer.
- CARD-165 Done (`AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Frontend` - CARD-165):
  - **Agent Studio Autonomous Training Controls**: Added "Allow Autonomous Training" checkbox (`#forgeAutoTrainCheckbox`) and "Max Auto-Train Retries" input (`#forgeMaxTrainRetriesInput`) in Agent Studio, persisted into `pack.json`, `AgentProfile`, `agent_overrides`, and `custom_agents` [REQ-FACT-023].
  - **Turn-Time Missing Capability Detection**: Implemented `CapabilityDetector` identifying missing tools or capability deficiency phrases in agent responses during operational chat turns [REQ-FACT-024].
  - **In-Flight JIT Sandbox Tool Synthesis & Live Telemetry**: Implemented `JitToolSynthesizer` evaluating drafted tools in ephemeral workspaces through the full 4-stage verification battery, bounded by per-agent max retries (1╬ô├ç├┤5, default 2), with real-time `auto_train_progress` status indicators in Chat Studio [REQ-FACT-024, REQ-FACT-025].
  - **Strict 4-Stage Battery HITL Auto-Bypass**: Automatically bypassed HITL deployment gate strictly when all 4 sandbox battery stages pass 100% cleanly, deploying tools to `packs/<agent_id>/tools/<tool>.py`, registering runbooks, and updating live tool registries [REQ-FACT-025].
  - **Seamless Turn Resumption**: Automatically resumed the paused turn upon verified tool deployment, injecting the new tool into active context so the agent completes the original user request without manual re-prompts [REQ-FACT-026].
  - **Capability Gap Backlog Queue**: Implemented SQLite table `agent_capability_gaps`, `CapabilityGapRepository`, and Agent Studio "Needs Training" backlog card (`#agentTrainingBacklogCard`) with live count badge and one-click `[╬ô├£├¡ Train in Lab]` or dismissal actions [REQ-FACT-027].
  - **Intelligent Capability Extraction & Direct Chat Queuing**: Enhanced `CapabilityDetector` with `extract_capabilities_from_turn` and `analyze_turn_with_llm` to synthesize technical capability titles, suggested tool names, and starter objectives from user intent and assistant code/commands (e.g. PowerShell `New-VM` / `New-VHD`), eliminating naive retry phrase capture ("can you try again"); streamlined Chat Studio's `[╬ô├£├¡ Train in Lab]` action to queue directly into Agent Studio's "Needs Training" backlog without interrupting modal popups, and fixed backlog list unpacking and rendering in `forge.js` [REQ-FACT-027, REQ-FACT-028].
  - **Operational PowerShell & System Tool Synthesis**: Implemented `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and integrated into `FactoryRunner` and `promote_factory_job`; dynamically generates real, runnable PowerShell scripts (`tools/<tool>.ps1`) with cmdlets (`Get-VM`, `New-VM`, `Start-VM`, `Stop-VM`, `Restart-VM`, `Checkpoint-VM`, `Remove-VM`, `New-VHD`, `Get-VMSwitch`), Python wrappers with subprocess execution, and runbooks (`SKILL.md`); tests generated tools against the 4-stage verification battery in `_step_sandbox_battery` without dummy code stubs, and mounts the live module dynamically upon promotion [REQ-FACT-009, REQ-FACT-017].
  - **Skill Runbook Feasibility & Parity Audit**: Integrated `evaluate_skill_runbook` into Stage 4 SRE Critic Audit in `VerificationBattery`, strictly validating `agentskills.io` YAML frontmatter (`name`, `description`), structured markdown headers, and 100% action schema parity against synthesized tools before certification.
  - **Instant UI Catalog Sync & Agent Pack Preservation**: Enhanced `promote_factory_job` to merge existing agent metadata, tools, and skills without overwriting custom profiles, sync `SKILL.md` to user skills root, refresh `UserSkillCatalog`, and update in-memory registries and SQLite state store; wired `forge.js` and `app.js` to automatically reload Agent Studio Cards 5 & 6 and Chat Studio dropdowns with zero manual page refreshes.

- CARD-163 Done (`AutoReiv.Data`, `AutoReiv.Infrastructure`, `AutoReiv.Deploy` - CARD-163):
  - **Database Reconciliation & Root Cleanup**: Safely merged 91 older historical sessions and 951 messages from orphaned root `autoreiv.db` into `database/autoreiv.db` (bringing totals to 161 sessions and 1,521 messages) with zero loss of modern settings or custom agents, created a pre-reconciliation zip archive under `backups/`, and cleaned up the obsolete root database and sidecar files.
  - **Enforce database/ Subfolder Invariant in Resolver**: Removed obsolete root path candidate from `_peek_setting_data_dir()` so startup never connects to or touches root SQLite files, and updated `migrate_if_needed()` to automatically reconcile and clean up any legacy root database file detected during bootstrap.
  - **Launcher & Memory Connection Alignment**: Updated Windows launcher (`run_autoreiv.ps1`) to display `database\autoreiv.db` in startup banner, and updated SQLite connection manager fallback to `./data/database/autoreiv.db`.

- CARD-162 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-162):
  - **Per-Agent Context Window Control in Agent Studio**: Moved `#forgeContextWindowInput` out of the conditionally hidden provider container into Card 4 ("LLM Provider & Model Override"), making it visible and editable for all agents regardless of whether they use the default provider or a custom provider.
  - **Unrestricted Context Window Persistence**: Updated `forge.js` agent payload builder to parse and persist typed context window tokens for any agent without clearing them when provider is set to "default".
  - **Unified 3-Tier Context Limit Resolution Cascade**: Implemented `resolve_agent_context_limit` in `context_compactor.py` and aligned `agent_kernel.py` and `chat.py` so that token budgets strictly resolve: 1) explicit per-agent setting, 2) per-agent custom model default/overrides, and 3) platform-wide `default_context_window` (e.g. 131,072) from Settings Studio, ensuring chat context meters and execution loops never prematurely truncate to 8k when using default provider.

- CARD-161 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-161):
  - **Chat Options Drawer Context Tokens & Compaction**: Added live token usage badge and progress bar (`#chatContextTokensBadge`, `#chatContextProgressBar`) inside the Chat Options Drawer displaying estimated consumed tokens vs. model context limit (e.g. `2,150 / 32,768 (7%)`), backed by `GET /api/sessions/{session_id}/context`.
  - **Manual Early Session Compaction**: Added `[Compact]` action (`#chatManualCompactBtn`) and `POST /api/sessions/{session_id}/compact` endpoint enabling users to manually compact earlier chat turns into a summary turn before hitting automated context overflow limits, refreshing the chat message stream and token budget immediately.
  - **Active Tools Summary & Inspector Modal**: Added loaded tools badge (`#chatToolsCountBadge`) and `[View Tools]` action (`#chatViewToolsBtn`) opening an interactive modal (`#chatToolsModal`) with live search to inspect all tools and descriptions authorized for the active specialist agent without leaving chat.

- CARD-159 Done (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-159):
  - **Autonomous Agent Pack Factory & Capability Loop**: Implemented the "Factory in a Lab" architecture for autonomous, overnight creation and training of specialist User Agent Packs with zero breaking changes to existing platform packs.
  - **Core Platform Factory Pack Roster**: Added 5 dedicated factory agent packs under `platform-packs/` (`conductor`, `inspector`, `coder`, `sandbox_runner`, `critic`) hidden from standard chat pickers (`show_in_chat: false`).
  - **Isolated User Pack Authoring Boundary**: Strictly isolated all generated tools, skills, and runbooks within `$DATA_DIR/packs/<agent_id>/`, never polluting platform directories.
  - **Read-Only Environment Inspection & Domain SOP Extraction**: Implemented safe, read-only discovery tools compiling ground-truth `EnvironmentManifest` metadata and domain SOP constraints.
  - **Isolated Sandbox Execution & Mocking**: Extended `EphemeralSandbox` and `SandboxedSubprocessWorker` to support directory mirroring, secret scrubbing, and command stubbing.
  - **4-Stage Automated Verification Battery**: Implemented an exhaustive verification pipeline requiring deterministic execution (Stage 1), safety & path traversal guardrails (Stage 2), idempotency & dirty-state replay (Stage 3), and SRE Critic AST security review (Stage 4).
  - **Conditional Graph Orchestrator & Anti-Bloat Gates**: Built deterministic graph walker with typed SQLite packet interchange (`WorkPacket`, `GapPacket`, `EvalPacket`, `PromotePacket`), anti-bloat `ToolConsolidationGate`, domain `AgentSplitPolicy`, and `UserPackFinalizer`.
  - **Socratic Handshake UX & Promotion UI**: Added "Train Agent" toggle chip, 3-question modal handshake in Chat Studio, and certification promotion card with human-in-the-loop deployment approval.
  - **Universal Attachment Reading Across All Agents**: Authorized `read_document_file` universally in `ScopedToolRegistry` so any agent (platform or custom pack) receiving file attachments in chat can extract and inspect document contents without requiring custom file-reading tools.
  - **End-to-End Hardening & Personal Finance Pack**: Successfully verified the Factory loop end-to-end against a real Personal Finance Agent (`finance`), authoring and certifying 4 atomic domain tools (`log_transactions`, `manage_budget`, `set_savings_goal`, `summarize_finances`) across all 4 battery stages, consolidating tool bloat, and executing live bank transaction ingestion, budgeting, and savings targets with zero database corruption.

## [0.19.0] - 2026-09-05

- CARD-116 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory`, `AutoReiv.Skills` - CARD-116):
  - **First-Class Per-Agent Cognitive Memory Brain**: Implemented private SQLite cognitive memory brain (`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`), strictly separate from domain application database (`<agent_slug>_storage.db`), providing three retrieval shelves: Shelf 1 (Permanent Pinned Directives), Shelf 2 (Rolling Episodic Session Summaries), and Shelf 3 (Atomic Semantic Facts with Porter-stemmed FTS5 BM25 search).
  - **Conflict-Resolved Compilation & Decay Physics**: Compiles facts post-turn without rescanning raw transcripts, performing automated `ADD`, `UPDATE`, `DELETE`, and `BUMP` conflict resolution with mathematical half-life temperature decay and logarithmic access frequency reinforcement.
  - **Dynamic Context Budgeting & Memory Kernel Tools**: Dynamically scales memory token injection according to active model limits (tight <=8k, standard 8k-32k, broad 32k+), and equips memory-enabled agents with `recall_agent_memory` and `memorize_fact` tools.
  - **Autonomous Consolidation Routine**: Implemented background `MemoryConsolidationRoutine` to merge near-duplicates, prune decayed facts past retention days, and compile rolling session summaries without blocking chat turns.
  - **Agent Studio Cognitive Memory Controls & Inspector Drawer**: Added dedicated Cognitive Memory configuration card in Agent Studio with retention range slider (`#forgeMemoryRetentionDays`), pinned directives editor (`#forgePinnedMemory`), and an interactive Brain Inspector drawer (`#agentBrainDrawer`) with FTS5 search, individual fact forgetting (`DELETE /api/agents/{id}/memory/facts/{fact_id}`), and complete memory purge actions.

- CARD-148 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory` - CARD-148):
  - **Per-Agent Persistent Storage in Agent Studio**: Added Persistent Storage checkbox (`#forgeStorageEnabled`) and Database Type selector (`#forgeStorageType`) to Agent Studio roster sheet, allowing specialist agents to maintain dedicated private databases.
  - **Pack-Scoped Storage & Artifact Layout**: Placed agent persistent storage databases (`<agent_slug>_storage.db`) and recipes (`workflows/`) directly inside that agent's pack directory (`$DATA_DIR/packs/<agent_id>/`), eagerly creating the database upon save so the agent's files stay together throughout their lifecycle.
  - **Dedicated Central Database Directory**: Relocated central system SQLite database from the root of `$DATA_DIR` into `$DATA_DIR/database/autoreiv.db`, with automatic on-boot migration of existing `autoreiv.db`, `-wal`, and `-shm` files.
  - **Auto-Authorized Storage Platform Tools**: Added `query_agent_database` (read queries) and `execute_agent_database` (DDL & mutations) tools in `src/application/skills/agent_storage_tools.py`, automatically authorized for storage-enabled agents during execution turns.
  - **Agent Pack SDK Storage Support**: Extended `AgentPackManifest` (`pack.json`) and `AgentPackService` to preserve storage configuration during agent pack export, import, and scaffolding.

- CARD-157 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-157):
  - **Host Command Auto-Delegation**: Updated Assistant platform pack system prompt to immediately delegate host terminal, CLI, PowerShell, and network diagnostic commands (e.g. `ipconfig`, `ping`) to the `AutoReiv` platform agent via `handoff_to_agent(target_agent='autoreiv')`.
  - **Subagent-Aware Pending Approvals**: Updated `/api/approvals/pending` and SQLite approvals repository to return pending approvals for the active session and all its child and phase execution branches (`session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%'`), ensuring subagent approval cards are not hidden when querying from the parent chat session.
  - **Chained Nested HITL Flow**: Updated `shouldResumeChatAfterHitl` and Chat Studio approval handlers to detect intermediate subagent approvals (`nested.status === 'approval_required'`), rendering the next pending approval card rather than prematurely resuming the parent assistant turn.
  - **Chat Bubble Lifecycle & Streaming Indicator Cleanup**: Removed premature `loadMessages` call at turn start to prevent wiping the user prompt bubble and flashing the empty conversation placeholder, and ensured the pulsing `Streaming...` badge is cleanly removed upon completion, stop, or HITL approval pause.

- CARD-151 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-151):
  - **Grey Out HITL Action Buttons Upon Decision**: Added immediate disabled visual feedback (`disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none`) to Human-In-The-Loop approval cards in Chat Studio and plan review milestones.
  - **Persistent Resolved Styling**: Permanently strips bright emerald/rose background colors upon approval or rejection, replacing them with neutral slate styling (`bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50`) to clearly indicate the decision is finalized and prevent accidental duplicate clicks.
  - **Pre-Resolved Card Rendering**: Added pre-resolved disabled rendering in `buildHitlCardInnerHtml` for cards rendered from history with existing decisions.

- CARD-150 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-150):
  - **Chat Session Summaries & Compact Timestamp Badges in History Drawer**: Replaced generic "Assistant Chat" list items in the past conversations drawer with a compact 2-line stacked card showing a clean 2╬ô├ç├┤5 word topic title and a shorthand timestamp (e.g. `Sep 03, 11:50 AM`).
  - **Turn-1 Automatic Title Summarization**: Automatically extracts a clean 2╬ô├ç├┤5 word topic summary from the user's initial turn prompt and persists it to the SQLite `sessions` table, replacing generic default titles.
  - **Session Title Update Endpoint**: Added `PATCH /api/sessions/{session_id}` endpoint to support programmatic session title updates and manual rename actions.
  - **Session Timestamp Formatter**: Added `formatSessionTimestamp` in pure frontend formatters converting UTC ISO timestamps to local `MMM DD, h:mm A` format.

- CARD-154 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-154):
  - **Shield Background Workers from Mobile Client Disconnects**: Prevented client-side SSE disconnects (mobile phone sleep, tab lock, or app switching) from canceling background worker execution tasks, ensuring subagent handoffs run to completion and persist final responses.
  - **Session Status Endpoint**: Added `GET /api/sessions/{session_id}/status` returning whether a session has an active background task or job in flight and the ID of the active agent.
  - **Tab Sleep Wakeup & Background Polling Recovery**: Updated `chat.js` visibility and window focus listeners to check session status on wake-up; if background work completed while away, streaming UI state automatically resets and loads all persisted messages from SQLite; if work is still underway, it polls and smoothly recovers upon completion.
  - **Preserved Explicit User Abort**: Preserved explicit user cancellation via `POST /api/chat/stream/{session_id}/abort` when the Stop button is clicked.

- CARD-156 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-156):
  - **Per-Agent LLM Endpoint Credentials & Configuration**: Added expandable endpoint controls in Agent Studio (API Base URL, API Key/Token, and Context Window tokens) revealed whenever an agent's LLM Provider is set to a specific provider.
  - **Live Model Discovery in Agent Studio**: Added `[ Γëí╞Æ├╢├ñ Refresh Models ]` button in Agent Studio that queries live models from the configured endpoint and dynamically populates the Model selector.
  - **Clean Collapsed Default**: When set to "Use Global Default", per-agent endpoint controls remain hidden and inherit settings directly from Settings Studio.
  - **Persistence & Kernel Dispatch**: Persisted `api_base_url`, `api_key`, and `context_window` in SQLite `custom_agents` and `agent_overrides` tables and updated `AgentKernel` to route agent generation through custom endpoint adapters and respect agent context token limits.

- CARD-153 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-153):
  - **Per-Agent LLM Provider and Model Configuration**: Replaced the abstract Purpose Matrix with direct LLM Provider and Model dropdowns on the Agent Studio roster sheet, defaulting to "Use Global Default".
  - **Purpose Matrix Retirement**: Completely removed the Purpose-Based Model Routing grid from Settings Studio and deprecated the `ModelPurpose` enum, simplifying model configuration into a single, direct path.
  - **Streamlined Resolution Cascade**: Simplified `AgentKernel._resolve_model()` cascade: agent override (`provider`/`model`) -> global default from Settings -> gateway fallback, eliminating matrix lookups.
  - **Agent Pack Schema & Persistence**: Added `provider` field to `AgentProfile`, `AgentCustomization`, and `AgentPackManifest` schema, persisting per-agent provider choices across restarts, exports, and imports.

## [0.18.0] - 2026-09-03

- CARD-152 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-152):
  - **Prompts Studio (Dedicated Prompt Management Space)**: Added a dedicated, first-class Prompts Studio (`#promptsStudio`, `#view-prompts`) in the main sidebar navigation with an ergonomic dual-pane management interface.
  - **Dual-Pane Prompt Workspace**: Left pane provides live search, category filter pills (All, System, Productivity, Coding, Analysis), and prompt cards with built-in badges; right pane provides a full-height template editor with tags, category selection, and instant `[ Test in Chat ]` workflow.
  - **Lightweight Chat Quick-Picker**: Streamlined the Chat Studio options drawer by replacing the large modal with a fast, non-intrusive Quick Prompt popover dropdown (`#chatPromptsQuickPicker`) for 1-tap template insertion and a direct bridge to Prompts Studio.

- CARD-147 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-147):
  - **Prompt Catalog & Saved Prompts Manager**: Delivered an end-to-end prompt template management system with instant 1-click insertion into the Chat Studio input dock.
  - **SQLite Prompt Catalog Repository & Schema**: Implemented `prompt_catalog` schema, migrations, and `PromptRepositoryMixin` with full CRUD support and curated built-in system, productivity, coding, and analysis seed templates.
  - **REST API Endpoints**: Added `GET /api/prompts`, `POST /api/prompts`, `PUT /api/prompts/{id}`, and `DELETE /api/prompts/{id}` with search and category filtering.
  - **Interactive Drawer Trigger & Modal**: Activated `#chatPromptsBtn` in `#chatOptionsDrawer` opening `#promptCatalogModal` with search, category tabs (System, Productivity, Coding, Analysis), card previews, inline create/edit form, and 1-click **Insert into Chat** action.

- CARD-145 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-145):
  - **Comprehensive Document Extraction Pipeline**: Added universal document parsing tools to extract text, tables, and structures from PDFs (`.pdf`), Excel spreadsheets (`.xlsx`, `.xls`), Word documents (`.docx`), CSVs (`.csv`), and code/text files.
  - **Specialist Agent Tool (`read_document_file`)**: Registered `read_document_file(path, max_pages, max_rows)` tool in `DocumentTools` accessible to both `assistant` and `autoreiv` platform agents.
  - **Automatic Turn-1 Previews**: Enhanced chat prompt formatting so attached small documents and spreadsheets (< 16 KB) automatically inline parsed table grids and section summaries directly into the initial turn prompt.

- CARD-144 Done (`AutoReiv.Gateway`, `AutoReiv.Web` - CARD-144):
  - **Native Multimodal Image Vision Gateway**: Extended LLM provider adapters (`OpenAIProviderAdapter`, `OllamaProviderAdapter`) and `ChatMessage` domain models to support native vision image input payloads.
  - **OpenAI & Gemini Multimodal Formatting**: Serializes attached images and local path references into OpenAI-standard `{"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}` content structures for vision-capable models (e.g. Gemini 1.5/2.0 Flash, GPT-4o).
  - **Ollama Vision Support**: Automatically extracts and packages Base64 image byte strings into Ollama's native `images: [...]` payload for local Vision-Language Models (e.g. `qwen2.5-vl`, `llava`).
  - **Zero-Migration Backward Compatibility**: Automatically detects and extracts local image paths referenced in prompt annotations without database schema alterations.

- CARD-143 Done (`AutoReiv.Web` - CARD-143):
  - **Chat Media & File Attachments Pipeline**: Introduced backend and frontend infrastructure allowing users to attach images, videos, audio, PDFs, code, and text files directly to chat sessions.
  - **Secure Ingestion & Serving Endpoints**: Built `POST /api/chat/upload` with path traversal sanitization and safe session directory sandboxing, and `GET /api/chat/attachments/{file_id}/{filename}` for streaming files with accurate MIME types.
  - **Interactive Attachment Staging Bar**: Activated `#chatAttachBtn` in the options drawer to open device file pickers; added `#chatAttachmentsPreviewList` inside the input form rendering file thumbnails, names, formatted sizes, and 1-click removal buttons before dispatch.
  - **Message Thread Previews**: Updated user message rendering in the chat thread to display media attachment grids and download pills.

- CARD-142 Done (`AutoReiv.Web` - CARD-142):
  - **Collapsible Chat Actions Drawer**: Replaced the cluttered mode checkboxes and dropdown that permanently occupied 2+ rows in the input dock with an ergonomic **`[ + ]` Action Button** (`#chatOptionsToggleBtn`) and expandable drawer (`#chatOptionsDrawer`), reclaiming 50px+ of vertical chat space on mobile.
  - **Options Popout Sheet**: Built an accessible, animated popout tray featuring runtime mode toggles (Verify, Goal Mode, Auto-run), the workflow selector, and reserved slots for upcoming media attachments and prompt catalog tools.
  - **Active Modes Indicator**: Added `#chatActiveModesIndicator` displaying real-time badges (e.g. `Γëí╞Æ├ä┬╗ Multi-phase job`, `Auto-run`, `Verify Active`) adjacent to the options trigger button so active modes are immediately visible even when the drawer is tucked away.
  - **Keyboard & Click-Away Dismissal**: Supports pressing `Escape` or tapping anywhere outside the drawer to dismiss it naturally.

- CARD-141 Done (`AutoReiv.Web` - CARD-141):
  - **Wiki Note Responsive Header**: Redesigned `#wikiNoteHeader` to stack comfortably on mobile (`flex-col sm:flex-row`), guaranteeing full-width breathing room for note titles (`#activeWikiTitle`) and relative path pills (`#activeWikiPath`) without truncating behind action controls.
  - **Collapsible YAML Frontmatter Inspector**: Replaced the bulky static metadata box with a slim 28px summary bar (`#wikiFmSummaryBar`) and quick toggle button (`#wikiToggleFmBtn`), reclaiming massive vertical space for note reading and editing.
  - **Rendered vs. Raw YAML Toggle**: Built a segmented view mode switcher inside the expanded frontmatter card, allowing users to toggle between visual pills/tags/summaries (`#fmRenderedView`) and exact monospace YAML syntax (`#fmRawView`) with a 1-click clipboard copy button (`#fmCopyRawBtn`).
  - **Backend Raw Frontmatter Extraction**: Enhanced `read_note` in `WikiStore` and `FrontmatterParser` to extract and return exact `raw_frontmatter` strings in note REST payloads.

- CARD-140 Done (`AutoReiv.Web` - CARD-140):
  - **Removed Obsolete Wiki Knowledge Graph Modal and Button**: Deleted the non-interactive Mermaid-based Graph modal (`#wikiGraphModal`) and its toolbar button (`#wikiGraphViewBtn`), uncluttering the Wiki Studio toolbar and focusing users on the interactive Force-Directed Mind Map (`#wikiMindMapModal`).

- CARD-139 Done (`AutoReiv.Web` - CARD-139):
  - **Three-Surface Information Architecture**: Replaced the cluttered 7-page navigation with 3 consolidated core surfaces: **Cockpit** (Chat Studio & Workbench), **Vault** (Wiki & Projects), and **Fleet** (Agents, Routines, Observability, Settings).
  - **Mobile Header Surface Switcher**: Added `#mobileSurfaceSwitcher` with quick pills for `#surfaceBtnCockpit`, `#surfaceBtnVault`, and `#surfaceBtnFleet`.
  - **Streamlined Conversations Drawer**: Redesigned `#sidebar` so that **+ New Conversation** and the full **Conversations List** (`#sessionList`) take 85% of the drawer, moving the 7 studios to a compact 2-column footer strip (`#sidebarNav`) while preserving all ARIA contracts.
  - **Desktop Default-Collapsed Sessions**: Configured `#sidebar` to default to collapsed on desktop, maximizing chat space while remaining instantly accessible via the session toggle button.

- CARD-138 Done (`AutoReiv.Web` - CARD-138):
  - **52px Slim Icon Rail**: Replaced permanent 280px left sidebar with a sleek, responsive desktop rail (`#appRail`) and toggleable sessions drawer (`#toggleSidebarBtn`), reclaiming over 220px of desktop horizontal space.
  - **Dual-Pane Workbench Canvas**: Built `#chatWorkbenchPane` that renders artifacts (markdown plans, code snippets, diffs) side-by-side with conversation on desktop ($> 1024\text{px}$) and as an intuitive full-height slide-out sheet on mobile ($< 1024\text{px}$).
  - **Artifact Interaction Controls**: Added tabbed preview/raw views (`#workbenchTabPreview`, `#workbenchTabRaw`), one-click clipboard copy (`#workbenchCopyBtn`), and save-to-wiki (`#workbenchSaveWikiBtn`).
  - **Message Artifact Integration**: Inlined `.workbench-msg-btn` in agent message bubbles for seamless one-click artifact inspection.

- CARD-137 Done (`AutoReiv.Web` - CARD-137):
  - **Modern Systematic UI Overhaul**: Implemented concentric corner radius system (`inner = outer - padding`), edge-touching zero-radius rules, size-following hierarchy, and focus ring offsets across AutoReiv's frontend.
  - **Unified Ergonomic Chat Input Card**: Replaced stacked two-row input bar with an integrated floating card container, reclaiming 40px+ of vertical chat space while preserving 100% of mode toggles, status pills, and action controls.
  - **Maximized Chat Workspace**: Expanded message container from `max-w-2xl` to `max-w-4xl` for spacious multi-agent reasoning, rich code blocks, and markdown tables.
  - **Refined Control Center & Drawers**: Upgraded top bar action group and applied concentric nested radii to the Journey Drawer and Debug Inspector.

- CARD-136 Done (`AutoReiv.Web`, `AutoReiv.Observability` - CARD-136):
  - **Per-Chat Debug Inspector**: Created slide-over inspector `#chatDebugPane` with button `#chatDebugToggleBtn` in Chat Studio.
  - **Diagnostic Envelopes Endpoint**: Added `GET /api/chat/sessions/{session_id}/debug` returning raw LLM message lists, tool call parameters, latency breakdown, TTFT, token usage, and system prompt.
  - **Multi-Tab Payload Viewer**: Integrated tabbed view for Messages, Tool Executions, Metrics, and System Prompt with one-click JSON clipboard copy.

- CARD-135 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Memory` - CARD-135):
  - **Execution Journey Timeline**: Created slide-out inspector `#chatJourneyDrawer` with action button `#chatShowJourneyBtn` in Chat Studio.
  - **Journey Synthesis Endpoint**: Added `GET /api/chat/sessions/{session_id}/journey` aggregating active multi-phase jobs, chronological milestones, tool execution spans with duration, and session artifacts.
  - **Interactive Milestones & Artifacts**: Visual vertical timeline with status badges (queued, running, done, failed) and key discoveries list.

- CARD-134 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-134):
  - **Control Plane Focus & Dashboard Retirement**: Cleanly retired experimental dynamic dashboard renderer and custom pack UI tabs to preserve AutoReiv's core focus as a high-performance Multi-Agent Control Plane.
  - **Stream Cancellation & Engine Delegation**: Implemented true task abort on `POST /api/chat/stream/{session_id}/abort` with `#stopBtn` UI control; delegated `dispatch_handoff` to `HandoffIsolationEngine`.
  - **Episodic Full-Text Search**: Added native SQLite FTS5 virtual table `episodic_facts_fts` with BM25 ranking and automatic triggers for memory retrieval.

- CARD-133 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-133):
  - **Declarative Dashboard Schema**: Created `AgentDashboardManifest` and `DashboardCardDefinition` models supporting `stat_group`, `action_group`, `data_table`, `markdown_editor`, and `markdown_viewer` card types.
  - **AutoReiv Platform Authoring Tools**: Added `scaffold_agent_dashboard` and `read_agent_dashboard` tools to the `build-agent-pack` skill, enabling AutoReiv to generate rich custom dashboards via natural language in Chat.
  - **Dashboard REST API**: Added `GET /api/agent-packs/dashboards`, `GET /api/agent-packs/{pack_id}/dashboard`, `POST /api/agent-packs/{pack_id}/dashboard`, and `POST /api/agent-packs/{pack_id}/action` with ScopedToolRegistry RBAC verification.
  - **Dynamic Studio Frontend Renderer**: Implemented `dynamic_studio.js` module dynamically mounting custom specialist studio tabs into the sidebar navigation, rendering interactive KPI stats, action buttons with loading spinners and toasts, data tables with row actions, and markdown editors.
  - **Gardening Specialist Starter Pack**: Seeded `agent-packs/gardening/` starter pack with `pack.json`, `SKILL.md`, `dashboard.json`, and sample `docs/garden_journal.md`.

- CARD-132 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-132):
  - **Cascading Custom Agent Cleanup**: Standardized custom agent deletion to always cleanly unbind assigned routines, delete operator overrides, and remove physical pack folders from disk.
  - **Permanent Telemetry Purge Toggle**: Added `purge_history` query option and Agent Studio confirmation modal (`#deleteAgentModal`) allowing operators to toggle permanent historical purge of session messages and telemetry records upon agent deletion.

- CARD-131 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-131):
  - **Dynamic Tone Registry**: Created `ToneDefinition` model and SQLite table `tones` seeded with 6 built-in presets (_default, technical, concise, friendly, academic, socratic_) and supporting durable custom tones.
  - **Tone REST API**: Implemented `/api/tones` endpoints for listing, creating, updating, and deleting custom tone directives with built-in protection.
  - **Agent Studio Manage Tones Modal**: Added `[ ╬ô├£├ûΓê⌐Γòò├à Manage Tones ]` button to Card 3 in Agent Studio opening a rich management modal (`#manageTonesModal`) with live list, create form, inline editing, and deletion.
  - **Dynamic System Prompt Injection**: Updated `AgentProfile.get_effective_system_prompt()` and `AgentKernel` to dynamically resolve custom tone directives from database when assembling system prompts.

- CARD-130 Done (`AutoReiv.Observability`, `AutoReiv.Web` - CARD-130):
  - **Agent Studio Lifetime Telemetry**: Bound `loadAgentTelemetry(agentId)` to parse per-agent breakdown metrics from `data.agents` with legacy ID alias resolution, fixing the 0-stat blank display.
  - **Per-Agent Estimated Cost ($)**: Added `estimated_cost_usd` to `AgentKPISummary` and added a dedicated **Est. Cost ($)** badge in Agent Studio under _Agent Telemetry & Lifetime Stats_.
  - **Observability Studio Cost & TTFT Surfacing**: Added **Est. Cost ($)** and **Avg TTFT (ms)** cards to the top KPI overview row, and added an **Est. Cost ($)** column to the _Per-Agent KPI Breakdown_ table.

## [0.17.0] - 2026-08-31

- CARD-129 Done (live-test pass) (`AutoReiv.Observability`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-129):
  - **Distributed Hierarchical Tracing**: Extended `TelemetrySpan` and SQLite `telemetry_spans` table with `trace_id` and `parent_span_id` columns, propagating trace context across turns, tool calls, and subagent handoffs.
  - **Provider & Model Attribution**: Added indexed `provider` and `model` columns on telemetry spans for side-by-side performance comparisons across Ollama, Gemini, Claude, and OpenAI.
  - **Time-To-First-Token (TTFT)**: Captured streaming latency `ttft_ms` across gateway adapters and exposed `avg_ttft_ms` in `KPIDashboardSummary`.
  - **HITL Safety Classification**: Fixed intentional Human-in-the-Loop safety pauses (`approval_required`) to record as `status="hitl_paused"` (`success=True`), eliminating false-positive error spikes.
  - **Cost & KPI Modernization**: Added real-time token cost estimation (`estimated_cost_usd`) and `hitl_paused_count` to KPI dashboard aggregations.
  - **Database Evolution**: Added automatic lightweight schema migrations in `connection.py` preserving existing SQLite databases with zero data loss.
  - **Delegation & Parameter Resilience**: Added automatic type coercion to `HandoffPacket` and tool argument aliasing across orchestration and wiki tools.

- CARD-125 Done (live-test pass) (`AutoReiv.Wiki`, `AutoReiv.Skills` - CARD-125):
  - Deterministic 27-key YAML front matter sequence serialization (`uid`, `title`, `aliases`, `document_type`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
  - Added 16-character SHA-256 `content_hash` computation on notes and tracking for `author`, `model`, `source`, `pinned`, and `access_count`.
  - Enforced strict 2-depth limit under `notes/<domain>/<topic>/<slug>.md` and standard `operations/worklog` / `operations/diagnostics` for routine and weekly logs.
  - Added atomic `wiki_note_append` tool and enhanced `wiki_note_list` with status, tag, author, pinned, and priority metadata filtering.
  - Added incoming `backlinks` calculation on note reads.
  - Authoritative Platform skill runbook in `src/infrastructure/skills/seeds/wiki/SKILL.md` and `platform-packs/assistant/skills/wiki/SKILL.md`.
  - Cleaned vault root folders: removed misplaced templates from `notes/`, relocated weekly logs to `notes/operations/worklog/`, removed legacy directories, and seeded single canonical template at `resources/templates/note_template.md`.

## [0.16.0] - 2026-08-31

- CARD-128 Done (live-test pass) (`AutoReiv.Gateway`, `AutoReiv.Settings` - CARD-128):
  - Added dedicated presets and gateway support for 10 LLM providers: **Ollama (Local)**, **LM Studio (Local)**, **vLLM (Self-Hosted)**, **Google Gemini**, **OpenAI**, **Anthropic Claude**, **OpenRouter**, **Groq Cloud**, **DeepSeek**, and **Together AI**.
  - Built `AnthropicProviderAdapter` (`src/infrastructure/gateway/anthropic_adapter.py`) supporting direct Anthropic Messages API (`/v1/messages`) with `x-api-key`, message/tool translation, and streaming SSE events.
  - Hardened `OpenAIProviderAdapter` to capture reasoning tokens (`reasoning_content` / `reasoning`), robust tool call parsing, Gemini thought signature preservation, guaranteed tool message name resolution, and standard `/v1/models` discovery.
  - Implemented automatic per-provider `HTTP 429` rate limit backoff retry loops with intelligent `retryDelay` and `Retry-After` parsing across OpenAI and Anthropic adapters.
  - Updated Settings Studio dropdown and defaults in `index.html` and `settings.js` for 1-click provider switching.

## [0.15.0] - 2026-08-31

- CARD-127 Done (live-test pass; Jacob approved layout) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-127):
  - Agent Studio top-down hierarchy: Top box is "Platform Skills & Tools" (shared capabilities: `wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sdlc-cards`, `sandbox`), bottom box is "[Agent Name] Pack Skills & Tools" (dedicated pack skills).
  - Completely removed "Also ticked" / `ungrouped_pack_tools` floating checkbox rendering. Every single tool is nested under a parent skill accordion.
  - Promoted cross-assigned / shared tools into first-class Platform skills (`coordination`, `proposals`, `worker`, etc.) with full metadata and nested tool toggles.
  - Updated `platform-packs/assistant` (dedicated `weekly-tasks`) and `platform-packs/autoreiv` (dedicated `build-agent-pack`, `platform-health`, `session-inspect`) to receive shared permissions from Platform skills without orphan tools.
- CARD-126 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-126):
  - Three homes: Platform skills/tools, Platform Agent Packs (`platform-packs/assistant` + `autoreiv`, always seed-if-missing into `$DATA_DIR/packs/`), user packs (`agent-packs/` still not scanned on startup). Dropped Python builtins for Assistant and AutoReiv; Agent Builder stays hidden. Platform skill `wiki` stub with nested wiki tools. Assistant pack owns `weekly-tasks`; AutoReiv owns `build-agent-pack` / `platform-health` / `session-inspect`. Agent Studio nests tools under skills (Platform box, then this pack). Chat still lists ticked tool schemas every turn (CARD-117/121).
- CARD-124 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-124):
  - Shipped core is Assistant + AutoReiv (Agent Builder stays a hidden builtin). Conductor, Coding, and Review are three Agent Packs in `agent-packs/` (optional import, not auto-loaded on startup). Chat shows Conductor; Coding/Review stay handoff-only. Review ticks `git_diff` / `git_status` and never write/commit. Jacob's `$DATA_DIR/packs/` imported on this card.
- CARD-125 Ready (later backlog, not this pickup) (`docs/cards/` - CARD-125):
  - Revisit Wiki schema, tools, and operating manual. Emphasis: correct deterministic YAML front matter and extensive metadata. Platform skill `wiki` stub is the Studio/packs squeeze-in; this card is the later fill. Do not implement until Jacob says build.
- CARD-119 Done (live-test pass; Jacob said look good) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Agent Packs are packaging of one specialist (nested skills/tools schema 1.1, Agent Studio Import/Export, New Agent hands off to AutoReiv in Chat). AutoReiv skills: build-agent-pack (scaffold/import/export) and recommend-capability (HITL propose when stuck). Agent Builder hidden from Chat and Agent Studio list. Show in Chat default on. Foo pack create + delete worked. Local commit only. No push.
- CARD-119 hide Agent Builder from Chat picker (`AutoReiv.Web` - CARD-119): skip `agent-builder` by id in Chat pickers; API serializes `show_in_chat=false` so a stale override cannot turn it back on. Status Done (live-test pass). Local commit only. No push.
- CARD-119 AutoReiv pack vs recommend skills; hide Agent Builder (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - AutoReiv skills are `build-agent-pack` (scaffold/import/export a named specialist) and `recommend-capability` (HITL propose_* when there is no path). `save_agent_specification` is not ticked on AutoReiv; pack write is `scaffold_agent_pack`. Agent Builder is hidden from Chat (`show_in_chat=false`) and skipped in the Agent Studio left list; API/handoff may still resolve the id. Coding / Conductor / Review stay. No named observability skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 follow-up New Agent AutoReiv handoff and nested pack skills (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - New Agent in Agent Studio switches to Chat, selects AutoReiv, starts a fresh session, and fills `I am ready to create a new agent.` (focused, not auto-sent). Nested pack schema 1.1 puts tools under skills; `allowed_skill` / `pack_tool_names` stay derived compat. AutoReiv `build-agent-pack` asks for agent details, each skill, and tools per skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 Agent Packs import/export/build (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Product landed. Agent Pack is packaging, not a fourth primitive: schema + how-to (`docs/specs/agent-packs.md`), Agent Studio Import/Export on the selected agent, `show_in_chat` (default on) persisted and filtered in Chat pickers only, pack-owned tool ids fill the Pack-owned group and come on with the pack, AutoReiv runbook `build-agent-pack` plus `export_agent_pack` / `import_agent_pack` / `scaffold_agent_pack`. Workflows ride along; transcripts, secrets, and instance facts do not. Builtins not ripped. okta-admin not reshipped. No Pack Studio. Status Done (live-test pass). Local commit only. No push.

- CARD-123 Done (live-test pass; Jacob said it feels great) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-123):
  - Workflow is a reusable plan on the agent who starts it (JSON under `$DATA_DIR/agents/<id>/workflows/`). Goal remains the one-off factory. After a Goal-planned job: Save as workflow stores the chapter list (who, skill vs handoff, done-when), not instance facts. Chat picker next to Goal and Verify is empty until the first save. Pick a recipe + new prompt instantiates a Job with those Phase rows. Agent Studio has a small owned-recipes list (edit name/order/who/skill-vs-handoff, delete with confirm). No Workflow Studio. No Agent Packs (119), no memory (116). CARD-118 marked Done (live-test pass). Pickup later is CARD-119 or CARD-116 when Jacob asks.

- CARD-118 one Agent Studio; drop Skills Studio and Forge place name (`AutoReiv.Web` - CARD-118):
  - One screen: Agent Studio. Skills Studio removed from the main nav and page. Selected agent shows identity, instructions, tone, Tools (CARD-121 checklists), and Skills runbooks (CARD-117 ticks plus open/edit of SKILL.md name, blurb, and body). Archive/confirm-delete of user runbooks moved here. Users do not hand-edit Python tool implementations. Retire Forge as a place name (h2/copy/app init). `forge.js` filename and element ids kept. Stop shipping `okta-admin` as a bundled seed: removed repo seed `src/infrastructure/skills/seeds/okta-admin` and the live data-dir copy only (`%LOCALAPPDATA%\\AutoReiv\\skills\\okta-admin`). No mass-delete of other user skills. APIs for list/read/write SKILL.md kept. No Agent Packs (119), no Workflow Studio (123), no memory (116). CARD-120 marked Done (live-test pass). Status In Review.

- CARD-120 Done (live-test pass; Jacob said ok next) (`AutoReiv.Kernel` - CARD-120):
  - Rename-only accepted. Skill in code means SKILL.md runbook. Pickup is CARD-118.

- CARD-120 rename Python tool groups so skill means runbook (`AutoReiv.Kernel` - CARD-120):
  - Tool-group modules/classes renamed `*Skill` ╬ô├Ñ├å `*Tools` (`wiki_tools.py` / `WikiTools`, `git_tools.py` / `GitTools`, `card_tools.py` / `CardTools`, sandbox `execute_code` wrappers, etc.). Folder `src/application/skills/` kept: runbook catalog (`user_catalog`, `dynamic_loader`, `skill_curator`) stays; tool-group files are no longer `*_skill.py`. Manifest clustering identifiers no longer call tool groups skills. Zero behavior change. Tool callable names, `allowed_skill`, and `skill_view` unchanged. CARD-121 marked Done (live-test pass).

- CARD-121 tools as one callable and two Studio groups (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-121):
  - Done (live-test pass). Tool = one atomic callable. Agent Studio tools card is Pack-owned (empty until Agent Packs) and Platform checkboxes. Dropped pack-master / skill-pack grouping and RBAC copy. Untick still omits schema. SKILL.md JSON stubs stay labels, not model callables. Wiki stays split (`wiki_note_read` / `wiki_note_create` / ...). Builtin allowlists unchanged. CARD-117 marked Done.

- CARD-117 skill allowlist and name+blurb prompt inject (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-117):
  - `AgentProfile.allowed_skill` persists via the agents API (and across reload). Prompt injects this agent's ticked SKILL.md names + short descriptions, not the runbook body. `skill_view` refuses unticked ids. Empty allowlist injects nothing. Platform skills default off (no silent okta-admin). Pack-owned group is empty until Agent Packs. Agent Studio checklist next to the existing tool checkboxes.

- CARD-123 walked save Goal plan as workflow, picker in Chat (`docs/cards/` - CARD-123):
  - Walked lock recorded, not built (Jacob t161-t164u). Workflow = reusable plan. Lives with the agent who starts it. Picker in Chat next to Goal and Verify, only that agent's startable recipes. Do not force workflows day one; empty picker is correct. Primary birth: Goal checkbox then Chat 'Save as workflow' after a plan/run you like. New prompt + picked workflow = new Job, same chapters, different facts. Goal is the factory, not already a workflow. Goal plans phases today; there is no save and no picker. Start in Chat; optional later edit in Agent Studio on the owner. No Workflow Studio. One object: a phase is skill or handoff. Save the chapter list, not instance facts. Pickup after CARD-117 / CARD-121 / CARD-120. Skills Studio is not the house (CARD-118). Status stays Ready. No product code.

- CARD-118 walked one Agent Studio; drop Skills Studio and okta-admin seed (`docs/cards/` - CARD-118):
  - Walked lock recorded, not built (Jacob t159-t160u). Drop Skills Studio as a standalone pack editor (not freeze-as-the-destination). A skill belongs to an agent. One screen: Agent Studio. Sidebar already says Agent Studio; app.js/h2 still say Agent Forge / Agent Forge Studio ╬ô├ç├╢ retire Forge as a place name. Checkbox grid is the Tools section, not a second product. Selected agent: instructions, tone, platform ticks (All Off except Assistant/AutoReiv), pack skill list (open/edit runbooks), pack tool ticks. Users do not hand-edit tool implementations; pack-builder / Agent Builder later owns wiring tools. Fewer pages. Later CARD-119 Agent Packs = import/export/backup of the same agent in user data on this screen, not a third pack-manager tab unless the list gets huge. Drop shipped `okta-admin` seed as a product pack (teaching example, not a specialist). Do not delete files here; seed lives `src/infrastructure/skills/seeds/okta-admin` and `$DATA_DIR/skills/okta-admin`. CARD-108 was the seed; this card owns do-not-keep-as-product-pack. Core roster still Assistant + AutoReiv (CARD-119). Status stays Ready. No product code.

- Opened backlog CARD-123 Workflow recipe (`docs/cards/` - CARD-123):
  - Alignment only. Workflow is a first-class recipe. Not a skill. Not Goal. Instantiating creates a Job with Phase rows. Lives next to jobs, not in Skills Studio. Agent Studio / later a section, not a new graph runtime. Pickup after CARD-117 / CARD-121 / CARD-120. Cheat-sheet lock: workflow (recipe) vs job (this run) vs phase (chapter). HR new-employee-onboarding example without requiring live HR. Change list stub: object is missing today; Goal checkbox is a one-off planner; every chat is a Job named Chat. Status Ready. `type:docs` `type:refactor`. No product code.

- Artifact naming scrub 2026-08-30 t157u (cards, specs, CHANGELOG, ADRs, RTM, user-visible strings):
  - Inspiration product names removed from AutoReiv artifacts unless we are literally integrating that product. CARD-116 may still name Mem0/Letta/Zep as a vendor evaluation. Research folder outside this repo may keep names. Reworded to: user data outside git; progressive disclosure (name+blurb then body); skill curator archive; purpose-based model routing; child session gets the packet only; prior art studied outside this repo. Do not point this repo at a research path for inspiration products. No product code.

- CARD-121 walked change list 2026-08-30 (`docs/cards/` - CARD-121):
  - Walked lock recorded, not built. Tool = one callable. Split read vs write where it matters (`wiki_read` / `wiki_write`). Agent Studio two groups: pack-owned ON with the agent; platform All Off except Assistant and AutoReiv. Untick omits schema (already true via `allowed_tool_names`; keep it true). Do not put stub JSON tools from SKILL.md into the model as callables. Do not hide real tools inside a skill. Drop/rename Forge pack-master grouping so it does not say skill pack. `manifest.py` clustering tools into skill packs is the wrong mix. No live Okta, no mapper, no 12-tool warning (CARD-115 already removed it). Artifacts do not name inspiration products (t157u). Status stays Ready. No product code.

- CARD-120 walked rename-only (`docs/cards/` - CARD-120):
  - Walked lock recorded, not built. Rename-only after CARD-117 and CARD-121. Python `*Skill` modules (WikiSkill, GitSkill, CardSkill, etc. under `src/application/skills/`) are tool groups, not runbooks. After rename, skill in code means `SKILL.md`. No new features, no behavior change. `wiki_read` vs `wiki_write` split belongs to CARD-121, not extra scope here. Status stays Ready. No product code.

- CARD-117 walked change list 2026-08-30 (`docs/cards/` - CARD-117):
  - Walked lock recorded, not built. Skill = one SKILL.md runbook (stop saying skill pack for that file). Agent profile skill checklist next to Forge (`allowed_skill` ids; today `AgentProfile` only has `allowed_tool_names` in `src/domain/kernel/models.py`). Pack-owned skills ON with that agent; platform skills All Off except Assistant and AutoReiv. Untick omits name+blurb and refuses `skill_view` for that id. Prompt injects ticked names+blurbs; keep `skill_view` for body; drop must-call-list-first. `user_catalog.py` already lists name+description; only Assistant/AutoReiv/Agent Builder have those tools (`profiles.py`). Okta Admin = agent, user-provisioning = skill; no live Okta. CARD-118 studio freeze; CARD-120 Python `*Skill` rename. Status stays Ready. No product code.

- CARD-117/121 controls: platform All Off except Assistant/AutoReiv; pack-owned on; untick omits context (`docs/cards/` - CARD-117):
  - t154u lock recorded, not built. Ditch RBAC as the name. Two Agent Studio checkbox groups per agent: pack-owned come ON at create/import; platform/shared (`wiki_read`, `wiki_write` separate, etc.) default All Off except builtin Assistant and AutoReiv (those keep useful platform ticks we choose). Untick MUST omit tool schema / skill name+blurb from model context. Agent directory is name + one-line purpose only. No in-flight dynamic mapper. No pixel spec. CARD-119 roster epic not duplicated. CARD-121 one-line pointer. Status stays Ready. No product code.

- CARD-119 intent: core ship Assistant+AutoReiv; specialists as packs later (`docs/cards/` - CARD-119):
  - Later-discuss only. When Agent Packs are eventually implemented, shipped core roster is two agents: Assistant and AutoReiv. Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) arrive as Agent Packs (agent + skills + tools), not more builtins. Do not rip existing builtins on this card. Foundations first (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 unrelated low-priority. Controls notes (not this card to build): two Agent Studio checkbox groups (pack-owned vs small platform group); untick omits schema; no RBAC engine; no in-flight dynamic mapper; handoff is name+blurb directory. Status stays Ready. No product code.

- Opened low-priority CARD-122 three-beats skill idea (`docs/cards/` - CARD-122):
  - Later SKILL.md runbook for an autonomous coder working with a visionary (Jacob). Documents the 2026-08-30 three-beats working agreement. Ultra low priority. Do not pick up until CARD-117/121/120 (and workflow later) are in motion or done. Not a reason to build Skills Studio features. No product code.

- CARD-116 explore Mem0 then native; pickup after refactors (`docs/specs/per-agent-memory/` - CARD-116):
  - Research still Ready. Explore both Mem0 and a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do not lock Mem0. When later executed: start with Mem0 deep research, then compare. Pickup blocked until after the other pile (orchestration / Goal / loops / graphs) and foundation refactor cards (CARD-117, CARD-121, CARD-120, CARD-118; CARD-119 later-discuss). Memory is a bolt-on after those are ironed out. Three-shelf architecture kept. Wiki / Letta product / Zep product stay out. No product code.

- CARD-116 research leaning (`docs/specs/per-agent-memory/` - CARD-116):
  - Research leaning recorded (not a locked vendor purchase). Wiki / Letta product / Zep product: no. Mem0 to evaluate for archive (shelf 3). Three-shelf per-agent brain. No product code.

- Opened backlog CARD-121 tools ground-up (`docs/cards/` - CARD-121):
  - Alignment only. Tool = one atomic callable (name + description + parameters to the model every turn if allowlisted). Not a worker, not a runbook, not a skill pack. Ground-up: current Forge pack grouping, `manifest.py` skill-pack clustering, and Python `*_skill.py` tool modules are likely off/mixed. Working agreement recorded (walk with CARD-117/120; no silent-big-bang). No product code.

- CARD-117 points at the shared working agreement and CARD-121 (`docs/cards/` - CARD-117):
  - Short "When we pick this up" pointer. CARD-121 is the sibling tools pass, not a second definition of skill. No product code.

- Expanded CARD-117 skills primitive intent (`docs/cards/` - CARD-117):
  - Ground-up revisit recorded, not implemented. Intent expanded for controls, load path, levers, and built-in vs user-added. Current Skills Studio, `$DATA_DIR/skills` packs, `list_user_skill_packs` + `skill_view`, Python `*Skill` classes, and leftover orchestration `skills: List[str]` are likely off. Two explicit per-agent lists (tools already in Agent Studio; skills list missing). Load path: inject name+blurb every turn; body on open; extra list call is off vs progressive disclosure (name+blurb then body). Skill on/off levers next to the agent, not Skills Studio. CARD-118/119/120 cross-linked. No product code.

- Opened backlog CARD-117 skills primitive = one SKILL.md runbook (`docs/cards/` - CARD-117):
  - Alignment only. Skill = one runbook (order, pitfalls, done-when), not a skill pack, not a worker. Progressive disclosure name+description first; skill index is name+blurb only. Tools on the agent allowlist still go to the model every turn. Stop using Skill Pack for the primitive. Points at CARD-114 findings and prior art studied outside this repo. No product code.

- Opened backlog CARD-118 rethink or replace Skills Studio (`docs/cards/` - CARD-118):
  - Freeze only. Jacob's original studio organized before definitions were solid. Current studio edits `$DATA_DIR/skills` SKILL.md packs. Likely drop/replace later. No big studio features until CARD-117. No product code.

- Opened backlog CARD-119 Agent Packs later discussion (`docs/cards/` - CARD-119):
  - Conceptual packaging: ship an agent with its skills and tools (e.g. Okta Admin bundle). Not a fourth primitive. Not build-now. Discuss after agent/skill/tool foundations. No product code.

- Opened backlog CARD-120 rename Python *Skill modules (`docs/cards/` - CARD-120):
  - Refactor-and-alignment later. WikiSkill, GitSkill, CardSkill, etc. are tool groups, not runbooks. Skill in code should mean a SKILL.md runbook. Foundations first. No new features. No product code.

- Opened backlog CARD-116 per-agent memory research (`docs/specs/per-agent-memory/` - CARD-116):
  - Research only. Independent first-class brain per agent (not one markdown for all, not only Chat session history). Agent Studio fact-lifetime and other levers with hard min/max. Prior art studied outside this repo. No vendor pick. No product code.

- Remove Forge 12-tool allowlist warning (`AutoReiv.Web` - CARD-115):
  - Agent Studio no longer shows the CARD-078 amber banner when 12+ tools are checked. `FORGE_ALLOWLIST_WARN_AT` and `#forgeAllowlistWarning` are removed. Save and tool mounting are unchanged. No hard cap.

- Opened CARD-114 user intent review and product alignment (`docs/specs/user-intent-review/` - CARD-114):
  - Review artifact only. Findings SSOT at `docs/specs/user-intent-review/findings.md` (35 findings, verified on `qa`). No product code.

- Skills Studio archive and confirm-delete for user packs (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-113):
  - Studio lists `$DATA_DIR/skills` user packs only. Python builtins (WikiSkill, execute_code, handoff) stay out (`[REQ-DATA-015]`).
  - Archive / Unarchive reuse CARD-112 `POST /api/skills/user-packs/{id}/archive`, unarchive, and `GET /api/skills/archived-packs`. Live list hides archived packs; Unarchive restores (`[REQ-DATA-015]` `[REQ-DATA-016]`).
  - `DELETE /api/skills/user-packs/{id}` requires `confirm=true` (400 without). Removes the jailed live dir and `_archive/<id>/` if present. Path traversal (`../`) is rejected (`[REQ-DATA-017]`).
  - Bundled seed `okta-admin` DELETE is 409 unless `confirm_seed=true`. Repo `src/infrastructure/skills/seeds/` is never deleted. UI uses `window.confirm` plus a second confirm for okta-admin (`[REQ-DATA-018]`).

- Skill curator stale/archive (`AutoReiv.Skills`, `AutoReiv.Routines` - CARD-112):
  - Unused user packs go active -> stale (30d) -> archive (90d). Archive is a directory move to `$DATA_DIR/skills/_archive/<id>/`. Live `SKILL.md` is never deleted (`[REQ-IMPROVE-013]`).
  - `okta-admin` / `BUNDLED_PACK_IDS` are never auto-archived or deleted. Repo `src/infrastructure/skills/seeds/` is untouched. Explicit confirm is required to archive a bundled pack (`[REQ-IMPROVE-014]`).
  - Unarchive is the reverse move. Dest-exists fails closed. Pack reappears in `GET /api/skills/user-packs` / Skills Studio. No `propose_skill` (`[REQ-IMPROVE-015]`).
  - Curator function + paused sibling routine `skill-curator` (`enabled=false`). CARD-111 harvest hook is off (`metadata.auto_archive=false`). Unknown last-used fails closed. Does not rewrite packs mid-chat-turn (`[REQ-IMPROVE-016]`).

- Nightly skill eval routine (`AutoReiv.Routines`, `AutoReiv.Skills` - CARD-111):
  - Seed `skill-eval-sleep` into existing `routines` / `BUILTIN_ROUTINES` targeting `agent-builder`. Same `RoutineExecutor` + `routine_runs`. No second scheduler. No `skillopt` pip (`[REQ-IMPROVE-007]` `[REQ-IMPROVE-012]`).
  - Default **paused** (`enabled=false`). When enabled, `next_run_at` is weekday 21:00 `America/New_York` (timezone-aware UTC instant). Not 02:00 local (surprise GPU load) and not 21:00 UTC (`[REQ-IMPROVE-008]`).
  - In-process job harvests failed `telemetry_spans` turns and FAILED jobs/phases from the live `$DATA_DIR` db (lookback 72h, capped). Refuses checkout `./data` when LocalAppData is live. Empty harvest is a success no-op (`[REQ-IMPROVE-009]`).
  - Replay optional and default off; honors generation slot default 1. Checker must pass to stage; missing named checker is honest skip. Stage is CARD-106 `propose_skill` draft only (`auto_commit` false). No `SKILL.md` write, no `commit_skill_pack`, no `stream_turn` child phase (`[REQ-IMPROVE-010]` `[REQ-IMPROVE-011]` `[REQ-IMPROVE-016]`).

- ACE-style online playbook notes + snapshot/rollback (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-110):
  - Failed turn / checker miss produces at most one tiny ACE delta. Generator is existing `AgentKernel`. In-process Reflector + Curator. No second kernel, LangGraph, or ACE vendor (`[REQ-IMPROVE-001]` `[REQ-IMPROVE-002]`).
  - Online path parks a CARD-106 `propose_skill` draft (`ace_delta`, snapshot id). Live `SKILL.md` is not rewritten in the turn. Python-shaped deltas stay `propose_tool` drafts with `requires human/code card`. No `src/` writes (`[REQ-IMPROVE-003]` `[REQ-IMPROVE-005]`).
  - `UserSkillCatalog` snapshots `SKILL.md` + sidecar notes under `$DATA_DIR/skills/<id>/snapshots/<utc-iso>/` before apply. Rollback restores bytes. Snapshot I/O failure skips apply (`[REQ-IMPROVE-004]`).
  - Optional append-only `PLAYBOOK_NOTES.md` / `notes.jsonl` sidecar does not modify `SKILL.md`. Promotion into the playbook is still `propose_skill`. Online path does not enqueue nightly eval (`[REQ-IMPROVE-006]` `[REQ-IMPROVE-016]`).

- Skill self-improve (`docs/specs/skill-self-improve/` - CARD-110-112): spec and Slice D cards opened. ACE-style online playbook deltas with snapshot/rollback (HITL `propose_skill` if writing SKILL.md), nightly SkillOpt-Sleep-shaped eval routine on the existing routines table (21:00 America/New_York weekdays, default paused, validation gate), skill curator stale user-pack archive (never delete bundled/okta-admin). No feature code. No push. No DB wipe.

- Windows launcher uses data dir (`AutoReiv.Deploy` - CARD-109):
  - `deploy/windows/run_autoreiv.ps1` no longer defaults `--db-path` / `--wiki-path` (or `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH`) to checkout `./data`. Default Windows boot (including `-Reload`) lets `DataDirResolver` open `%LOCALAPPDATA%\AutoReiv` for db, wiki, and skills (`[REQ-DATA-001]`, `[REQ-DATA-003]`).
  - Explicit `AUTOREIV_DB_PATH` / `-DbPath` / `--db-path` still win when they are not the checkout legacy path. Leftover checkout env from an old launcher session is stripped.

- Okta admin skill pack scaffold (`AutoReiv.Skills` - CARD-108):
  - Bundled agentskills.io pack `okta-admin` at `src/infrastructure/skills/seeds/okta-admin/SKILL.md` is copy-if-missing seeded into `$DATA_DIR/skills/okta-admin/SKILL.md` on data-dir bootstrap. Existing dest is left alone so user edits survive a second boot (`[REQ-BUILD-015]`).
  - Playbook SOP (list users, groups, conceptual MFA reset/unlock, assign app) plus JSON tool stubs. No live Okta API, no credentials, no Okta env keys, no Python Okta SDK in `src/` (`[REQ-BUILD-016]`).

- Agent Builder specialist writes approved skill packs (`AutoReiv.Agents`, `AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-107):
  - Builtin `agent-builder` Chat specialist (not Conductor). Allowlist stays under 12: lookup, propose_*, list packs, skill_view, commit_skill_pack, agent-spec tools, handoff. No execute_code, git, or card writes (`[REQ-BUILD-009]`).
  - New tools stay on existing `AgentBuilderSkill`. `commit_skill_pack` writes approved skill/tool/workflow proposals through `UserSkillCatalog.save_pack` into `$DATA_DIR/skills` (same files Skills Studio edits). Draft/rejected fail closed. Python stubs never write `src/` (`[REQ-BUILD-010]` `[REQ-BUILD-012]` `[REQ-BUILD-014]`).
  - Default Chat is one Job + one Phase + `stream_turn`. Goal mode uses the CARD-099 no-tool planner with linear research phases (survey, draft playbook, declare tools, HITL propose). Research does not write `SKILL.md` (`[REQ-BUILD-011]`).
  - Soft CARD-078 sprawl / extend-specialist warning is visible before commit and on `save_agent_specification`. Not a hard gate (`[REQ-BUILD-013]`). Approve still does not write disk; commit is the write.

- propose_skill / propose_tool / propose_workflow HITL drafts (`AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-106):
  - Tools on existing `AgentBuilderSkill` write a `proposals` row (`kind` skill|tool|workflow, `status` draft) plus a Chat HITL `pending_approvals` park (`[REQ-BUILD-001]` `[REQ-BUILD-002]` `[REQ-BUILD-003]` `[REQ-BUILD-007]`).
  - Payload is what / why / how / where, jailed under `$DATA_DIR/skills`. Missing field fails closed. No `SKILL.md` write. No Python under `src/`. Workflow is playbook SOP, not job-template YAML (`[REQ-BUILD-004]` `[REQ-BUILD-005]`).
  - Approve marks `approved` and does **not** write disk. Reject marks `rejected`. Pack commit is CARD-107. Tool drafts that look like Python builtins stay draft-only with note `requires human/code card` (`[REQ-BUILD-008]`).
  - Soft CARD-078 sprawl warning when the target allowlist would be >= 12 or a new agent is preferred over extending a specialist. Does not block the draft (`[REQ-BUILD-006]`).
  - Allowlisted on Assistant and AutoReiv (discovery). Not Coding, Review, or Conductor. `save_agent_specification` unchanged (immediate, no HITL).

- Agent Builder HITL (`docs/specs/agent-builder-hitl/` - CARD-106-108): spec and Slice C cards opened. `propose_skill` / `propose_tool` / `propose_workflow` HITL drafts on existing AgentBuilderSkill, Agent Builder specialist wired to Job/Phase + data_dir skills, Okta admin pack scaffold. No feature code. No push.

- Skills Studio UI (`AutoReiv.Web`, `AutoReiv.Skills` - CARD-105):
  - Sibling tab of Agent Studio lists user packs from `$DATA_DIR/skills` (name + description) and reads/edits `SKILL.md` on disk. Disk is the source of truth (`[REQ-DATA-012]`).
  - Opening a pack lists JSON tools parsed from that `SKILL.md`. No tool blocks yields an empty list (playbook-only packs are valid) (`[REQ-DATA-013]`).
  - Job templates are a later placeholder only. Playbook SOP is the SKILL.md body; `jobs.template_id` stays nullable (`[REQ-DATA-014]`).
  - `GET/POST /api/skills/user-packs` and `GET/PUT /api/skills/user-packs/{id}` are jailed to the skills tree. Saves match Forge (direct write, no HITL). Writes do not land in repo `.agents/skills`.

- User agentskills.io packs (`AutoReiv.Skills` - CARD-104):
  - Bootstrap scans `$DATA_DIR/skills/**/SKILL.md` via `DynamicSkillLoader.list_skill_manifests` (frontmatter name + description + path only). Python builtins still register when `skills/` is missing (`[REQ-DATA-009]`, `[REQ-DATA-010]`).
  - `skill_view` loads the SKILL.md body and JSON tool blocks on demand. Colliding user tool names are skipped; builtin Python tools win (`[REQ-DATA-011]`). Pack JSON is not executed as Python.
  - User-pack tools still go through each agent's Forge `allowed_tool_names`. `list_user_skill_packs` and `skill_view` are allowlisted on Assistant and AutoReiv only. Repo `.agents/skills` packs are not auto-mounted.

- Backup and restore of the data dir (`AutoReiv.Data` - CARD-103):
  - `DataDirBackupService` zips the resolved data dir (`autoreiv.db`, wiki, skills, and other tree files) to a timestamped archive under `$DATA_DIR/backups/` (or a user-chosen path). SQLite is snapshotted via the backup API. Checkout source, venv, and `backups/` itself are not included (`[REQ-DATA-007]`).
  - Confirmed restore (`autoreiv restore <src.zip> --yes` / Settings Restore) replaces the tree after extracting to a staging area. Cancel and missing `autoreiv.db` leave the live tree unchanged. A pre-restore zip is kept under `backups/` (`[REQ-DATA-008]`).
  - `POST /api/data-dir/backup` (zip download) and `POST /api/data-dir/restore` (multipart zip, `confirm=true`). Settings Studio Backup / Restore next to the CARD-102 data-dir panel.

- User data directory (`AutoReiv.Data` - CARD-102):
  - `DataDirResolver` resolves `AUTOREIV_DATA_DIR` env > persisted `data_dir` setting > platform default (`%LOCALAPPDATA%\AutoReiv` on Windows, `~/.autoreiv` on POSIX, `/data` in Docker) (`[REQ-DATA-001]`, `[REQ-DATA-002]`).
  - Database, wiki, and skills paths derive from the data dir unless `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` are explicit (`[REQ-DATA-003]`).
  - First boot copy-migrates live `./data/autoreiv.db` and `./data/wiki` into an empty dest. Copy, not move. Does not overwrite dest. Does not wipe source (`[REQ-DATA-004]`).
  - Wired in `create_app`, CLI `--data-dir`, `.env.example`, Docker one volume at `/data` (`[REQ-DATA-005]`, `[REQ-DATA-006]`).

- Control-plane data dir (`docs/specs/control-plane-data-dir/` - CARD-102-105): spec and Slice B cards opened. User data dir outside the checkout, backup/restore, user SKILL.md packs via DynamicSkillLoader, Skills Studio. No feature code. No push.

- propose_followup draft jobs (`AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-101):
  - `propose_followup` writes a `proposals` row kind `followup_job` status `draft` with `requested_by_job_id`, plus a queued Job (`template_id=followup_job`) and a HITL `pending_approvals` park (`[REQ-ORCH-043]`).
  - Creating the draft does not start a phase and does not call `stream_turn` / the kernel. There is no `set_goal` tool.
  - Approve marks the proposal `approved` and leaves the Job `queued`. It does **not** auto `stream_turn`. Reject marks `rejected` and cancels the job.
  - Tool is mounted on OrchestrationSkill next to `handoff_to_agent`. Allowlisted on Conductor / Assistant / AutoReiv, not Coding or Review.

- Chat Job/Phase status strip (`AutoReiv.Chat` - CARD-100):
  - Chat shows job status, current phase name, assigned agent, and react_state (THINKING / CALLING_TOOLS / PARKED / DONE / FAILED) from SSE (`[REQ-ORCH-042]`).
  - Goal badge is "Multi-phase job" (not Plan Graph). PARKED and FAILED are named in the strip.

- Bind chat Goal and Verify to persisted Job/Phase (`AutoReiv.Orchestration`, `AutoReiv.Chat`, `AutoReiv.Kernel` - CARD-099):
  - Default chat creates one Job + one Phase and runs `stream_turn` (`[REQ-ORCH-035]`).
  - Goal mode uses a no-tool `gateway.complete` planner (tools disabled; not `run_turn`), persists linear Job+Phases, and waits for HITL `goal_plan_review` before per-phase `stream_turn` (`[REQ-ORCH-039]`, `[REQ-ORCH-040]`).
  - Verify is a named checker gate; a missing checker is an honest skip and does not claim `verification_passed` (`[REQ-ORCH-041]`).
  - SSE emits `job_created` / `phase_start` / `phase_complete` plus existing `react_state` job/phase ids.

- Packet handoff via stream_turn (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-098):
  - Child handoff requires a `HandoffPacket` (goal, facts, constraints, done_when, budget). The child user message is the packet only; parent transcript is not copied (`[REQ-ORCH-036]`).
  - Child runs `stream_turn` on a new empty session with the child's full context window. No `run_turn` / nested `complete()`, no 32k CARD-094 cap on this path (`[REQ-ORCH-037]`).
  - Global Ollama generation semaphore default 1 (setting `max_concurrent_generations` range 1-3). Extra generations QUEUE. A handoff batch larger than the cap errors and is not silent-truncated (`[REQ-ORCH-038]`).

- Named ReAct States (`AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-097):
  - AgentKernel overlays THINKING|CALLING_TOOLS|PARKED|DONE|FAILED on the existing loop and persists `phase.react_state` when phase_id is in scope (`[REQ-KERNEL-001]`).
  - Chat SSE emits `react_state` with react_state, turn_idx, job_id, phase_id, assigned_agent_id (`[REQ-KERNEL-002]`). No LangGraph. No Chat badge (CARD-100).

- Job/Phase records + orchestrator (AutoReiv.Orchestration - CARD-096): SQLite jobs/phases, JobRepositoryMixin, JobPhaseOrchestrator linear next-or-finish. No LLM. No LangGraph.

- Control-plane Job/Phase (`docs/specs/control-plane-job-phase/` - CARD-096-101): spec and Slice A cards opened. CARD-014 parked (superseded by Job/Phase; DAG idea not deleted). No feature code. No push.

- Card board hygiene: parked CARD-023 through CARD-028 (nothing in flight). Closed CARD-046 (shipped as 063) and CARD-058 (already in CHANGELOG). Real backlog stays Ready. No push.

- Nested Write Budget (`AutoReiv.Orchestration`, `AutoReiv.SDLC` - CARD-095):
  - Nested `max_tokens` is 8192 and Ollama read timeout is 600s so CARD-001 can actually write `react-loop.ps1` (`[REQ-ORCH-030]`).
  - `git_status` / `git_commit` on a non-repo return `skip_commit`. Coding writes the deliverable first (`[REQ-SDLC-073]`).

- Nested Complete Context Cap (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-094):
  - `run_turn` caps `num_ctx` at 32768 and `max_tokens` at 1024. Nested `complete()` sends `think=false` (`[REQ-ORCH-028]`, `[REQ-ORCH-029]`).
  - Conductor handoff passes card id + spec slug. Coding reads the spec; it does not paste bodies.

- Nested Complete Uses Stream (`AutoReiv.Gateway`, `AutoReiv.Orchestration` - CARD-092):
  - Ollama `complete()` consumes `stream=true` so Coding handoff shares Chat's HTTP shape (`[REQ-ORCH-026]`).
  - Usage comes from the done chunk. Timeout/connect/404 labels unchanged (`[REQ-ORCH-027]`).

- Persist Builtin Agent Purpose (`AutoReiv.Forge`, `AutoReiv.Agents` - CARD-093):
  - `AgentCustomization.purpose` is saved on builtin Forge updates and applied on GET (`[REQ-FORGE-020]`).
  - Invalid purpose strings are ignored (`[REQ-FORGE-021]`).

- Close Parent LLM Stream Before Child Handoff (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-091):
  - `stream_turn` acloses the parent LLM stream before tools so Coding `complete()` is not nested inside the Conductor HTTP request (`[REQ-ORCH-023]`).
  - `gateway.stream` acloses inner `provider.stream`. Ollama POSTs relative `/api/chat`; pool timeout is 30s (`[REQ-ORCH-024]`).
  - `TimeoutException` is `Ollama timed out at ...`, not Failed to connect. Connect/timeout still HandoffResult failed (`[REQ-ORCH-025]`).

- Handoff Child Turn Budget (`AutoReiv.Orchestration` - CARD-090):
  - Child handoff `max_turns` defaults to 10 and is `min(max(envelope, profile, 10), 15)` so Coding is not silently capped at 5 (`[REQ-ORCH-020]`).
  - Provider connection failures (`Failed to connect`, `candidate providers failed`) map to HandoffResult status `failed` / success False, not completed (`[REQ-ORCH-021]`).
  - Ollama connect timeout is 30s; nested `complete()` uses its own httpx client so it is not starved by the parent stream (`[REQ-ORCH-022]`).

- YAML Card Frontmatter (`AutoReiv.SDLC` - CARD-089):
  - `parse_card_frontmatter` reads YAML `---` KEY: VALUE `---` plus blockquote `> **Key**: value`. Blockquote wins on conflict; YAML fills missing keys (`[REQ-SDLC-070]`).
  - `spec_reference` aliases Spec Reference / spec_reference / spec; `status` aliases Status / status (`[REQ-SDLC-071]`).
  - YAML-origin cards keep YAML on `set_card_status`. Discuss -> Ready works when the spec dir exists (`[REQ-SDLC-072]`).

- Spec-Driven SDLC Team (`AutoReiv.SDLC` - CARD-080-089): Conductor / Coding / Review loop on project-scoped cards and specs. Jail, Projects studio, SDD scaffold, conventional git, GitHub issue sync. Hold all pushes.

- Cards As GitHub Issues (`AutoReiv.SDLC` - CARD-088):
  - `sync_card_issue` maps card status and type labels and uses `gh` when present (`[REQ-SDLC-040]`, `[REQ-SDLC-041]`).
  - Missing `gh` is a clear error. No tokens. No GitHub MCP. HITL on create/update (`[REQ-SDLC-042]`).

- Git Conventional Commits (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-087):
  - `git_status`, `git_diff`, `git_branch`, `git_commit` are jailed to `project_root`. Conventional subjects only (`[REQ-SDLC-060]`).
  - `git_commit` parks on HITL. Coding allowlist stays at 12. No push (`[REQ-SDLC-061]`).

- SDD Project Scaffold (`AutoReiv.SDLC` - CARD-086):
  - `create_project` copies `templates/sdlc-project/` (AGENTS.md, specs, cards, CHANGELOG, VERSION, CONTRIBUTING, tests, README) (`[REQ-SDLC-050]`).
  - Tool is registered and HITL-parked. Slug cannot escape `projects_root` (`[REQ-SDLC-053]`).

- Projects Studio (`AutoReiv.SDLC`, `AutoReiv.Web` - CARD-085):
  - `projects_root` setting plus GET/POST/DELETE `/api/projects` jailed under that root (`[REQ-SDLC-050]`, `[REQ-SDLC-051]`).
  - Projects Studio is a sidebar tab, not wiki. Selected project is the default card/file root (`[REQ-SDLC-052]`).

- SDLC Bounce Back (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-084):
  - Bounce-back is the CARD-080 state machine plus `handoff_to_agent`. No second engine (`[REQ-SDLC-006]`).
  - Coding may `set_card_status` In Progress -> In Review only and is granted card/file tools under 12 (`[REQ-SDLC-033]`).

- Review Builtin (`AutoReiv.Agents` - CARD-083):
  - Builtin Review (`id=review`) has a 9-tool allowlist. Writes and `execute_code` are denied (`[REQ-SDLC-031]`).
  - Aliases qa / tester / review. Review can set Returned or Done from In Review (`[REQ-SDLC-035]`).

- Conductor Builtin (`AutoReiv.Agents` - CARD-082):
  - Builtin Conductor (`id=conductor`) has an 11-tool allowlist. No `execute_code`, `cli_exec`, or `write_project_file` (`[REQ-SDLC-030]`).
  - Lookup aliases product / plan / scrum / conductor. Chat and Forge list it without a Forge save (`[REQ-SDLC-034]`).

- Project File Tools (`AutoReiv.SDLC` - CARD-081):
  - `list_project_dir`, `read_project_file`, `write_project_file` are jailed under `project_root` (`[REQ-SDLC-021]`, `[REQ-SDLC-022]`).
  - Writes park on existing HITL. Grants wait for Conductor / Review / Coding cards (`[REQ-SDLC-023]`).

- Card Spec Steering Tools (`AutoReiv.SDLC` - CARD-080):
  - Tools `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering` operate on `project_root` (default AutoReiv checkout) (`[REQ-SDLC-012]`, `[REQ-SDLC-013]`).
  - `set_card_status` enforces Discuss | Ready | In Progress | In Review | Returned | Done. Ready needs a spec. Returned increments rounds; max rounds deny and tell the caller to ask the operator (`[REQ-SDLC-010]`, `[REQ-SDLC-011]`).
  - Writes and status changes park on existing HITL (`[REQ-SDLC-014]`, `[REQ-SDLC-020]`).

- Coding Agent Execute Code (`AutoReiv.Agents`, `AutoReiv.Kernel` - CARD-079):
  - Builtin Coding agent is in the roster with a tight allowlist. `execute_code` is granted only on Coding (`[REQ-AGENTS-010]`).
  - Bootstrap registers the sandbox skill so `execute_code` is in the Forge catalog; Assistant is allowlist-denied (`[REQ-AGENTS-011]`).
  - Chat, Forge, and `lookup_agents` list Coding without a Forge save. SQLite overrides still win (`[REQ-AGENTS-012]`).

- Routine Resume From Chat (`AutoReiv.Routines`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-076):
  - Routine parks store `agent_id` and `routine_id` so Chat can list them (`[REQ-HITL-041]`).
  - Chat loads pending approvals for the open agent and shows the existing Approve/Reject card (`[REQ-HITL-042]`).
  - Approve/Reject on a routine park resumes that session with `run_turn(..., resume=True)` and no extra USER (`[REQ-HITL-043]`).

- Forge Allowlist Warning (`AutoReiv.Web` - CARD-078):
  - Forge shows an amber warning when 12 or more tools are checked; save is not blocked (`[REQ-FORGE-007]`, `[REQ-FORGE-008]`).

- Card status hygiene: normalize `docs/cards` labels to Done / Ready / In Progress.

- Remember Last Auto-run (`AutoReiv.Web` - CARD-077):
  - Chat Auto-run toggle is remembered in localStorage; missing memory fail-closes to ask (`[REQ-HITL-039]`, `[REQ-HITL-040]`).

- Goal Mode Review Gate (`AutoReiv.Planning`, `AutoReiv.Web` - CARD-075):
  - Goal Mode parks after formulate so the operator can Approve or Reject the plan (`[REQ-GOAL-020]`, `[REQ-GOAL-021]`).
  - Approve runs the existing step executor; Reject ends cleanly. Send a message to revise (`[REQ-GOAL-022]`).

- Nested Child-Session HITL Resume (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-074):
  - Nested Approve/Reject persist the TOOL on the child session and resume child ReAct with no new USER message (`[REQ-HITL-036]`).
  - Child completion or a second park is written onto the parent as a handoff TOOL (`[REQ-HITL-037]`).
  - Parent resume replays a nested park and stops, or continues after the child result (`[REQ-HITL-038]`).

- Resume After HITL Approve (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-073):
  - After Approve or Reject, Chat starts a continue stream with no new USER message (`[REQ-HITL-033]`).
  - `stream_turn` resume loads existing history and continues ReAct (`[REQ-HITL-034]`). Failed decide does not resume (`[REQ-HITL-035]`).

- Stop Stream After HITL Park (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-072):
  - `stream_turn` yields TURN_END and returns after a gated or nested park so the model cannot keep talking (`[REQ-HITL-031]`).
  - Parked handoffs emit `HANDOFF_COMPLETE` with `status=approval_required`; Chat shows Waiting for approval / Parked (`[REQ-HITL-032]`).

- Agent Chat History Retention (`AutoReiv.Agents`, `AutoReiv.Memory` - CARD-047):
  - Per-agent `history_retention_days` defaults to 30. `0` means never (`[REQ-RET-001]`).
  - Stale chat sessions and messages are pruned on startup and when Chat lists sessions (`[REQ-RET-002]`, `[REQ-RET-004]`).
  - Wiki, facts, and routines are not touched (`[REQ-RET-003]`).

- Session And Routine Approval Mode (`AutoReiv.Safety`, `AutoReiv.Web` - CARD-071):
  - Chat Auto-run toggle sends `approval_mode=run`; default is ask (`[REQ-HITL-027]`).
  - Handoff inherits the parent turn policy (`[REQ-HITL-028]`).
  - Routines store `approval_mode` on the job, default ask (`[REQ-HITL-029]`).
  - Run mode still hard-denies dangerous `cli_exec` (`[REQ-HITL-030]`).

- Keep HITL Approve Output On Screen (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-070):
  - Stream-end history reload no longer wipes a visible HITL card (`[REQ-HITL-025]`).
  - Approve/Reject persist the tool output on the chat session (`[REQ-HITL-026]`).

- Bubble Child HITL Parks To Parent Chat (`AutoReiv.Orchestration`, `AutoReiv.Safety` - CARD-069):
  - A specialist that parks a tool during handoff now surfaces `approval_required` on the parent stream (`[REQ-HITL-023]`, `[REQ-HITL-024]`).
  - Chat Approve/Reject cards use the child tool name and arguments.

- Chat HITL Approve / Reject Buttons (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-068):
  - Chat stream shows a HITL card with tool name, arguments, Approve, and Reject (`[REQ-HITL-020]`).
  - Buttons call `POST /api/approvals/{id}/decision`; the card shows the result (`[REQ-HITL-021]`, `[REQ-HITL-022]`).

- Allowlist-Only Tool Mount (`AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-067):
  - Chat turns mount the full RBAC allowlist; BM25 no longer drops granted tools (`[REQ-TOOLS-010]`).
  - Assistant pins `lookup_agents` next to `handoff_to_agent` (`[REQ-TOOLS-011]`).
  - `list_available_skills_and_tools` is no longer on builtin chat allowlists; Forge still lists the catalog (`[REQ-TOOLS-012]`).

- Unify Agent Handoff To One Public Tool (`AutoReiv.Orchestration`, `AutoReiv.Kernel` - CARD-066):
  - Chat now exposes only `handoff_to_agent`; `delegate_task` is no longer registered (`[REQ-ORCH-010]`).
  - App startup injects the live kernel into `HandoffIsolationEngine` (`[REQ-ORCH-011]`).
  - Caller agent id and session come from the in-flight turn so child sessions follow the real chat (`[REQ-ORCH-012]`).

- Keep Reflexion Critiques Off Transcript (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-065):
  - Self-verify retries no longer persist `CRITIQUE ON PREVIOUS OUTPUT` as USER messages (`[REQ-VERIFY-014]`, `[REQ-VERIFY-015]`).
  - Chat SSE emits `reflexion_attempt` per try and `reflexion_critique` on each failed check (`[REQ-VERIFY-016]`).

- Honest Reflexion Verification (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-064):
  - Missing verifier/critic is now `skipped` with `verification_passed=false` instead of a fake pass (`[REQ-VERIFY-010]`).
  - Chat `self_verify` runs a builtin JSON critic (`is_valid` / `discrepancies`) and fails closed on empty output or unparseable critic JSON (`[REQ-VERIFY-011]`, `[REQ-VERIFY-012]`).
  - SSE `reflexion_verified.passed` matches the engine; Chat Studio shows a failed badge when verification does not pass (`[REQ-VERIFY-013]`).

- Wire HITL Approval Into Kernel Tool Loop (`AutoReiv.Kernel`, `AutoReiv.Safety`, `AutoReiv.Web` - CARD-063):
  - `AgentKernel` parks high-risk tools (`cli_exec`, wiki writes, `save_agent_specification`, `execute_code`) in `pending_approvals` instead of executing them (`[REQ-HITL-010]`, `[REQ-HITL-011]`).
  - `DangerousCommandFilter` hard-denies prohibited `cli_exec` commands without parking (`[REQ-HITL-012]`).
  - Chat stream emits `approval_required`; `POST /api/approvals/{id}/decision` with APPROVED runs the parked tool (`[REQ-HITL-013]`).

- Settings-Owned Model Context Window Overrides (`AutoReiv.Kernel`, `AutoReiv.Settings`, `AutoReiv.Gateway` - CARD-062):
  - Stopped treating `qwen3.8:latest` as an 8k model; name table now maps `qwen3.8` / `qwen35` and explicit size tags (`65k`, `256k`, `262k`) (`[REQ-CTX-001]`).
  - Added `default_context_window` and `model_context_windows` on the purpose matrix, editable in Settings Studio and saved via `POST /api/settings/matrix` (`[REQ-CTX-002]`, `[REQ-CTX-003]`).
  - Kernel compaction and Ollama `num_ctx` use the Settings override first, then the name table (`[REQ-CTX-004]`).

- Host OS-Aware Tool Guidance & System Info Description Alignment (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-061):
  - Updated `system_info` and `cli_exec` tool schema descriptions to advertise host IP capabilities and enforce OS-appropriate command syntax (`[REQ-OS-AWARE-001]`).
  - Enriched `AUTOREIV_PROFILE.system_prompt` with host OS awareness (Windows vs Linux) and directed the model to use `system_info` first for telemetry and platform-specific CLI commands (`[REQ-OS-AWARE-002]`).
  - **Fixed** `cli_exec` and `SandboxedSubprocessWorker` subprocess execution on Windows: uvicorn uses `SelectorEventLoop` which throws `NotImplementedError` on `asyncio.create_subprocess_shell/exec`. Replaced with `subprocess.run` dispatched via `loop.run_in_executor` (thread pool) for cross-platform compatibility.

- Host IP Telemetry in System Info & AutoReiv CLI Exec Pinning (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-060):
  - Enriched `SysadminSkill.get_system_info()` with `hostname`, `primary_ip`, and `ip_addresses` telemetry using resilient cross-platform UDP and DNS socket probes (`[REQ-SYSINFO-001]`, `[REQ-SYSINFO-003]`).
  - Pinned `cli_exec` in `AUTOREIV_PROFILE.pinned_tool_names` ensuring safe shell command execution is unconditionally delivered in active tool sets on every turn (`[REQ-SYSINFO-002]`).

- Mobile Stream Resiliency, Background Task Persistence & Goal Deliverable Markdown Synthesis (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-059):
  - Decoupled FastAPI `/api/chat/stream` SSE generator from underlying turn execution using shielded background worker tasks and in-memory async queues, guaranteeing database persistence even if mobile screen locks or tabs disconnect mid-stream (`[REQ-MOB-STREAM-001]`).
  - Implemented mobile tab visibility (`document.visibilitychange`) and window focus synchronization in Chat Studio to automatically re-fetch and restore completed messages upon returning to the app (`[REQ-MOB-STREAM-002]`).
  - Added strict Markdown output instructions and negative constraints against raw JSON dicts in Goal Mode synthesis prompts (`[REQ-MOB-STREAM-003]`).
  - Implemented graceful `format_json_deliverable_to_markdown` fallback formatter in both Python backend and JavaScript frontend to format structured deliverables into clean Markdown sections (`[REQ-MOB-STREAM-004]`).

- Visual Goal Mode & Reflexion Streaming UI (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-058):
  - Added `goal_mode` and `self_verify` boolean parameters to `/api/chat/stream` (`[REQ-CHAT-010]`).
  - Implemented SSE emission for multi-step goal execution (`plan_formulated`, `step_start`, `step_complete`) and self-verification (`reflexion_attempt`, `reflexion_critique`, `reflexion_verified`) (`[REQ-CHAT-011]`, `[REQ-CHAT-012]`).
  - Added interactive Milestone DAG progress card and real-time Reflexion verification badges inside Chat Studio message bubbles (`[REQ-CHAT-013]`).
  - Supported dual-mode execution where decomposed goal milestones run with iterative self-verification (`[REQ-CHAT-014]`).
  - Isolated plan formulation and step prompts from chat thread history (`save_to_history=False`) to prevent raw JSON and system prompts in chat bubbles.
  - Enhanced Gateway and Agent Kernel model cascade to correctly resolve configured default models (e.g. `qwen3.8:latest`) and increased Ollama read timeout to 180s for local reasoning models.
- Weekly Notes Rollover Routine & Markdown Task Skill (`AutoReiv.Skills`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-057):
  - Seeded default Obsidian-compatible weekly notes template in `data/wiki/03_Resources/templates/weekly_notes.md` with dynamic Monday╬ô├ç├┤Sunday date interpolation (`[REQ-WNOTE-001]`).
  - Implemented `WeeklyNotesSkill` (`src/application/skills/weekly_notes_skill.py`) with conversational tools for logging daily progress, checking off tasks with `╬ô┬ú├á YYYY-MM-DD`, and viewing weekly summaries (`[REQ-WNOTE-002]`).
  - Built automated task carry-over engine rolling over unfinished tasks from previous weeks into `### Γëí╞Æ├╢├ñ Carry-Over` (`[REQ-WNOTE-003]`).
  - Added built-in autonomous routine `weekly_note_rollover` (`0 0 * * 1` Monday midnight) bound to `assistant` (`[REQ-WNOTE-004]`).
- Skill Pack Taxonomy Realignment & AutoReiv Dedicated Diagnostics (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-056):
  - Structured skill pack manifests into a 3-tier functional taxonomy: **User Knowledge & Productivity**, **System Operations & Platform**, and **Agent Cognition & Runtime** (`[REQ-TAX-001]`).
  - Branded internal diagnostics as `"AutoReiv Core Platform SRE & Diagnostics"` with dedicated core indicators and renamed self-reflection tools to `"Agent Logic Verification (Critic)"` (`[REQ-TAX-002]`).
  - Pruned redundant `yaml_frontmatter_parse` micro-tool from the tool registry in favor of `wiki_note_read`'s native metadata extraction (`[REQ-TAX-003]`).
  - Updated Agent Forge Studio to render skill packs grouped into 3 distinct visual sections with tier headers, subtitles, and dedicated badges (`[REQ-TAX-004]`).
- Session Artifact Store & Context-Isolated Batch Worker Skill (`AutoReiv.Memory`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-055):
  - Implemented SQLite `session_artifacts` schema with `ON DELETE CASCADE` session bound foreign keys, indexed 7-day TTL timestamps, and manual artifact pinning (`[REQ-ART-001]`, `[REQ-ART-002]`).
  - Built `BatchWorkerSkill` map-reduce pipeline partitioning massive target paths across parallel in-memory subagents and saving structured reports to `session_artifacts` (`[REQ-ART-003]`).
  - Added REST API endpoints (`/api/sessions/{id}/artifacts`, `/api/artifacts/{id}`, `/api/artifacts/{id}/promote`, `/api/artifacts/{id}/pin`) (`[REQ-ART-004]`).
  - Added Chat Studio interactive artifact cards in message bubbles and slide-over `#artifactModal` viewer with 1-click **"Promote to Wiki Vault"** capability (`[REQ-ART-005]`).
- Agent Forge Studio Mobile Responsive Toolbar, Header Cleanup & Default Collapsed Skills (`AutoReiv.Web` - CARD-054):
  - Removed obsolete `"RPG Character Sheet"` badge text from the Agent Forge Studio header (`[REQ-MOB-001]`).
  - Refactored the Agent Forge top toolbar into a mobile-first responsive flex container allowing dropdown and action buttons to wrap naturally on viewports $\le 480\text{px}$ (`[REQ-MOB-002]`).
  - Set skill pack tool item grids in Agent Forge to be collapsed by default upon page navigation for a compact overview (`[REQ-MOB-003]`).
- Agent Forge Studio Layout Refactor & Legacy Co-Pilot Pruning (`AutoReiv.Web` - CARD-053):
  - Removed obsolete "System Architect Co-Pilot" chat sidebar, starter prompt chips, and prompt input form from Agent Forge Studio (`[REQ-PRUNE-001]`).
  - Expanded RPG Character Sheet workspace into a clean, spacious full-width container (`max-w-6xl mx-auto`) with responsive single and multi-column grid cards (`[REQ-PRUNE-002]`).
  - Pruned unused Co-Pilot JS state, streaming handlers, and legacy `system-agent` stream calls from `src/web/static/modules/studios/forge.js` (`[REQ-PRUNE-003]`).
- MCP Server Environment Variables, Live Tool Discovery Preview & Agent Forge Pack Binding (`AutoReiv.MCP`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-052):
  - Enabled per-server secure key-value environment variables injection into MCP stdio subprocesses (`[REQ-MCP-007]`).
  - Added transient diagnostic handshake probe endpoint `POST /api/settings/mcp/test` measuring connection latency and advertising tool schemas without persistence (`[REQ-MCP-008]`).
  - Upgraded Settings Studio MCP panel with dynamic key-value environment editor, secret value masking, and live tool discovery badge preview (`[REQ-MCP-009]`).
  - Integrated dynamic MCP Server skill pack clustering and master checkboxes into Agent Forge Studio (`[REQ-MCP-010]`).
- Model Context Protocol (MCP) Standard Client Adapter & 3-Tier Tool Resolution Pipeline (`AutoReiv.MCP`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-012):
  - Implemented `ToolRanker` (`src/application/kernel/tool_ranker.py`) with fast sub-millisecond BM25 keyword relevance scoring over tool names, descriptions, and parameter schemas (`[REQ-MCP-004]`).
  - Integrated 3-Tier Tool Resolution in `AgentKernel` (`run_turn` & `stream_turn`), strictly enforcing Tier 1 Hard RBAC, Tier 2 Pinned Core Tools, and Tier 3 Dynamic Tool Ranking when authorized tools exceed `max_active_tools: int = 6` (`[REQ-MCP-004]`).
  - Built `MCPClientAdapter` and `MCPClientManager` (`src/infrastructure/mcp/client_adapter.py`) managing stdio JSON-RPC 2.0 subprocesses, namespace scoping (`mcp_<server>_<tool>`), execution timeouts, and graceful shutdown (`[REQ-MCP-001]`, `[REQ-MCP-002]`, `[REQ-MCP-003]`).
  - Added MCP server management REST endpoints (`GET/POST/DELETE /api/settings/mcp`) and Settings Studio UI panel with connection status badges and auto-mount lifecycles (`[REQ-MCP-005]`).
  - Added portable markdown skill manual parsing via `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) (`[REQ-MCP-006]`).

## [0.14.0] - 2026-08-27

### Changed

- System Simplification: Dual Core Agents, Universal Wiki Skill & System Info Pruning (`AutoReiv.Agents`, `AutoReiv.Skills` & `AutoReiv.Web` - CARD-050):
  - Consolidated built-in baseline agents down to two crystal-clear identities: `assistant` (daily workflow coordinator) and `autoreiv` (self-introspecting platform SRE and codebase expert).
  - Maintained backward-compatibility alias resolution across `SupervisorOrchestrator` and `BuiltinAgentRegistry` for legacy agent IDs (`general-assistant`, `linux-sysadmin`, `librarian`, `system-agent`).
  - Elevated Wiki into a first-class, reusable `WikiSkill` (`src/application/skills/wiki_skill.py`) attachable to both baseline agents and custom user agents in Agent Forge.
  - Pruned obsolete System Info / Docs Studio and associated backend services from the UI, focusing the control plane into a clean 6-studio suite.
  - Passed all 301 Pytest unit & integration tests, 50 Vitest frontend tests, Playwright multi-studio smoke tests, and unified pre-flight verification.
- SQLite State Store Decomposition into Focused Domain Repositories (`AutoReiv.Memory` - CARD-049):
  - Decomposed monolithic 1,559-line `src/infrastructure/memory/sqlite_store.py` into 7 focused domain repository mixins under `src/infrastructure/memory/repositories/` (`sessions.py`, `facts.py`, `settings.py`, `routines.py`, `telemetry.py`, `approvals.py`, `tasks.py`).
  - Isolated SQL DDL and index creation into `src/infrastructure/memory/schema.py` and thread-safe connection management into `src/infrastructure/memory/connection.py`.
  - Maintained 100% public method signatures and return types via `SQLiteStateStore` faΓö£┬║ade (~34 lines).
  - Verified 100% data persistence and backward compatibility across all 314 tests in under 19 seconds.
- FastAPI Router Decomposition & Architectural Modularization (`AutoReiv.Web` - CARD-048):
  - Decomposed monolithic 1,340-line `src/web/app.py` into 8 focused domain routers under `src/web/routers/` (`chat.py`, `agents.py`, `wiki.py`, `settings.py`, `routines.py`, `observability.py`, `hitl.py`, `system.py`).
  - Reduced `src/web/app.py` application factory to a lean ~170 lines managing lifespan, CORS, static mounts, and dependency attachments.
  - Consolidated multi-agent delegation under `SupervisorOrchestrator` as the unified delegation engine.
  - Verified 100% route and contract compatibility across 314 pytest tests, 50 Vitest unit tests, and Playwright multi-studio smoke suites.

### Added

- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation Orchestration (`AutoReiv.Orchestration`, `AutoReiv.Kernel` & `AutoReiv.Web`):
  - Standardized 5-Key A2A Handoff Envelope (`src/domain/orchestration/models.py`), defining `HandoffEnvelope` (`sender_agent_id`, `recipient_agent_id`, `session_id`, `task_intent`, `context_payload`, `correlation_id`, `depth`, `max_turns`, `timeout_seconds`) and `HandoffResult` (`[REQ-A2A-001]`).
  - Supervisor Orchestration Engine with Recursion & Self-Handoff Guardrails (`src/application/kernel/supervisor_orchestrator.py`), enforcing anti-recursion depth limits (max 2 tiers), circular self-handoff prevention, specialist alias resolution (`sysadmin`, `librarian`, `system`, `general`), and child session isolation (`[REQ-A2A-002]`).
  - Delegate Subtask Tool & Skill (`src/application/skills/delegate_skill.py`), exposing the `delegate_task` tool for registration in `ScopedToolRegistry` (`[REQ-A2A-003]`).
  - Inter-Agent Context Hydration (`src/application/kernel/supervisor_orchestrator.py`), hydrating working memory facts and parameters into delegated prompts (`[REQ-A2A-004]`).
  - Inter-Agent Telemetry & Correlation Tracing (`src/application/telemetry/collector.py`), recording `handoff` spans linking session IDs, correlation IDs, agent IDs, durations, and outcomes (`[REQ-A2A-005]`).
  - REST Multi-Agent Delegation API (`src/web/app.py`), exposing `POST /api/agents/delegate` for external invocation (`[REQ-A2A-006]`).
  - Chat Stream & UI Live Handoff Indicators (`src/application/kernel/agent_kernel.py`, `src/web/app.py`, `src/web/static/modules/studios/chat.js`), streaming `handoff_start` and `handoff_complete` SSE events and rendering animated delegation badges in Chat Studio (`[REQ-A2A-007]`).
  - Comprehensive Multi-Agent Handoff Test Suite (`tests/unit/orchestration/test_handoff_envelope.py`, `tests/unit/skills/test_delegate_skill.py`, `tests/unit/kernel/test_agent_kernel.py`, `tests/unit/web/test_agent_delegation_api.py`) (`[REQ-A2A-001]` - `[REQ-A2A-007]`).

- Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine (`AutoReiv.Kernel` & `AutoReiv.Web`):
  - Domain HITL Models (`src/domain/hitl/models.py`), defining `ApprovalStatus`, `PendingAction`, and `ApprovalDecision` (`[REQ-HITL-001]`).
  - Approval Manager State Parking & Resume (`src/application/hitl/approval_manager.py`), parking agent actions in an in-memory queue with `asyncio.Future` suspension and human-triggered resolution (`[REQ-HITL-002]`).
  - HITL REST API Endpoints (`src/web/app.py`), exposing `GET /api/hitl/pending` and `POST /api/hitl/decide` for human operator interaction (`[REQ-HITL-003]`).
  - Comprehensive HITL Unit & Integration Test Suite (`tests/unit/hitl/test_approval_manager.py`), verifying action parking, approval/rejection resolution, and REST endpoint integration across 6 tests (`[REQ-HITL-004]`).

- Dangerous Shell Command Safety Guardrails & Path Traversal Protection (`AutoReiv.Kernel` & `AutoReiv.Deploy`):
  - Domain Safety Risk Models (`src/domain/safety/models.py`), defining `RiskLevel`, `SafetyViolation`, and `CommandSafetyReport` (`[REQ-GUARD-001]`).
  - Deterministic Command Guardrail Engine (`src/application/safety/command_guardrail.py`), providing rule-based inspection across destructive recursive deletions, disk wiping tools, system shutdowns, fork bombs, and remote pipe-to-shell attacks (`[REQ-GUARD-002]`).
  - Workspace Path Traversal Protection (`src/application/safety/command_guardrail.py`), intercepting path traversal escapes and sensitive OS directory tampering (`[REQ-GUARD-003]`).
  - Subprocess Sandbox Guardrail Interception (`src/application/skills/sandbox_worker.py`), screening all subprocess execution requests and aborting dangerous operations prior to spawning child processes (`[REQ-GUARD-002]`).
  - Comprehensive Safety Guardrails Unit Test Suite (`tests/unit/safety/test_command_guardrail.py`), verifying safety evaluation across 6 tests (`[REQ-GUARD-004]`).

- Ephemeral Subprocess Execution Sandbox & Process Isolation (`AutoReiv.Skills` & `AutoReiv.Deploy`):
  - Workspace File Provisioning & Output Artifact Extraction (`src/application/skills/sandbox_worker.py`), supporting provisioning multi-file input payloads into ephemeral temporary workspaces and extracting generated output files prior to clean teardown (`[REQ-SANDBOX-001]`).
  - Sensitive Environment Variable Scrubbing & Stream Capping (`src/application/skills/sandbox_worker.py`), automatically filtering out host API keys, tokens, and credentials while enforcing standard stream output limits (`max_output_bytes = 1MB`) (`[REQ-SANDBOX-002]`).
  - Agent Sandbox Execution Skill (`src/application/skills/sandbox_skill.py`), exposing the `execute_code` tool for registration in `ScopedToolRegistry` with structured execution telemetry (`[REQ-SANDBOX-003]`).
  - Comprehensive Sandbox Unit & Integration Test Suite (`tests/unit/skills/test_sandbox_worker.py`), verifying workspace file provisioning, output artifact capture, secret scrubbing, timeout killing, and tool execution across 5 tests (`[REQ-SANDBOX-004]`).

- Gateway Resilience Hardening & Streaming Cycle Detection (`AutoReiv.Gateway` & `AutoReiv.Kernel`):
  - Decorrelated Exponential Backoff with Full Jitter (`src/application/gateway/gateway_service.py`), implementing `calculate_backoff` to eliminate synchronized retry storms during transient 5xx and rate-limit errors (`[REQ-RESIL-001]`).
  - Connection Pool Limits & Graceful Lifecycle Teardown (`src/infrastructure/gateway/openai_adapter.py` & `ollama_adapter.py`), standardizing keep-alive connection pools (`max_keepalive_connections=20`, `max_connections=50`, `keepalive_expiry=30.0`) and introducing `async def close()` (`[REQ-RESIL-002]`).
  - Dual-Mode Agent Reasoning & Streaming Cycle Detector (`src/application/kernel/cycle_detector.py` & `agent_kernel.py`), analyzing both repeated tool-call signatures and streaming text phrase loops to halt infinite model loops safely (`[REQ-RESIL-003]`).
  - Comprehensive Gateway Resilience Unit Test Suite (`tests/unit/gateway/test_resilience.py`), verifying backoff bounds, connection pool configuration, and cycle detection break conditions across 4 tests (`[REQ-RESIL-004]`).

- SQLite Episodic Fact Memory Store & Agent Auto-Recall (`AutoReiv.Memory`, `AutoReiv.Skills` & `AutoReiv.Gateway`):
  - Tokenized Substring Fact Search (`src/infrastructure/memory/sqlite_store.py`), implementing `search_facts` filtering across `entity`, `key`, and `value` fields with confidence thresholding and ranking (`[REQ-EPISODIC-001]`).
  - Dynamic Memory Context Formatting & Auto-Recall (`src/application/skills/memory_skill.py`), implementing `render_memory_context` and `auto_recall` generating clean Markdown context blocks for agents (`[REQ-EPISODIC-002]`).
  - Automated Kernel Memory Injection (`src/application/kernel/agent_kernel.py`), transparently enriching agent system instructions with matching cross-session episodic memory facts during synchronous and streaming turn execution (`[REQ-EPISODIC-003]`).
  - Episodic Memory Management REST API (`src/web/app.py`), exposing `GET`, `POST`, and `DELETE` endpoints under `/api/memory/facts` (`[REQ-EPISODIC-004]`).
  - Comprehensive Unit & Integration Test Suite (`tests/unit/memory/test_episodic_memory.py`), validating store CRUD, search filtering, Markdown rendering, kernel auto-recall injection, and REST endpoints across 4 test suites (`[REQ-EPISODIC-005]`).

- Context Window Compaction & Sliding Dynamic Token Budget Strategy (`AutoReiv.Kernel`):
  - Model-Aware Dynamic Token Budgeting (`src/application/kernel/context_compactor.py`), implementing `get_model_context_limit` mapping model families (8k, 32k, 128k, 1M) and enforcing a 75% safety ceiling to prevent context overflows (`[REQ-COMPACT-001]`).
  - Root User Intent Preservation (`src/application/kernel/context_compactor.py`), locking the initial user prompt alongside the system directive during sliding window summarization to eliminate task amnesia in long-running agentic loops (`[REQ-COMPACT-002]`).
  - Structured Compaction Telemetry (`src/application/kernel/context_compactor.py`), introducing `CompactionMetrics` and `compact_with_stats` tracking token savings, turn summarization counts, and tool truncation events (`[REQ-COMPACT-003]`).
  - Comprehensive Unit Test Coverage (`tests/unit/kernel/test_context_compactor.py`), validating pattern mapping, intent preservation, and metrics tracking across 5 tests (`[REQ-COMPACT-004]`).

- Error Boundary Toasts & Offline Backend Messaging (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Non-Blocking Accessible Toast Notification Subsystem (`src/web/static/modules/ui/toast.js` & `src/web/templates/index.html`), introducing `showToast` with `info`, `success`, `warning`, and `error` variants, ARIA live region announcements (`polite` / `assertive`), auto-dismiss timers, and dismiss actions (`[REQ-TOAST-001]`).
  - Studio Error Boundary Migration (`src/web/static/modules/studios/forge.js`, `routines.js`, `wiki.js`), eliminating 100% of intrusive browser `alert()` popups in favor of non-blocking visual toasts (`[REQ-TOAST-002]`).
  - Proactive Gateway Connectivity & Recovery Monitor (`src/web/static/modules/ui/toast.js` & `src/web/static/app.js`), polling `/api/health` in the background, rendering a top-level alert banner on disconnect, and triggering reconnect toasts (`[REQ-TOAST-003]`).
  - Toast Subsystem Unit & Smoke Test Suite (`tests/unit/frontend/toast.test.js`), introducing 6 unit tests verifying toast container creation, variant rendering, timer auto-dismissal, and connectivity state transitions (`[REQ-TOAST-004]`).

- Performance Budgets, Module Bundling & First-Paint Optimization (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Kinetic Energy Equilibrium Sleeping (`src/web/static/modules/utils/physics.js` & `src/web/static/modules/studios/wiki.js`), calculating total system kinetic energy on each simulation frame and pausing `requestAnimationFrame` when convergence drops below `0.005`, driving idle CPU consumption to 0% (`[REQ-PERF-001]`).
  - Strict Modal Animation Teardown (`src/web/static/modules/studios/wiki.js`), halting background animation runners immediately upon modal close, dismissal, or note selection (`[REQ-PERF-002]`).
  - First-Paint Module Preloading (`src/web/templates/index.html`), introducing `<link rel="modulepreload">` directives for core ES modules to optimize browser network waterfalls and Time-To-Interactive (`[REQ-PERF-003]`).
  - Performance & Simulation Lifecycle Unit Suite (`tests/unit/frontend/perf.test.js`), adding 7 unit tests verifying kinetic calculations, start/sleep/wake/stop runner state machines, and zero CPU leakage (`[REQ-PERF-004]`).

- Mobile & Keyboard Accessibility Architecture (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Semantic ARIA Roles & Screen Reader Landmarks (`src/web/templates/index.html` & `src/web/static/modules/utils/accessibility.js`), adding `role="tablist"` navigation, dynamic `aria-selected` toggling, `role="tabpanel"` views, `role="dialog"` modal wrappers, and `aria-live="polite"` chat stream announcements (`[REQ-A11Y-001]`).
  - Modal Focus Trapping & Global Escape Key Dismissal (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), trapping `Tab` and `Shift+Tab` within active modal dialogs, closing open modals on `Escape`, and restoring user focus (`[REQ-A11Y-002]`).
  - Studio Navigation Arrow-Key Keyboard Controls (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), enabling `ArrowDown`/`ArrowRight`/`ArrowUp`/`ArrowLeft`/`Home`/`End` cyclical tab switching (`[REQ-A11Y-003]`).
  - Automated Accessibility Test Suite (`tests/unit/frontend/accessibility.test.js`), introducing 10 pure unit tests verifying focus containment, keyboard navigation, and ARIA syncing (`[REQ-A11Y-004]`).

- Steering & Product Documentation Truth Synchronization (`AutoReiv.Docs`):
  - 7-Studio Product Architecture Specification (`steering/product.md`), detailing the operational capabilities of Chat, Routines, Observability, Agent Forge, Settings, Docs, and Wiki & Mind Map studios alongside local-first privacy boundaries (`[REQ-DOCS-005]`).
  - Dual-Runtime Environment & Topology Steering (`steering/tech.md` & `steering/structure.md`), formally documenting the zero-build ES Module frontend architecture, Python 3.12/FastAPI backend, and directory topology (`[REQ-DOCS-006]`).
  - Milestone 10 Formal Closure & Roadmap Alignment (`steering/roadmap.md`), certifying 100% completion of Milestone 10 (v0.10.0 - Quality & Testability) across all 4 work cards with 174 tracked requirements (`[REQ-DOCS-007]`).

- Gateway, Wiki & Settings End-to-End API Contract Integration Tests (`AutoReiv.Gateway`, `AutoReiv.Wiki`, `AutoReiv.Settings`):
  - Multi-Provider Gateway Model Discovery Contract Suite (`tests/integration/test_gateway_contract_api.py`), validating `/api/models/discover` and `/api/settings/presets` across mocked local and cloud providers with fallback resilience (`[REQ-API-001]`).
  - Wiki Studio Vault & Knowledge Graph Contract Suite (`tests/integration/test_wiki_contract_api.py`), exercising full note CRUD lifecycle (`GET/POST/PUT/DELETE /api/wiki/note`), tree traversal, search, mind map graph serialization, and direct chat thread inbox export (`[REQ-API-002]`).
  - Settings Studio Configuration & Secret Masking Contract Suite (`tests/integration/test_settings_contract_api.py`), verifying provider persistence, purpose-to-model matrix assignments, system documentation topics, and zero secret leakage (`[REQ-API-003]`).
  - Hermetic FastAPI Integration Test Fixtures & Runner Integration (`tests/integration/` & `preflight.py`), providing isolated in-memory SQLite and scratch vault testing executing 12 integration tests in < 5s (`[REQ-API-004]`).

- Comprehensive Unit Test Suite for Frontend Pure Logic (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - 2D Physics Layout Engine Extraction & Unit Testing (`src/web/static/modules/utils/physics.js` & `tests/unit/frontend/physics.test.js`), decoupling force-directed graph calculation algorithms from the DOM and validating repulsion, spring attraction, damping, and equilibrium convergence (`[REQ-UNIT-001]`).
  - Reactive State Store Implementation & Testing (`src/web/static/modules/state/store.js` & `tests/unit/frontend/store.test.js`), implementing a lightweight `createStore` factory with mutation isolation, updater callbacks, and listener subscription/teardown mechanics (`[REQ-UNIT-002]`).
  - Comprehensive Boundary Testing for Formatters & Sanitizers (`src/web/static/modules/utils/formatters.js` & `tests/unit/frontend/formatters.test.js`), hardening byte formatting, token counting, timestamp parsing, and HTML escaping against negative values, non-numeric strings, and XSS injection vectors (`[REQ-UNIT-003]`).
  - Fast-Feedback Pure Logic Test Runner Integration (`package.json` & `preflight.py`), scaling Vitest coverage across 27 pure unit tests running cleanly in < 400ms (`[REQ-UNIT-004]`).

- ESLint & Prettier Static Analysis Pipeline for Frontend (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - Flat Config ESLint 9 Integration (`eslint.config.js` & `package.json`), establishing automated static linting with browser/node globals, rules prohibiting unused identifiers, and full ES module validation (`[REQ-LINT-001]`).
  - Prettier Code Formatting Standard (`.prettierrc` & `package.json`), enforcing single quotes, trailing commas (`es5`), 2-space indentation, and 120 print width across frontend files (`[REQ-LINT-002]`).
  - Unified Pre-Flight & CI Frontend Lint Gate (`.agents/skills/rtm-sync/scripts/preflight.py` & `.github/workflows/ci.yml`), integrating `npm run lint:frontend` as stage 3 of the unified 6-stage pre-flight runner and continuous integration pipeline (`[REQ-LINT-003]`).
  - Zero Linting Errors Baseline Sweep (`src/web/static/` & `tests/`), formatting all frontend source modules and resolving all unused variables, empty catch blocks, and missing globals (`[REQ-LINT-004]`).

- Defensive DOM Query & Null-Safety Architecture Across Studio Interfaces (`AutoReiv.Web`):
  - Complete Helper Migration for All Studio Modules (`src/web/static/modules/studios/`), replacing all raw un-scoped `document.getElementById`, `document.querySelector`, and `document.querySelectorAll` queries across `docs.js`, `settings.js`, `observability.js`, `forge.js`, and `wiki.js` with defensive `$`, `$query`, and `$queryAll` helpers (`[REQ-DOM-001]`).
  - Defensive Event Binding & Helper Infrastructure (`src/web/static/modules/dom.js`), adding `$on(targetOrId, event, handler, options)`, `$show()`, `$hide()`, and `$toggle()` utilities with automated null-guarding (`[REQ-DOM-002]`).
  - Strict XSS Sanitization for Dynamic HTML Content (`src/web/static/modules/studios/chat.js` & `forge.js`), passing all dynamic note, agent, and routine attributes through `escapeHtml()` (`[REQ-DOM-003]`).
  - Automated DOM Architecture Static Lint Rule (`tests/unit/frontend/dom_audit.test.js`), establishing a Vitest static test that parses all frontend JavaScript modules and permanently prevents regressions of raw DOM queries outside `dom.js` (`[REQ-DOM-004]`).

- Playwright CI Pre-Flight Gate & Multi-Studio Navigation Smoke Suite (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - GitHub Actions Continuous Integration Workflow (`.github/workflows/ci.yml`), automating Python 3.12, Node 20, Astral UV caching, Ruff, Pytest, Vitest, and Playwright Chromium smoke gates on every push/PR to `main` and `qa` (`[REQ-SMK-001]`).
  - Multi-Studio Deep Navigation & Element Smoke Assertions (`tests/e2e/smoke.spec.js`), expanding Playwright end-to-end smoke coverage across all 7 studios (Chat, Routines, Observability, Forge, Settings, Docs, Wiki) verifying critical anchors attach without error (`[REQ-SMK-002]`).
  - Interactive Studio Mutation Smoke Checks (`tests/e2e/smoke.spec.js`), exercising non-destructive user interactions including manual topic search, 2D physics Mind Map modal launch/close, New Routine modal, and New Note modal (`[REQ-SMK-003]`).
  - Unified Local Pre-Flight CLI Harness (`.agents/skills/rtm-sync/scripts/preflight.py` & `npm run preflight`), providing a single CLI runner executing all 5 static, unit, integration, smoke, and RTM gates in sequence with formatted summary reporting (`[REQ-SMK-004]`).
  - Playwright Failure Artifacts & Diagnostics Capture (`playwright.config.js` & `.github/workflows/ci.yml`), capturing failure screenshots, console logs, and trace archives in `test-results/` uploaded automatically in CI on test failure (`[REQ-SMK-005]`).

- Frontend Modularization Foundation & Baseline Quality Gates (`AutoReiv.Web`):
  - Native ES Module Decomposition (`src/web/static/app.js`, `src/web/static/modules/`, & `src/web/templates/index.html`), deconstructing the 3,800+ line monolithic `app.js` into isolated ES modules partitioned by concern (`dom.js`, `services/api.js`, `state/store.js`, `utils/`, and individual `studios/` for Chat, Routines, Observability, Forge, Settings, Docs, and Wiki) loaded natively via `<script type="module">` (`[REQ-FE-001]`).
  - Isolated Subsystem Initialization (`src/web/static/app.js`), executing each studio initializer in an independent `try/catch` ring within `initApp()` to ensure faults in one studio cannot crash the primary UI or navigation (`[REQ-FE-002]`).
  - Defensive DOM Query Helpers (`src/web/static/modules/dom.js`), introducing `$(id)`, `$query()`, `$queryAll()`, and `safeCreateIcons()` that log informative console warnings on missing elements rather than throwing uncaught `TypeErrors` (`[REQ-FE-003]`).
  - Pure Logic Utility Extraction & Vitest Test Suite (`src/web/static/modules/utils/` & `tests/unit/frontend/`), isolating pure functions (`debounce`, `formatBytes`, `formatTokenCount`, `formatTimestamp`, `escapeHtml`, `storageGet`, `storageSet`) covered by automated unit tests running in < 300ms (`[REQ-FE-004]`).
  - Playwright Zero-Error Page Load & Multi-Studio Navigation Smoke Gate (`tests/e2e/smoke.spec.js` & `playwright.config.js`), establishing automated headless browser smoke testing asserting zero console errors, zero uncaught page errors, and active tab rendering across all 7 studios (`[REQ-FE-005]`).

- Comprehensive Web UI Tab Hydration & Rendering Hardening (`AutoReiv.Web`):
  - Agent Studio Skill Pack Grid Hydration (`src/web/static/app.js` & `src/web/templates/index.html`), ensuring `renderSkillsCatalog()` deterministically hydrates all 7 skill pack categories and 34 tools on initial and repeated visits regardless of memory caching state (`[REQ-FIX-001]`).
  - System Info Topic Navigation & Viewer Resilience (`src/application/web/system_info_service.py`, `src/web/app.py`, & `src/web/static/app.js`), expanding the topic categories index and displaying default architecture manuals with defensive error boundaries and mobile drawer controls (`[REQ-FIX-002]`).
  - Wiki Studio Vault Auto-Selection & Mobile Navigation (`src/web/templates/index.html` & `src/web/static/app.js`), auto-loading the first available note into Markdown preview on tab load, providing accessible mobile drawer toggles, and ensuring visible action buttons (`[REQ-FIX-003]`).
  - Wiki Mind Map & Graph Canvas Robustness (`src/web/static/app.js` & `src/web/templates/index.html`), introducing viewport bounding fallbacks for 2D canvas sizing and sanitized Mermaid diagram rendering (`[REQ-FIX-004]`).
  - Universal Tab Switching Error Quarantine (`src/web/static/app.js`), wrapping all tab loader triggers inside isolated try/catch boundaries within `switchTab()` (`[REQ-FIX-005]`).

- Chat Studio Agent Selection & Provider Model Discovery Fixes (`AutoReiv.Web` & `AutoReiv.Gateway`):
  - Chat Studio Persistent Multi-Surface Agent Switcher (`src/web/templates/index.html` & `src/web/static/app.js`), introducing an inline `#chatTopBarAgentSelect` dropdown directly in the chat topbar synchronized two-way with the sidebar, and persisting the active agent ID in browser `localStorage` across page reloads and tab navigations (`[REQ-UI-001]`).
  - Multi-Preset Model Discovery & Saved Model Retention (`src/infrastructure/gateway/openai_adapter.py`, `src/infrastructure/gateway/ollama_adapter.py`, `src/web/app.py`, & `src/web/static/app.js`), providing dynamic `provider_id` support across all presets (Ollama, OpenAI, OpenRouter, Anthropic, Groq, DeepSeek, Together, vLLM) and preserving saved custom models in dropdowns (`[REQ-UI-002]`).
- System Observability Live Event Stream, System Agent Root Cause Diagnostics & Librarian Inbox Organization (`AutoReiv.Observability`, `AutoReiv.Skills`, `AutoReiv.Wiki`, & `AutoReiv.Web`):
  - In-Memory System Event Logger & REST Log Buffer (`SystemLogBuffer` in `src/application/observability/log_buffer.py` & `GET /api/observability/logs` in `src/web/app.py`), maintaining a thread-safe 1,000-entry ring buffer capturing all server logs, gateway events, tool calls, and error traces (`[REQ-OBS-007]`).
  - Observability Studio Live Event Terminal UI (`src/web/templates/index.html` & `src/web/static/app.js`), featuring a real-time auto-scrolling log console with level filtering (`ALL`, `INFO`, `WARN`, `ERROR`), search filter, pause/resume toggle, and buffer clear action (`[REQ-OBS-008]`).
  - System Agent Diagnostic Skill Pack & Tooling (`SystemAgentSkill` in `src/application/skills/system_agent_skill.py` & `SYSTEM_AGENT_PROFILE` in `src/domain/agents/profiles.py`), equipping the System Agent with `get_recent_errors`, `get_session_transcript`, `get_agent_sessions`, `test_provider_connectivity`, and `get_system_logs` to diagnose agent failures and network timeouts directly in chat (`[REQ-AGENTS-007]`).
  - Librarian Inbox Triage & Organization Engine (`WikiStore.organize_note` in `src/domain/wiki/store.py`, `LibrarianSkill.organize_wiki_note` in `src/application/skills/librarian_skill.py`, & `LIBRARIAN_PROFILE` in `src/domain/agents/profiles.py`), empowering the Librarian to atomically move staged notes from `inbox/` to permanent `notes/<domain>/<topic>/` taxonomy with complete 35-field YAML frontmatter hydration (`[REQ-WIKI-010]`).
- Mobile-First Responsive Layout & Sticky Viewport Overhaul (`AutoReiv.Web`):
  - Dynamic `100dvh` Viewport & Sticky Chat Input Bar (`src/web/templates/index.html` & `src/web/static/app.js`), anchoring root layout height to `100dvh` across mobile browsers, preventing whole-page scroll bouncing, isolating message stream scrolling to `#messagesContainer`, and pinning the prompt textarea bar firmly at the bottom above virtual keyboards (`[REQ-RESP-001]`).
  - Responsive Off-Canvas Split Drawers for Wiki Studio & System Info (`#wikiDrawerPane` & `#docsDrawerPane`), converting desktop sidebars into slide-over mobile drawers with quick toggle buttons (`[Γëí╞Æ├┤├╝ Vault Tree]` / `[╬ô├┐Γûæ Topics]`) and automatic auto-collapse upon note/topic selection (`[REQ-RESP-002]`).
  - Mobile Touch Physics Canvas & Fullscreen Modal Sheets (`src/web/static/app.js`), providing single-finger touch drag, two-finger pinch-to-zoom for the 2D Mind Map, and responsive modal sheet sizing across all mobile viewports (`[REQ-RESP-003]`).
- Chat to Wiki Direct Inbox Export & Flat Staging Vault Structure (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Flat Inbox Staging Engine (`WikiStore` in `src/domain/wiki/store.py` & `WikiService` in `src/application/wiki/service.py`), eliminating priority subfolders (`need_to_do`, `should_do`, `want_to_do`) in favor of direct, zero-friction flat file staging under `data/wiki/inbox/<slug>.md` (`[REQ-WIKI-007]`).
  - Unified Chat-to-Wiki Inbox Artifact Generation (`POST /api/export/wiki` in `src/web/app.py` & `src/web/static/app.js`), routing single message "Save to Wiki" and full conversation "Export to Wiki" actions directly through `WikiService` to generate structured 35-field YAML frontmatter notes in `inbox/` (`[REQ-WIKI-008]`).
  - Flat Inbox Tree Navigation & Simplified New Note Modal (`src/web/static/app.js` & `src/web/templates/index.html`), rendering all staged inbox notes directly under `inbox (Staging) (X)` without intermediate priority group nesting (`[REQ-WIKI-009]`).
- Provider & Model Settings Persistence & Hydration (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Model Choice Persistence Contract (`ProviderSettingsRequest` & `GET /api/settings` / `POST /api/settings/providers` in `src/web/app.py`), persisting `default_model_id` in SQLite and synchronizing with Gateway fallback resolution (`[REQ-SET-007]`).
  - Settings Studio Model Selection Retention & Auto-Hydration (`src/web/static/app.js`), preserving selected model dropdown values across manual saves, provider switching, dynamic catalog queries, and page reloads (`[REQ-SET-008]`).
- Wiki Studio Interactive Obsidian-Style Mind Map & Tree Navigation (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Nested Degree & Subject Tree Expand/Collapse Engine (`src/web/static/app.js`), rendering Degree Level 1 (`<domain>`) and Subject Level 2 (`<topic>`) folders as independent interactive collapsible buttons with chevrons, open/closed folder indicators, note count badges, and auto-expanded initial discovery state (`[REQ-MIND-001]`).
  - Multi-Dimensional Knowledge Graph Engine & REST API (`WikiStore.get_mindmap()` in `src/domain/wiki/store.py` & `GET /api/wiki/mindmap` in `src/web/app.py`), extracting heterogeneous node entities (Notes, Tags `#tag`, Degree Domains, Subject Topics) and typed relation edges (`wikilink`, `has_tag`, `in_topic`, `in_domain`) (`[REQ-MIND-002]`).
  - Obsidian-Style Interactive 2D Physics Canvas Mind Map Explorer (`#wikiMindMapModal` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring velocity-Verlet Coulomb particle simulation, spring tension physics, live search filtering, entity dimension toggle pills (Notes, Tags, Domains, Topics), repulsion slider, smooth pan/zoom, interactive hover tooltips with note telemetry, and direct click-to-open note navigation (`[REQ-MIND-003]`).
- Wiki Document Management System & Librarian Architecture (`AutoReiv.Wiki`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Local-First Degree/Class Taxonomy & Scaffolding Engine (`WikiStore` in `src/domain/wiki/store.py`), organizing human documents into `inbox/` (`need_to_do`, `should_do`, `want_to_do`), `notes/<domain>/<topic>/` (Degree/Field Level 1, Subject/Class Level 2), and `resources/` (`operating_manuals`, `templates`) with path jailing (`[REQ-WIKI-001]`).
  - 35-Field Additive YAML Frontmatter Schema Standard & Telemetry Engine (`FrontmatterParser` & `WikiNoteMeta` in `src/domain/wiki/frontmatter.py`), auto-computing immutable timestamp UIDs (`YYYYMMDD-HHMMSS`), word count, and token telemetry ($round(max(chars / 4, words \times 0.75))$) (`[REQ-WIKI-002]`).
  - Non-Destructive Note Modification Engine (`WikiStore.write_note()`), preserving existing YAML metadata and relations while safely updating note content and bumping `last_updated` (`[REQ-WIKI-003]`).
  - Knowledge Graph & WikiLink Extraction Engine (`WikiStore.get_graph()`), parsing `[[wikilink]]` references across markdown bodies to build interconnected network nodes and edges (`[REQ-WIKI-004]`).
  - Upgraded Librarian Skill & Scoped Tool Grants (`LibrarianSkill` in `src/application/skills/librarian_skill.py`), providing tools for `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, and `wiki_graph` (`[REQ-WIKI-005]`).
  - Interactive Wiki Studio Web Interface & REST Endpoints (`#view-wiki` in `src/web/templates/index.html`, `src/web/static/app.js`, and `src/web/app.py`), featuring hierarchical tree navigation, markdown preview and editor, YAML Frontmatter Inspector card, new note modal, and knowledge graph visualization (`[REQ-WIKI-006]`).
- System Info Conceptual Knowledge Hub & Architectural Manual (`AutoReiv.Web` & `AutoReiv.Docs`):
  - Curated System Info Topic Catalog & Service (`SystemInfoService` in `src/application/web/system_info_service.py` & `GET /api/system-info/topics`, `GET /api/system-info/topic/{id}`), delivering structured, educational chapters with rich Markdown and interactive Mermaid diagrams (`[REQ-SYST-001]`).
  - System Info UI Sidebar & Interactive Reader (`[╬ô├ñΓòúΓê⌐Γòò├à System Info]` in `src/web/templates/index.html` and `src/web/static/app.js`), featuring categorized topic groups, real-time search filtering, deep links, and Mermaid Pan-Tilt-Zoom inspection (`[REQ-SYST-002]`).
  - Formal 5-Tier Architectural Hierarchy Reference Manual (`[REQ-SYST-003]`), clearly distinguishing and explaining the interactions between **Agents** (Autonomous Personas), **Workflows** (Multi-step Goal DAGs), **Routines** (Background Cron Jobs), **Skill Packs** (Domain Capability Bundles), and **Atomic Tools** (Pydantic / JSON-RPC Function Contracts).
- Lean Just-In-Time (JIT) Agent Discovery & Isolated Subagent Handoff Engine (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Just-In-Time (JIT) Agent Directory Indexer (`AgentDirectoryService` in `src/application/orchestration/directory_service.py`), dynamically searching and ranking built-in profiles and custom SQLite agents by capability keywords, specialization summaries, and authorized skill tags without pre-loading fleet manifests into system prompts (`[REQ-ORCH-001]`).
  - Ultralight 2-Primitive Orchestration Skill (`OrchestrationSkill` in `src/application/skills/orchestration_skill.py`), exposing `lookup_agents(query, limit=3)` returning compact Agent Cards (<60 tokens) and `handoff_to_agent(target_agent_id, task_directive, input_payload)` adhering to strict schema contracts (`[REQ-ORCH-002]`).
  - Isolated Context Execution & Anti-Recursion Engine (`HandoffIsolationEngine` in `src/application/orchestration/handoff_engine.py`), executing subagents in clean 0-turn contexts, bounding execution turns (1╬ô├ç├┤10), enforcing a maximum recursion depth limit of 2 tiers, and rejecting circular self-handoff deadlocks (`[REQ-ORCH-003]`).
  - Real-Time Handoff Telemetry & Chat UI Affordance (`src/web/app.py`, `src/web/templates/index.html`, `src/web/static/app.js`), emitting streaming events and rendering live subagent delegation status pills in Chat Studio showing the target agent, directive, and completion state (`[REQ-ORCH-004]`).
- System Documentation Folder Tree Navigation & Interactive Mermaid Pan-Zoom Inspector (`AutoReiv.Web`):
  - Nested Folder Tree Navigation API (`SystemDocumentationService.get_navigation_tree()` in `src/application/web/system_docs_service.py`), organizing platform specifications into milestone subfolders with `requirements.md`, `design.md`, and `tasks.md` children, ADRs, SDLC rules, and RTM metadata (`[REQ-DOCS-001]`).
  - Interactive Collapsible Folder Tree Sidebar UI (`#view-docs` & `renderDocsNav()` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring folder chevron toggles, open/closed folder icons, child file counts, active document highlighting, and real-time deep search filtering (`[REQ-DOCS-002]`).
  - Interactive Mermaid Diagram Hover Overlay & High-Resolution Modal Inspector (`#mermaidZoomModal` in `src/web/templates/index.html` & `src/web/static/app.js`), attaching hover action buttons (`[Γëí╞Æ├╢├¼ Inspect & Zoom]`) to all rendered Mermaid diagrams in documentation and chat streams (`[REQ-DOCS-003]`).
  - Smooth Pan-Tilt-Zoom (PTZ) Engine (`src/web/static/app.js`), supporting mouse-wheel zooming (20% to 500%), click-and-drag canvas panning, zoom toolbar controls (`+`, `-`, `╬ô├ÑΓòæ 100% Reset`), and fullscreen toggle (`[REQ-DOCS-004]`).
- Skill Pack Hierarchy, Deterministic Guardrails, and System Documentation Browser (`AutoReiv.Skills`, `AutoReiv.Agents`, & `AutoReiv.Web`):
  - Hierarchical Skill Pack Manifests and Catalog Aggregator (`src/application/skills/manifest.py`), clustering 20+ atomic tools into cohesive, categorized Skill Packs (`Sysadmin`, `Librarian`, `Verification`, `Planning`, `AgentBuilder`, `Orchestration`, `General & Custom`) (`[REQ-SKIL-001]`).
  - Agent Forge Hierarchical Skill Pack UI with Expandable Tool Cards (`#view-agents` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring one-click bundle checkboxes, automatic indeterminate state propagation, and granular tool-level RBAC (`[REQ-SKIL-002]`).
  - Deterministic Agent Specification Guardrail Engine (`AgentProfileGuardrail` in `src/domain/agents/guardrails.py`), enforcing strict invariants across `AgentBuilderSkill`, `POST /api/agents`, and `PUT /api/agents/{id}`: kebab-case regex slug validation, anti-hallucination tool catalog verification, `ModelPurpose` and `AgentTone` domain checking, and 1-50 turn bounding (`[REQ-SKIL-003]`).
  - System Documentation & Specs Navigation REST API (`SystemDocumentationService` in `src/application/web/system_docs_service.py` & `GET /api/docs/nav`, `GET /api/docs/content`), safely indexing repository specs (`docs/specs/`), Architecture Decision Records (`docs/adr/`), SDLC rules, and RTM matrices with strict directory traversal prevention (`[REQ-SKIL-004]`).
  - Control Plane System Documentation & Specs Browser View (`#view-docs` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring a searchable multi-section document tree, real-time query filtering, and rich Markdown rendering with GitHub alerts and code syntax blocks (`[REQ-SKIL-005]`).
- Routine Management, Dual Cron Humanization, and Agent Forge Binding (`AutoReiv.Routines` & `AutoReiv.Web`):
  - Dual Cron Schedule Humanizer & Next-Run Calculator (`src/application/routines/humanizer.py`) bidirectionally translating cron expressions (`0 * * * *`, `*/15 * * * *`, `0 8 * * *`) into clean English (e.g., _"Every 15 minutes"_, _"Daily at 08:00 UTC"_) with next execution ETA countdown calculations (`[REQ-ROUT-001]`).
  - Full Routine REST API CRUD, Toggle, and Trigger Endpoints (`POST /api/routines`, `PUT /api/routines/{id}`, `DELETE /api/routines/{id}`, `POST /api/routines/{id}/toggle`, `POST /api/routines/{id}/run`, `GET /api/routines?agent_id=...`) with built-in baseline routine protection (`[REQ-ROUT-002]`, `[REQ-ROUT-003]`).
  - Routines Studio Management UI (`#view-routines` in `src/web/templates/index.html` & `src/web/static/app.js`) with frequency presets, live humanizer preview, directive prompts, active status badges, and action controls (`[╬ô├╗ΓòóΓê⌐Γòò├à Run Now]`, `[╬ô┬ú├àΓê⌐Γòò├à Edit]`, `[╬ô├àΓòòΓê⌐Γòò├à Pause/Resume]`, `[Γëí╞Æ├╣├ªΓê⌐Γòò├à Delete]`) (`[REQ-ROUT-004]`).
  - Agent Forge "Assigned Routines" Character Sheet Integration (`#forgeAssignedRoutinesList` in `src/web/templates/index.html` & `src/web/static/app.js`) rendering all standing jobs led by the selected agent with direct run and edit triggers (`[REQ-ROUT-005]`).
- Dynamic Purpose-Based Model Cascade & "Agent Forge" Character Sheet Studio (`AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - 3-Tier Purpose-to-Model Resolution Cascade (`Agent Kernel -> Agent Profile Override -> Purpose Matrix Slot -> Global Default Model`) implemented in `AgentKernel._resolve_model()`.
  - SQLite Custom Agent Persistence & Scoped Registry (`custom_agents` table in `SQLiteStateStore` and `BuiltinAgentRegistry`), supporting full CRUD operations, built-in baseline agent protection, and operator override overlays.
  - System Agent Meta-Builder Skill (`AgentBuilderSkill` in `src/application/skills/agent_builder_skill.py`) exposing `list_available_skills_and_tools`, `propose_agent_specification`, and `save_agent_specification` to `system-agent`.
  - REST Agent Management Endpoints: `GET /api/skills/catalog`, `GET /api/agents`, `GET /api/agents/{id}`, `POST /api/agents`, `PUT /api/agents/{id}`, and `DELETE /api/agents/{id}`.
  - "Agent Forge" Studio Character Sheet SPA UI (`#view-agents` in `src/web/templates/index.html` and `src/web/static/app.js`) featuring compartmentalized RPG character sheet cards (Identity & Avatar, Persona & Tone, Operating Manual System Prompt, Purpose Matrix & Model Override, Authorized Skill Capability Checkboxes, Real-time Lifetime Telemetry Stats).
  - Embedded System Agent AI Architect Co-Pilot with live streaming advice, quick starter chips (K8s SRE, Postgres DBA, Security Auditor), and one-click `[╬ô┬ú┬┐ Apply to Sheet]` blueprint synthesis.
- Unified Settings Studio, Provider Presets & Model Matrix (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Standard `ProviderPresetRegistry` (`src/application/settings/presets.py`) providing built-in presets for Ollama, OpenAI, Anthropic Claude, OpenRouter, Groq Cloud, DeepSeek, Together AI, and vLLM / Local with auto-populated default base URLs.
  - Dynamic Model Discovery endpoint `GET /api/models/discover` querying installed and cloud models across active providers with live hardware RAM fit evaluation.
  - Active Default Model Picker in Settings Studio allowing operators to discover models and persist the default platform model.
  - Harmonized Purpose-Based Model Routing with auto-populated dropdowns bound directly to discovered models.
  - Live Hardware Fit & Sizing Table displaying model parameter size, quantization format, estimated RAM in GiB, and status classification tags (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`, `cloud`).
- Plan-and-Execute Graph Engine & Goal Mode (`AutoReiv.Kernel`, `AutoReiv.Planning`, & `AutoReiv.Web`):
  - Structured `ExecutionPlan` and `PlanStep` domain models (`src/domain/planning/models.py`) with lifecycle states (`pending`, `in_progress`, `completed`, `failed`).
  - `PlanAndExecuteEngine` (`src/application/kernel/plan_engine.py`) deconstructing complex multi-phase user goals into ordered 2-to-6 step milestone DAGs and executing them sequentially with intermediate synthesis.
  - `PlanningSkill` (`src/application/skills/planning_skill.py`) providing dynamic plan modification tools (`mark_plan_step_completed`, `append_plan_step`, `get_active_plan`).
  - REST endpoint `POST /api/chat/goal` for goal formulation and autonomous multi-step execution.
  - Companion Web UI controls (`[╬ô┬ú├┤] Γëí╞Æ├ä┬╗ Goal Mode (Plan Graph)`), `/goal <instruction>` slash command parser, and live visual milestone checklist rendering in chat.
- Reflexive Self-Verification Loops & SRE Health Auditing (`AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Agents`):
  - Deterministic `VerificationSkill` (`src/application/skills/verification_skill.py`) exposing ground-truth assertion tools: `verify_telemetry_consistency`, `assert_json_schema`, and `validate_metric_bounds`.
  - Iterative `ReflexionLoopEngine` (`src/application/kernel/reflexion_engine.py`) catching verification discrepancies, feeding structured critique notes back to the model, and orchestrating multi-turn autonomous refinement loops (up to 3 attempts).
  - Kernel verified execution methods `kernel.run_verified_turn` and integration into `AgentKernel`.
  - Built-in `auditor-critic` agent profile (`src/domain/agents/profiles.py`) specialized in zero-shot adversarial reviews, risk scoring (1-10), and assumption validation.
  - REST endpoints `POST /api/chat/verified` and `POST /api/agents/audit` for verified execution and external audit pipelines.
- Model Context Protocol (MCP) Client Adapter & Dynamic Skill Loader (`AutoReiv.MCP` & `AutoReiv.Skills`):
  - Standard JSON-RPC 2.0 `MCPClientAdapter` (`src/infrastructure/mcp/client_adapter.py`) managing stdio subprocess transports, tool discovery (`tools/list`), and execution (`tools/call`).
  - Dynamic `SKILL.md` parser `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) discovering YAML frontmatter and JSON tool manifests.
  - `mount_mcp_tool` integration in `ScopedToolRegistry` dynamically binding MCP tools with RBAC enforcement.
  - SQLite persistent MCP server registry and REST routes `GET /api/mcp/servers` and `POST /api/mcp/servers`.
- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation (`AutoReiv.Orchestration`):
  - Standardized 5-Key `HandoffEnvelope` domain model (`src/domain/orchestration/models.py`) transferring intent and hydrated context across agent boundaries.
  - `SupervisorOrchestrator` (`src/application/kernel/supervisor_orchestrator.py`) managing specialist agent dispatch, execution, and response synthesis.
  - `DelegateSubtaskSkill` (`src/application/skills/delegate_skill.py`) exposing `delegate_task` tool to allow coordinator agents to route sub-problems.
  - `handoff` telemetry spans linking parent session, sender, recipient, and correlation IDs.
  - REST endpoint `POST /api/agents/delegate` for direct external invocation of specialized workflows.
- Ephemeral Subprocess Sandbox & HITL Approvals (`AutoReiv.Safety` & `AutoReiv.Kernel`):
  - `DangerousCommandFilter` (`src/application/skills/command_filter.py`) statically rejecting destructive commands (`rm -rf /`, `dd`, `mkfs`, `format c:`, raw DB drop queries).
  - `SandboxedSubprocessWorker` (`src/application/skills/sandbox_worker.py`) executing CLI commands and Python scripts within isolated temporary directories with strict timeouts and cleanup.
  - `is_high_risk` tool metadata and `HITLApprovalEngine` (`src/application/kernel/hitl_engine.py`) parking execution awaiting human operator decisions.
  - SQLite `pending_approvals` table and REST endpoints (`GET /api/approvals/pending`, `POST /api/approvals/{id}/decision`) to approve or reject parked tool calls.
  - Real-time streaming cancellation endpoint (`POST /api/chat/stream/{session_id}/abort`) to abort in-flight agent reasoning loops.
- Context Window Compaction & Episodic Memory (`AutoReiv.Memory` & `AutoReiv.Kernel`):
  - `ContextCompactor` (`src/application/kernel/context_compactor.py`) implementing sliding-window message preservation, intermediate turn summarization, and large tool output pruning (>8000 chars) to prevent context window overflow.
  - `episodic_facts` SQLite table and `EpisodicMemorySkill` (`src/application/skills/memory_skill.py`) storing discrete cross-session facts (user preferences, environment settings).
  - Gateway transient error resilience with localized exponential backoff and randomized jitter in `MultiProviderGateway._execute_with_retry`.
  - HTTP persistent client connection pooling (`httpx.Limits(max_keepalive_connections=20)`) in `OllamaProviderAdapter` and `OpenAIProviderAdapter`.
  - `CycleDetector` (`src/application/kernel/cycle_detector.py`) enforcing repetition trap detection across both synchronous `run_turn` and real-time `stream_turn`.
- Multi-OS Packaging & Bare-Metal / Docker Deployment (`AutoReiv.Deploy`): Unified CLI tool (`autoreiv`), background routine engine server lifespan, Ubuntu systemd daemon, Windows service scripts, and Docker Compose with persistent volume mounts.
- Unified CLI entry point (`src/cli/main.py`) with commands:
  - `autoreiv serve`: Launches FastAPI web server and routine tick engine.
  - `autoreiv status`: Reports host CPU/RAM specs, database connectivity, and registered agents.
  - `autoreiv chat`: Interactive terminal chat loop with live token streaming.
  - `autoreiv routine [list|run]`: Direct terminal management and one-shot trigger of background routines.
- FastAPI `lifespan` context manager running `RoutineScheduler` background task concurrently with web request handling.
- Ubuntu / Debian `systemd` daemon unit file (`deploy/systemd/autoreiv.service`) and automated installer (`deploy/systemd/install_systemd.sh`) optimized for Mini PC bare-metal deployment.
- Windows PowerShell runner (`deploy/windows/run_autoreiv.ps1`), batch runner (`run_autoreiv.bat`), and service registration script (`install_windows_service.ps1`).
- Multi-stage production `Dockerfile` with non-root security user, health check, and `docker-compose.yml` with host volume mounts for persistent database (`./data/autoreiv.db`) and wiki documents (`./data/wiki`).
- Environment variable configuration template (`.env.example`) documenting `OLLAMA_HOST`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH`, and `PORT`.
- Responsive Web & Mobile Front-Door with Wiki Export (`AutoReiv.Web`): Complete zero-build Single-Page Application (SPA) with real-time SSE streaming, collapsible `<think>` tags, and one-click PARA-Wiki markdown export.
- FastAPI application backend (`src/web/app.py`) providing unified REST and SSE endpoints for agents, sessions, chat streaming, wiki note export, settings matrix, KPI dashboard metrics, and autonomous routine triggers.
- `WikiExportService` (`src/application/web/wiki_export_service.py`) generating formatted markdown documents with YAML frontmatter and enforcing path-jailed security.
- Modern responsive desktop and mobile interface (`src/web/templates/index.html`, `src/web/static/app.js`) with tabbed workflows:
  - Γëí╞Æ├å┬╝ **Interactive Chat**: Live token streaming, reasoning `<think>` toggle bubbles, and real-time tool execution status indicators.
  - Γëí╞Æ├┤├ñ **One-Click Action Buttons**: "Export to Wiki" and "Copy to Clipboard" buttons on both full threads and individual assistant replies.
  - ╬ô├àΓûæ **Routines Studio**: Active schedule monitoring, status indicators, and manual "Run Now" execution triggers.
  - Γëí╞Æ├┤├¿ **Observability Dashboard**: High-level platform KPI cards, per-agent resource consumption table, and tool reliability matrix.
  - ╬ô├£├ûΓê⌐Γòò├à **Settings Studio**: Live provider model picker, purpose matrix configuration, and interactive hardware RAM fit calculator (with custom specs input for 128GB Nimo PC).
- Observability & KPI Dashboard Backend (`AutoReiv.Observability`): Comprehensive telemetry aggregation, per-agent breakdowns, tool reliability matrices, timeline charts, and structured JSON export.
- `ObservabilityDashboardService` for unified platform KPI calculation (total turns, prompt/completion tokens, avg turn latency, error rate percentage).
- Per-agent segregated KPI breakdown reporting turns, token usage, tool invocations, and error counts.
- `ToolReliabilityMetric` matrix tracking tool call frequencies, failure rates, and average duration.
- Time-series metric aggregation into hourly and customizable timeline buckets.
- `TraceExporter` for structured JSON and session trace dumping without external SaaS dependencies.
- Indexed SQLite analytical queries on `telemetry_spans(agent_id, span_type, created_at)`.
- Settings Studio Engine (`AutoReiv.Settings`): Dynamic live model discovery, purpose matrix routing, and hardware fit estimation.
- Live model discovery on `OllamaProviderAdapter` (`/api/tags`) and `OpenAIProviderAdapter` (`/v1/models`) with parameter size and quant level extraction.
- Purpose-Based Model Routing (`ModelPurposeMatrix`) for `GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, and `FAST` operational roles.
- `HardwareFitCalculator` predicting model RAM footprint (weight bits + KV cache headroom) and classifying host fit (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`) with custom specs overrides (e.g. 128GB Nimo PC).
- `SettingsService` for unified settings key-value management and runtime agent persona/tone/prompt customizations (`AgentCustomization`).
- SQLite persistence tables (`settings` and `agent_overrides`) for zero-loss configuration storage across application restarts.
- Autonomous Routine Engine & Background Scheduler (`AutoReiv.Routines`).
- Declarative `Routine` and `RoutineRun` models with interval and cron schedule configurations.
- SQLite persistence for routine configurations and chronological execution run histories (`routines` and `routine_runs` tables).
- `ScheduleMatcher` for deterministic interval and cron due time calculations.
- `RoutineExecutor` for isolated autonomous session execution via `AgentKernel` and automatic telemetry span recording.
- `RoutineScheduler` with non-blocking async tick loop and manual out-of-schedule trigger API.
- 4 Day-1 default routine manifests: Morning Briefing, Daily System Info, Nightly Note Hygiene, and Hourly SRE Pulse.
- 4 Built-In Agent Manifests (`AutoReiv.Agents`): General Assistant, Linux Sysadmin, Librarian, and System Agent.
- `TaskTrackerSkill` with SQLite-backed task CRUD (`create_task`, `list_tasks`, `update_task_status`, `delete_task`).
- `SysadminSkill` with cross-platform host metrics (`get_system_info`) and asynchronous timeout-protected command execution (`cli_exec`).
- `LibrarianSkill` with YAML frontmatter parser and path-jailed PARA-Wiki note creator (`wiki_note_create`, `wiki_note_read`, `wiki_note_list`).
- `SystemAgentSkill` providing platform health diagnostics, database latency testing, and token usage summaries.
- `BuiltinAgentRegistry` for one-line ecosystem bootstrapping and automatic scoped tool binding.
- Agent Kernel & ReAct execution engine (`AutoReiv.Kernel`) supporting multi-turn tool loops, cycle detection, and max turn budgeting.
- Declarative `AgentProfile` manifest with configurable `AgentTone` prompt directive formatting.
- `ScopedToolRegistry` with strict Role-Based Access Control (RBAC) tool execution permissions.
- `SQLiteStateStore` with WAL mode (`AutoReiv.Memory`) for chronological conversation checkpointer and session management.
- `TelemetryCollector` and `TelemetrySpan` tracking per-agent token usage, tool reliability/error metrics, and global platform KPIs.
- Real-time streaming `KernelEvent` generator for tokens, tool execution starts, tool outputs, and turn completions.
- Multi-Provider LLM Gateway (`AutoReiv.Gateway`) with unified message schema (`ChatMessage`, `Role`, `ToolCall`).
- Abstract `LLMProviderPort` protocol and dynamic provider registry.
- `OllamaProviderAdapter` for local/LAN Ollama execution with streaming and tool calling.
- `OpenAIProviderAdapter` for OpenAI-compatible cloud/local endpoints with SSE streaming.
- `MultiProviderGateway` orchestrator with multi-model fallback execution chains.
- `ReasoningDemuxer` for splitting `<think>...</think>` tokens in real-time streams.
- `GatewayProviderFactory` for zero-boilerplate initialization from environment variables.
- 55 hermetic unit tests with mock HTTP transports and zero outbound network calls.

### Added

- **Repo/code capability path [CARD-262 / REQ-REPO-001..005]**: Catalog-registered read-only `repo_file_list` / `repo_file_read` jailed under AutoReiv checkout (`AUTOREIV_CHECKOUT_ROOT` or detect) with sensitive denylist ╬ô├ç├╢ no FS escape. CARD-221 SAFE (no write tools in this card). Standing Chat injects repo grounding constraint for code-aware asks; claim guard + honest-fail when no successful read (Homelab-class: never invent AGENTS.md/source). Homelab + Assistant packs gain tools. Live `notes/marathon-card262-live-smoke.json`.

### Added

- **Standing honesty/smoke pack tip merge gate [CARD-261 / REQ-HSP-001..005]**: Freeze stress classes `timeout|gate|tool|honesty|kill_resume|pass` as a standing tip merge gate. Classifier + `notes/scripts/honesty_smoke_pack_261.py` (`--validate` / `--live`) exit non-zero on red Done-on-FAILED / honesty theatre / silent SSE death. Wired into unified preflight; runbook `steering/honesty-smoke-merge-gate.md`. Live `notes/marathon-card261-live-smoke.json`.

### Fixed

- **Wiki-thin fail-closed grounding [CARD-260 / REQ-WIKITHIN-001..004]**: Empty/thin vault topics no longer invent Okta-class Wiki paths/titles. Standing Chat probes the vault before Formulate; source-dependent thin asks HITL-park with **need sources**; create-shaped thin asks proceed **grounded_only** (paths only from `wiki_note_create`/`wiki_note_read`). Chat turn claims that cite paths outside tool provenance **and** this Job vault grounding hit/read allow-list are honesty-rewritten (not Done theatre); ellipsis table paths are ignored. Live `notes/marathon-card260-live-smoke.json`.

- **Kill/resume mid-LLM same job_id [CARD-259 / REQ-KILLR-001..005]**: Operator abort during standing Formulate/Execute no longer `fail_phase` / cancel the Job (live other `job_9836e6ddd4a2`). Abort writes a durable checkpoint (`operator_kill_mid_llm`), re-queues the RUNNING phase, stops the worker (no orphan after SSE death), and `resume: true` continues the **same** `job_id` to DONE or honest park. Never Done-on-FAILED. Live `notes/marathon-card259-live-smoke.json`.

- **Phase LLM longer budget + retries [CARD-258 / REQ-PLLM-001..005]**: Standing Formulate/Execute/Research no longer die at the import-time 120s default (live FAIL `job_cbf0a330fc5c`). Default budget 300s for qwen KV fill; timeout/retries resolve at **call time** from env; CLI serve + `restart_serve` load repo `.env` (do not overwrite process env). 1╬ô├ç├┤2 retries on `phase_llm_timeout` / connection stall before `fail_phase`; exhausted reason includes `retries_exhausted` + CARD-257 honesty (never Done / invent a note). Live `notes/marathon-card258-live-smoke.json`; stress pack `notes/marathon-card258-stress-pack.json`.

- **Research gate skip-or-continue + Chat status honesty [CARD-257 / REQ-RGATE-001..005]**: Matched tools covering the outcome (`outcome_covered_by_matched`) skip Research even when `count < 2` ╬ô├ç├╢ never hard-fail on `below_threshold` alone. Standing Research with side-effects already at mint **auto-completes without LLM** (Chat + routine executor) so thin Research cannot `phase_llm_timeout` ╬ô├Ñ├å `fail_phase` kill Formulate/Execute. On Job/phase FAILED, Chat emits honest `turn_done` (job_id + phase + reason) instead of leaving streamed "Done╬ô├ç┬¬" / invented notes as the claim. `derive_success_rule` prefers colon-form `Done-when:`. Live `notes/marathon-card257-live-smoke.json`.

### Added

- **Self-scaffold queue E2E [CARD-255 / REQ-SSQ-001..005]**: Education gap Ask -> Forge candidate -> sandbox/HITL Approve (251 same job_id) -> trusted; next Job trusted-only resolve can use the skill; rollback restores prior trusted; standing catalog resolve never auto-trusts candidates. Live `notes/marathon-card255-live-smoke.json`.
- **Verifier / replan harden [CARD-254 / REQ-VRH-001..005]**: Binary external verify only (LLM self-critique never standing pass); `apply_forced_fail_verify_gate` forces fail -> CARD-232 replan <=3 -> HITL park (no infinite loop); Chat standing checker-fail uses `apply_phase_complete_verify_gate` (not `fail_phase` dead-end); handoff != replan. Live `notes/marathon-card254-live-smoke.json`.
- **Long-run context / working-set holds N╬ô├Ñ├åN+1 [CARD-253 / REQ-LRCTX-001..005]**: Phase-scoped working set (228 progressive skill + 229 working set) survives kill/resume; phase N+1 rebuilds from ledger/`memory.db` facts + durable notes ╬ô├ç├╢ full Chat transcript dumps rejected as memory theatre. `rebuild_working_set_after_resume` + Chat resume wire; live `notes/marathon-card253-live-smoke.json` (qwen SAW_LEDGER).
- **Frozen operator eval pack [CARD-252 / REQ-EVAL-PACK-001..004]**: 3-5 frozen asks (Chat outcome Job, Education Ask/quiz, Wiki Job, Forge Approve same job_id) with Observe `job_id` checklist; CI-scriptable runner `notes/scripts/frozen_eval_pack_252.py` + `tests/unit/eval/test_frozen_eval_pack_252.py`; live `notes/marathon-card252-live-smoke.json`.
- **Serve / orphan process hygiene [CARD-256 / REQ-SERVE-HYG-001..004]**: Documented Jarvis restart runbook (`steering/serve-orphan-hygiene.md`); `scripts/restart_serve.py` (+ `.ps1`) finds/kills :8000 orphans, starts one tip serve, prints tip SHA + `app.js?v=` from `index.html`; unit tests lock version parse + dry-run; live smoke `notes/marathon-card256-live-smoke.json`. Prevents stale-serve / stale-chrome false fails.
- **Education Studio viewport layout [CARD-250 / REQ-EDU-VP-001..004]**: Learning OS pedagogy panels (Quiz╬ô├Ñ├åAmplifiers) wrap/stack inside `#educationPedagogyColumns` with in-panel `overflow-y` and `overflow-x: hidden` so Studio fits one viewport ╬ô├ç├╢ no sideways peek / forever-horizontal overflow; CARD-242..249 engines untouched; Lumina out of scope.
- **Education Visual Amplifiers / Mermaid + step-through on Retrieval [CARD-249 / REQ-EDU-VA-001..004]**: Dual Coding Mermaid and ordered step-through attach to quiz/mastery Retrieval items only; visuals-only / missing ledger path refused (edutainment guard); video/film player OUT of P0; Education Studio Amplifiers panel + `/api/education/amplifiers/*`; quiz/next surfaces amplifiers without rewriting `next_due`.
- **Education Environment / study-session delivery profiles [CARD-248 / REQ-EDU-ENV-001..004]**: Named delivery profiles (tone + timer / ADHD bite-size) shape Ask and quiz _presentation_ only; mastery ledger + Routine->Job SRS remain sole due/resurface source; Education Studio Environment panel + `/api/education/environment/*`; quiz/next returns delivery metadata without rewriting `next_due`.
- **Education Analysis / error log + metacog [CARD-247 / REQ-EDU-AN-001..004]**: On miss/fail, deterministic `miss_reason` taxonomy writes durable error_log + metacog facts into agent `memory.db` (never `storage.db`); `/api/education/quiz/next` prefers miss-reason pressured weak items (feeds CARD-243); Wiki + memory write-back; Education Studio Analysis panel + `/api/education/analysis/*`.
- **Education Application / Exercise Job + binary verify [CARD-246 / REQ-EDU-APP-001..004]**: Application exercises from Wiki `## Application`/`## Exercise`; binary external grade (reference/concepts ╬ô├ç├╢ never LLM self-score); prefer standing Exercise Job mint; fail ╬ô├Ñ├å bounded replan or HITL park (CARD-232) + mastery miss/resurface; pass advances mastery; Wiki + memory.db write-back; Education Studio Application panel + `/api/education/application/*`.
- **Education Construction / generative study artifacts [CARD-245 / REQ-EDU-CONST-001..004]**: Deterministic Construction engine builds schema + dual-code + quiz/elaboration study notes and stages them to Wiki `00_Inbox/` via catalog-matched `wiki_note_*` only (CARD-241 allowlist; fail-soft search/read; never `wiki_overview`). Seed `education-construction`, Ask mode chip, Education Studio Generate panel, `/api/education/construction/generate`.
- **Education Elaboration / explain-it-back [CARD-244 / REQ-EDU-ELAB-001..004]**: Binary external grade (reference token containment or required-concepts rubric ╬ô├ç├╢ never LLM self-score); miss updates mastery ledger + 1-3-7-30 and can Routine╬ô├Ñ├åstanding Job resurface (reuse CARD-242); Wiki + memory.db write-back of elaboration outcomes; Education Studio Elaboration panel + `/api/education/elaboration/*` endpoints.
- **Education Learner Model [CARD-243 / REQ-EDU-LM-001..004]**: Quiz grades write durable strengths/weaknesses/patterns into agent `memory.db` semantic facts (adjacent to the CARD-242 mastery ledger ╬ô├ç├╢ never `storage.db`); `/api/education/quiz/next` prefers due/weak/missed over random; Education Ask + Studio Next Quiz / Pressure Ask pressure known misses; kill/resume serve still prefers the known miss from `memory.db` (no second tutor runtime).
- **Education Retrieval + Retention [CARD-242 / REQ-EDU-RR-001..005]**: Quiz engine over Wiki Priming/Dual notes with binary external grade (not LLM self-score); thin mastery ledger in agent \memory.db\ (item id, topic/path, grade, next_due); miss schedules fixed 1-3-7-30; \ducation-retrieval-retention\ Routine mints standing Jobs for due reviews (chat toast is not Done); Education Studio Quiz/Due operator path + \/api/education/*\ endpoints.

### Fixed

- **P0 empty-rail / blank Chat [CARD-251 syntax]**: `7ca3f9d` stripped template-literal backticks in `forge.js` (`SyntaxError: Invalid regular expression flags`). Static `import` of Forge prevented `initApp` (CARD-237 class: chrome loads, rail+Chat dead). Restored templates + `$()` lookups; Forge is now dynamic-import so one studio parse failure cannot blank Chat. Live `notes/marathon-card255-spa-rail-fix-smoke.json`.
- **Forge Approve resumes same job_id [CARD-251 / REQ-FORGE-RESUME-001..004]**: Parked mid-job HITL Forge Approve promotes via 218 spine then unparks/`start_phase` on the **same** `job_id` / origin session (no orphan mint, no soft-delete). Forge UI resumes origin Chat + Observe one tree; Chat standing mint refuses orphan while `waiting_approval`. Live smoke `notes/marathon-card251-live-smoke.json`.
- **Education Priming/Dual Coding Wiki allowlist [CARD-241 / REQ-EDU-WIKI-001..003]**: Skills + Ask shaping only call catalog-matched `wiki_note_*` (never bare `wiki_overview`). Unregistered / out-of-matched-subset tool calls fail soft / skip so Execute can still land an Inbox note; Education skill matches expand to the `wiki_note_*` allowlist; job-bound turns stop offering `wiki_overview` to the model.

### Fixed

- **Unified Job phase chrome on Education origin [CARD-240 / REQ-JOB-CHROME-001..003]**: Education Ask forwards SSE phase events into Chat's grape-vine inline Job chrome (`updateJobChromeFromEvent` -> Formulate/Execute bars + `plan-steps`) and the shared strip; replays after `selectSession` so origin is not prompt-only. No Education-only progress UI.

### Added

- **Learning OS 1╬ô├ç├┤2**: Education Priming + Dual Coding skill seeds and Education Ask mode chips (Wiki schema / prose+Mermaid write-back via standing Jobs) [CARD-238].

### Fixed

- **HITL origin cohesion**: Education Ask keeps SSE after `job_created`, opens origin Chat for phase Approve, and Education Jobs show Needs approval / Approve in Chat [CARD-239 / REQ-HITL-ORIGIN-001..003].

### Fixed

- **Education Ask mint**: always create a fresh Education session (do not reuse Chat/phase `activeSessionId`); return on `job_created` so Ask cannot hang disabled [CARD-237 / REQ-EDU-SHELL-002a].

### Fixed

- **Education Studio P0**: stray brace in `app.js` tab loader blanked SPA (rail/dock never init); Education now dynamic-imported so one studio cannot take down `initApp` [CARD-237 / REQ-EDU-SHELL-005].

### Added

- **Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]**: New Education Studio in SPA nav + desktop dock. Wiki-backed ask (topic + how-to-teach + optional Wiki note search) mints a standing Job via the CARD-236 Chat `/api/chat/stream` path with outcome-shaped `done-when` / `success_rule`, shows copyable `job_id`, and lists Education Jobs with Open in Chat / Open in Observe. Shell + Job mint only ╬ô├ç├╢ no quiz/SRS/concept-player depth.

### Fixed

- **Chat Job strip + Journey show copyable `job_id` [CARD-236 / REQ-JOBMINT-005]**: When a standing Job is bound, the Chat Job strip and Journey header render the full `job_╬ô├ç┬¬` string (monospace chip) with one-click Copy so operators can paste into Observe without us supplying the id.
- **Chat outcome ask always mints standing Job [CARD-236]**: Wiki-write / done-when outcome-shaped Chat asks (incl. hyphenated `done-when:`) always create a durable Job via `create_job_from_catalog_resolve` before phase 1 ╬ô├ç├╢ never silent ReAct with `jobs=[]` after a successful outcome reply. Classifier covers create/write/save/author wiki|note deliverables; `derive_success_rule` extracts hyphenated done-when clauses. Chat fail-closes when orchestrator unavailable instead of ReAct-bypass theatre. Short chitchat stays plain ReAct. Observability standing-journey by `job_id` shows intake ╬ô├Ñ├å phases.

### Fixed

- **Chat composer hit-testing [CARD-235]**: Incomplete CARD-215 Goal-theatre cleanup left orphan Enable/dismiss buttons and a stray `</div>` that closed the composer `pointer-events-auto` wrapper early, so **+ Options** (and the rest of the form) sat under `#chatInputWrapper.pointer-events-none` and could not receive clicks. Removed the orphan controls, restored nesting, set `pointer-events: auto` on `#chatForm` / Options, and disabled maximized window resize hit-targets so they cannot cover the composer. Dock chrome remains PE-none with PE-auto only on `.desktop-dock-shell`.

### Added

- **Supervisor specialist pick from matched catalog [CARD-234]**: `JobPhaseOrchestrator.supervisor_pick_specialist` picks handoff targets **only** from matched catalog agent/pack IDs (working set) ╬ô├ç├╢ not free-form role theatre. Reuses CARD-224 standing child job (never-widen + linked `child_job_id` + checkpoint). Out-of-catalog handoff rejected; no specialty match => park/scaffold (233) or fail-closed (never invent). Observability journey `standing.supervisor_pick` + Chat strip parent╬ô├Ñ├╢child link. Closes wave 2 (230╬ô├ç├┤234).

- **Mid-job self-scaffold via 218 spine [CARD-233]**: When a running Job hits a capability gap (tool/skill missing for `success_rule` / phase), standing runtime opens a **candidate** draft via `SelfScaffoldSpine` ╬ô├ç├╢ never writes trusted from a live phase. Path: draft ╬ô├Ñ├å sandbox ╬ô├Ñ├å version ╬ô├Ñ├å HITL approve ╬ô├Ñ├å trusted ╬ô├Ñ├å catalog re-resolve (updates matched IDs on checkpoint). Until HITL promotes, Job parks (or continues with remaining matched only) ╬ô├ç├╢ no silent candidate-as-trusted. Observability journey shows `standing.scaffold_candidate` + `standing.scaffold_hitl` + `standing.catalog_reresolve`; Forge candidate queue is the operator path. Rejects unscoped trusted write mid-phase. Extends 215╬ô├ç├┤232 + 218 only.

- **Bounded auto-replan on verifier failed [CARD-232]**: On standing verifier `failed`, Job auto-replans remaining phases against the same `success_rule` + matched capability IDs (never silent advance). Cap `MAX_REPLAN_ATTEMPTS=3` (durable `replan_count` on checkpoint); 4th fail => HITL park with `last_fail_reason` (not infinite loop, not auto-success). `skipped_no_checker` still does not replan and never counts as verified advance (216). Observability standing journey shows `standing.replan` + `standing.replan_park` spans. Extends 215-231 only.

- **Standing research-before-plan on capability gap [CARD-231]**: After intake catalog resolve, thin/gap matches (empty IDs, below threshold <2, or missing critical roles implied by `success_rule`) insert a **Research** phase before Formulate/Execute. Sufficient matches skip research (Formulate/Execute only ╬ô├ç├╢ no latency tax). Research writes facts into `<agent>_memory.db` and may propose catalog gaps; never writes trusted skills/tools (218/233). Checkpoint persists `research_inserted` + reason; Observability standing journey shows `standing.research` span. Extends 215╬ô├ç├┤230 only.

### Added

- **Outcome intake ╬ô├Ñ├å durable Job + success_rule [CARD-230]**: Outcome-shaped Chat asks (multi-step / goal / deliverable language) create a standing Job with a **testable** `success_rule` stop condition and catalog-resolved `matched_capability_ids` before phase 1. Vibes-only rules (`"looks good"`) reject at intake. Agent picker is preference only ╬ô├ç├╢ matched IDs remain capability authority. Fail-closed phase-1 gate when either field is missing. Extends 215╬ô├ç├┤229 standing path only (no second orchestrator).

### Added

- **Phase-scoped working-set context [CARD-229]**: Each standing Job/Phase turn carries phase goal + matched capability metadata + **bound** skill body only + this-phase `memory.db` facts. Prior phases distill to short durable notes (tool dumps / unbound skill bodies stripped; M12 ContextCompactor truncation aligned). Wired into Chat standing + crash-resume and Routines standing path. AGENTS.md invariant: Chat still lists ticked tools every turn.

### Added

- **Progressive SKILL.md disclosure [CARD-228]**: Catalog/resolve returns skill metadata only (`id`, `title`, `risk`, HITL flags) ╬ô├ç├╢ never full `SKILL.md` bodies (qwen context tax / theatre). Standing Job/Phase `bind_skill_for_phase` loads one runbook body on phase bind/select (`skill_bound` journey event + SSE). `POST /api/capabilities/bind-skill`. Chat still mounts that agent's ticked tool schemas every turn (AGENTS.md / CARD-117/121 invariant).
- **Observability standing journey timeline [CARD-227]**: One `job_id`-correlated standing path replay (`GET /api/observability/standing-journey`) with OpenTelemetry-style GenAI agent span tree. Includes Job/Phase steps, catalog matches, verifier statuses, CARD-221 policy decisions (MCP BLOCKs), durable A2A `child_job_id` links, and `resumed_from_checkpoint` events. Observability Studio filter UI closes scattered-panel theatre.

### Added

- **Job/Phase cross-phase memory.db recall [CARD-226]**: Standing Job/Phase path persists phase reflections/facts into per-agent `<slug>_memory.db` via CARD-116 `AgentMemoryRepository` (never `<slug>_storage.db`). Checkpoints stamp accumulating `memory_fact_ids`. Kill/resume rebuilds prior from memory.db for phase N+1 (`memory_recalled` SSE + `GET /api/observability/job-phase-memory`). Closes ephemeral-prior theatre on resume.

### Added

- **MCP tools through matched-subset + CARD-221 gate [CARD-225]**: MCP ools/list / mount is transport only (listing ╬ô├½├í authorization). Mounted mcp_<server>_<tool> calls hit matched capability subset (when job-bound) and ToolPolicyGate ALLOW / REQUIRE_CONFIRM / BLOCK before executor. Outside-subset / unknown MCP ╬ô├Ñ├å BLOCK (never runs). Dangerous MCP names ╬ô├Ñ├å REQUIRE_CONFIRM ╬ô├Ñ├å existing HITL. Extends MCPClientAdapter / ScopedToolRegistry / ToolPolicyGate ╬ô├ç├╢ no parallel auth.

### Fixed

- Standing Job/Phase LLM hang no longer leaves orphan RUNNING phases: routine and Chat standing turns bound by `STANDING_PHASE_LLM_TIMEOUT_SECONDS` and call `fail_phase` with checkpoint on timeout/cancel/error [CARD-222 reliability].

### Added

- **A2A handoff inherits standing Job/Phase path [CARD-224]**: Linked `child_job_id` inherits parent matched capability IDs (no cold re-resolve / no tool widen). `HandoffResult` stamps `parent_job_id`/`child_job_id`; child has own checkpoint; CARD-221 BLOCK/REQUIRE_CONFIRM preserved; kill╬ô├Ñ├åresume same child `job_id`. `/api/agents/delegate` prefers `HandoffIsolationEngine`; `handoff_to_agent` stamps `parent_job_id` from tool context; child `stream_turn` bound to `job_id`; kernel resolves matched IDs for the tool policy gate when job-bound. Lazy `ToolPolicyGate` import breaks kernel╬ô├Ñ├╢policy circular import.
- Marathon scorecard `notes/marathon-scorecard-standing-job-graph.md` (cards 215╬ô├ç├┤224).

- **Routines join standing Job/Phase path [CARD-222]**: Cron/scheduler remains trigger-only. Multi-step `RoutineExecutor` calls `JobPhaseOrchestrator.create_job_from_catalog_resolve` (same catalog R/H/E + matched IDs + verifier gate + CARD-221 policy/HITL as Chat). Durable `job_id` on `RoutineRun` / routine metadata; crash-resume same `job_id`. Short prompts stay plain ReAct. Special curator/skill-eval jobs unchanged. Trigger/run API returns durable job_id.
- **Steering truth sync [CARD-223]**: Roadmap M15╬ô├ç├┤17 marked Done/Superseded (MCP, external verifier/Reflexion, Job-Graph superseding Goal-mode). `steering/product.md` no longer claims a shipped Docs Studio (`docs.js` absent). FastAPI OpenAPI version aligned to package `0.28.0`. `PROJECT.md` labeled stale audit brief.
- **Tool policy gate [CARD-221]**: Every tool call gets durable `ALLOW` / `REQUIRE_CONFIRM` / `BLOCK` via `ToolPolicyGate` before the executor (registry listing ╬ô├½├í authorization). `REQUIRE_CONFIRM` parks through existing HITL; `BLOCK` fail-closed. Decision log + `GET /api/observability/tool-policy-decisions`. Extends DangerousCommandFilter / HITL ╬ô├ç├╢ no parallel HITL.
- **Chat standing path uses catalog resolve [CARD-220 anti-theatre]**: `/api/chat/stream` multi-step now calls `JobPhaseOrchestrator.create_job_from_catalog_resolve` (Research/Handoff/Execute + matched capability IDs); emits `catalog_resolved`. App wires `capability_resolver` into the orchestrator. Short turns stay plain ReAct.

### Added

- **Catalog Resolve into JobPhaseOrchestrator [CARD-220]**: Standing Capability Catalog C runtime ╬ô├ç├╢ `JobPhaseOrchestrator.create_job_from_catalog_resolve` maps `intent ╬ô├Ñ├å matched subset ╬ô├Ñ├å Research / Handoff / Execute`. Matched capability IDs persist on `job_phase_checkpoints` (extend CARD-219); `resume_after_crash` reuses the same subset (no cold re-resolve drift). Advance rules: only `verified` advances Execute; `failed` ╬ô├º├å park + `needs_replan`; `skipped_no_checker` never counts as verified advance (Research/Handoff may continue on honest skip). Out of scope: UI polish, new Studios.

- **Job/Phase Crash-Resume Checkpoints [CARD-219]**: Durable `job_phase_checkpoints` rows after each phase commit (`job_id`, phase index, verifier status `verified|skipped_no_checker|failed`, HITL park state). `JobPhaseOrchestrator.resume_after_crash` continues the same `job_id` after mid-phase process kill (LangGraph-style); replan-from-zero only when checkpoint is corrupt/missing. Chat SSE + Job/Phase strip + Observability surface `resumed_from_checkpoint`. Extends existing SQLite Job/Phase persistence ╬ô├ç├╢ no second graph engine.
- **Self-Scaffold Spine [CARD-218]**: New skill/tool always lands **candidate** (never trusted by default). Durable `scaffold_spine` path draft ╬ô├Ñ├å sandbox_exec ╬ô├Ñ├å version ╬ô├Ñ├å HITL approve ╬ô├Ñ├å trusted. Run gate rejects unsandboxed candidates; unscoped write to trusted is rejected; rollback restores prior trusted via UserSkillCatalog snapshots. Agent Forge candidate queue + `/api/capabilities/scaffold/*`. Extends propose_skill/HITL/catalog (no second product). Cite SoK Agentic Skills arXiv 2602.20867. Out of scope: crash-resume (CARD-219).

- **Capability Catalog C (match-only) [CARD-217]**: Progressive capability index over `agent|skill|tool|pack|routine` with trust tiers (`candidate`╬ô├Ñ├å`reviewed`╬ô├Ñ├å`trusted`), risk + HITL flags, SQLite `capability_index`, and `POST /api/capabilities/resolve` returning a matched **subset only**. Operator `GET /api/capabilities/registry` is capped and marked `prompt_dump_forbidden`. No dump-all-for-prompt path. Out of scope: self-scaffold write spine.

- **Standing External Verifier Policy [CARD-216]**: Reflexion/retry only when a named binary checker is present (pytest/schema/health/tool). Missing checker yields durable `skipped_no_checker` (never same-model pass). Wired via `external_verifier_policy` phase-complete gate + `run_verified_turn`; Chat/Observability surface `verified` / `skipped_no_checker` / `failed`. Cites Shinn Reflexion 2023; Panickssery 2024 same-model judges.

- CARD-215 In Review (`AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre` - CARD-215):
  - **Standing Job-Graph Runtime**: Multi-step Chat outcomes formulate/advance durable Job+Phase rows via `JobPhaseOrchestrator` without requiring `goal_mode=true`. Short turns stay plain `AgentKernel` ReAct.
  - **Retire Goal-mode theatre**: Removed Chat UI Goal toggle and Goal suggestion chip; `goal_mode` on `/api/chat/stream` is ignored for routing. `POST /api/chat/goal` is deprecated to formulate-into-Job/Phase only (no `execute_plan` bypass).
  - **PlanAndExecuteEngine formulator-only**: Kept as no-tool phase formulator writing into Job/Phase; `execute_plan` marked retired as parallel execute authority.
  - **Honest verify**: `self_verify` / Reflexion runs only with a named external checker; missing checker yields honest skip (no same-model-only success).
  - **Replan**: `JobPhaseOrchestrator.replan_job` replaces queued remaining phases while preserving DONE history.

## [0.28.0] - 2026-09-10

- CARD-213 Done (`AutoReiv.Gateway`, `AutoReiv.Settings`, `AutoReiv.Chat` - CARD-213):
  - **Google Gemini Provider Compatibility & Tool Message Sanitization**: Fixed silent hanging and HTTP 400 errors when using Google Gemini as the LLM provider in Chat Studio (`#view-chat`).
  - **Orphan Tool Call Sanitization**: In `OpenAIProviderAdapter._format_messages()`, unlinked or orphan `role: "tool"` messages without a matching `tool_call_id` in the immediately preceding assistant turn (from past provider runs, approval pauses, or handoffs) are automatically transformed into clean user context notes (`[Tool Output: <name>]: <content>`), preserving full conversational history while preventing Google Gemini's OpenAI endpoint from rejecting calls with `HTTP 400: function_response.name: Name cannot be empty`.
  - **Verified Model Recommendations**: Updated Gemini model catalog in `presets.py` to verified, low-latency models (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.1-flash-lite-preview`), deprecating non-existent models (`gemini-3.8-flash`, `gemini-3.5-flash`).
  - **Automatic Obsolete Model Normalization**: Added automatic migration in `src/web/routers/settings.py` and `OpenAIProviderAdapter._format_model_name()` that normalizes dead Gemini model names in stored provider configurations to `gemini-3.6-flash` / `gemini-3.7-flash`.

- CARD-212 Done (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Web` - CARD-212):
  - **LLM Provider Hybrid Credential Vault Picker**: Added a hybrid credential source selector (`#provVaultCredSelect`) in Settings Studio allowing operators to link any provider directly to an existing Credential Vault secret or type a direct key.
  - **Direct & Linked Vault Modes**: Selecting an existing Vault credential disables the input field and displays a linked badge (`Linked: <name>`), preventing secret duplication and ensuring single-source-of-truth credential management. Selecting "Direct Secret Input (Auto-Vault)" re-enables direct input to auto-encrypt secrets to `llm-provider-{pid}`.
  - **Live Vault Synchronization**: The credential picker dynamically refreshes when secrets are added, edited, or deleted in the Credential Vault table below.
  - **Dynamic Gateway & Model Discovery Binding**: Backend `POST /api/settings/providers` persists `vault_cred_id`, while `/api/settings` and `/api/models/discover` resolve keys dynamically from the linked Vault credential.

- CARD-211 Done (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Gateway` - CARD-211):
  - **Per-Provider LLM Credentials & Vault Persistence**: Updated `provider_settings` to persist configurations as an independent per-provider map (`gemini`, `openai`, `anthropic`, `ollama`, etc.), ensuring swapping between providers never clears or overwrites saved API keys.
  - **AES-256-GCM Vault Encryption**: Integrated LLM provider secrets with AutoReiv's Credential Vault (`credentials` table). API keys are encrypted at rest with zero plaintext secrets exposed in SQLite settings.
  - **Automatic Legacy Key Migration**: On boot and first load, existing legacy plaintext keys (including active Google Gemini keys) are automatically migrated into encrypted Vault records.
  - **Settings Studio Vault Hydration & Masking**: Changing the Provider Preset dropdown dynamically restores the provider's saved host URL, displays an "Encrypted in Vault" badge (`#provKeyVaultBadge`), and masks saved credentials (`╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│╬ô├ç├│`) to prevent accidental key exposure while allowing one-click overrides.
  - **Vault-Aware Model Discovery**: Updated `/api/models/discover` to dynamically resolve provider keys directly from the Credential Vault when omitted from client query parameters.

## [0.27.0] - 2026-09-10

- CARD-210 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-210):
  - **Enterprise Neutral Chrome & Restrained Theme Accents**: Window shells and focused borders use neutral white/alpha borders (`rgba(255, 255, 255, 0.10)`) and elevation shadows without brand halos. Window titlebar icons retain clean slate chrome (`#94a3b8`).
  - **Enterprise Palette Presets**: Recalibrated preset color models for professional enterprise workstations: Indigo, Slate Graphite, Violet, Warm Sand, and Teal.
  - **Storage Key Upgrade**: Upgraded client theme persistence to `autoreiv.theme.v2` to prevent legacy neon/high-saturation test settings from sticking across browser sessions.

- CARD-209 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-209):
  - **Dynamic Stage Wallpaper Theming**: Routed `.desktop-wallpaper` radial gradients and backgrounds through `--theme-brand-glow`, `--theme-bg-surface`, and `--theme-bg-base`, allowing the background desktop stage to transform organically with active themes.
  - **Deep Studio Card & Panel Skinning**: Mapped hosted studio cards, panels, and containers (`.bg-slate-900`, `.bg-slate-950`, `.card-nested`, and border dividers) to `--theme-bg-surface` and `--theme-border`, extending palette colors deeply across all windows (Settings, Observability, Routines, Chat).
  - **Primary Buttons & Metric Highlights**: Mapped primary action buttons (`button.bg-brand-600`, `button.bg-indigo-600`, `.btn-primary`) and text highlights (`.text-indigo-400`, `.text-brand-400`) to `--theme-brand` with calculated high-contrast text (`--theme-brand-contrast`).
  - **Rich Palette Tuning**: Enhanced prebuilt presets with distinctly calibrated dark base and surface tones for Amber Phosphor, Emerald Matrix, Orbital Monochrome, and Obsidian Slate.

- CARD-208 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Settings` - CARD-208):
  - **Theme Customizer and Color Palette Presets**: Added an interactive theme customizer to Settings Studio (`#view-settings` -> `#settingsThemeCard`) with 5 prebuilt themes: AutoReiv Indigo, Orbital Monochrome, Obsidian Slate, Amber Phosphor, and Emerald Matrix.
  - **Slider-Style Custom Palette Tuner**: Implemented custom palette controls with Hue (0-360Γö¼Γûæ), Saturation (0-100%), and Background Tone (0-30%) range sliders allowing real-time color adjustments, dynamic hex display tags, and instant window preview.
  - **CSS Variable Architecture**: Routed desktop window shells, titlebars, dock buttons, and active borders through dynamic CSS custom properties (`--theme-brand`, `--theme-brand-hover`, `--theme-brand-glow`, `--theme-bg-base`, `--theme-bg-surface`, `--theme-border`), providing seamless real-time theme switching without DOM recreation.
  - **Persistence & Reset**: Added browser local storage caching under `autoreiv.theme.v1` with automatic boot restoration and a one-click Reset button to restore defaults.

- CARD-207 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Desktop` - CARD-207):
  - **Sessions Window Studio Cleanup**: Hid the redundant "All Studios" navigation grid (`#sidebarNav`) and close button when opening the Sessions drawer/window in desktop mode, giving the recent conversation history list (`#sessionList`) full vertical space to display and scroll.
  - **Studio Page Vertical Scrolling**: Updated `.tab-view.desktop-view-hosted` layout rules so page-style studio views╬ô├ç├╢including Settings (`#view-settings`), Routines (`#view-routines`), Observability (`#view-observability`), and any scrollable tab views╬ô├ç├╢allow smooth vertical scrolling without clipping content on both desktop floating windows and mobile viewports.
  - **Desktop Window Resize Layer & Corner Handles**: Changed `#desktopWindowLayer` to `display: contents` and elevated window shells and 8-directional resize handles to `win.z + 2` above hosted views (`win.z + 1`), completely eliminating stacking context traps that prevented corner clicks. Attached pointer drag/resize handlers to `window` on interaction to prevent event drop during rapid cursor movements.
  - **Dynamic Sessions Window Stacking & Alignment**: Removed hardcoded `z-index: 50 !important` and replaced `inset: auto` with explicit bounds on `#sidebar`, ensuring conversations embed directly into the draggable `#desktopWin-sessions` window shell. Hid the redundant internal drawer header (`#sidebarDrawerHeader`), leaving a single unified window titlebar with smooth dragging and corner resizing.
  - **Window Clarity & Sharp Text Rendering**: Removed `backdrop-filter: blur(10px)` from `.desktop-window` shell overlay, resolving blur artifacts that softened text and UI elements across all floating windows.

- CARD-206 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-206):
  - **Online ACE Proposal Deduplication & Approval Filter**: Hardened `ace_online.py` and `agent_kernel.py` so standard HITL `approval_required:` tool execution pauses are never misclassified as tool execution errors, completely eliminating runaway and duplicate draft skill proposals during agent execution loops (`[REQ-HOMELAB-005]`).
  - **OpenTofu Compiler Diagnostic Extraction**: Added `extract_hcl_diagnostics` to `opentofu_tools.py` parsing both structured JSON and human-readable CLI compiler errors (`tofu validate` and `tofu plan`) into actionable `{file, line, summary, detail, severity}` records, empowering the Homelab Engineer to self-correct HCL syntax errors autonomously (`[REQ-HOMELAB-004]`).
  - **Domain Topology HCL Generator & Network Isolation Invariants**: Implemented `generate_domain_topology_hcl` in `homelab_domain_recipe.py` enforcing strict safety invariants: private isolated `Internal` virtual switch (`DomainSwitch`), 10.10.10.0/24 subnet, and 3 Gen2 VMs (`DC01`, `DC02`, and `FS01`) with static memory and zero modifications or exposure to physical host network adapters (`[REQ-HOMELAB-002]`, `[REQ-HOMELAB-003]`).
  - **Multi-Agent Homelab Domain Workflow Recipe**: Defined the reusable 4-chapter relay recipe `homelab-domain-deployment` (`homelab-admin` -> `homelab-architect` -> `homelab-engineer` -> `homelab-admin`) with strict per-phase success criteria (`[REQ-HOMELAB-001]`, `[REQ-HOMELAB-006]`).
  - **OpenTofu Hyper-V Skill Runbook**: Authored canonical `skills/opentofu-hyperv/SKILL.md` runbook codifying Hyper-V provider syntax, Gen2 VM configurations, compiler-guided self-correction protocols, and dry-run safety gates. Equipped `homelab-engineer` pack with `opentofu-hyperv` (`[REQ-HOMELAB-004]`).

- CARD-205 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Factory` - CARD-205):
  - **Multi-Window Agent Desktop Adoption**: Formally adopted the OS-style Agent Desktop environment (`#desktopStage`, `#desktopDock`, `#desktopWindowLayer`) on `qa`. Dock launchers open Chat, Wiki, Projects, Agents, Factory, Routines, Observability, Settings, Prompts, and Sessions as draggable, resizable, stackable floating windows.
  - **Factory Orchestrator Constructor Fix**: Assigned `self.store = store` in `FactoryOrchestrator.__init__`, resolving an `AttributeError` that impacted Agent Training Factory background advancement and verification battery phases.
  - **Defensive DOM Architecture Compliance**: Replaced raw `document.getElementById` lookup in `agent-desktop.js` with defensive `$` query helper from `dom.js` satisfying `REQ-DOM-001`. Added `id="${d.id}"` attributes to dock buttons for explicit DOM element targeting.
  - **Modal Layer Elevation**: Elevated all modal dialogs (`aria-modal="true"`) to `z-index: 120 !important` so modal cancellation and confirmation buttons are never intercepted by the bottom application dock.
  - **Automated Smoke Test Modernization**: Modernized Playwright E2E smoke suite (`smoke.spec.js`) to test the desktop dock launchers and multi-window interface across all studios with zero console errors.

## [0.26.0] - 2026-09-09

- CARD-204 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-204):
  - **Pure Chat Runtime Promotion**: Decoupled Goal and Self-Verify execution entirely from agent platform tool schemas. Multi-phase jobs and reflexion critic loops operate strictly as server-side runtimes triggered by Chat Studio toggles (`goalMode`, `selfVerify`).
  - **Retired Planning & Verification from Platform Skills**: Removed `planning` ("Goal Planning Engine") and `verification` ("Logic Verification (Critic)") from `PLATFORM_SKILL_TOOLS`, `PLATFORM_SKILL_METADATA`, and `BUILTIN_TOOL_GROUPS`. Platform skills in Agent Studio Box 1 are strictly the 5 active tool suites (`wiki`, `coordination`, `proposals`, `worker`, `sandbox`).
  - **Pruned Skill Seeds**: Removed `planning` and `verification` from `BUNDLED_PACK_IDS` and deleted their bundled runbooks from `src/infrastructure/skills/seeds/`. Added both to `BLED_AGENT_SKILL_IDS` to ensure automatic pruning from `$DATA_DIR/skills/`.
  - **Prompt Token Savings**: Removed dead tool schemas (`formulate_plan`, `get_active_plan`, `append_plan_step`, `mark_plan_step_completed`, `assert_json_schema`, `validate_metric_bounds`) from agent turn payloads.

- CARD-203 Done (`AutoReiv.Skills`, `AutoReiv.Packs`, `AutoReiv.Data` - CARD-203):
  - **Zero Skill Bleed on Inbound Pack Import**: Removed `_copy_skills_in` from `AgentPackService._import_folder`. Agent pack skills stay strictly isolated under `packs/<agent_id>/skills/` and are never copied into `$DATA_DIR/skills/`.
  - **Pack-Aware Skill Export**: Updated `_copy_skills_out` to read from the agent's dedicated `packs/<agent_id>/skills/` folder first, preventing false dependencies on the platform skills directory.
  - **Platform Skills Isolation**: Hardened `forge.js` `loadPlatformSkills()` to render exclusively the verified `platform_skills` from `/api/skills/catalog`, eliminating fallback polling of `$DATA_DIR/skills/`.
  - **Automated Data Pruning in Resolver**: Added `prune_bled_platform_skills` and `prune_orphan_databases` to `bootstrap_data_dir` to automatically remove historical bled agent skills from `$DATA_DIR/skills/` and unlink 0-byte orphan state/storage database files.
  - **Purged Retired Personas**: Deleted retired persona directories (`coder/`, `critic/`, `inspector/`, `sandbox_runner/`) from `platform-packs/` and cleaned obsolete `fleet.json` and `shared_skills/` discovery logic from `agents.py` and `user_catalog.py`.

## [0.25.0] - 2026-09-09

- CARD-202 Done (`AutoReiv.Web`, `AutoReiv.UI` - CARD-202):
  - **Flat Alphabetized Agent Studio Picker**: Removed `<optgroup>` categorizations ("Primary Specialists" and "Internal / Fleet Workers") from Agent Studio (`#forgeAgentSelect`). All agents are rendered in a single, clean list sorted alphabetically from A to Z.
  - **Simplified Platform vs. Custom Tagging**: Options in the Agent Studio dropdown display only `${name} (Platform)` (for built-in and platform agents) or `${name} (Custom)`, eliminating `[fleet]` and `(Internal)` badge clutter.

- CARD-201 Done (`AutoReiv.Web`, `AutoReiv.Skills`, `AutoReiv.Fleet` - CARD-201):
  - **Strict Platform Primitives in Box 1**: Locked `/api/skills/catalog` `platform_skills` strictly to the 7 core platform primitives (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`), preventing user skills or domain runbooks from ever polluting Box 1.
  - **Platform Skills Leakage Guard in Box 2**: Hardened `AgentPackManifest.derive_compat_lists`, `AgentPackService`, and `_pack_skills_payload` so platform capability IDs (`wiki`, `coordination`) ticked in `allowed_skill` are never synthesized into pack skills or rendered in Box 2 (**Agent Pack Skills & Tools**).
  - **Permanent Platform Skills (Zero Dynamic Filtering)**: Eliminated `pack_owned` filtering in `/api/skills/catalog` and `packOwnedIds` filtering in `forge.js`. All 7 core platform skill primitives are permanently visible in Box 1 (**Platform Skills & Tools**) for every agent.
  - **Strict Two-Box UI**: Removed `#forgeFleetBox` entirely from Agent Studio (`index.html` and `forge.js`). Restored the clean two-tier layout: Box 1 (Platform Skills & Tools) and Box 2 (Agent Pack Skills & Tools).
  - **1:1 Agent to Agent Pack on Disk**: Flattened the nested `platform-packs/homelab/` suite into 5 standard, top-level 1:1 agent pack folders: `homelab/`, `homelab-architect/`, `homelab-engineer/`, `homelab-admin/`, and `homelab-janitor/`. Removed `fleet.json`, `shared_skills/`, and nested `agents/` directories.
  - **Standard Platform Levers**: Homelab coordinator and architect agents leverage standard platform `wiki` tools (`wiki_note_read`, `wiki_note_search`, `wiki_note_create`) and platform `coordination` tools (`delegate_to_fleet_agent`, `lookup_agents`, `handoff_to_agent`), eliminating custom duplicate tools.
  - **Automated Platform Pack Seeding & Sync**: Updated `ALL_PLATFORM_PACK_IDS` and `install_platform_agent_packs` in `platform_packs.py` to automatically seed and synchronize all 5 homelab agents directly into the registry alongside platform core agents.

- CARD-200 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-200):
  - **Inline Skill Runbook Editor Placement**: Updated Agent Studio so clicking "Edit" mounts `#studioRunbookEditor` directly adjacent to the clicked skill row rather than rendering below remote MCP servers and credential cards.
  - **Platform Primitive Seed Runbooks**: Authored canonical Matt Pocock 5-section seed runbooks for `sandbox`, `coordination`, `worker`, `planning`, and `verification` in `src/infrastructure/skills/seeds/` and registered them in `BUNDLED_PACK_IDS`.
  - **Multi-Source Catalog Resolution**: Enhanced `UserSkillCatalog.resolve_pack_scoped_skill_md` to seamlessly resolve platform seeds, fleet shared skills (`shared_skills/`), and nested fleet agents.
  - **Accurate Not-Found Error Reporting**: Fixed `get_user_pack` endpoint so unarchived missing packs report `Pack '<id>' not found.` instead of misleading `Archived pack` text.

- CARD-199 Done (`AutoReiv.Fleet`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-199):
  - **Platform Wiki Skill Restoration & Visibility**: Fixed metadata conflict in `homelab-architect` and hardened the backend catalog endpoint so "Wiki & Knowledge Vault" (`wiki`) is consistently visible and functional in the Platform Skills & Tools container (`[REQ-FLEET-010]`).
  - **Unpolluted Core Platform Skills & Tools**: Removed domain-specific homelab infrastructure tools (`manage-opentofu-hyperv`, `lookup-network-spec`, `lookup-host-spec`) from `PLATFORM_SKILL_TOOLS`, keeping AutoReiv platform core strictly isolated (`[REQ-FLEET-011]`).
  - **Consolidated Multi-Agent Fleet Suite Layout**: Unified the 5 homelab specialist packs and their 3 shared skills under a canonical fleet suite format (`platform-packs/homelab/`) with `fleet.json`, `shared_skills/`, and `agents/` (`[REQ-FLEET-012]`).
  - **Agent Studio Three-Tier Skill Architecture**: Introduced `#forgeFleetBox` ("Fleet Shared Skills & Tools") between Platform Skills and Agent Pack Skills in Agent Studio, displaying fleet-wide shared runbooks and tools with batch select/clear actions (`[REQ-FLEET-013]`).
  - **Contextual Fleet Container Visibility**: Configured `#forgeFleetBox` to automatically appear when inspecting an agent belonging to a fleet and gracefully hide for standalone agents (`[REQ-FLEET-014]`).
  - **Consolidated Fleet Suite Single-Door Import & Export**: Updated `AgentPackService` to detect fleet manifests and seamlessly import and export multi-agent suites and their shared runbooks in one unified operation (`[REQ-FLEET-015]`).
  - **Redundant Wiki Toggle Deprecation**: Removed standalone `[x] Allow Wiki Access` toggle in Agent Studio Card 3 (`#forgeAllowWikiAccessCheckbox`), establishing the Platform Skills & Tools checkboxes as the single source of truth for agent Wiki grants.

## [0.24.0] - 2026-09-09

- CARD-196 Done (`AutoReiv.System`, `AutoReiv.Web`, `AutoReiv.SettingsStudio` - CARD-196):
  - **Installed Version & Runtime Environment Inspection**: Added dynamic version resolution, git commit hash, active branch name, and runtime deployment mode detection (`Git Clone`, `Docker Container`, `Systemd Service`, `Windows Service`, `Standalone`) surfaced in Settings Studio (`[REQ-UPD-001]`).
  - **Configurable Upstream Repository & Tracked Branch**: Implemented SQLite persistence and REST API endpoints (`GET/PUT /api/system/updates/config`) to allow operators to track private forks or mirrors (`[REQ-UPD-002]`).
  - **Automated Upstream Update Check & Changelog Preview**: Created `check_for_updates` endpoint querying upstream GitHub REST API or git remotes with commit distance comparison, release notes, and status indicators (`[REQ-UPD-003]`).
  - **Safe In-App Update Apply with Database Snapshotting**: Built one-click update apply with pre-flight dirty tree guard (`git status --porcelain`), timestamped SQLite backup (`autoreiv.db.bak-<timestamp>`), and fast-forward pull (`git pull --ff-only`) (`[REQ-UPD-004]`).
  - **Non-Git Deployment Guidance and Guardrails**: Added copyable upgrade commands (`docker compose pull && docker compose up -d`) for containerized deployments and abort protections on merge conflicts (`[REQ-UPD-005]`).

- CARD-198 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-198):
  - **Agent Visibility & Fleet Grouping**: Added `visibility` (`"public"` vs `"internal"`) and `fleet` metadata to `AgentProfile` and `AgentPackManifest`. Chat Studio filters out internal specialist workers while Agent Studio groups them under dedicated fleet sections (`[REQ-FLEET-001]`).
  - **Monolithic Hyper-V Deprecation**: Decoupled the legacy monolithic hyperv agent in favor of modular fleet capabilities and exempted it from chat selectors (`[REQ-FLEET-002]`).
  - **Enterprise IT Homelab Documentation Framework**: Populated standard IT documentation hierarchy (`00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`, `templates`) strictly under `notes/homelab/` with zero impact to the existing Wiki engine (`[REQ-FLEET-003]`).
  - **Homelab Fleet Roles & Starter Profiles**: Established starter profiles and platform packs for 5 homelab roles (`homelab` Coordinator, `homelab-architect`, `homelab-engineer`, `homelab-admin`, `homelab-janitor`) adhering to the 6-section system prompt blueprint (`[REQ-FLEET-004]`).
  - **Scoped Domain Lookup & Delegation Protocol**: Implemented `lookup_homelab_docs` and `delegate_to_fleet_agent` in `fleet_coordinator.py`, allowing the lead coordinator to inject note context and delegate directives to internal specialists (`[REQ-FLEET-005]`).
  - **OpenTofu Hyper-V Capability & Safe Tool Execution**: Created `manage_opentofu_hyperv` tool supporting plan, apply, destroy, validate, inspect_host, and get_vm_status with safe dry-run simulation mode (`[REQ-FLEET-006]`).
  - **Homelab Fleet Skills & Runbooks**: Authored runbook skills (`lookup-network-spec`, `lookup-host-spec`, `manage-opentofu-hyperv`) adhering strictly to Matt Pocock's 5-section layout and YAML frontmatter (`[REQ-FLEET-007]`).
  - **8-Stage Training Factory Dogfooding**: Programmatically executed AutoReiv's 8-stage Training Factory pipeline on `homelab-engineer`, verifying duration tracking, self-healing loop, and deliverable quality gates end-to-end (`[REQ-FLEET-008]`).

- CARD-197 Done (`AutoReiv.Agents`, `AutoReiv.Factory`, `AutoReiv.Web`, `AutoReiv.Orchestration` - CARD-197):
  - **Socratic Agent Pack Creation Directive**: Upgraded `build-agent-pack` skill and prompt directives with Socratic discovery, asking 3-4 targeted questions (specialization, host environment, safety/approval boundaries, tools needed) and instilling the 6-section system prompt architectural blueprint (`[IDENTITY & ROLE]`, `[DOMAIN BOUNDARIES & REFUSALS]`, `[EXECUTION PROTOCOL]`, `[SAFETY & APPROVALS]`, `[TOOL USAGE RULES]`, `[OUTPUT FORMAT]`) (`[REQ-FACT-046]`).
  - **Specialist Agent Quick-Scaffold Modal**: Added `#forgeNewAgentModal` with manual inputs for ID, display name, role, description, purpose slot, and safety requirements in Factory and Agent Studios, enabling rapid agent definition without conversational overhead (`[REQ-FACT-047]`).
  - **Post-Creation Agent Training Handoff Card**: Implemented an immediate post-creation card in Chat Studio (`[ Γëí╞Æ├£├ç Launch Training in Factory ]` and `[ ╬ô├£├ûΓê⌐Γòò├à Open in Studio ]`) enabling seamless one-click routing to Factory Studio pre-scoped with the newly created agent (`[REQ-FACT-048]`).
  - **8-Stage Factory Prompt Registry Refinement**: Upgraded default system prompts across all 8 pipeline stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) with agentic constraints, few-shot schema enforcement, and explicit context tokens (`[REQ-FACT-049]`).
  - **Self-Healing Verification Loop**: Added automatic repair edge (`retry_author`) and execution traceback forwarding from Verify to Author phase, enabling automatic self-healing (up to 2 attempts) before failing a training job (`[REQ-FACT-050]`).
  - **Per-Phase Execution Duration Tracking**: Recorded `duration_ms` on phase packets and rendered duration badges on visual flowchart stepper nodes in Factory Studio (`[REQ-FACT-051]`).
  - **Progressive Disclosure Runbook Standard**: Enforced 5-section progressive disclosure runbook layout (`## Overview`, `## Tools`, `## Order`, `## Pitfalls`, `## Done-when`) with YAML frontmatter in synthesized `SKILL.md` runbooks while preserving backward compatibility (`[REQ-FACT-052]`).
  - **Standardized Tool Return Envelope & Google-Style Docstrings**: Standardized synthesized tools to include Google-style docstrings (`Args:`, `Returns:`, `Raises:`) and structured dictionary return envelopes (`{"status": "success" | "error", "data": ..., "error": ...}`) (`[REQ-FACT-053]`).
  - **Tool Name Collision Guard in Promotion**: Added callable name inspection in promote phase and REST API to prevent duplicate callable names and cross-pack tool name collisions, supporting `allow_overwrite` flag for intentional updates (`[REQ-FACT-054]`).
  - **Tabbed HITL Promotion Deliverable Inspector**: Built tabbed deliverable inspection modal (`#factoryDeliverableModal`) with tabs for Runbook preview, Python tool code, and manifest diff (`pack.json`) for operator pre-promotion verification (`[REQ-FACT-055]`).
  - **Comprehensive Automated Verification**: All 1,048 Python backend tests and 284 frontend unit tests passing cleanly with zero lint errors.

## [0.23.0] - 2026-09-08

- CARD-195 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration` - CARD-195):
  - **Dedicated Agent Training Factory Studio**: Elevated the Agent Training Factory into a first-class, top-level Studio workspace (`#view-factory` / `#factoryStudio`) accessible via the navigation bar (`#navFactory`) and desktop app rail (`#railBtnFactory`).
  - **Single Hub Agent Context Dropdown**: Integrated `<select id="factoryAgentSelect">` directly in the Factory Studio header, dynamically populated from `/api/agents` with `All Agents (Platform View)` and all loaded specialist agents, strictly filtering out internal system agents (`agent_builder`, `agent-builder`) (`[REQ-FACT-040]`).
  - **Agent-Scoped Telemetry & Pre-Scoped Launcher**: Selecting an agent automatically filters historical and active runs, updates status filter counters and active run badges, filters the capability backlog, and turns the primary launch action into `[ Γëí╞Æ├£├ç Train <agent_name> ]` pre-scoped with target ID and starter objectives (`[REQ-FACT-041]`).
  - **Retirement of Agent Studio Training Buttons**: Removed `[Train in Lab]` (`#forgeTrainAgentBtn`) and `[Lab Monitor]` (`#forgeLabMonitorBtn`) from Agent Studio (`#view-forge`), consolidating all training lifecycle, monitoring, and HITL approvals exclusively within Factory Studio (`[REQ-FACT-042]`).
  - **Single-Pick Target Lock & Live Pack Verification in Training Launcher**: Streamlined `#trainAgentHandshakeModal` by removing redundant `<select id="trainAgentTargetSelect">` and `#trainAgentNameGroup`. The launcher directly locks to the selected agent from `#factoryAgentSelect`, rendering an on-disk inspection banner (`Target: <Agent>` with `packs/<agent_id>/`, existing skill count, and registered tool count) to guarantee training augments the target pack without duplicate definitions. In Platform View (`All Agents`), attempting to launch training prompts the operator to pick an agent first (`[REQ-FACT-043]`).
  - **Conversational New Agent Creator in Factory Studio**: Added `[ + New Agent ]` button (`#factoryNewAgentBtn`) directly in the Factory Studio top bar, which smoothly transitions the operator to Chat Studio to converse with AutoReiv to define the new agent's brief, instructions, identity, and tone prior to any capability training (`[REQ-FACT-044]`).
  - **Factory Studio Capability Gap Backlog Consolidation**: Relocated the "Needs Training" capability gap backlog (`#agentTrainingBacklogCard`) from Agent Studio into Factory Studio's Runs & Monitor view, dynamically rendering queued gaps for the selected agent (or all pending gaps in Platform View) with one-click training launch (`[REQ-FACT-045]`).
  - **Pipeline & Phase Prompts Sub-View**: Built visual 8-stage interactive flowchart canvas and Phase Prompt Inspector with read-only runtime context variable tokens (click-to-insert `{{seed_intent}}`, `{{objectives}}`, etc.), live prompt editing, platform-level SQLite persistence via REST API, and built-in default resetting.
  - **Training Runs & Live Monitor Sub-View**: Implemented a responsive two-pane layout with search filtering, status tabs (All, In Progress, Needs Review, Completed, Failed), an 8-stage visual progress stepper, HITL human-in-the-loop deployment gate with approved tools promotion, artifact preview modal triggers, and streaming packet activity feed with copy-to-clipboard.
  - **Mobile & Desktop Responsive Design**: Designed with mobile-first breakpoint adaptations, including an intuitive back-to-runs navigation button (`#factoryMobileBackToRunsBtn`) for small screens and sticky controls.
  - **Full Automated Verification & Zero Quality Gaps**: Added and verified comprehensive test suites in `tests/unit/frontend/factory_studio.test.js`, `tests/unit/frontend/train_agent_handshake.test.js`, and `tests/unit/frontend/auto_train_backlog.test.js` (276 frontend tests passing 100%), full Python test suites (107 tests passing 100%), zero eslint errors, zero ruff errors, and full RTM validation for `[REQ-FACT-034]` through `[REQ-FACT-045]`.

- CARD-175 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.HITL` - CARD-175):
  - **Agent Training Factory Instruction Registry & Dynamic Resolution**: Implemented backend system prompt registry and runtime customization for all 8 training phases (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`).
  - **SQLite Prompt Persistence & REST API**: Created `src/application/agent_training_factory/prompt_registry.py` managing `factory_phase_instructions` table in SQLite, and REST endpoints `GET`, `PUT`, `DELETE` at `/api/agent_training_factory/phases/instructions` and `/api/agent_training_factory/phases/{phase_id}/instructions`.
  - **Dynamic Phase Runner Integration**: Updated factory phase runners (`intent_distill.py`, `ground.py`, `blueprint.py`, `author.py`, `optimize.py`) to query dynamic system prompts via `get_phase_system_prompt(phase_id, db_path)`.
  - **Drawer Streamlining & Studio Path**: Kept the Lab Monitor drawer focused strictly on real-time activity and HITL deployment, delegating the dedicated visual prompt inspector and flowchart canvas to the dedicated Factory Studio (`CARD-195`).
  - **Agent Studio Action Hygiene**: Removed redundant `[Train New]` button from the Agent Studio header per operator direction, keeping `[Train in Lab]` on active agents.
  - **Full Automated Verification**: Added Python registry tests and REST API router tests, passing 100% with zero linter errors.

- CARD-122 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-122):
  - **Three Beats Alignment Protocol Embedded in Developer Agent**: Formally closed CARD-122, validating that the Three Beats working agreement is operationalized directly in the Developer Agent's `plan` runbook (`platform-packs/developer/skills/plan/SKILL.md`), canonical card templates (`card.template.md`), and the Master Constitution (`AGENTS.md` & `GEMINI.md`). Preserved strictly within the Developer Agent and SDLC workflow with zero external skill bloat.

- CARD-155 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-155):
  - **Open Standards Constitution & Rules Adoption**: Adopted the canonical DotAgents Protocol (`.agents/`) and `AGENTS.md` open standard for project constitutions and agentic rules under CARD-190, formally closing CARD-155. Intentionally excluded vendor-specific instruction files in favor of unified, vendor-neutral open standards for the Platform Developer Agent.

- CARD-149 Done (`AutoReiv.Agents`, `AutoReiv.Packs`, `AutoReiv.Memory` - CARD-149):
  - **Finance Specialist Agent Pack with Transaction Tracking**: Verified Personal Finance Lead user pack (`packs/finance`) with dedicated SQLite storage (`finance_storage.db`), `personal_finance` runbook, and tools for transaction ingestion (`log_transactions`), category budgeting (`manage_budget`), savings targets (`set_savings_goal`), and financial health reporting (`summarize_finances`).
  - **Isolated Storage & Automated Proof**: Confirmed 100% test pass in `tests/unit/orchestration/test_finance_agent_e2e.py` validating that personal ledger data remains fully isolated in `$DATA_DIR/packs/finance/` without modifying core `autoreiv.db`. Per operator direction, maintained as private user agent state external to git.

- CARD-193 Done (`AutoReiv.Deploy`, `AutoReiv.Docker` - CARD-193):
  - **Linux Systemd Service Uninstaller**: Created `deploy/systemd/uninstall_systemd.sh` providing clean automated uninstallation that stops and disables `autoreiv.service`, cleans up service unit files, removes `/opt/autoreiv`, and preserves `/var/lib/autoreiv` persistent storage by default unless `--purge-data` is explicitly passed.
  - **Linux Systemd Service & Installer Alignment**: Modernized `deploy/systemd/autoreiv.service` to declare single canonical `Environment="AUTOREIV_DATA_DIR=/var/lib/autoreiv"`. Updated `deploy/systemd/install_systemd.sh` to initialize directory layout and sync `templates/` into the installation tree.
  - **Windows Service Uninstaller**: Created `deploy/windows/uninstall_windows_service.ps1` with Administrator privilege checking to safely stop and unregister `AutoReivService` via NSSM with fallback to `sc.exe delete`, preserving local app data.
  - **Docker & Docker Compose Modernization**: Updated `Dockerfile` to copy `templates/` into `/app/templates/` with `autoreiv:autoreiv` ownership for Developer Agent project scaffolding, and provisioned `/data` subdirectories. Modernized `docker-compose.yml` by removing obsolete top-level `version: '3.8'` and verifying persistent volume mounts.
  - **Deploy Suite Documentation & Verification**: Added comprehensive operator manual in `deploy/README.md` and automated test suite in `tests/unit/deploy/test_deploy_suite.py`.

- CARD-189 Done (`AutoReiv.Skills`, `AutoReiv.PlatformPacks`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-189):
  - **Retirement of `propose_workflow` Tool**: Removed obsolete `propose_workflow` tool registration and handler from `AgentBuilderTools` (`agent_builder_tools.py`) and `skill_proposals.py`. Removed `propose_workflow` from Platform skill `proposals` in `schema.py`, builtin tool groups in `manifest.py`, and allowed tool lists on `AGENT_BUILDER_PROFILE` (`profiles.py`), `platform-packs/assistant/pack.json`, and `platform-packs/autoreiv/pack.json`.
  - **Unified Capability Proposals Platform Skill**: Collapsed the duplicate `recommend-capability` runbook and `proposals` tools container into a single unified Platform Skill: `proposals` ("Capability Proposals & Discovery"). Relocated the seed runbook to `src/infrastructure/skills/seeds/proposals/SKILL.md` and updated `BUNDLED_PACK_IDS`. Added automatic cleanup of legacy `recommend-capability` folders during startup seeding, eliminating the redundant empty skill row from Agent Studio and connecting the 7 proposal tools directly to their operating runbook.

- CARD-192 Done (`AutoReiv.SDLC`, `AutoReiv.Developer`, `AutoReiv.Skills` - CARD-192):
  - **Developer Agent End-to-End Verification**: Supervised the Developer agent across a complete 10-feature real-world project (`SentinelPulse`) built inside `agentic-test` with zero external wheel dependencies (`[REQ-DEVVER-001]` - `[REQ-DEVVER-012]`).
  - **Strict TDD & SOLID Verification**: Followed red-green-refactor TDD on all 10 vertical slices (`models.py`, `storage.py`, `probes.py`, `rules.py`, `alerts.py`, `remediation.py`, `circuit_breaker.py`, `diagnostics.py`, `reporter.py`, `cli.py`), achieving 35/35 passing automated tests and zero ruff lint errors (`[REQ-DEVVER-012]`).
  - **Project Scaffolding .gitignore & Git Repository Initialization**: Enhanced `ProjectsService.create_project` to automatically initialize git repository (`git init -b main`) on project scaffolding and added standard `.gitignore` to `REQUIRED_SCAFFOLD` and `templates/sdlc-project/` to prevent bytecode and cache clutter (`[REQ-DEVVER-001]`).
  - **GitTools Conventional Commit Message Alias**: Updated `GitTools.git_commit` to accept `message` as an alias for `subject`, preventing unexpected keyword argument runtime exceptions when agents invoke git commit tools (`[REQ-DEVVER-011]`).

- CARD-191 Done (`AutoReiv.Web`, `AutoReiv.Projects` - CARD-191):
  - **Active Project State & Explicit Selection**: Upgraded Projects Studio project rows with an explicit "Set as Active" action button and persistent `[Active Project]` green indicator badge (`[REQ-PROJ-010]`).
  - **Two-Pane Workspace Layout**: Expanded Projects Studio from a simple list into a full dual-pane web workspace with Directory Explorer on the left and Artifact Viewer on the right (`[REQ-PROJ-011]`).
  - **Directory Tree Navigation & Quick Filters**: Implemented collapsible folder navigation with file-type iconography and quick category filter buttons for **All**, **Cards** (`.agents/cards/`), **Specs** (`.agents/specs/`), **Steering** (`.agents/steering/`), and **ADRs** (`.agents/adr/`), plus real-time search filtering (`[REQ-PROJ-012]`).
  - **Artifact & File Viewer**: Added rich viewer rendering formatted Markdown via `marked` for cards/specs and styled monospace views for code scripts (`.py`, `.ps1`, `.json`, etc.) with file path breadcrumbs, character counts, and one-click path copying (`[REQ-PROJ-013]`).
  - **Mobile Responsive Reading & Touch Scrolling**: Clamped directory tree height on mobile (`max-h-48`) with independent touch scrolling, added mobile tree collapse/expand toggle controls, and auto-focused the reading pane with full-height scrolling on file selection (`[REQ-PROJ-011]`, `[REQ-PROJ-013]`).
  - **Jailed Project File API Endpoints**: Implemented secure `GET /api/projects/files/list` and `GET /api/projects/files/read` endpoints strictly clamped inside the active project root, filtering out `.git`, `__pycache__`, and `node_modules` (`[REQ-PROJ-014]`).

- CARD-190 Done (`AutoReiv.SDLC`, `AutoReiv.Skills` - CARD-190):
  - **DotAgents Protocol Directory Standardization**: Adopted the open DotAgents Protocol (`.agents/`) as the canonical project-level directory convention, eliminating artifact fragmentation (`[REQ-SDLC-060]`).
  - **Dual-Path SDLC Resolution**: Enhanced `CardTools` with dual-path resolution to prioritize `.agents/cards/`, `.agents/specs/`, and `.agents/steering/` while seamlessly falling back to legacy `docs/cards/` and `docs/specs/` (`[REQ-SDLC-061]`).
  - **AWS Kiro Steering & 3-File Specs**: Integrated AWS Kiro persistent steering (`product.md`, `tech.md`, `structure.md`, `roadmap.md`) and 3-file specifications (`requirements.md`, `design.md`, `tasks.md`) under `.agents/` (`[REQ-SDLC-060]`).
  - **Standardized Artifact Templates with Three Beats**: Created standard templates in `templates/sdlc-project/.agents/templates/` embedding the Three Beats operating instructions (`card.template.md`, `requirements.template.md`, `design.template.md`, `tasks.template.md`, `adr.template.md`) (`[REQ-SDLC-062]`).
  - **Constitution & SDLC Invariants**: Updated `AGENTS.md` and `GEMINI.md` to document the canonical `.agents/` directory standard and AWS Kiro framework (`[REQ-SDLC-063]`).

- CARD-181 Done (`AutoReiv.Agents`, `AutoReiv.PlatformPacks`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-181):
  - **Shipped Platform Developer Agent**: Created `platform-packs/developer` (Schema 1.1) equipped with modular `plan`, `build`, and `test` skills, automatically seeded into `$DATA_DIR/packs/developer/` on launch (`[REQ-DEV-001]`, `[REQ-DEV-003]`).
  - **Unified Multi-Language Engineering Toolset**: Equipped Developer with full engineering tools (`read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, git tools, card tools), enabling shell execution for PowerShell Pester/PSScriptAnalyzer, Python pytest/ruff, and TypeScript vitest (`[REQ-DEV-002]`).
  - **Agent Studio & Chat Presentation**: Configured Developer to display with `[Platform]` badge and enabled chat visibility (`show_in_chat=true`) (`[REQ-DEV-004]`).
  - **Retirement of SDLC Trio**: Retired `conductor`, `coding`, and `review` from active catalog and hid them from chat pickers (`[REQ-DEV-005]`).
  - **Active Selected Project Root Resolution**: Bound `SysadminTools` (`cli_exec`) to `ProjectsService.resolve_root` with optional `cwd` parameter, and injected active project context into `AgentKernel` prompt assembly, ensuring scripts and CLI commands execute directly within the active project directory selected in Projects Studio.

- CARD-188 Done (`AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings` - CARD-188):
  - **Operator Credential Secret Reveal Endpoint**: Added `GET /api/vault/credentials/{cred_id}/reveal` endpoint returning decrypted secrets for operator verification (`[REQ-VAULT-006]`).
  - **Settings Studio Credential Edit Flow**: Added row edit button pre-populating the credential modal form and supporting retention of existing encrypted secrets when updating metadata (`[REQ-VAULT-007]`).
  - **Settings Studio Sensitive Field Unmask Controls**: Added eye toggle buttons to reveal and re-mask secrets in the table and toggle password visibility in the input form (`[REQ-VAULT-008]`).
  - **Settings Studio Remote Host Edit Flow**: Added row edit button pre-populating the remote host modal form and enabling full modification of host parameters (`[REQ-REMOTE-006]`).

- CARD-160 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings` - CARD-160):
  - **Remote Host Profile Persistence**: Added SQLite `remote_hosts` repository and migrations linking remote SSH endpoints directly into the encrypted Credential Vault (`[REQ-REMOTE-001]`).
  - **REST API for Remote Host Management & Probes**: Built `/api/remote_hosts` endpoints (`GET`, `POST`, `DELETE`, and `POST /{id}/test`) supporting connection configuration and in-memory connection latency probes (`[REQ-REMOTE-002]`).
  - **Settings Studio Remote Hosts UI**: Added dedicated Remote Hosts management card and modal in Settings Studio, complete with host listings, connection handshake testing, and deletion controls (`[REQ-REMOTE-003]`).
  - **Platform Remote Execution & Inspection Tools**: Implemented `ssh_exec_command`, `ssh_read_file`, and `ssh_inspect_environment` platform tools for remote machine management without writing temporary private keys to disk (`[REQ-REMOTE-004]`).
  - **Security Guardrails & Access Control**: Enforced agent credential grant verification (`allowed_credentials`), dangerous command blocking via filter checks, and full compatibility with human-in-the-loop approval cards (`[REQ-REMOTE-005]`).

- CARD-168 Done (`AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-168):
  - **Encrypted Local Credential Storage**: Built AES-256-GCM encrypted `CredentialVault` domain engine and SQLite `credentials` repository, automatically creating and storing a 256-bit local master key under `$DATA_DIR/.vault_key` (`[REQ-VAULT-001]`).
  - **REST API for Credential Management**: Added `/api/vault/credentials` endpoints (`GET`, `POST`, `DELETE`) with strict secret masking on read (`****...abcd`) (`[REQ-VAULT-002]`).
  - **Agent Studio Credential Grants**: Added Credential Vault management UI in Settings Studio and per-agent direct credential grants list with live counter badge in Agent Studio, persisted into agent profiles and `pack.json` under `allowed_credentials` (`[REQ-VAULT-003]`).
  - **JIT Tool Execution Injection**: Extended `ScopedToolRegistry.execute()` to dynamically resolve authorized secrets for the active agent, injecting them into tool context (`_tool_context["credentials"]`) and ephemeral environment variables (`AUTOREIV_CRED_<KEY>`), popping them in a `finally` block (`[REQ-VAULT-004]`).
  - **Real-Time Secret Output Scrubbing**: Added `TranscriptScrubber` integrated into `AgentKernel` (`execute_and_scrub_tool`), scanning and masking all plaintext secret occurrences with `***MASKED***` across tool stdout/stderr, message histories, and LLM payloads (`[REQ-VAULT-005]`).

- CARD-187 Done (`AutoReiv.Chat`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-187):
  - **Human-Readable HITL Code & Command Preview**: Added `formatHitlArgs` in `src/web/static/modules/studios/chat.js` to extract primary script and command arguments (`code`, `command`, `CommandLine`, `script`, `sql`, `query`, `prompt`), rendering them as unescaped, formatted multiline text with metadata neatly listed above, replacing raw JSON stringification with escaped `\n` (`[REQ-HITL-050]`).
  - **Direct Standard Output Display**: Added `formatHitlOutput` in `chat.js` and updated `submitHitlDecision` to extract `stdout` / `stderr` directly. Formats terminal outputs and automatically pretty-prints embedded JSON strings with indentation and real line breaks, eliminating `\r\n` escaping (`[REQ-HITL-051]`).
  - **Routine API Built-in Flag Parity**: Updated `GET /api/routines` in `src/web/routers/routines.py` to check `BUILTIN_ROUTINES` and return `is_builtin: boolean` on each routine (`[REQ-ROUTINE-050]`).
  - **Universal Routine Deletion & Toast Feedback**: Rendered functional Delete button on all routine cards in `src/web/static/modules/studios/routines.js`. Added confirmation dialog checks, direct `DELETE /api/routines/{id}` invocation, grid refresh, and floating toast feedback (`showToast`) (`[REQ-ROUTINE-051]`, `[REQ-ROUTINE-053]`).
  - **Unrestricted Database Routine Deletion & Startup Seeding Guard**: Removed artificial `builtin_ids` deletion rejection from `src/infrastructure/memory/repositories/routines.py`, allowing operators to delete any routine from SQLite storage. Updated `src/web/app.py` and `scheduler.py` to seed default routines once on initial setup so deleted routines stay deleted across restarts (`[REQ-ROUTINE-052]`).

- CARD-179 Done (`AutoReiv.Chat`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web` - CARD-179):
  - **Smart Goal & Verify Checkbox Coupling**: Checking the Goal checkbox in Chat Studio now automatically pairs with and enables Self-Verify (`#verifyToggle`), ensuring multi-phase execution plans default to active critic verification while preserving operator choice to explicitly untick it (`[REQ-REF-001]`).
  - **Live Reflexion SSE Streaming**: Extended `_apply_verify_gate` in `src/web/routers/chat.py` to stream `reflexion_attempt` and `reflexion_critique` events to the chat SSE queue when running named tool checkers, giving real-time visibility into verification attempts and discrepancy critiques before final resolution (`[REQ-REF-002]`).
  - **Collapsible Reflexion Status Badges**: Unified chat stream reflexion badge rendering with `renderReflexionBadge` in `chat.js`, providing expandable/collapsible details (`.reflexion-badge-toggle` and `.reflexion-details`) for inspection of critic verdicts, checkers, and discrepancy logs (`[REQ-REF-003]`).
  - **Autonomous Mode Suggestion for Multi-Step Prompts**: Added prompt heuristic `isComplexMultiStepPrompt` in `chat.js` and suggestion chip `#chatGoalSuggestionChip` in `src/web/templates/index.html`. Prompts with numbered lists, explicit step markers, or multi-action sequential phrases offer a 1-click upgrade to Goal & Self-Verify mode (`[REQ-REF-004]`).

- CARD-180 Done (`AutoReiv.Chat`, `AutoReiv.Web`, `AutoReiv.Agents` - CARD-180):
  - **Chat Options Drawer Workflow Picker Retirement**: Removed `#workflowPicker` and its loading logic from `chat.js` and `index.html`. The chat options drawer now focuses strictly on execution modes, context budget, and loaded tools (`[REQ-CLEAN-001]`).
  - **Completed Job "Save as workflow" Retirement**: Removed `#saveAsWorkflowBtn` and modal triggers from `chat.js` and `index.html` (`[REQ-CLEAN-002]`).
  - **Chat Stream Endpoint Simplification**: Removed `workflow_id` parameter from `ChatStreamRequest` and stripped workflow recipe instantiation branching from `src/web/routers/chat.py` (`[REQ-CLEAN-003]`).
  - **Agent Studio Workflows Card Retirement**: Removed `#studioWorkflowsList` ("Workflows: Saved multi-step plans") box from `index.html` and deleted `loadAgentWorkflows`, chapter editing, saving, and deletion methods from `src/web/static/modules/studios/forge.js` (`[REQ-CLEAN-004]`).

- CARD-186 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-186):
  - **Visible Training Goal & Intent Input**: Added `#trainSeedIntentInput` field to `#trainAgentHandshakeModal` in `src/web/templates/index.html` and wired in `chat.js` and `forge.js`. If left blank, intent derives cleanly from the first objective rather than injecting generic `"Train capabilities for <slug>"` strings (`[AC-1]`).
  - **Pack-Aware Blueprinting**: Extended `BlueprintPhase` with `_load_existing_pack_info` to inspect `pack.json` when targeting existing agents. Passes existing skills, tools, and SQLite storage into the LLM context and heuristic fallback, anchoring new tools to existing skills and guarding against duplicate `{agent_id}` skills or `manage_{agent_id}` dummy dispatchers (`[AC-2]`, `[AC-3]`).
  - **Data & Analytics Tool Synthesis**: Added data query and analytics actions (`query`, `analyze`, `forecast`, `summary`, `report`) to `_synthesize_generic_python_tool` in `src/application/orchestration/tool_synthesizer.py` for agents with SQLite storage or reporting objectives (`[AC-3]`).
  - **Private Pack Skill Isolation**: Restricted `AgentPackService._import_folder()` skill copying to platform pack IDs, keeping private agent pack skills isolated inside `packs/<agent_id>/skills/` without leaking into the global `$DATA_DIR/skills/` catalog (`[AC-4]`).
  - **Pack-Scoped Runbook Editing**: Updated `UserSkillCatalog` with `resolve_pack_scoped_skill_md` allowing the runbook editor (`GET/PUT /api/skills/user-packs/{pack_id}`) to directly read and write private pack-scoped runbooks (`[AC-5]`).

- CARD-185 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Skills` - CARD-185):
  - **Deliverable Auto-Detection & Existing Pack Expansion**: Enhanced `classify_deliverable_type` in `src/application/agent_training_factory/phases/blueprint.py` to inspect target agent packs (`pack.json`, `mcp/`, `tools/`) when deliverable architecture is set to `"auto"`. Automatically maintains and expands existing MCP servers or native tools rather than guessing from scratch (`[AC-2]`).
  - **Procedural Skill Runbook Only Deliverable**: Added first-class support for `"skill"` deliverable architecture in `BlueprintPhase`, `AuthorPhase`, and `VerifyPhase`, authoring pure operational `SKILL.md` runbooks with zero tools or MCP files (`[AC-1]`).
  - **Distinct Multi-Skill Titles & Content Alignment**: Fixed title and content bleed in `AuthorPhase` where all skills previously inherited the first skill's title and dumped raw user prompt paragraphs. Each skill now generates its own unique title (e.g. `# Hyper-V Unattend Templates` vs `# Hyper-V Checkpoint Lifecycle`) and clean operational SOP objectives (`[AC-3]`, `[AC-4]`).
  - **All-Tools Verification Battery Logging**: Updated `VerifyPhase` battery logging and packet outcomes to enumerate all verified authored tools rather than truncating to the first tool (`[AC-5]`).
  - **MCP Container Rebuild Guidance**: Added container rebuild instructions (`docker build -t autoreiv-<slug>-mcp:latest packs/<slug>/mcp`) to `PromotePhase` gate messages, promote API responses, and promotion packets for operator visibility (`[AC-2]`).

- CARD-184 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Docker` - CARD-184):
  - **Remote MCP Server Pack Scaffolding**: Configured Agent Training Factory `AuthorPhase` to generate a self-contained, zero-internal-dependency MCP package under `mcp/` consisting of dual-mode stdio/HTTP `server.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `run.ps1`, `run.sh`, and `README.md` (`[REQ-MCP-SCAFF-001]`).
  - **Strict No-Loose-Tools Invariant**: Enforced strict deliverable boundary in `AuthorPhase`, `ScenarioVerifyPhase`, `VerifyPhase`, and `PromotePhase` ensuring that selecting MCP deliverable architecture strictly generates only `mcp/` artifacts and declarative skill runbooks (`skills/`), completely omitting loose `tools/` ad-hoc scripts (`[REQ-MCP-SCAFF-002]`).
  - **Docker Container Execution & Verification**: Built and ran the scaffolded Hyper-V MCP server container (`autoreiv-hyperv-mcp:latest`) on port 8080 over HTTP/SSE, successfully executing remote JSON-RPC 2.0 tool calls and discovering tools over network boundaries (`[REQ-MCP-SCAFF-003]`).
  - **Per-Agent MCP On-Demand Mount Endpoint & UI Control**: Added `POST /api/agents/{agent_id}/mcp/{server_name}/mount` and Agent Studio Inspector "Connect" control to dynamically mount running remote MCP containers into AutoReiv's `ScopedToolRegistry` without restarting the application (`[REQ-MCP-SCAFF-004]`).
  - **Pack Manifest Import & Upsert Parity**: Updated `AgentPackService._upsert_agent` to seamlessly map `mcp_servers` from `pack.json` into `AgentProfile`, ensuring custom and built-in agents automatically retain their configured MCP servers across restarts and reloads (`[REQ-MCP-SCAFF-005]`).

- CARD-183 Done (`AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Infrastructure`, `AutoReiv.Packs` - CARD-183):
  - **Per-Agent Remote MCP Server Architecture**: Scoped Model Context Protocol (MCP) servers directly to individual agent profiles and pack manifests (`pack.json`) instead of global-only settings, establishing external microservices as the primary target (`[REQ-MCP-AGENT-001]`).
  - **Remote HTTP/SSE Client Adapter**: Enhanced `MCPClientAdapter` in `src/infrastructure/mcp/client_adapter.py` with HTTP/SSE transport (`transport="sse"`), remote URL endpoints, custom authorization headers, and JSON-RPC 2.0 dispatch over HTTP without requiring local subprocesses (`[REQ-MCP-AGENT-002]`).
  - **Agent Studio MCP Inspector**: Added `#forgeMcpServersCard` in Agent Studio with live server badges, mount status indicators, tool counts, "Add Remote MCP Server" form supporting both remote SSE and stdio modes, and single-click connection probe testing (`[REQ-MCP-AGENT-003]`).
  - **Agent MCP Management Endpoints**: Created endpoints `GET /api/agents/{agent_id}/mcp`, `POST /api/agents/{agent_id}/mcp`, `DELETE /api/agents/{agent_id}/mcp/{server_name}`, and `POST /api/agents/{agent_id}/mcp/test` with SQLite state store and pack manifest synchronization (`[REQ-MCP-AGENT-003]`).

- CARD-182 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-182):
  - **Lab Monitor Retry Training Attempt**: Added `#labRetryJobBtn` ("Retry Training") to the Lab Training Monitor drawer run selector row, allowing operators to immediately re-launch a training run with all prior inputs preserved (agent name, seed intent/objectives, deliverable architecture, constraints, prerequisites, reference docs, and target location) into `#trainAgentHandshakeModal` (`[REQ-LAB-002]`).
  - **Structured Job Inputs Endpoint**: Enhanced `GET /api/agent_training_factory/jobs/{job_id}` in `src/web/routers/agent_training_factory.py` to extract and expose structured `inputs` parsed from the initial orchestrator work packet (`[REQ-LAB-003]`).
  - **Copy Activity Feed Control**: Added `#labCopyFeedBtn` to the Live Activity Feed box header in the Lab Training Monitor drawer, enabling single-click copying of the complete timestamped terminal trace to system clipboard with visual "Copied!" feedback (`[REQ-LAB-001]`).

- CARD-176 Done (`AutoReiv.Orchestration`, `AutoReiv.Infrastructure`, `AutoReiv.Web`, `AutoReiv.Packs` - CARD-176):
  - **Capability Architecture Taxonomy**: Established clear architectural separation between external service Model Context Protocol (MCP) servers, local atomic tools, and procedural skill runbooks (`[REQ-DELIV-001]`).
  - **Reusable Pack MCP Server Micro-Framework**: Implemented zero-dependency `PackMCPServer` in `src/infrastructure/mcp/pack_server.py` with standard JSON-RPC 2.0 stdio transport, `@server.tool` decorator, automatic type annotation introspection, and schema derivation (`[REQ-DELIV-002]`).
  - **Socratic Train Agent Modal Deliverable Inputs**: Added `#trainDeliverableType` selector ("Auto-detect", "Model Context Protocol", "Native Atomic Tool", "Procedural Skill Runbook Only") and collapsible `#trainAdvancedReqsAccordion` with constraints, prerequisites, and reference docs inputs in `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js` (`[REQ-DELIV-003]`).
  - **Agent Studio Badges**: Rendered distinct indigo `[MCP Server]` and slate `[Native Tool]` badges next to capability tools in `src/web/static/modules/studios/forge.js` (`[REQ-DELIV-003]`).
  - **Pack Manifest MCP Server Specification**: Extended `AgentPackManifest` in `src/application/agent_packs/schema.py` with `mcp_server: Optional[PackMCPServerConfig]` and dynamic lifecycle mounting in `src/infrastructure/mcp/client_adapter.py` (`[REQ-DELIV-004]`).
  - **Author Phase Dual Scaffolding**: Integrated deliverable classification in `BlueprintPhase` and scaffolded `mcp/server.py` in `AuthorPhase`, pairing with agentskills.io YAML frontmatter and 5-section imperative SOP skill runbooks (`[REQ-DELIV-005]`).
  - **Verification Battery MCP Subprocess Gate**: Implemented `run_mcp_battery()` in `VerificationBatteryService` and integrated into `VerifyPhase`, validating MCP servers across deterministic stdio execution, invariant safety, idempotency stress replay, and SRE Critic AST audit (`[REQ-DELIV-006]`).
  - **Windows SelectorEventLoop Compatibility**: Refactored `MCPClientAdapter` from `asyncio.create_subprocess_exec` to `subprocess.Popen` in a thread executor with an async lock, resolving the `NotImplementedError` that occurred when running inside Uvicorn on Windows, and improved `critic_notes` error formatting so exceptions never evaluate to blank (`[REQ-DELIV-006]`).
  - **Promote Phase Pack Manifest Persistence**: Saved `mcp_server` configuration to `pack.json` upon job promotion and mounted pack server into `MCPClientManager` (`[REQ-DELIV-007]`).

- CARD-174 Done (`AutoReiv.Architecture`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-174):
  - **Execution Primitives Taxonomy**: Formalized the AutoReiv agentic execution stack (CoT -> ReAct -> Plan & Execute -> Reflexion -> Multi-Agent -> Graphs).
  - **Platform vs. User Pack Boundaries**: Locked platform-owned core anchors (Assistant, Developer, AutoReiv) vs modular User Agent Packs (`$DATA_DIR/packs/`).
  - **Derived Card Scaffolding**: Spawned CARD-179 (Smart Goal & Verify Coupling), CARD-180 (Retire Chat Workflow Picker), and CARD-181 (Platform Core Developer Agent).

- CARD-169 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Architecture` - CARD-169):
  - **Nomenclature Lock**: Locked standard name as **Agent Training Factory** (ATF) and Lab Monitor across all documentation, UI, and code.
  - **Location Semantics Clarification**: Formally defined the path field as strictly an optional read-only reference codebase directory, never writing generated pack files to the project root.

## [0.22.0] - 2026-09-07

- CARD-178 Done (`AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-178):
  - **Structured Note Templates**: Added 6 canonical templates (`feynman-technique.md`, `concept-map-system-hub.md`, `dikw-pyramid-of-insight.md`, `zettelkasten-atomic.md`, `sop-runbook.md`, `adr-decision.md`) seeded in `02_Resources/_Templates/` with standard YAML frontmatter and clear step-by-step markdown sections.
  - **Template Endpoints**: Added `GET /api/wiki/templates` and `GET /api/wiki/template?slug=...` REST API endpoints to list and fetch structured template skeletons.
  - **Optional Directive System**: Kept freeform topic synthesis untouched as the default. Templates are strictly optional directives that can be requested naturally in chat or selected from the UI.
  - **New Note Modal Integration**: Added `#newNoteTemplateSelect` dropdown to `#wikiNewNoteModal` defaulting to "None (Freeform Topic Synthesis)". Selecting a template dynamically pre-fills the body textarea with the chosen skeleton.
  - **Agent Tool Support**: Added `wiki_template_list` tool and `template` parameter to `wiki_note_create` for assistants to inspect templates and apply structured frameworks when explicitly requested.

- CARD-177 Done (`AutoReiv.Wiki`, `AutoReiv.Web` - CARD-177):
  - **Collapsible Folders Default Closed**: All top-level sections (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) and nested domain/topic subfolders start collapsed on initial page load and vault reload, with toggle persistence and search-driven auto-expansion.
  - **Select-Then-Delete Navigation Flow**: Clicking a folder row selects it, updates `#activeWikiTitle` and `#activeWikiPath`, renders a Folder Overview card with item count and note links, and activates `#wikiFolderActionsGroup` with `#wikiDeleteFolderBtn` in the main header bar.
  - **Subfolder Deletion (`DELETE /api/wiki/folder`)**: Enabled deleting subfolders directly from the Wiki Studio header toolbar, folder overview card, or tree hover buttons with confirmation prompts and reactive editor cleanup.
  - **Guarded Root Invariant**: Explicitly prohibited deleting foundation root folders (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) across both the UI (displaying a `#wikiRootFolderBadge` `[Γëí╞Æ├╢├å Protected Root]`) and backend validator.

- CARD-173 Done (`AutoReiv.Wiki`, `AutoReiv.Routines`, `AutoReiv.Web`, `AutoReiv.Kernel` - CARD-173):
  - **Platform-Owned PARA-Wiki Standard**: Enforced Jacob's single PARA-Wiki vault layout (`00_Inbox/`, `01_Notes/<domain>/<topic>/`, `02_Resources/_Templates/`, `03_Archive/`) with transparent backwards-compatible path aliasing.
  - **Single-Door Inbox Filing**: All new notes land in `00_Inbox/` with a lightweight 10-field staging YAML frontmatter schema.
  - **Pre-Write Fluff Scrubber**: Added `clean_note_content()` purging conversational AI greetings, sign-offs, and filler while protecting code blocks and technical content verbatim.
  - **Tag Authority Registry**: Seeded `02_Resources/_Templates/tag-authority.md` with check-first normalization and novel tag self-registration.
  - **Wiki Curation Routine**: Autonomous scheduled background routine (`wiki-curation`) and on-demand `[╬ô├£├¡ Curate Inbox Now]` toolbar button to scrub fluff, validate metadata, check/register tags, deduplicate notes, and graduate notes to `01_Notes/`.
  - **Per-Agent Wiki Access Gate**: Added `[x] Allow Wiki Access` toggle in Agent Studio, controlling RBAC access to wiki tools in `ScopedToolRegistry`.
  - **One-Door Policy Hardening for Agent Tools**: Enforced that `wiki_note_create` and the UI new note modal strictly stage new captures into `00_Inbox/`, preventing agent bypasses into `01_Notes/` and ensuring all notes pass through staging and the autonomous curation routine.

## [0.21.0] - 2026-09-06

- CARD-171/172 Factory domain-taint cleanup (`AutoReiv.Orchestration`, `AutoReiv.Web`):
  - Restored domain-agnostic Scenario Verify, Blueprint, Author, Ground, and Optimize phases (gated Hyper-V bleed and tool fragment rules strictly to Hyper-V domains).
  - Restored promotion file selection to cleanly prefer latest Author files map.
  - Fixed `_latest_blueprint` packet lookup order in Author phase.
  - Fixed 14 ruff lint errors and 5 test regressions across unit and web test suites.

- CARD-171/172 Factory quality harden (AutoReiv.Orchestration):
  - **Checkpoint focus** bucket: Checkpoint-VM / Get-VMSnapshot / Restore / Remove only (no New-VM/switch/unattend bleed).
  - **Scenario Verify** fails on out-of-focus action branches / banned tokens (not prose-only; ignores `no oscdimg` constraint echo).
  - **Intent Distill + Ground** generic SOP rubric (purpose / steps / verify / rollback); reject vacuous brief-echo.
  - Author seed-only + re-filter for any `manage_hyperv_*` tool (narrow trains stay narrow).
  - **Negation scrub** so `no switch/NIC` / `No New-VM` do not widen focus; Scenario Verify flags out-of-scope tool files.

- CARD-172 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Frontend` - CARD-172):
  - **Intent Distill** phase (question battery -> structured answers) before Ground.
  - **Scenario Verify** phase (Blueprint capability done-whens) before Code Verify.
  - **Inner rinse** (implementation) -> Author; **outer rinse** (sop/how) -> Intent Distill + Ground with Reflexion lessons; caps `max_verify_rinses` / `max_outer_rinses`.
  - Lab Monitor 8-stage stepper + feed lines for inner/outer rinse reasons.
  - Persist `outer_rinse_count`, `max_outer_rinses`, `failure_class`, `scenario_matrix_json` on FactoryJob.

- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Verify multi-skill tool selection**: battery loads exact `tools/<primary>.py` (no sibling overwrite ImportError).
  - **Author seed-only fast path** for Hyper-V multi-skill blueprints (avoid 4x LLM hangs).
  - **Docstring path sanitize** so `D:\` in seed intent does not break generated tool AST.

- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Multi-skill Hyper-V blueprints**: Blueprint keeps VM lifecycle / networking / unattend-templates / template-maintenance skills (no single fat manage_hyperv collapse). Author emits all blueprint tools+skills. Promote merges skills/<id>/SKILL.md. Focus synthesizer builders emit real Hyper-V\ cmdlets (New-VMSwitch, Set-VMDvdDrive, Autounattend ISO, template maintenance).
  - **Synthesizer/Author hardeness**: sanitize seed docstring paths (D:/...); Author rejects LLM tool_code that fails st.parse and restores synthesizer seed.

- CARD-171 Done follow-up (`AutoReiv.Orchestration` - CARD-171):
  - **Non-Hyper-V CLI synthesizer path**: Windows services/sysadmin briefs synthesize `Get-Service` tools + matching SKILL actions (no Hyper-V `Get-VM` costume bleed).
  - **Author domain-bleed gate**: If LLM returns Hyper-V `Get-VM` tool/skill for a Windows services brief, restore synthesizer `Get-Service` seed (CARD-171).
  - **Promote/Optimize files_map preference**: Latest Author `files_map` wins over stale Optimize snapshots so rinsed Get-Service packs are not clobbered by earlier Hyper-V copies.
  - **Safe OBJECTIVES literals**: Generated tool `OBJECTIVES` lists use `json.dumps` so apostrophes in objectives no longer SyntaxError the sandbox battery.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-171):
  - **Max verify rinses**: `FactoryJob.verify_rinse_count` / `max_verify_rinses` (default 3); Verify fail increments; at max, job status `failed` with packet `critic_notes` (no infinite Author╬ô├Ñ├╢Verify loop).
  - **Fail reasons visible**: Verify packet messages include rinse progress + short reason; Lab Monitor live feed shows a `Reason:` line from `critic_notes` via `formatLabPacketFeedLines`.
  - **Path false-positive fix**: Stage-2 preflight no longer bans `"C:\`; uses real `..` traversal / sensitive Unix-path checks so `D:\Archive\...\2022.ISO` and `C:\Users\...` are allowed.
  - **Author adapts**: Latest Verify `critic_notes` injected into Author LLM user context as `LAST VERIFY FAILURE`.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Live-test grounding/author/verify fix**: Persist `objectives` on `FactoryJob` (SQLite `objectives_json`); create-job copies payload objectives; PhaseContext merges job objectives with orchestrator work-packet facts.
  - **Ground heuristics**: Match `hyperv` (no hyphen), `unattend`/`autounattend`/`iso`/`vhdx`/`template`; force cli + Hyper-V module when keywords match; rich operating manual includes full seed, objectives, and ISO paths (no costume computation/`{slug}-cli` when intent is Hyper-V).
  - **Author quality gate**: Pass objectives into LLM; reject stub `Agent for managing ... tasks` / missing Purpose+Objectives / missing unattend-ISO keywords; enrich SKILL with seed brief.
  - **Verify shallow-stub gate**: `is_shallow_stub_artifact` fails battery when skill/tool ignore seed objective keywords.
  - **Lab Monitor artifact preview**: Clickable `#labArtifactPills` open `#labArtifactPreviewModal` with packet content, pre-promote note, and expected `%LOCALAPPDATA%\AutoReiv\packs\<agent_id>\...` paths.

- CARD-171 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Agent Training Factory Orchestrator**: Replaced costume `FactoryRunner` (deterministic ToolSynthesizer walker + five persona packs) with `FactoryOrchestrator` under `src/application/agent_training_factory/` ╬ô├ç├╢ thin phase registry (Ground -> Blueprint -> Author -> Verify -> Optimize -> Promote), rinse edges (Verify fail -> Author), real gateway LLM phase context, Wiki grounding with front-matter contract v1 (`type=factory-grounding`, `agent_id`, `medium`; optional `factory_job_id`/`status`).
  - **Consistent rename**: API prefix `/api/agent_training_factory`, package/modules/UI copy use Agent Training Factory / `agent_training_factory`. Lab Monitor shows six phases (not personas). FE fetch URLs updated.
  - **Persona packs retired from Factory**: `FACTORY_PACK_IDS` emptied; former `{conductor,inspector,coder,sandbox_runner,critic}` recorded as `RETIRED_FACTORY_PERSONA_PACK_IDS` and no longer presented as Factory runtime. Assistant/AutoReiv and unrelated user packs untouched. SQLite `factory_*` tables kept (legacy names documented in code).
  - Surfaces kept: Train Agent, Lab Monitor, Needs Training backlog, auto-train, promote/HITL. Done after review and live test.

## [0.20.0] - 2026-09-05

- CARD-167 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Skills` - CARD-167):
  - **Agent Studio Skill Runbook Editor Close & Cancel Controls**: Added top-right close `x` button (`#studioRunbookCloseBtn`) and bottom `[Cancel]` button (`#studioRunbookCancelBtn`) to the skill runbook editor in Agent Studio (`#studioRunbookEditor`), wired to `hideRunbookEditor()` in `forge.js` to dismiss the editor, clear form inputs, and return the operator to the skills list [REQ-DATA-019, REQ-DATA-020].

- CARD-166 Done (`AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.Kernel` - CARD-166):
  - **Module-Qualified Host Cmdlet Tool Synthesis**: Updated `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and live agent packs to fully qualify all virtualization cmdlets (`Hyper-V\Get-VM`, `Hyper-V\New-VM`, `Hyper-V\Start-VM`, `Hyper-V\Stop-VM`, `Hyper-V\Restart-VM`, `Hyper-V\Checkpoint-VM`, `Hyper-V\Get-VMSnapshot`, `Hyper-V\Remove-VM`, `Hyper-V\Get-VMSwitch`, `Hyper-V\New-VHD`, `Hyper-V\Add-VMHardDiskDrive`) and explicitly import `Import-Module Hyper-V -ErrorAction SilentlyContinue;`, eliminating command lookup shadowing and ambient namespace collisions on the host [REQ-FACT-029, REQ-FACT-030, REQ-FACT-031].
  - **Domain-Agnostic Purpose-Grounded Environment Discovery**: Grounded `_step_discovery_probe` in `factory_runner.py` directly in the agent's purpose, intent, and objectives, dynamically detecting target execution medium (CLI, API, Database, Filesystem, Computation) and inspecting module availability and namespace isolation rules rather than returning static mocks [REQ-FACT-032].
  - **Verification Battery Command Collision Guardrail**: Enhanced the 4-stage verification battery in `verification_battery.py` and `generate_verification_test` to actively detect foreign module command collisions and unhandled subsystem interception signatures in runtime stderr, failing Stage 2 safety with actionable diagnostics before any code is approved for deployment [REQ-FACT-033].

- CARD-164 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.HITL` - CARD-164):
  - **Autonomous Background Factory Runner**: Implemented `FactoryRunner` background worker loop in `src/application/orchestration/factory_runner.py` started in `app.py` lifespan to automatically advance queued and active training jobs across all graph nodes to `hitl_deploy_gate_node` without manual intervention during sandbox testing.
  - **AutoReiv Platform Chat Anchoring**: Anchored all training jobs and HITL promotion milestone notifications to the `autoreiv` platform agent's session, guaranteeing that new or headless agents (`show_in_chat: false`) never orphan deployment approval cards.
  - **Lab Monitor Slide-Over Drawer in Agent Studio**: Added `#forgeLabMonitorBtn` with dynamic active runs badge (`#forgeLabRunsBadge`) and a full slide-over `#labMonitorDrawer` featuring an active run selector, a 5-stage visual stepper (Discovery, Blueprint, Toolmaker, Sandbox QA, Deploy Gate), a live packet activity feed, and direct **Approve & Deploy** and **Reject** buttons.
  - **Lab Monitor Drawer Visibility & Handshake Input Alignment**: Fixed DOM nesting in `index.html` by properly closing `agentBrainDrawer` tags so `#labMonitorDrawer` is an independent sibling and slides open immediately when clicked, added auto-open on job launch, added `autocomplete="off"` and input resets to prevent browser pre-filling `admin`, marked project path as optional with OS/hypervisor hints, and added dedicated `#trainAgentNameInput` for training brand new agents from scratch.
  - **Pack Tool Persistence & Registry Mount**: Fixed `promote_factory_job` to extract authored tool files and runbooks from packet payloads, persist `tools/<tool>.py` and `skills/<agent>/SKILL.md` into `$DATA_DIR/packs/<agent_id>/`, register tools under `pack_tool_names` and `allowed_tool_names` in `pack.json`, and register tool dispatch handlers directly in `ScopedToolRegistry` and `master_tool_registry` so promoted agents immediately possess callable tools.
  - **Chat Studio Lab Monitor Link**: Added a direct "View in Lab Monitor &rarr;" trigger inside the Chat Studio training launch bubble, allowing instant transition from chat to the live monitor drawer.
- CARD-165 Done (`AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Frontend` - CARD-165):
  - **Agent Studio Autonomous Training Controls**: Added "Allow Autonomous Training" checkbox (`#forgeAutoTrainCheckbox`) and "Max Auto-Train Retries" input (`#forgeMaxTrainRetriesInput`) in Agent Studio, persisted into `pack.json`, `AgentProfile`, `agent_overrides`, and `custom_agents` [REQ-FACT-023].
  - **Turn-Time Missing Capability Detection**: Implemented `CapabilityDetector` identifying missing tools or capability deficiency phrases in agent responses during operational chat turns [REQ-FACT-024].
  - **In-Flight JIT Sandbox Tool Synthesis & Live Telemetry**: Implemented `JitToolSynthesizer` evaluating drafted tools in ephemeral workspaces through the full 4-stage verification battery, bounded by per-agent max retries (1╬ô├ç├┤5, default 2), with real-time `auto_train_progress` status indicators in Chat Studio [REQ-FACT-024, REQ-FACT-025].
  - **Strict 4-Stage Battery HITL Auto-Bypass**: Automatically bypassed HITL deployment gate strictly when all 4 sandbox battery stages pass 100% cleanly, deploying tools to `packs/<agent_id>/tools/<tool>.py`, registering runbooks, and updating live tool registries [REQ-FACT-025].
  - **Seamless Turn Resumption**: Automatically resumed the paused turn upon verified tool deployment, injecting the new tool into active context so the agent completes the original user request without manual re-prompts [REQ-FACT-026].
  - **Capability Gap Backlog Queue**: Implemented SQLite table `agent_capability_gaps`, `CapabilityGapRepository`, and Agent Studio "Needs Training" backlog card (`#agentTrainingBacklogCard`) with live count badge and one-click `[╬ô├£├¡ Train in Lab]` or dismissal actions [REQ-FACT-027].
  - **Intelligent Capability Extraction & Direct Chat Queuing**: Enhanced `CapabilityDetector` with `extract_capabilities_from_turn` and `analyze_turn_with_llm` to synthesize technical capability titles, suggested tool names, and starter objectives from user intent and assistant code/commands (e.g. PowerShell `New-VM` / `New-VHD`), eliminating naive retry phrase capture ("can you try again"); streamlined Chat Studio's `[╬ô├£├¡ Train in Lab]` action to queue directly into Agent Studio's "Needs Training" backlog without interrupting modal popups, and fixed backlog list unpacking and rendering in `forge.js` [REQ-FACT-027, REQ-FACT-028].
  - **Operational PowerShell & System Tool Synthesis**: Implemented `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and integrated into `FactoryRunner` and `promote_factory_job`; dynamically generates real, runnable PowerShell scripts (`tools/<tool>.ps1`) with cmdlets (`Get-VM`, `New-VM`, `Start-VM`, `Stop-VM`, `Restart-VM`, `Checkpoint-VM`, `Remove-VM`, `New-VHD`, `Get-VMSwitch`), Python wrappers with subprocess execution, and runbooks (`SKILL.md`); tests generated tools against the 4-stage verification battery in `_step_sandbox_battery` without dummy code stubs, and mounts the live module dynamically upon promotion [REQ-FACT-009, REQ-FACT-017].
  - **Skill Runbook Feasibility & Parity Audit**: Integrated `evaluate_skill_runbook` into Stage 4 SRE Critic Audit in `VerificationBattery`, strictly validating `agentskills.io` YAML frontmatter (`name`, `description`), structured markdown headers, and 100% action schema parity against synthesized tools before certification.
  - **Instant UI Catalog Sync & Agent Pack Preservation**: Enhanced `promote_factory_job` to merge existing agent metadata, tools, and skills without overwriting custom profiles, sync `SKILL.md` to user skills root, refresh `UserSkillCatalog`, and update in-memory registries and SQLite state store; wired `forge.js` and `app.js` to automatically reload Agent Studio Cards 5 & 6 and Chat Studio dropdowns with zero manual page refreshes.

- CARD-163 Done (`AutoReiv.Data`, `AutoReiv.Infrastructure`, `AutoReiv.Deploy` - CARD-163):
  - **Database Reconciliation & Root Cleanup**: Safely merged 91 older historical sessions and 951 messages from orphaned root `autoreiv.db` into `database/autoreiv.db` (bringing totals to 161 sessions and 1,521 messages) with zero loss of modern settings or custom agents, created a pre-reconciliation zip archive under `backups/`, and cleaned up the obsolete root database and sidecar files.
  - **Enforce database/ Subfolder Invariant in Resolver**: Removed obsolete root path candidate from `_peek_setting_data_dir()` so startup never connects to or touches root SQLite files, and updated `migrate_if_needed()` to automatically reconcile and clean up any legacy root database file detected during bootstrap.
  - **Launcher & Memory Connection Alignment**: Updated Windows launcher (`run_autoreiv.ps1`) to display `database\autoreiv.db` in startup banner, and updated SQLite connection manager fallback to `./data/database/autoreiv.db`.

- CARD-162 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-162):
  - **Per-Agent Context Window Control in Agent Studio**: Moved `#forgeContextWindowInput` out of the conditionally hidden provider container into Card 4 ("LLM Provider & Model Override"), making it visible and editable for all agents regardless of whether they use the default provider or a custom provider.
  - **Unrestricted Context Window Persistence**: Updated `forge.js` agent payload builder to parse and persist typed context window tokens for any agent without clearing them when provider is set to "default".
  - **Unified 3-Tier Context Limit Resolution Cascade**: Implemented `resolve_agent_context_limit` in `context_compactor.py` and aligned `agent_kernel.py` and `chat.py` so that token budgets strictly resolve: 1) explicit per-agent setting, 2) per-agent custom model default/overrides, and 3) platform-wide `default_context_window` (e.g. 131,072) from Settings Studio, ensuring chat context meters and execution loops never prematurely truncate to 8k when using default provider.

- CARD-161 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-161):
  - **Chat Options Drawer Context Tokens & Compaction**: Added live token usage badge and progress bar (`#chatContextTokensBadge`, `#chatContextProgressBar`) inside the Chat Options Drawer displaying estimated consumed tokens vs. model context limit (e.g. `2,150 / 32,768 (7%)`), backed by `GET /api/sessions/{session_id}/context`.
  - **Manual Early Session Compaction**: Added `[Compact]` action (`#chatManualCompactBtn`) and `POST /api/sessions/{session_id}/compact` endpoint enabling users to manually compact earlier chat turns into a summary turn before hitting automated context overflow limits, refreshing the chat message stream and token budget immediately.
  - **Active Tools Summary & Inspector Modal**: Added loaded tools badge (`#chatToolsCountBadge`) and `[View Tools]` action (`#chatViewToolsBtn`) opening an interactive modal (`#chatToolsModal`) with live search to inspect all tools and descriptions authorized for the active specialist agent without leaving chat.

- CARD-159 Done (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-159):
  - **Autonomous Agent Pack Factory & Capability Loop**: Implemented the "Factory in a Lab" architecture for autonomous, overnight creation and training of specialist User Agent Packs with zero breaking changes to existing platform packs.
  - **Core Platform Factory Pack Roster**: Added 5 dedicated factory agent packs under `platform-packs/` (`conductor`, `inspector`, `coder`, `sandbox_runner`, `critic`) hidden from standard chat pickers (`show_in_chat: false`).
  - **Isolated User Pack Authoring Boundary**: Strictly isolated all generated tools, skills, and runbooks within `$DATA_DIR/packs/<agent_id>/`, never polluting platform directories.
  - **Read-Only Environment Inspection & Domain SOP Extraction**: Implemented safe, read-only discovery tools compiling ground-truth `EnvironmentManifest` metadata and domain SOP constraints.
  - **Isolated Sandbox Execution & Mocking**: Extended `EphemeralSandbox` and `SandboxedSubprocessWorker` to support directory mirroring, secret scrubbing, and command stubbing.
  - **4-Stage Automated Verification Battery**: Implemented an exhaustive verification pipeline requiring deterministic execution (Stage 1), safety & path traversal guardrails (Stage 2), idempotency & dirty-state replay (Stage 3), and SRE Critic AST security review (Stage 4).
  - **Conditional Graph Orchestrator & Anti-Bloat Gates**: Built deterministic graph walker with typed SQLite packet interchange (`WorkPacket`, `GapPacket`, `EvalPacket`, `PromotePacket`), anti-bloat `ToolConsolidationGate`, domain `AgentSplitPolicy`, and `UserPackFinalizer`.
  - **Socratic Handshake UX & Promotion UI**: Added "Train Agent" toggle chip, 3-question modal handshake in Chat Studio, and certification promotion card with human-in-the-loop deployment approval.
  - **Universal Attachment Reading Across All Agents**: Authorized `read_document_file` universally in `ScopedToolRegistry` so any agent (platform or custom pack) receiving file attachments in chat can extract and inspect document contents without requiring custom file-reading tools.
  - **End-to-End Hardening & Personal Finance Pack**: Successfully verified the Factory loop end-to-end against a real Personal Finance Agent (`finance`), authoring and certifying 4 atomic domain tools (`log_transactions`, `manage_budget`, `set_savings_goal`, `summarize_finances`) across all 4 battery stages, consolidating tool bloat, and executing live bank transaction ingestion, budgeting, and savings targets with zero database corruption.

## [0.19.0] - 2026-09-05

- CARD-116 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory`, `AutoReiv.Skills` - CARD-116):
  - **First-Class Per-Agent Cognitive Memory Brain**: Implemented private SQLite cognitive memory brain (`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`), strictly separate from domain application database (`<agent_slug>_storage.db`), providing three retrieval shelves: Shelf 1 (Permanent Pinned Directives), Shelf 2 (Rolling Episodic Session Summaries), and Shelf 3 (Atomic Semantic Facts with Porter-stemmed FTS5 BM25 search).
  - **Conflict-Resolved Compilation & Decay Physics**: Compiles facts post-turn without rescanning raw transcripts, performing automated `ADD`, `UPDATE`, `DELETE`, and `BUMP` conflict resolution with mathematical half-life temperature decay and logarithmic access frequency reinforcement.
  - **Dynamic Context Budgeting & Memory Kernel Tools**: Dynamically scales memory token injection according to active model limits (tight <=8k, standard 8k-32k, broad 32k+), and equips memory-enabled agents with `recall_agent_memory` and `memorize_fact` tools.
  - **Autonomous Consolidation Routine**: Implemented background `MemoryConsolidationRoutine` to merge near-duplicates, prune decayed facts past retention days, and compile rolling session summaries without blocking chat turns.
  - **Agent Studio Cognitive Memory Controls & Inspector Drawer**: Added dedicated Cognitive Memory configuration card in Agent Studio with retention range slider (`#forgeMemoryRetentionDays`), pinned directives editor (`#forgePinnedMemory`), and an interactive Brain Inspector drawer (`#agentBrainDrawer`) with FTS5 search, individual fact forgetting (`DELETE /api/agents/{id}/memory/facts/{fact_id}`), and complete memory purge actions.

- CARD-148 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory` - CARD-148):
  - **Per-Agent Persistent Storage in Agent Studio**: Added Persistent Storage checkbox (`#forgeStorageEnabled`) and Database Type selector (`#forgeStorageType`) to Agent Studio roster sheet, allowing specialist agents to maintain dedicated private databases.
  - **Pack-Scoped Storage & Artifact Layout**: Placed agent persistent storage databases (`<agent_slug>_storage.db`) and recipes (`workflows/`) directly inside that agent's pack directory (`$DATA_DIR/packs/<agent_id>/`), eagerly creating the database upon save so the agent's files stay together throughout their lifecycle.
  - **Dedicated Central Database Directory**: Relocated central system SQLite database from the root of `$DATA_DIR` into `$DATA_DIR/database/autoreiv.db`, with automatic on-boot migration of existing `autoreiv.db`, `-wal`, and `-shm` files.
  - **Auto-Authorized Storage Platform Tools**: Added `query_agent_database` (read queries) and `execute_agent_database` (DDL & mutations) tools in `src/application/skills/agent_storage_tools.py`, automatically authorized for storage-enabled agents during execution turns.
  - **Agent Pack SDK Storage Support**: Extended `AgentPackManifest` (`pack.json`) and `AgentPackService` to preserve storage configuration during agent pack export, import, and scaffolding.

- CARD-157 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-157):
  - **Host Command Auto-Delegation**: Updated Assistant platform pack system prompt to immediately delegate host terminal, CLI, PowerShell, and network diagnostic commands (e.g. `ipconfig`, `ping`) to the `AutoReiv` platform agent via `handoff_to_agent(target_agent='autoreiv')`.
  - **Subagent-Aware Pending Approvals**: Updated `/api/approvals/pending` and SQLite approvals repository to return pending approvals for the active session and all its child and phase execution branches (`session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%'`), ensuring subagent approval cards are not hidden when querying from the parent chat session.
  - **Chained Nested HITL Flow**: Updated `shouldResumeChatAfterHitl` and Chat Studio approval handlers to detect intermediate subagent approvals (`nested.status === 'approval_required'`), rendering the next pending approval card rather than prematurely resuming the parent assistant turn.
  - **Chat Bubble Lifecycle & Streaming Indicator Cleanup**: Removed premature `loadMessages` call at turn start to prevent wiping the user prompt bubble and flashing the empty conversation placeholder, and ensured the pulsing `Streaming...` badge is cleanly removed upon completion, stop, or HITL approval pause.

- CARD-151 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-151):
  - **Grey Out HITL Action Buttons Upon Decision**: Added immediate disabled visual feedback (`disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none`) to Human-In-The-Loop approval cards in Chat Studio and plan review milestones.
  - **Persistent Resolved Styling**: Permanently strips bright emerald/rose background colors upon approval or rejection, replacing them with neutral slate styling (`bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50`) to clearly indicate the decision is finalized and prevent accidental duplicate clicks.
  - **Pre-Resolved Card Rendering**: Added pre-resolved disabled rendering in `buildHitlCardInnerHtml` for cards rendered from history with existing decisions.

- CARD-150 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-150):
  - **Chat Session Summaries & Compact Timestamp Badges in History Drawer**: Replaced generic "Assistant Chat" list items in the past conversations drawer with a compact 2-line stacked card showing a clean 2╬ô├ç├┤5 word topic title and a shorthand timestamp (e.g. `Sep 03, 11:50 AM`).
  - **Turn-1 Automatic Title Summarization**: Automatically extracts a clean 2╬ô├ç├┤5 word topic summary from the user's initial turn prompt and persists it to the SQLite `sessions` table, replacing generic default titles.
  - **Session Title Update Endpoint**: Added `PATCH /api/sessions/{session_id}` endpoint to support programmatic session title updates and manual rename actions.
  - **Session Timestamp Formatter**: Added `formatSessionTimestamp` in pure frontend formatters converting UTC ISO timestamps to local `MMM DD, h:mm A` format.

- CARD-154 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-154):
  - **Shield Background Workers from Mobile Client Disconnects**: Prevented client-side SSE disconnects (mobile phone sleep, tab lock, or app switching) from canceling background worker execution tasks, ensuring subagent handoffs run to completion and persist final responses.
  - **Session Status Endpoint**: Added `GET /api/sessions/{session_id}/status` returning whether a session has an active background task or job in flight and the ID of the active agent.
  - **Tab Sleep Wakeup & Background Polling Recovery**: Updated `chat.js` visibility and window focus listeners to check session status on wake-up; if background work completed while away, streaming UI state automatically resets and loads all persisted messages from SQLite; if work is still underway, it polls and smoothly recovers upon completion.
  - **Preserved Explicit User Abort**: Preserved explicit user cancellation via `POST /api/chat/stream/{session_id}/abort` when the Stop button is clicked.

- CARD-156 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-156):
  - **Per-Agent LLM Endpoint Credentials & Configuration**: Added expandable endpoint controls in Agent Studio (API Base URL, API Key/Token, and Context Window tokens) revealed whenever an agent's LLM Provider is set to a specific provider.
  - **Live Model Discovery in Agent Studio**: Added `[ Γëí╞Æ├╢├ñ Refresh Models ]` button in Agent Studio that queries live models from the configured endpoint and dynamically populates the Model selector.
  - **Clean Collapsed Default**: When set to "Use Global Default", per-agent endpoint controls remain hidden and inherit settings directly from Settings Studio.
  - **Persistence & Kernel Dispatch**: Persisted `api_base_url`, `api_key`, and `context_window` in SQLite `custom_agents` and `agent_overrides` tables and updated `AgentKernel` to route agent generation through custom endpoint adapters and respect agent context token limits.

- CARD-153 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-153):
  - **Per-Agent LLM Provider and Model Configuration**: Replaced the abstract Purpose Matrix with direct LLM Provider and Model dropdowns on the Agent Studio roster sheet, defaulting to "Use Global Default".
  - **Purpose Matrix Retirement**: Completely removed the Purpose-Based Model Routing grid from Settings Studio and deprecated the `ModelPurpose` enum, simplifying model configuration into a single, direct path.
  - **Streamlined Resolution Cascade**: Simplified `AgentKernel._resolve_model()` cascade: agent override (`provider`/`model`) -> global default from Settings -> gateway fallback, eliminating matrix lookups.
  - **Agent Pack Schema & Persistence**: Added `provider` field to `AgentProfile`, `AgentCustomization`, and `AgentPackManifest` schema, persisting per-agent provider choices across restarts, exports, and imports.

## [0.18.0] - 2026-09-03

- CARD-152 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-152):
  - **Prompts Studio (Dedicated Prompt Management Space)**: Added a dedicated, first-class Prompts Studio (`#promptsStudio`, `#view-prompts`) in the main sidebar navigation with an ergonomic dual-pane management interface.
  - **Dual-Pane Prompt Workspace**: Left pane provides live search, category filter pills (All, System, Productivity, Coding, Analysis), and prompt cards with built-in badges; right pane provides a full-height template editor with tags, category selection, and instant `[ Test in Chat ]` workflow.
  - **Lightweight Chat Quick-Picker**: Streamlined the Chat Studio options drawer by replacing the large modal with a fast, non-intrusive Quick Prompt popover dropdown (`#chatPromptsQuickPicker`) for 1-tap template insertion and a direct bridge to Prompts Studio.

- CARD-147 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-147):
  - **Prompt Catalog & Saved Prompts Manager**: Delivered an end-to-end prompt template management system with instant 1-click insertion into the Chat Studio input dock.
  - **SQLite Prompt Catalog Repository & Schema**: Implemented `prompt_catalog` schema, migrations, and `PromptRepositoryMixin` with full CRUD support and curated built-in system, productivity, coding, and analysis seed templates.
  - **REST API Endpoints**: Added `GET /api/prompts`, `POST /api/prompts`, `PUT /api/prompts/{id}`, and `DELETE /api/prompts/{id}` with search and category filtering.
  - **Interactive Drawer Trigger & Modal**: Activated `#chatPromptsBtn` in `#chatOptionsDrawer` opening `#promptCatalogModal` with search, category tabs (System, Productivity, Coding, Analysis), card previews, inline create/edit form, and 1-click **Insert into Chat** action.

- CARD-145 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-145):
  - **Comprehensive Document Extraction Pipeline**: Added universal document parsing tools to extract text, tables, and structures from PDFs (`.pdf`), Excel spreadsheets (`.xlsx`, `.xls`), Word documents (`.docx`), CSVs (`.csv`), and code/text files.
  - **Specialist Agent Tool (`read_document_file`)**: Registered `read_document_file(path, max_pages, max_rows)` tool in `DocumentTools` accessible to both `assistant` and `autoreiv` platform agents.
  - **Automatic Turn-1 Previews**: Enhanced chat prompt formatting so attached small documents and spreadsheets (< 16 KB) automatically inline parsed table grids and section summaries directly into the initial turn prompt.

- CARD-144 Done (`AutoReiv.Gateway`, `AutoReiv.Web` - CARD-144):
  - **Native Multimodal Image Vision Gateway**: Extended LLM provider adapters (`OpenAIProviderAdapter`, `OllamaProviderAdapter`) and `ChatMessage` domain models to support native vision image input payloads.
  - **OpenAI & Gemini Multimodal Formatting**: Serializes attached images and local path references into OpenAI-standard `{"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}` content structures for vision-capable models (e.g. Gemini 1.5/2.0 Flash, GPT-4o).
  - **Ollama Vision Support**: Automatically extracts and packages Base64 image byte strings into Ollama's native `images: [...]` payload for local Vision-Language Models (e.g. `qwen2.5-vl`, `llava`).
  - **Zero-Migration Backward Compatibility**: Automatically detects and extracts local image paths referenced in prompt annotations without database schema alterations.

- CARD-143 Done (`AutoReiv.Web` - CARD-143):
  - **Chat Media & File Attachments Pipeline**: Introduced backend and frontend infrastructure allowing users to attach images, videos, audio, PDFs, code, and text files directly to chat sessions.
  - **Secure Ingestion & Serving Endpoints**: Built `POST /api/chat/upload` with path traversal sanitization and safe session directory sandboxing, and `GET /api/chat/attachments/{file_id}/{filename}` for streaming files with accurate MIME types.
  - **Interactive Attachment Staging Bar**: Activated `#chatAttachBtn` in the options drawer to open device file pickers; added `#chatAttachmentsPreviewList` inside the input form rendering file thumbnails, names, formatted sizes, and 1-click removal buttons before dispatch.
  - **Message Thread Previews**: Updated user message rendering in the chat thread to display media attachment grids and download pills.

- CARD-142 Done (`AutoReiv.Web` - CARD-142):
  - **Collapsible Chat Actions Drawer**: Replaced the cluttered mode checkboxes and dropdown that permanently occupied 2+ rows in the input dock with an ergonomic **`[ + ]` Action Button** (`#chatOptionsToggleBtn`) and expandable drawer (`#chatOptionsDrawer`), reclaiming 50px+ of vertical chat space on mobile.
  - **Options Popout Sheet**: Built an accessible, animated popout tray featuring runtime mode toggles (Verify, Goal Mode, Auto-run), the workflow selector, and reserved slots for upcoming media attachments and prompt catalog tools.
  - **Active Modes Indicator**: Added `#chatActiveModesIndicator` displaying real-time badges (e.g. `Γëí╞Æ├ä┬╗ Multi-phase job`, `Auto-run`, `Verify Active`) adjacent to the options trigger button so active modes are immediately visible even when the drawer is tucked away.
  - **Keyboard & Click-Away Dismissal**: Supports pressing `Escape` or tapping anywhere outside the drawer to dismiss it naturally.

- CARD-141 Done (`AutoReiv.Web` - CARD-141):
  - **Wiki Note Responsive Header**: Redesigned `#wikiNoteHeader` to stack comfortably on mobile (`flex-col sm:flex-row`), guaranteeing full-width breathing room for note titles (`#activeWikiTitle`) and relative path pills (`#activeWikiPath`) without truncating behind action controls.
  - **Collapsible YAML Frontmatter Inspector**: Replaced the bulky static metadata box with a slim 28px summary bar (`#wikiFmSummaryBar`) and quick toggle button (`#wikiToggleFmBtn`), reclaiming massive vertical space for note reading and editing.
  - **Rendered vs. Raw YAML Toggle**: Built a segmented view mode switcher inside the expanded frontmatter card, allowing users to toggle between visual pills/tags/summaries (`#fmRenderedView`) and exact monospace YAML syntax (`#fmRawView`) with a 1-click clipboard copy button (`#fmCopyRawBtn`).
  - **Backend Raw Frontmatter Extraction**: Enhanced `read_note` in `WikiStore` and `FrontmatterParser` to extract and return exact `raw_frontmatter` strings in note REST payloads.

- CARD-140 Done (`AutoReiv.Web` - CARD-140):
  - **Removed Obsolete Wiki Knowledge Graph Modal and Button**: Deleted the non-interactive Mermaid-based Graph modal (`#wikiGraphModal`) and its toolbar button (`#wikiGraphViewBtn`), uncluttering the Wiki Studio toolbar and focusing users on the interactive Force-Directed Mind Map (`#wikiMindMapModal`).

- CARD-139 Done (`AutoReiv.Web` - CARD-139):
  - **Three-Surface Information Architecture**: Replaced the cluttered 7-page navigation with 3 consolidated core surfaces: **Cockpit** (Chat Studio & Workbench), **Vault** (Wiki & Projects), and **Fleet** (Agents, Routines, Observability, Settings).
  - **Mobile Header Surface Switcher**: Added `#mobileSurfaceSwitcher` with quick pills for `#surfaceBtnCockpit`, `#surfaceBtnVault`, and `#surfaceBtnFleet`.
  - **Streamlined Conversations Drawer**: Redesigned `#sidebar` so that **+ New Conversation** and the full **Conversations List** (`#sessionList`) take 85% of the drawer, moving the 7 studios to a compact 2-column footer strip (`#sidebarNav`) while preserving all ARIA contracts.
  - **Desktop Default-Collapsed Sessions**: Configured `#sidebar` to default to collapsed on desktop, maximizing chat space while remaining instantly accessible via the session toggle button.

- CARD-138 Done (`AutoReiv.Web` - CARD-138):
  - **52px Slim Icon Rail**: Replaced permanent 280px left sidebar with a sleek, responsive desktop rail (`#appRail`) and toggleable sessions drawer (`#toggleSidebarBtn`), reclaiming over 220px of desktop horizontal space.
  - **Dual-Pane Workbench Canvas**: Built `#chatWorkbenchPane` that renders artifacts (markdown plans, code snippets, diffs) side-by-side with conversation on desktop ($> 1024\text{px}$) and as an intuitive full-height slide-out sheet on mobile ($< 1024\text{px}$).
  - **Artifact Interaction Controls**: Added tabbed preview/raw views (`#workbenchTabPreview`, `#workbenchTabRaw`), one-click clipboard copy (`#workbenchCopyBtn`), and save-to-wiki (`#workbenchSaveWikiBtn`).
  - **Message Artifact Integration**: Inlined `.workbench-msg-btn` in agent message bubbles for seamless one-click artifact inspection.

- CARD-137 Done (`AutoReiv.Web` - CARD-137):
  - **Modern Systematic UI Overhaul**: Implemented concentric corner radius system (`inner = outer - padding`), edge-touching zero-radius rules, size-following hierarchy, and focus ring offsets across AutoReiv's frontend.
  - **Unified Ergonomic Chat Input Card**: Replaced stacked two-row input bar with an integrated floating card container, reclaiming 40px+ of vertical chat space while preserving 100% of mode toggles, status pills, and action controls.
  - **Maximized Chat Workspace**: Expanded message container from `max-w-2xl` to `max-w-4xl` for spacious multi-agent reasoning, rich code blocks, and markdown tables.
  - **Refined Control Center & Drawers**: Upgraded top bar action group and applied concentric nested radii to the Journey Drawer and Debug Inspector.

- CARD-136 Done (`AutoReiv.Web`, `AutoReiv.Observability` - CARD-136):
  - **Per-Chat Debug Inspector**: Created slide-over inspector `#chatDebugPane` with button `#chatDebugToggleBtn` in Chat Studio.
  - **Diagnostic Envelopes Endpoint**: Added `GET /api/chat/sessions/{session_id}/debug` returning raw LLM message lists, tool call parameters, latency breakdown, TTFT, token usage, and system prompt.
  - **Multi-Tab Payload Viewer**: Integrated tabbed view for Messages, Tool Executions, Metrics, and System Prompt with one-click JSON clipboard copy.

- CARD-135 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Memory` - CARD-135):
  - **Execution Journey Timeline**: Created slide-out inspector `#chatJourneyDrawer` with action button `#chatShowJourneyBtn` in Chat Studio.
  - **Journey Synthesis Endpoint**: Added `GET /api/chat/sessions/{session_id}/journey` aggregating active multi-phase jobs, chronological milestones, tool execution spans with duration, and session artifacts.
  - **Interactive Milestones & Artifacts**: Visual vertical timeline with status badges (queued, running, done, failed) and key discoveries list.

- CARD-134 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-134):
  - **Control Plane Focus & Dashboard Retirement**: Cleanly retired experimental dynamic dashboard renderer and custom pack UI tabs to preserve AutoReiv's core focus as a high-performance Multi-Agent Control Plane.
  - **Stream Cancellation & Engine Delegation**: Implemented true task abort on `POST /api/chat/stream/{session_id}/abort` with `#stopBtn` UI control; delegated `dispatch_handoff` to `HandoffIsolationEngine`.
  - **Episodic Full-Text Search**: Added native SQLite FTS5 virtual table `episodic_facts_fts` with BM25 ranking and automatic triggers for memory retrieval.

- CARD-133 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-133):
  - **Declarative Dashboard Schema**: Created `AgentDashboardManifest` and `DashboardCardDefinition` models supporting `stat_group`, `action_group`, `data_table`, `markdown_editor`, and `markdown_viewer` card types.
  - **AutoReiv Platform Authoring Tools**: Added `scaffold_agent_dashboard` and `read_agent_dashboard` tools to the `build-agent-pack` skill, enabling AutoReiv to generate rich custom dashboards via natural language in Chat.
  - **Dashboard REST API**: Added `GET /api/agent-packs/dashboards`, `GET /api/agent-packs/{pack_id}/dashboard`, `POST /api/agent-packs/{pack_id}/dashboard`, and `POST /api/agent-packs/{pack_id}/action` with ScopedToolRegistry RBAC verification.
  - **Dynamic Studio Frontend Renderer**: Implemented `dynamic_studio.js` module dynamically mounting custom specialist studio tabs into the sidebar navigation, rendering interactive KPI stats, action buttons with loading spinners and toasts, data tables with row actions, and markdown editors.
  - **Gardening Specialist Starter Pack**: Seeded `agent-packs/gardening/` starter pack with `pack.json`, `SKILL.md`, `dashboard.json`, and sample `docs/garden_journal.md`.

- CARD-132 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-132):
  - **Cascading Custom Agent Cleanup**: Standardized custom agent deletion to always cleanly unbind assigned routines, delete operator overrides, and remove physical pack folders from disk.
  - **Permanent Telemetry Purge Toggle**: Added `purge_history` query option and Agent Studio confirmation modal (`#deleteAgentModal`) allowing operators to toggle permanent historical purge of session messages and telemetry records upon agent deletion.

- CARD-131 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-131):
  - **Dynamic Tone Registry**: Created `ToneDefinition` model and SQLite table `tones` seeded with 6 built-in presets (_default, technical, concise, friendly, academic, socratic_) and supporting durable custom tones.
  - **Tone REST API**: Implemented `/api/tones` endpoints for listing, creating, updating, and deleting custom tone directives with built-in protection.
  - **Agent Studio Manage Tones Modal**: Added `[ ╬ô├£├ûΓê⌐Γòò├à Manage Tones ]` button to Card 3 in Agent Studio opening a rich management modal (`#manageTonesModal`) with live list, create form, inline editing, and deletion.
  - **Dynamic System Prompt Injection**: Updated `AgentProfile.get_effective_system_prompt()` and `AgentKernel` to dynamically resolve custom tone directives from database when assembling system prompts.

- CARD-130 Done (`AutoReiv.Observability`, `AutoReiv.Web` - CARD-130):
  - **Agent Studio Lifetime Telemetry**: Bound `loadAgentTelemetry(agentId)` to parse per-agent breakdown metrics from `data.agents` with legacy ID alias resolution, fixing the 0-stat blank display.
  - **Per-Agent Estimated Cost ($)**: Added `estimated_cost_usd` to `AgentKPISummary` and added a dedicated **Est. Cost ($)** badge in Agent Studio under _Agent Telemetry & Lifetime Stats_.
  - **Observability Studio Cost & TTFT Surfacing**: Added **Est. Cost ($)** and **Avg TTFT (ms)** cards to the top KPI overview row, and added an **Est. Cost ($)** column to the _Per-Agent KPI Breakdown_ table.

## [0.17.0] - 2026-08-31

- CARD-129 Done (live-test pass) (`AutoReiv.Observability`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-129):
  - **Distributed Hierarchical Tracing**: Extended `TelemetrySpan` and SQLite `telemetry_spans` table with `trace_id` and `parent_span_id` columns, propagating trace context across turns, tool calls, and subagent handoffs.
  - **Provider & Model Attribution**: Added indexed `provider` and `model` columns on telemetry spans for side-by-side performance comparisons across Ollama, Gemini, Claude, and OpenAI.
  - **Time-To-First-Token (TTFT)**: Captured streaming latency `ttft_ms` across gateway adapters and exposed `avg_ttft_ms` in `KPIDashboardSummary`.
  - **HITL Safety Classification**: Fixed intentional Human-in-the-Loop safety pauses (`approval_required`) to record as `status="hitl_paused"` (`success=True`), eliminating false-positive error spikes.
  - **Cost & KPI Modernization**: Added real-time token cost estimation (`estimated_cost_usd`) and `hitl_paused_count` to KPI dashboard aggregations.
  - **Database Evolution**: Added automatic lightweight schema migrations in `connection.py` preserving existing SQLite databases with zero data loss.
  - **Delegation & Parameter Resilience**: Added automatic type coercion to `HandoffPacket` and tool argument aliasing across orchestration and wiki tools.

- CARD-125 Done (live-test pass) (`AutoReiv.Wiki`, `AutoReiv.Skills` - CARD-125):
  - Deterministic 27-key YAML front matter sequence serialization (`uid`, `title`, `aliases`, `document_type`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
  - Added 16-character SHA-256 `content_hash` computation on notes and tracking for `author`, `model`, `source`, `pinned`, and `access_count`.
  - Enforced strict 2-depth limit under `notes/<domain>/<topic>/<slug>.md` and standard `operations/worklog` / `operations/diagnostics` for routine and weekly logs.
  - Added atomic `wiki_note_append` tool and enhanced `wiki_note_list` with status, tag, author, pinned, and priority metadata filtering.
  - Added incoming `backlinks` calculation on note reads.
  - Authoritative Platform skill runbook in `src/infrastructure/skills/seeds/wiki/SKILL.md` and `platform-packs/assistant/skills/wiki/SKILL.md`.
  - Cleaned vault root folders: removed misplaced templates from `notes/`, relocated weekly logs to `notes/operations/worklog/`, removed legacy directories, and seeded single canonical template at `resources/templates/note_template.md`.

## [0.16.0] - 2026-08-31

- CARD-128 Done (live-test pass) (`AutoReiv.Gateway`, `AutoReiv.Settings` - CARD-128):
  - Added dedicated presets and gateway support for 10 LLM providers: **Ollama (Local)**, **LM Studio (Local)**, **vLLM (Self-Hosted)**, **Google Gemini**, **OpenAI**, **Anthropic Claude**, **OpenRouter**, **Groq Cloud**, **DeepSeek**, and **Together AI**.
  - Built `AnthropicProviderAdapter` (`src/infrastructure/gateway/anthropic_adapter.py`) supporting direct Anthropic Messages API (`/v1/messages`) with `x-api-key`, message/tool translation, and streaming SSE events.
  - Hardened `OpenAIProviderAdapter` to capture reasoning tokens (`reasoning_content` / `reasoning`), robust tool call parsing, Gemini thought signature preservation, guaranteed tool message name resolution, and standard `/v1/models` discovery.
  - Implemented automatic per-provider `HTTP 429` rate limit backoff retry loops with intelligent `retryDelay` and `Retry-After` parsing across OpenAI and Anthropic adapters.
  - Updated Settings Studio dropdown and defaults in `index.html` and `settings.js` for 1-click provider switching.

## [0.15.0] - 2026-08-31

- CARD-127 Done (live-test pass; Jacob approved layout) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-127):
  - Agent Studio top-down hierarchy: Top box is "Platform Skills & Tools" (shared capabilities: `wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sdlc-cards`, `sandbox`), bottom box is "[Agent Name] Pack Skills & Tools" (dedicated pack skills).
  - Completely removed "Also ticked" / `ungrouped_pack_tools` floating checkbox rendering. Every single tool is nested under a parent skill accordion.
  - Promoted cross-assigned / shared tools into first-class Platform skills (`coordination`, `proposals`, `worker`, etc.) with full metadata and nested tool toggles.
  - Updated `platform-packs/assistant` (dedicated `weekly-tasks`) and `platform-packs/autoreiv` (dedicated `build-agent-pack`, `platform-health`, `session-inspect`) to receive shared permissions from Platform skills without orphan tools.
- CARD-126 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-126):
  - Three homes: Platform skills/tools, Platform Agent Packs (`platform-packs/assistant` + `autoreiv`, always seed-if-missing into `$DATA_DIR/packs/`), user packs (`agent-packs/` still not scanned on startup). Dropped Python builtins for Assistant and AutoReiv; Agent Builder stays hidden. Platform skill `wiki` stub with nested wiki tools. Assistant pack owns `weekly-tasks`; AutoReiv owns `build-agent-pack` / `platform-health` / `session-inspect`. Agent Studio nests tools under skills (Platform box, then this pack). Chat still lists ticked tool schemas every turn (CARD-117/121).
- CARD-124 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-124):
  - Shipped core is Assistant + AutoReiv (Agent Builder stays a hidden builtin). Conductor, Coding, and Review are three Agent Packs in `agent-packs/` (optional import, not auto-loaded on startup). Chat shows Conductor; Coding/Review stay handoff-only. Review ticks `git_diff` / `git_status` and never write/commit. Jacob's `$DATA_DIR/packs/` imported on this card.
- CARD-125 Ready (later backlog, not this pickup) (`docs/cards/` - CARD-125):
  - Revisit Wiki schema, tools, and operating manual. Emphasis: correct deterministic YAML front matter and extensive metadata. Platform skill `wiki` stub is the Studio/packs squeeze-in; this card is the later fill. Do not implement until Jacob says build.
- CARD-119 Done (live-test pass; Jacob said look good) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Agent Packs are packaging of one specialist (nested skills/tools schema 1.1, Agent Studio Import/Export, New Agent hands off to AutoReiv in Chat). AutoReiv skills: build-agent-pack (scaffold/import/export) and recommend-capability (HITL propose when stuck). Agent Builder hidden from Chat and Agent Studio list. Show in Chat default on. Foo pack create + delete worked. Local commit only. No push.
- CARD-119 hide Agent Builder from Chat picker (`AutoReiv.Web` - CARD-119): skip `agent-builder` by id in Chat pickers; API serializes `show_in_chat=false` so a stale override cannot turn it back on. Status Done (live-test pass). Local commit only. No push.
- CARD-119 AutoReiv pack vs recommend skills; hide Agent Builder (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - AutoReiv skills are `build-agent-pack` (scaffold/import/export a named specialist) and `recommend-capability` (HITL propose_* when there is no path). `save_agent_specification` is not ticked on AutoReiv; pack write is `scaffold_agent_pack`. Agent Builder is hidden from Chat (`show_in_chat=false`) and skipped in the Agent Studio left list; API/handoff may still resolve the id. Coding / Conductor / Review stay. No named observability skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 follow-up New Agent AutoReiv handoff and nested pack skills (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - New Agent in Agent Studio switches to Chat, selects AutoReiv, starts a fresh session, and fills `I am ready to create a new agent.` (focused, not auto-sent). Nested pack schema 1.1 puts tools under skills; `allowed_skill` / `pack_tool_names` stay derived compat. AutoReiv `build-agent-pack` asks for agent details, each skill, and tools per skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 Agent Packs import/export/build (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Product landed. Agent Pack is packaging, not a fourth primitive: schema + how-to (`docs/specs/agent-packs.md`), Agent Studio Import/Export on the selected agent, `show_in_chat` (default on) persisted and filtered in Chat pickers only, pack-owned tool ids fill the Pack-owned group and come on with the pack, AutoReiv runbook `build-agent-pack` plus `export_agent_pack` / `import_agent_pack` / `scaffold_agent_pack`. Workflows ride along; transcripts, secrets, and instance facts do not. Builtins not ripped. okta-admin not reshipped. No Pack Studio. Status Done (live-test pass). Local commit only. No push.

- CARD-123 Done (live-test pass; Jacob said it feels great) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-123):
  - Workflow is a reusable plan on the agent who starts it (JSON under `$DATA_DIR/agents/<id>/workflows/`). Goal remains the one-off factory. After a Goal-planned job: Save as workflow stores the chapter list (who, skill vs handoff, done-when), not instance facts. Chat picker next to Goal and Verify is empty until the first save. Pick a recipe + new prompt instantiates a Job with those Phase rows. Agent Studio has a small owned-recipes list (edit name/order/who/skill-vs-handoff, delete with confirm). No Workflow Studio. No Agent Packs (119), no memory (116). CARD-118 marked Done (live-test pass). Pickup later is CARD-119 or CARD-116 when Jacob asks.

- CARD-118 one Agent Studio; drop Skills Studio and Forge place name (`AutoReiv.Web` - CARD-118):
  - One screen: Agent Studio. Skills Studio removed from the main nav and page. Selected agent shows identity, instructions, tone, Tools (CARD-121 checklists), and Skills runbooks (CARD-117 ticks plus open/edit of SKILL.md name, blurb, and body). Archive/confirm-delete of user runbooks moved here. Users do not hand-edit Python tool implementations. Retire Forge as a place name (h2/copy/app init). `forge.js` filename and element ids kept. Stop shipping `okta-admin` as a bundled seed: removed repo seed `src/infrastructure/skills/seeds/okta-admin` and the live data-dir copy only (`%LOCALAPPDATA%\\AutoReiv\\skills\\okta-admin`). No mass-delete of other user skills. APIs for list/read/write SKILL.md kept. No Agent Packs (119), no Workflow Studio (123), no memory (116). CARD-120 marked Done (live-test pass). Status In Review.

- CARD-120 Done (live-test pass; Jacob said ok next) (`AutoReiv.Kernel` - CARD-120):
  - Rename-only accepted. Skill in code means SKILL.md runbook. Pickup is CARD-118.

- CARD-120 rename Python tool groups so skill means runbook (`AutoReiv.Kernel` - CARD-120):
  - Tool-group modules/classes renamed `*Skill` ╬ô├Ñ├å `*Tools` (`wiki_tools.py` / `WikiTools`, `git_tools.py` / `GitTools`, `card_tools.py` / `CardTools`, sandbox `execute_code` wrappers, etc.). Folder `src/application/skills/` kept: runbook catalog (`user_catalog`, `dynamic_loader`, `skill_curator`) stays; tool-group files are no longer `*_skill.py`. Manifest clustering identifiers no longer call tool groups skills. Zero behavior change. Tool callable names, `allowed_skill`, and `skill_view` unchanged. CARD-121 marked Done (live-test pass).

- CARD-121 tools as one callable and two Studio groups (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-121):
  - Done (live-test pass). Tool = one atomic callable. Agent Studio tools card is Pack-owned (empty until Agent Packs) and Platform checkboxes. Dropped pack-master / skill-pack grouping and RBAC copy. Untick still omits schema. SKILL.md JSON stubs stay labels, not model callables. Wiki stays split (`wiki_note_read` / `wiki_note_create` / ...). Builtin allowlists unchanged. CARD-117 marked Done.

- CARD-117 skill allowlist and name+blurb prompt inject (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-117):
  - `AgentProfile.allowed_skill` persists via the agents API (and across reload). Prompt injects this agent's ticked SKILL.md names + short descriptions, not the runbook body. `skill_view` refuses unticked ids. Empty allowlist injects nothing. Platform skills default off (no silent okta-admin). Pack-owned group is empty until Agent Packs. Agent Studio checklist next to the existing tool checkboxes.

- CARD-123 walked save Goal plan as workflow, picker in Chat (`docs/cards/` - CARD-123):
  - Walked lock recorded, not built (Jacob t161-t164u). Workflow = reusable plan. Lives with the agent who starts it. Picker in Chat next to Goal and Verify, only that agent's startable recipes. Do not force workflows day one; empty picker is correct. Primary birth: Goal checkbox then Chat 'Save as workflow' after a plan/run you like. New prompt + picked workflow = new Job, same chapters, different facts. Goal is the factory, not already a workflow. Goal plans phases today; there is no save and no picker. Start in Chat; optional later edit in Agent Studio on the owner. No Workflow Studio. One object: a phase is skill or handoff. Save the chapter list, not instance facts. Pickup after CARD-117 / CARD-121 / CARD-120. Skills Studio is not the house (CARD-118). Status stays Ready. No product code.

- CARD-118 walked one Agent Studio; drop Skills Studio and okta-admin seed (`docs/cards/` - CARD-118):
  - Walked lock recorded, not built (Jacob t159-t160u). Drop Skills Studio as a standalone pack editor (not freeze-as-the-destination). A skill belongs to an agent. One screen: Agent Studio. Sidebar already says Agent Studio; app.js/h2 still say Agent Forge / Agent Forge Studio ╬ô├ç├╢ retire Forge as a place name. Checkbox grid is the Tools section, not a second product. Selected agent: instructions, tone, platform ticks (All Off except Assistant/AutoReiv), pack skill list (open/edit runbooks), pack tool ticks. Users do not hand-edit tool implementations; pack-builder / Agent Builder later owns wiring tools. Fewer pages. Later CARD-119 Agent Packs = import/export/backup of the same agent in user data on this screen, not a third pack-manager tab unless the list gets huge. Drop shipped `okta-admin` seed as a product pack (teaching example, not a specialist). Do not delete files here; seed lives `src/infrastructure/skills/seeds/okta-admin` and `$DATA_DIR/skills/okta-admin`. CARD-108 was the seed; this card owns do-not-keep-as-product-pack. Core roster still Assistant + AutoReiv (CARD-119). Status stays Ready. No product code.

- Opened backlog CARD-123 Workflow recipe (`docs/cards/` - CARD-123):
  - Alignment only. Workflow is a first-class recipe. Not a skill. Not Goal. Instantiating creates a Job with Phase rows. Lives next to jobs, not in Skills Studio. Agent Studio / later a section, not a new graph runtime. Pickup after CARD-117 / CARD-121 / CARD-120. Cheat-sheet lock: workflow (recipe) vs job (this run) vs phase (chapter). HR new-employee-onboarding example without requiring live HR. Change list stub: object is missing today; Goal checkbox is a one-off planner; every chat is a Job named Chat. Status Ready. `type:docs` `type:refactor`. No product code.

- Artifact naming scrub 2026-08-30 t157u (cards, specs, CHANGELOG, ADRs, RTM, user-visible strings):
  - Inspiration product names removed from AutoReiv artifacts unless we are literally integrating that product. CARD-116 may still name Mem0/Letta/Zep as a vendor evaluation. Research folder outside this repo may keep names. Reworded to: user data outside git; progressive disclosure (name+blurb then body); skill curator archive; purpose-based model routing; child session gets the packet only; prior art studied outside this repo. Do not point this repo at a research path for inspiration products. No product code.

- CARD-121 walked change list 2026-08-30 (`docs/cards/` - CARD-121):
  - Walked lock recorded, not built. Tool = one callable. Split read vs write where it matters (`wiki_read` / `wiki_write`). Agent Studio two groups: pack-owned ON with the agent; platform All Off except Assistant and AutoReiv. Untick omits schema (already true via `allowed_tool_names`; keep it true). Do not put stub JSON tools from SKILL.md into the model as callables. Do not hide real tools inside a skill. Drop/rename Forge pack-master grouping so it does not say skill pack. `manifest.py` clustering tools into skill packs is the wrong mix. No live Okta, no mapper, no 12-tool warning (CARD-115 already removed it). Artifacts do not name inspiration products (t157u). Status stays Ready. No product code.

- CARD-120 walked rename-only (`docs/cards/` - CARD-120):
  - Walked lock recorded, not built. Rename-only after CARD-117 and CARD-121. Python `*Skill` modules (WikiSkill, GitSkill, CardSkill, etc. under `src/application/skills/`) are tool groups, not runbooks. After rename, skill in code means `SKILL.md`. No new features, no behavior change. `wiki_read` vs `wiki_write` split belongs to CARD-121, not extra scope here. Status stays Ready. No product code.

- CARD-117 walked change list 2026-08-30 (`docs/cards/` - CARD-117):
  - Walked lock recorded, not built. Skill = one SKILL.md runbook (stop saying skill pack for that file). Agent profile skill checklist next to Forge (`allowed_skill` ids; today `AgentProfile` only has `allowed_tool_names` in `src/domain/kernel/models.py`). Pack-owned skills ON with that agent; platform skills All Off except Assistant and AutoReiv. Untick omits name+blurb and refuses `skill_view` for that id. Prompt injects ticked names+blurbs; keep `skill_view` for body; drop must-call-list-first. `user_catalog.py` already lists name+description; only Assistant/AutoReiv/Agent Builder have those tools (`profiles.py`). Okta Admin = agent, user-provisioning = skill; no live Okta. CARD-118 studio freeze; CARD-120 Python `*Skill` rename. Status stays Ready. No product code.

- CARD-117/121 controls: platform All Off except Assistant/AutoReiv; pack-owned on; untick omits context (`docs/cards/` - CARD-117):
  - t154u lock recorded, not built. Ditch RBAC as the name. Two Agent Studio checkbox groups per agent: pack-owned come ON at create/import; platform/shared (`wiki_read`, `wiki_write` separate, etc.) default All Off except builtin Assistant and AutoReiv (those keep useful platform ticks we choose). Untick MUST omit tool schema / skill name+blurb from model context. Agent directory is name + one-line purpose only. No in-flight dynamic mapper. No pixel spec. CARD-119 roster epic not duplicated. CARD-121 one-line pointer. Status stays Ready. No product code.

- CARD-119 intent: core ship Assistant+AutoReiv; specialists as packs later (`docs/cards/` - CARD-119):
  - Later-discuss only. When Agent Packs are eventually implemented, shipped core roster is two agents: Assistant and AutoReiv. Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) arrive as Agent Packs (agent + skills + tools), not more builtins. Do not rip existing builtins on this card. Foundations first (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 unrelated low-priority. Controls notes (not this card to build): two Agent Studio checkbox groups (pack-owned vs small platform group); untick omits schema; no RBAC engine; no in-flight dynamic mapper; handoff is name+blurb directory. Status stays Ready. No product code.

- Opened low-priority CARD-122 three-beats skill idea (`docs/cards/` - CARD-122):
  - Later SKILL.md runbook for an autonomous coder working with a visionary (Jacob). Documents the 2026-08-30 three-beats working agreement. Ultra low priority. Do not pick up until CARD-117/121/120 (and workflow later) are in motion or done. Not a reason to build Skills Studio features. No product code.

- CARD-116 explore Mem0 then native; pickup after refactors (`docs/specs/per-agent-memory/` - CARD-116):
  - Research still Ready. Explore both Mem0 and a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do not lock Mem0. When later executed: start with Mem0 deep research, then compare. Pickup blocked until after the other pile (orchestration / Goal / loops / graphs) and foundation refactor cards (CARD-117, CARD-121, CARD-120, CARD-118; CARD-119 later-discuss). Memory is a bolt-on after those are ironed out. Three-shelf architecture kept. Wiki / Letta product / Zep product stay out. No product code.

- CARD-116 research leaning (`docs/specs/per-agent-memory/` - CARD-116):
  - Research leaning recorded (not a locked vendor purchase). Wiki / Letta product / Zep product: no. Mem0 to evaluate for archive (shelf 3). Three-shelf per-agent brain. No product code.

- Opened backlog CARD-121 tools ground-up (`docs/cards/` - CARD-121):
  - Alignment only. Tool = one atomic callable (name + description + parameters to the model every turn if allowlisted). Not a worker, not a runbook, not a skill pack. Ground-up: current Forge pack grouping, `manifest.py` skill-pack clustering, and Python `*_skill.py` tool modules are likely off/mixed. Working agreement recorded (walk with CARD-117/120; no silent-big-bang). No product code.

- CARD-117 points at the shared working agreement and CARD-121 (`docs/cards/` - CARD-117):
  - Short "When we pick this up" pointer. CARD-121 is the sibling tools pass, not a second definition of skill. No product code.

- Expanded CARD-117 skills primitive intent (`docs/cards/` - CARD-117):
  - Ground-up revisit recorded, not implemented. Intent expanded for controls, load path, levers, and built-in vs user-added. Current Skills Studio, `$DATA_DIR/skills` packs, `list_user_skill_packs` + `skill_view`, Python `*Skill` classes, and leftover orchestration `skills: List[str]` are likely off. Two explicit per-agent lists (tools already in Agent Studio; skills list missing). Load path: inject name+blurb every turn; body on open; extra list call is off vs progressive disclosure (name+blurb then body). Skill on/off levers next to the agent, not Skills Studio. CARD-118/119/120 cross-linked. No product code.

- Opened backlog CARD-117 skills primitive = one SKILL.md runbook (`docs/cards/` - CARD-117):
  - Alignment only. Skill = one runbook (order, pitfalls, done-when), not a skill pack, not a worker. Progressive disclosure name+description first; skill index is name+blurb only. Tools on the agent allowlist still go to the model every turn. Stop using Skill Pack for the primitive. Points at CARD-114 findings and prior art studied outside this repo. No product code.

- Opened backlog CARD-118 rethink or replace Skills Studio (`docs/cards/` - CARD-118):
  - Freeze only. Jacob's original studio organized before definitions were solid. Current studio edits `$DATA_DIR/skills` SKILL.md packs. Likely drop/replace later. No big studio features until CARD-117. No product code.

- Opened backlog CARD-119 Agent Packs later discussion (`docs/cards/` - CARD-119):
  - Conceptual packaging: ship an agent with its skills and tools (e.g. Okta Admin bundle). Not a fourth primitive. Not build-now. Discuss after agent/skill/tool foundations. No product code.

- Opened backlog CARD-120 rename Python *Skill modules (`docs/cards/` - CARD-120):
  - Refactor-and-alignment later. WikiSkill, GitSkill, CardSkill, etc. are tool groups, not runbooks. Skill in code should mean a SKILL.md runbook. Foundations first. No new features. No product code.

- Opened backlog CARD-116 per-agent memory research (`docs/specs/per-agent-memory/` - CARD-116):
  - Research only. Independent first-class brain per agent (not one markdown for all, not only Chat session history). Agent Studio fact-lifetime and other levers with hard min/max. Prior art studied outside this repo. No vendor pick. No product code.

- Remove Forge 12-tool allowlist warning (`AutoReiv.Web` - CARD-115):
  - Agent Studio no longer shows the CARD-078 amber banner when 12+ tools are checked. `FORGE_ALLOWLIST_WARN_AT` and `#forgeAllowlistWarning` are removed. Save and tool mounting are unchanged. No hard cap.

- Opened CARD-114 user intent review and product alignment (`docs/specs/user-intent-review/` - CARD-114):
  - Review artifact only. Findings SSOT at `docs/specs/user-intent-review/findings.md` (35 findings, verified on `qa`). No product code.

- Skills Studio archive and confirm-delete for user packs (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-113):
  - Studio lists `$DATA_DIR/skills` user packs only. Python builtins (WikiSkill, execute_code, handoff) stay out (`[REQ-DATA-015]`).
  - Archive / Unarchive reuse CARD-112 `POST /api/skills/user-packs/{id}/archive`, unarchive, and `GET /api/skills/archived-packs`. Live list hides archived packs; Unarchive restores (`[REQ-DATA-015]` `[REQ-DATA-016]`).
  - `DELETE /api/skills/user-packs/{id}` requires `confirm=true` (400 without). Removes the jailed live dir and `_archive/<id>/` if present. Path traversal (`../`) is rejected (`[REQ-DATA-017]`).
  - Bundled seed `okta-admin` DELETE is 409 unless `confirm_seed=true`. Repo `src/infrastructure/skills/seeds/` is never deleted. UI uses `window.confirm` plus a second confirm for okta-admin (`[REQ-DATA-018]`).

- Skill curator stale/archive (`AutoReiv.Skills`, `AutoReiv.Routines` - CARD-112):
  - Unused user packs go active -> stale (30d) -> archive (90d). Archive is a directory move to `$DATA_DIR/skills/_archive/<id>/`. Live `SKILL.md` is never deleted (`[REQ-IMPROVE-013]`).
  - `okta-admin` / `BUNDLED_PACK_IDS` are never auto-archived or deleted. Repo `src/infrastructure/skills/seeds/` is untouched. Explicit confirm is required to archive a bundled pack (`[REQ-IMPROVE-014]`).
  - Unarchive is the reverse move. Dest-exists fails closed. Pack reappears in `GET /api/skills/user-packs` / Skills Studio. No `propose_skill` (`[REQ-IMPROVE-015]`).
  - Curator function + paused sibling routine `skill-curator` (`enabled=false`). CARD-111 harvest hook is off (`metadata.auto_archive=false`). Unknown last-used fails closed. Does not rewrite packs mid-chat-turn (`[REQ-IMPROVE-016]`).

- Nightly skill eval routine (`AutoReiv.Routines`, `AutoReiv.Skills` - CARD-111):
  - Seed `skill-eval-sleep` into existing `routines` / `BUILTIN_ROUTINES` targeting `agent-builder`. Same `RoutineExecutor` + `routine_runs`. No second scheduler. No `skillopt` pip (`[REQ-IMPROVE-007]` `[REQ-IMPROVE-012]`).
  - Default **paused** (`enabled=false`). When enabled, `next_run_at` is weekday 21:00 `America/New_York` (timezone-aware UTC instant). Not 02:00 local (surprise GPU load) and not 21:00 UTC (`[REQ-IMPROVE-008]`).
  - In-process job harvests failed `telemetry_spans` turns and FAILED jobs/phases from the live `$DATA_DIR` db (lookback 72h, capped). Refuses checkout `./data` when LocalAppData is live. Empty harvest is a success no-op (`[REQ-IMPROVE-009]`).
  - Replay optional and default off; honors generation slot default 1. Checker must pass to stage; missing named checker is honest skip. Stage is CARD-106 `propose_skill` draft only (`auto_commit` false). No `SKILL.md` write, no `commit_skill_pack`, no `stream_turn` child phase (`[REQ-IMPROVE-010]` `[REQ-IMPROVE-011]` `[REQ-IMPROVE-016]`).

- ACE-style online playbook notes + snapshot/rollback (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-110):
  - Failed turn / checker miss produces at most one tiny ACE delta. Generator is existing `AgentKernel`. In-process Reflector + Curator. No second kernel, LangGraph, or ACE vendor (`[REQ-IMPROVE-001]` `[REQ-IMPROVE-002]`).
  - Online path parks a CARD-106 `propose_skill` draft (`ace_delta`, snapshot id). Live `SKILL.md` is not rewritten in the turn. Python-shaped deltas stay `propose_tool` drafts with `requires human/code card`. No `src/` writes (`[REQ-IMPROVE-003]` `[REQ-IMPROVE-005]`).
  - `UserSkillCatalog` snapshots `SKILL.md` + sidecar notes under `$DATA_DIR/skills/<id>/snapshots/<utc-iso>/` before apply. Rollback restores bytes. Snapshot I/O failure skips apply (`[REQ-IMPROVE-004]`).
  - Optional append-only `PLAYBOOK_NOTES.md` / `notes.jsonl` sidecar does not modify `SKILL.md`. Promotion into the playbook is still `propose_skill`. Online path does not enqueue nightly eval (`[REQ-IMPROVE-006]` `[REQ-IMPROVE-016]`).

- Skill self-improve (`docs/specs/skill-self-improve/` - CARD-110-112): spec and Slice D cards opened. ACE-style online playbook deltas with snapshot/rollback (HITL `propose_skill` if writing SKILL.md), nightly SkillOpt-Sleep-shaped eval routine on the existing routines table (21:00 America/New_York weekdays, default paused, validation gate), skill curator stale user-pack archive (never delete bundled/okta-admin). No feature code. No push. No DB wipe.

- Windows launcher uses data dir (`AutoReiv.Deploy` - CARD-109):
  - `deploy/windows/run_autoreiv.ps1` no longer defaults `--db-path` / `--wiki-path` (or `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH`) to checkout `./data`. Default Windows boot (including `-Reload`) lets `DataDirResolver` open `%LOCALAPPDATA%\AutoReiv` for db, wiki, and skills (`[REQ-DATA-001]`, `[REQ-DATA-003]`).
  - Explicit `AUTOREIV_DB_PATH` / `-DbPath` / `--db-path` still win when they are not the checkout legacy path. Leftover checkout env from an old launcher session is stripped.

- Okta admin skill pack scaffold (`AutoReiv.Skills` - CARD-108):
  - Bundled agentskills.io pack `okta-admin` at `src/infrastructure/skills/seeds/okta-admin/SKILL.md` is copy-if-missing seeded into `$DATA_DIR/skills/okta-admin/SKILL.md` on data-dir bootstrap. Existing dest is left alone so user edits survive a second boot (`[REQ-BUILD-015]`).
  - Playbook SOP (list users, groups, conceptual MFA reset/unlock, assign app) plus JSON tool stubs. No live Okta API, no credentials, no Okta env keys, no Python Okta SDK in `src/` (`[REQ-BUILD-016]`).

- Agent Builder specialist writes approved skill packs (`AutoReiv.Agents`, `AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-107):
  - Builtin `agent-builder` Chat specialist (not Conductor). Allowlist stays under 12: lookup, propose_*, list packs, skill_view, commit_skill_pack, agent-spec tools, handoff. No execute_code, git, or card writes (`[REQ-BUILD-009]`).
  - New tools stay on existing `AgentBuilderSkill`. `commit_skill_pack` writes approved skill/tool/workflow proposals through `UserSkillCatalog.save_pack` into `$DATA_DIR/skills` (same files Skills Studio edits). Draft/rejected fail closed. Python stubs never write `src/` (`[REQ-BUILD-010]` `[REQ-BUILD-012]` `[REQ-BUILD-014]`).
  - Default Chat is one Job + one Phase + `stream_turn`. Goal mode uses the CARD-099 no-tool planner with linear research phases (survey, draft playbook, declare tools, HITL propose). Research does not write `SKILL.md` (`[REQ-BUILD-011]`).
  - Soft CARD-078 sprawl / extend-specialist warning is visible before commit and on `save_agent_specification`. Not a hard gate (`[REQ-BUILD-013]`). Approve still does not write disk; commit is the write.

- propose_skill / propose_tool / propose_workflow HITL drafts (`AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-106):
  - Tools on existing `AgentBuilderSkill` write a `proposals` row (`kind` skill|tool|workflow, `status` draft) plus a Chat HITL `pending_approvals` park (`[REQ-BUILD-001]` `[REQ-BUILD-002]` `[REQ-BUILD-003]` `[REQ-BUILD-007]`).
  - Payload is what / why / how / where, jailed under `$DATA_DIR/skills`. Missing field fails closed. No `SKILL.md` write. No Python under `src/`. Workflow is playbook SOP, not job-template YAML (`[REQ-BUILD-004]` `[REQ-BUILD-005]`).
  - Approve marks `approved` and does **not** write disk. Reject marks `rejected`. Pack commit is CARD-107. Tool drafts that look like Python builtins stay draft-only with note `requires human/code card` (`[REQ-BUILD-008]`).
  - Soft CARD-078 sprawl warning when the target allowlist would be >= 12 or a new agent is preferred over extending a specialist. Does not block the draft (`[REQ-BUILD-006]`).
  - Allowlisted on Assistant and AutoReiv (discovery). Not Coding, Review, or Conductor. `save_agent_specification` unchanged (immediate, no HITL).

- Agent Builder HITL (`docs/specs/agent-builder-hitl/` - CARD-106-108): spec and Slice C cards opened. `propose_skill` / `propose_tool` / `propose_workflow` HITL drafts on existing AgentBuilderSkill, Agent Builder specialist wired to Job/Phase + data_dir skills, Okta admin pack scaffold. No feature code. No push.

- Skills Studio UI (`AutoReiv.Web`, `AutoReiv.Skills` - CARD-105):
  - Sibling tab of Agent Studio lists user packs from `$DATA_DIR/skills` (name + description) and reads/edits `SKILL.md` on disk. Disk is the source of truth (`[REQ-DATA-012]`).
  - Opening a pack lists JSON tools parsed from that `SKILL.md`. No tool blocks yields an empty list (playbook-only packs are valid) (`[REQ-DATA-013]`).
  - Job templates are a later placeholder only. Playbook SOP is the SKILL.md body; `jobs.template_id` stays nullable (`[REQ-DATA-014]`).
  - `GET/POST /api/skills/user-packs` and `GET/PUT /api/skills/user-packs/{id}` are jailed to the skills tree. Saves match Forge (direct write, no HITL). Writes do not land in repo `.agents/skills`.

- User agentskills.io packs (`AutoReiv.Skills` - CARD-104):
  - Bootstrap scans `$DATA_DIR/skills/**/SKILL.md` via `DynamicSkillLoader.list_skill_manifests` (frontmatter name + description + path only). Python builtins still register when `skills/` is missing (`[REQ-DATA-009]`, `[REQ-DATA-010]`).
  - `skill_view` loads the SKILL.md body and JSON tool blocks on demand. Colliding user tool names are skipped; builtin Python tools win (`[REQ-DATA-011]`). Pack JSON is not executed as Python.
  - User-pack tools still go through each agent's Forge `allowed_tool_names`. `list_user_skill_packs` and `skill_view` are allowlisted on Assistant and AutoReiv only. Repo `.agents/skills` packs are not auto-mounted.

- Backup and restore of the data dir (`AutoReiv.Data` - CARD-103):
  - `DataDirBackupService` zips the resolved data dir (`autoreiv.db`, wiki, skills, and other tree files) to a timestamped archive under `$DATA_DIR/backups/` (or a user-chosen path). SQLite is snapshotted via the backup API. Checkout source, venv, and `backups/` itself are not included (`[REQ-DATA-007]`).
  - Confirmed restore (`autoreiv restore <src.zip> --yes` / Settings Restore) replaces the tree after extracting to a staging area. Cancel and missing `autoreiv.db` leave the live tree unchanged. A pre-restore zip is kept under `backups/` (`[REQ-DATA-008]`).
  - `POST /api/data-dir/backup` (zip download) and `POST /api/data-dir/restore` (multipart zip, `confirm=true`). Settings Studio Backup / Restore next to the CARD-102 data-dir panel.

- User data directory (`AutoReiv.Data` - CARD-102):
  - `DataDirResolver` resolves `AUTOREIV_DATA_DIR` env > persisted `data_dir` setting > platform default (`%LOCALAPPDATA%\AutoReiv` on Windows, `~/.autoreiv` on POSIX, `/data` in Docker) (`[REQ-DATA-001]`, `[REQ-DATA-002]`).
  - Database, wiki, and skills paths derive from the data dir unless `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` are explicit (`[REQ-DATA-003]`).
  - First boot copy-migrates live `./data/autoreiv.db` and `./data/wiki` into an empty dest. Copy, not move. Does not overwrite dest. Does not wipe source (`[REQ-DATA-004]`).
  - Wired in `create_app`, CLI `--data-dir`, `.env.example`, Docker one volume at `/data` (`[REQ-DATA-005]`, `[REQ-DATA-006]`).

- Control-plane data dir (`docs/specs/control-plane-data-dir/` - CARD-102-105): spec and Slice B cards opened. User data dir outside the checkout, backup/restore, user SKILL.md packs via DynamicSkillLoader, Skills Studio. No feature code. No push.

- propose_followup draft jobs (`AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-101):
  - `propose_followup` writes a `proposals` row kind `followup_job` status `draft` with `requested_by_job_id`, plus a queued Job (`template_id=followup_job`) and a HITL `pending_approvals` park (`[REQ-ORCH-043]`).
  - Creating the draft does not start a phase and does not call `stream_turn` / the kernel. There is no `set_goal` tool.
  - Approve marks the proposal `approved` and leaves the Job `queued`. It does **not** auto `stream_turn`. Reject marks `rejected` and cancels the job.
  - Tool is mounted on OrchestrationSkill next to `handoff_to_agent`. Allowlisted on Conductor / Assistant / AutoReiv, not Coding or Review.

- Chat Job/Phase status strip (`AutoReiv.Chat` - CARD-100):
  - Chat shows job status, current phase name, assigned agent, and react_state (THINKING / CALLING_TOOLS / PARKED / DONE / FAILED) from SSE (`[REQ-ORCH-042]`).
  - Goal badge is "Multi-phase job" (not Plan Graph). PARKED and FAILED are named in the strip.

- Bind chat Goal and Verify to persisted Job/Phase (`AutoReiv.Orchestration`, `AutoReiv.Chat`, `AutoReiv.Kernel` - CARD-099):
  - Default chat creates one Job + one Phase and runs `stream_turn` (`[REQ-ORCH-035]`).
  - Goal mode uses a no-tool `gateway.complete` planner (tools disabled; not `run_turn`), persists linear Job+Phases, and waits for HITL `goal_plan_review` before per-phase `stream_turn` (`[REQ-ORCH-039]`, `[REQ-ORCH-040]`).
  - Verify is a named checker gate; a missing checker is an honest skip and does not claim `verification_passed` (`[REQ-ORCH-041]`).
  - SSE emits `job_created` / `phase_start` / `phase_complete` plus existing `react_state` job/phase ids.

- Packet handoff via stream_turn (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-098):
  - Child handoff requires a `HandoffPacket` (goal, facts, constraints, done_when, budget). The child user message is the packet only; parent transcript is not copied (`[REQ-ORCH-036]`).
  - Child runs `stream_turn` on a new empty session with the child's full context window. No `run_turn` / nested `complete()`, no 32k CARD-094 cap on this path (`[REQ-ORCH-037]`).
  - Global Ollama generation semaphore default 1 (setting `max_concurrent_generations` range 1-3). Extra generations QUEUE. A handoff batch larger than the cap errors and is not silent-truncated (`[REQ-ORCH-038]`).

- Named ReAct States (`AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-097):
  - AgentKernel overlays THINKING|CALLING_TOOLS|PARKED|DONE|FAILED on the existing loop and persists `phase.react_state` when phase_id is in scope (`[REQ-KERNEL-001]`).
  - Chat SSE emits `react_state` with react_state, turn_idx, job_id, phase_id, assigned_agent_id (`[REQ-KERNEL-002]`). No LangGraph. No Chat badge (CARD-100).

- Job/Phase records + orchestrator (AutoReiv.Orchestration - CARD-096): SQLite jobs/phases, JobRepositoryMixin, JobPhaseOrchestrator linear next-or-finish. No LLM. No LangGraph.

- Control-plane Job/Phase (`docs/specs/control-plane-job-phase/` - CARD-096-101): spec and Slice A cards opened. CARD-014 parked (superseded by Job/Phase; DAG idea not deleted). No feature code. No push.

- Card board hygiene: parked CARD-023 through CARD-028 (nothing in flight). Closed CARD-046 (shipped as 063) and CARD-058 (already in CHANGELOG). Real backlog stays Ready. No push.

- Nested Write Budget (`AutoReiv.Orchestration`, `AutoReiv.SDLC` - CARD-095):
  - Nested `max_tokens` is 8192 and Ollama read timeout is 600s so CARD-001 can actually write `react-loop.ps1` (`[REQ-ORCH-030]`).
  - `git_status` / `git_commit` on a non-repo return `skip_commit`. Coding writes the deliverable first (`[REQ-SDLC-073]`).

- Nested Complete Context Cap (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-094):
  - `run_turn` caps `num_ctx` at 32768 and `max_tokens` at 1024. Nested `complete()` sends `think=false` (`[REQ-ORCH-028]`, `[REQ-ORCH-029]`).
  - Conductor handoff passes card id + spec slug. Coding reads the spec; it does not paste bodies.

- Nested Complete Uses Stream (`AutoReiv.Gateway`, `AutoReiv.Orchestration` - CARD-092):
  - Ollama `complete()` consumes `stream=true` so Coding handoff shares Chat's HTTP shape (`[REQ-ORCH-026]`).
  - Usage comes from the done chunk. Timeout/connect/404 labels unchanged (`[REQ-ORCH-027]`).

- Persist Builtin Agent Purpose (`AutoReiv.Forge`, `AutoReiv.Agents` - CARD-093):
  - `AgentCustomization.purpose` is saved on builtin Forge updates and applied on GET (`[REQ-FORGE-020]`).
  - Invalid purpose strings are ignored (`[REQ-FORGE-021]`).

- Close Parent LLM Stream Before Child Handoff (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-091):
  - `stream_turn` acloses the parent LLM stream before tools so Coding `complete()` is not nested inside the Conductor HTTP request (`[REQ-ORCH-023]`).
  - `gateway.stream` acloses inner `provider.stream`. Ollama POSTs relative `/api/chat`; pool timeout is 30s (`[REQ-ORCH-024]`).
  - `TimeoutException` is `Ollama timed out at ...`, not Failed to connect. Connect/timeout still HandoffResult failed (`[REQ-ORCH-025]`).

- Handoff Child Turn Budget (`AutoReiv.Orchestration` - CARD-090):
  - Child handoff `max_turns` defaults to 10 and is `min(max(envelope, profile, 10), 15)` so Coding is not silently capped at 5 (`[REQ-ORCH-020]`).
  - Provider connection failures (`Failed to connect`, `candidate providers failed`) map to HandoffResult status `failed` / success False, not completed (`[REQ-ORCH-021]`).
  - Ollama connect timeout is 30s; nested `complete()` uses its own httpx client so it is not starved by the parent stream (`[REQ-ORCH-022]`).

- YAML Card Frontmatter (`AutoReiv.SDLC` - CARD-089):
  - `parse_card_frontmatter` reads YAML `---` KEY: VALUE `---` plus blockquote `> **Key**: value`. Blockquote wins on conflict; YAML fills missing keys (`[REQ-SDLC-070]`).
  - `spec_reference` aliases Spec Reference / spec_reference / spec; `status` aliases Status / status (`[REQ-SDLC-071]`).
  - YAML-origin cards keep YAML on `set_card_status`. Discuss -> Ready works when the spec dir exists (`[REQ-SDLC-072]`).

- Spec-Driven SDLC Team (`AutoReiv.SDLC` - CARD-080-089): Conductor / Coding / Review loop on project-scoped cards and specs. Jail, Projects studio, SDD scaffold, conventional git, GitHub issue sync. Hold all pushes.

- Cards As GitHub Issues (`AutoReiv.SDLC` - CARD-088):
  - `sync_card_issue` maps card status and type labels and uses `gh` when present (`[REQ-SDLC-040]`, `[REQ-SDLC-041]`).
  - Missing `gh` is a clear error. No tokens. No GitHub MCP. HITL on create/update (`[REQ-SDLC-042]`).

- Git Conventional Commits (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-087):
  - `git_status`, `git_diff`, `git_branch`, `git_commit` are jailed to `project_root`. Conventional subjects only (`[REQ-SDLC-060]`).
  - `git_commit` parks on HITL. Coding allowlist stays at 12. No push (`[REQ-SDLC-061]`).

- SDD Project Scaffold (`AutoReiv.SDLC` - CARD-086):
  - `create_project` copies `templates/sdlc-project/` (AGENTS.md, specs, cards, CHANGELOG, VERSION, CONTRIBUTING, tests, README) (`[REQ-SDLC-050]`).
  - Tool is registered and HITL-parked. Slug cannot escape `projects_root` (`[REQ-SDLC-053]`).

- Projects Studio (`AutoReiv.SDLC`, `AutoReiv.Web` - CARD-085):
  - `projects_root` setting plus GET/POST/DELETE `/api/projects` jailed under that root (`[REQ-SDLC-050]`, `[REQ-SDLC-051]`).
  - Projects Studio is a sidebar tab, not wiki. Selected project is the default card/file root (`[REQ-SDLC-052]`).

- SDLC Bounce Back (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-084):
  - Bounce-back is the CARD-080 state machine plus `handoff_to_agent`. No second engine (`[REQ-SDLC-006]`).
  - Coding may `set_card_status` In Progress -> In Review only and is granted card/file tools under 12 (`[REQ-SDLC-033]`).

- Review Builtin (`AutoReiv.Agents` - CARD-083):
  - Builtin Review (`id=review`) has a 9-tool allowlist. Writes and `execute_code` are denied (`[REQ-SDLC-031]`).
  - Aliases qa / tester / review. Review can set Returned or Done from In Review (`[REQ-SDLC-035]`).

- Conductor Builtin (`AutoReiv.Agents` - CARD-082):
  - Builtin Conductor (`id=conductor`) has an 11-tool allowlist. No `execute_code`, `cli_exec`, or `write_project_file` (`[REQ-SDLC-030]`).
  - Lookup aliases product / plan / scrum / conductor. Chat and Forge list it without a Forge save (`[REQ-SDLC-034]`).

- Project File Tools (`AutoReiv.SDLC` - CARD-081):
  - `list_project_dir`, `read_project_file`, `write_project_file` are jailed under `project_root` (`[REQ-SDLC-021]`, `[REQ-SDLC-022]`).
  - Writes park on existing HITL. Grants wait for Conductor / Review / Coding cards (`[REQ-SDLC-023]`).

- Card Spec Steering Tools (`AutoReiv.SDLC` - CARD-080):
  - Tools `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering` operate on `project_root` (default AutoReiv checkout) (`[REQ-SDLC-012]`, `[REQ-SDLC-013]`).
  - `set_card_status` enforces Discuss | Ready | In Progress | In Review | Returned | Done. Ready needs a spec. Returned increments rounds; max rounds deny and tell the caller to ask the operator (`[REQ-SDLC-010]`, `[REQ-SDLC-011]`).
  - Writes and status changes park on existing HITL (`[REQ-SDLC-014]`, `[REQ-SDLC-020]`).

- Coding Agent Execute Code (`AutoReiv.Agents`, `AutoReiv.Kernel` - CARD-079):
  - Builtin Coding agent is in the roster with a tight allowlist. `execute_code` is granted only on Coding (`[REQ-AGENTS-010]`).
  - Bootstrap registers the sandbox skill so `execute_code` is in the Forge catalog; Assistant is allowlist-denied (`[REQ-AGENTS-011]`).
  - Chat, Forge, and `lookup_agents` list Coding without a Forge save. SQLite overrides still win (`[REQ-AGENTS-012]`).

- Routine Resume From Chat (`AutoReiv.Routines`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-076):
  - Routine parks store `agent_id` and `routine_id` so Chat can list them (`[REQ-HITL-041]`).
  - Chat loads pending approvals for the open agent and shows the existing Approve/Reject card (`[REQ-HITL-042]`).
  - Approve/Reject on a routine park resumes that session with `run_turn(..., resume=True)` and no extra USER (`[REQ-HITL-043]`).

- Forge Allowlist Warning (`AutoReiv.Web` - CARD-078):
  - Forge shows an amber warning when 12 or more tools are checked; save is not blocked (`[REQ-FORGE-007]`, `[REQ-FORGE-008]`).

- Card status hygiene: normalize `docs/cards` labels to Done / Ready / In Progress.

- Remember Last Auto-run (`AutoReiv.Web` - CARD-077):
  - Chat Auto-run toggle is remembered in localStorage; missing memory fail-closes to ask (`[REQ-HITL-039]`, `[REQ-HITL-040]`).

- Goal Mode Review Gate (`AutoReiv.Planning`, `AutoReiv.Web` - CARD-075):
  - Goal Mode parks after formulate so the operator can Approve or Reject the plan (`[REQ-GOAL-020]`, `[REQ-GOAL-021]`).
  - Approve runs the existing step executor; Reject ends cleanly. Send a message to revise (`[REQ-GOAL-022]`).

- Nested Child-Session HITL Resume (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-074):
  - Nested Approve/Reject persist the TOOL on the child session and resume child ReAct with no new USER message (`[REQ-HITL-036]`).
  - Child completion or a second park is written onto the parent as a handoff TOOL (`[REQ-HITL-037]`).
  - Parent resume replays a nested park and stops, or continues after the child result (`[REQ-HITL-038]`).

- Resume After HITL Approve (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-073):
  - After Approve or Reject, Chat starts a continue stream with no new USER message (`[REQ-HITL-033]`).
  - `stream_turn` resume loads existing history and continues ReAct (`[REQ-HITL-034]`). Failed decide does not resume (`[REQ-HITL-035]`).

- Stop Stream After HITL Park (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-072):
  - `stream_turn` yields TURN_END and returns after a gated or nested park so the model cannot keep talking (`[REQ-HITL-031]`).
  - Parked handoffs emit `HANDOFF_COMPLETE` with `status=approval_required`; Chat shows Waiting for approval / Parked (`[REQ-HITL-032]`).

- Agent Chat History Retention (`AutoReiv.Agents`, `AutoReiv.Memory` - CARD-047):
  - Per-agent `history_retention_days` defaults to 30. `0` means never (`[REQ-RET-001]`).
  - Stale chat sessions and messages are pruned on startup and when Chat lists sessions (`[REQ-RET-002]`, `[REQ-RET-004]`).
  - Wiki, facts, and routines are not touched (`[REQ-RET-003]`).

- Session And Routine Approval Mode (`AutoReiv.Safety`, `AutoReiv.Web` - CARD-071):
  - Chat Auto-run toggle sends `approval_mode=run`; default is ask (`[REQ-HITL-027]`).
  - Handoff inherits the parent turn policy (`[REQ-HITL-028]`).
  - Routines store `approval_mode` on the job, default ask (`[REQ-HITL-029]`).
  - Run mode still hard-denies dangerous `cli_exec` (`[REQ-HITL-030]`).

- Keep HITL Approve Output On Screen (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-070):
  - Stream-end history reload no longer wipes a visible HITL card (`[REQ-HITL-025]`).
  - Approve/Reject persist the tool output on the chat session (`[REQ-HITL-026]`).

- Bubble Child HITL Parks To Parent Chat (`AutoReiv.Orchestration`, `AutoReiv.Safety` - CARD-069):
  - A specialist that parks a tool during handoff now surfaces `approval_required` on the parent stream (`[REQ-HITL-023]`, `[REQ-HITL-024]`).
  - Chat Approve/Reject cards use the child tool name and arguments.

- Chat HITL Approve / Reject Buttons (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-068):
  - Chat stream shows a HITL card with tool name, arguments, Approve, and Reject (`[REQ-HITL-020]`).
  - Buttons call `POST /api/approvals/{id}/decision`; the card shows the result (`[REQ-HITL-021]`, `[REQ-HITL-022]`).

- Allowlist-Only Tool Mount (`AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-067):
  - Chat turns mount the full RBAC allowlist; BM25 no longer drops granted tools (`[REQ-TOOLS-010]`).
  - Assistant pins `lookup_agents` next to `handoff_to_agent` (`[REQ-TOOLS-011]`).
  - `list_available_skills_and_tools` is no longer on builtin chat allowlists; Forge still lists the catalog (`[REQ-TOOLS-012]`).

- Unify Agent Handoff To One Public Tool (`AutoReiv.Orchestration`, `AutoReiv.Kernel` - CARD-066):
  - Chat now exposes only `handoff_to_agent`; `delegate_task` is no longer registered (`[REQ-ORCH-010]`).
  - App startup injects the live kernel into `HandoffIsolationEngine` (`[REQ-ORCH-011]`).
  - Caller agent id and session come from the in-flight turn so child sessions follow the real chat (`[REQ-ORCH-012]`).

- Keep Reflexion Critiques Off Transcript (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-065):
  - Self-verify retries no longer persist `CRITIQUE ON PREVIOUS OUTPUT` as USER messages (`[REQ-VERIFY-014]`, `[REQ-VERIFY-015]`).
  - Chat SSE emits `reflexion_attempt` per try and `reflexion_critique` on each failed check (`[REQ-VERIFY-016]`).

- Honest Reflexion Verification (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-064):
  - Missing verifier/critic is now `skipped` with `verification_passed=false` instead of a fake pass (`[REQ-VERIFY-010]`).
  - Chat `self_verify` runs a builtin JSON critic (`is_valid` / `discrepancies`) and fails closed on empty output or unparseable critic JSON (`[REQ-VERIFY-011]`, `[REQ-VERIFY-012]`).
  - SSE `reflexion_verified.passed` matches the engine; Chat Studio shows a failed badge when verification does not pass (`[REQ-VERIFY-013]`).

- Wire HITL Approval Into Kernel Tool Loop (`AutoReiv.Kernel`, `AutoReiv.Safety`, `AutoReiv.Web` - CARD-063):
  - `AgentKernel` parks high-risk tools (`cli_exec`, wiki writes, `save_agent_specification`, `execute_code`) in `pending_approvals` instead of executing them (`[REQ-HITL-010]`, `[REQ-HITL-011]`).
  - `DangerousCommandFilter` hard-denies prohibited `cli_exec` commands without parking (`[REQ-HITL-012]`).
  - Chat stream emits `approval_required`; `POST /api/approvals/{id}/decision` with APPROVED runs the parked tool (`[REQ-HITL-013]`).

- Settings-Owned Model Context Window Overrides (`AutoReiv.Kernel`, `AutoReiv.Settings`, `AutoReiv.Gateway` - CARD-062):
  - Stopped treating `qwen3.8:latest` as an 8k model; name table now maps `qwen3.8` / `qwen35` and explicit size tags (`65k`, `256k`, `262k`) (`[REQ-CTX-001]`).
  - Added `default_context_window` and `model_context_windows` on the purpose matrix, editable in Settings Studio and saved via `POST /api/settings/matrix` (`[REQ-CTX-002]`, `[REQ-CTX-003]`).
  - Kernel compaction and Ollama `num_ctx` use the Settings override first, then the name table (`[REQ-CTX-004]`).

- Host OS-Aware Tool Guidance & System Info Description Alignment (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-061):
  - Updated `system_info` and `cli_exec` tool schema descriptions to advertise host IP capabilities and enforce OS-appropriate command syntax (`[REQ-OS-AWARE-001]`).
  - Enriched `AUTOREIV_PROFILE.system_prompt` with host OS awareness (Windows vs Linux) and directed the model to use `system_info` first for telemetry and platform-specific CLI commands (`[REQ-OS-AWARE-002]`).
  - **Fixed** `cli_exec` and `SandboxedSubprocessWorker` subprocess execution on Windows: uvicorn uses `SelectorEventLoop` which throws `NotImplementedError` on `asyncio.create_subprocess_shell/exec`. Replaced with `subprocess.run` dispatched via `loop.run_in_executor` (thread pool) for cross-platform compatibility.

- Host IP Telemetry in System Info & AutoReiv CLI Exec Pinning (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-060):
  - Enriched `SysadminSkill.get_system_info()` with `hostname`, `primary_ip`, and `ip_addresses` telemetry using resilient cross-platform UDP and DNS socket probes (`[REQ-SYSINFO-001]`, `[REQ-SYSINFO-003]`).
  - Pinned `cli_exec` in `AUTOREIV_PROFILE.pinned_tool_names` ensuring safe shell command execution is unconditionally delivered in active tool sets on every turn (`[REQ-SYSINFO-002]`).

- Mobile Stream Resiliency, Background Task Persistence & Goal Deliverable Markdown Synthesis (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-059):
  - Decoupled FastAPI `/api/chat/stream` SSE generator from underlying turn execution using shielded background worker tasks and in-memory async queues, guaranteeing database persistence even if mobile screen locks or tabs disconnect mid-stream (`[REQ-MOB-STREAM-001]`).
  - Implemented mobile tab visibility (`document.visibilitychange`) and window focus synchronization in Chat Studio to automatically re-fetch and restore completed messages upon returning to the app (`[REQ-MOB-STREAM-002]`).
  - Added strict Markdown output instructions and negative constraints against raw JSON dicts in Goal Mode synthesis prompts (`[REQ-MOB-STREAM-003]`).
  - Implemented graceful `format_json_deliverable_to_markdown` fallback formatter in both Python backend and JavaScript frontend to format structured deliverables into clean Markdown sections (`[REQ-MOB-STREAM-004]`).

- Visual Goal Mode & Reflexion Streaming UI (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-058):
  - Added `goal_mode` and `self_verify` boolean parameters to `/api/chat/stream` (`[REQ-CHAT-010]`).
  - Implemented SSE emission for multi-step goal execution (`plan_formulated`, `step_start`, `step_complete`) and self-verification (`reflexion_attempt`, `reflexion_critique`, `reflexion_verified`) (`[REQ-CHAT-011]`, `[REQ-CHAT-012]`).
  - Added interactive Milestone DAG progress card and real-time Reflexion verification badges inside Chat Studio message bubbles (`[REQ-CHAT-013]`).
  - Supported dual-mode execution where decomposed goal milestones run with iterative self-verification (`[REQ-CHAT-014]`).
  - Isolated plan formulation and step prompts from chat thread history (`save_to_history=False`) to prevent raw JSON and system prompts in chat bubbles.
  - Enhanced Gateway and Agent Kernel model cascade to correctly resolve configured default models (e.g. `qwen3.8:latest`) and increased Ollama read timeout to 180s for local reasoning models.
- Weekly Notes Rollover Routine & Markdown Task Skill (`AutoReiv.Skills`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-057):
  - Seeded default Obsidian-compatible weekly notes template in `data/wiki/03_Resources/templates/weekly_notes.md` with dynamic Monday╬ô├ç├┤Sunday date interpolation (`[REQ-WNOTE-001]`).
  - Implemented `WeeklyNotesSkill` (`src/application/skills/weekly_notes_skill.py`) with conversational tools for logging daily progress, checking off tasks with `╬ô┬ú├á YYYY-MM-DD`, and viewing weekly summaries (`[REQ-WNOTE-002]`).
  - Built automated task carry-over engine rolling over unfinished tasks from previous weeks into `### Γëí╞Æ├╢├ñ Carry-Over` (`[REQ-WNOTE-003]`).
  - Added built-in autonomous routine `weekly_note_rollover` (`0 0 * * 1` Monday midnight) bound to `assistant` (`[REQ-WNOTE-004]`).
- Skill Pack Taxonomy Realignment & AutoReiv Dedicated Diagnostics (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-056):
  - Structured skill pack manifests into a 3-tier functional taxonomy: **User Knowledge & Productivity**, **System Operations & Platform**, and **Agent Cognition & Runtime** (`[REQ-TAX-001]`).
  - Branded internal diagnostics as `"AutoReiv Core Platform SRE & Diagnostics"` with dedicated core indicators and renamed self-reflection tools to `"Agent Logic Verification (Critic)"` (`[REQ-TAX-002]`).
  - Pruned redundant `yaml_frontmatter_parse` micro-tool from the tool registry in favor of `wiki_note_read`'s native metadata extraction (`[REQ-TAX-003]`).
  - Updated Agent Forge Studio to render skill packs grouped into 3 distinct visual sections with tier headers, subtitles, and dedicated badges (`[REQ-TAX-004]`).
- Session Artifact Store & Context-Isolated Batch Worker Skill (`AutoReiv.Memory`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-055):
  - Implemented SQLite `session_artifacts` schema with `ON DELETE CASCADE` session bound foreign keys, indexed 7-day TTL timestamps, and manual artifact pinning (`[REQ-ART-001]`, `[REQ-ART-002]`).
  - Built `BatchWorkerSkill` map-reduce pipeline partitioning massive target paths across parallel in-memory subagents and saving structured reports to `session_artifacts` (`[REQ-ART-003]`).
  - Added REST API endpoints (`/api/sessions/{id}/artifacts`, `/api/artifacts/{id}`, `/api/artifacts/{id}/promote`, `/api/artifacts/{id}/pin`) (`[REQ-ART-004]`).
  - Added Chat Studio interactive artifact cards in message bubbles and slide-over `#artifactModal` viewer with 1-click **"Promote to Wiki Vault"** capability (`[REQ-ART-005]`).
- Agent Forge Studio Mobile Responsive Toolbar, Header Cleanup & Default Collapsed Skills (`AutoReiv.Web` - CARD-054):
  - Removed obsolete `"RPG Character Sheet"` badge text from the Agent Forge Studio header (`[REQ-MOB-001]`).
  - Refactored the Agent Forge top toolbar into a mobile-first responsive flex container allowing dropdown and action buttons to wrap naturally on viewports $\le 480\text{px}$ (`[REQ-MOB-002]`).
  - Set skill pack tool item grids in Agent Forge to be collapsed by default upon page navigation for a compact overview (`[REQ-MOB-003]`).
- Agent Forge Studio Layout Refactor & Legacy Co-Pilot Pruning (`AutoReiv.Web` - CARD-053):
  - Removed obsolete "System Architect Co-Pilot" chat sidebar, starter prompt chips, and prompt input form from Agent Forge Studio (`[REQ-PRUNE-001]`).
  - Expanded RPG Character Sheet workspace into a clean, spacious full-width container (`max-w-6xl mx-auto`) with responsive single and multi-column grid cards (`[REQ-PRUNE-002]`).
  - Pruned unused Co-Pilot JS state, streaming handlers, and legacy `system-agent` stream calls from `src/web/static/modules/studios/forge.js` (`[REQ-PRUNE-003]`).
- MCP Server Environment Variables, Live Tool Discovery Preview & Agent Forge Pack Binding (`AutoReiv.MCP`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-052):
  - Enabled per-server secure key-value environment variables injection into MCP stdio subprocesses (`[REQ-MCP-007]`).
  - Added transient diagnostic handshake probe endpoint `POST /api/settings/mcp/test` measuring connection latency and advertising tool schemas without persistence (`[REQ-MCP-008]`).
  - Upgraded Settings Studio MCP panel with dynamic key-value environment editor, secret value masking, and live tool discovery badge preview (`[REQ-MCP-009]`).
  - Integrated dynamic MCP Server skill pack clustering and master checkboxes into Agent Forge Studio (`[REQ-MCP-010]`).
- Model Context Protocol (MCP) Standard Client Adapter & 3-Tier Tool Resolution Pipeline (`AutoReiv.MCP`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-012):
  - Implemented `ToolRanker` (`src/application/kernel/tool_ranker.py`) with fast sub-millisecond BM25 keyword relevance scoring over tool names, descriptions, and parameter schemas (`[REQ-MCP-004]`).
  - Integrated 3-Tier Tool Resolution in `AgentKernel` (`run_turn` & `stream_turn`), strictly enforcing Tier 1 Hard RBAC, Tier 2 Pinned Core Tools, and Tier 3 Dynamic Tool Ranking when authorized tools exceed `max_active_tools: int = 6` (`[REQ-MCP-004]`).
  - Built `MCPClientAdapter` and `MCPClientManager` (`src/infrastructure/mcp/client_adapter.py`) managing stdio JSON-RPC 2.0 subprocesses, namespace scoping (`mcp_<server>_<tool>`), execution timeouts, and graceful shutdown (`[REQ-MCP-001]`, `[REQ-MCP-002]`, `[REQ-MCP-003]`).
  - Added MCP server management REST endpoints (`GET/POST/DELETE /api/settings/mcp`) and Settings Studio UI panel with connection status badges and auto-mount lifecycles (`[REQ-MCP-005]`).
  - Added portable markdown skill manual parsing via `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) (`[REQ-MCP-006]`).

## [0.14.0] - 2026-08-27

### Changed

- System Simplification: Dual Core Agents, Universal Wiki Skill & System Info Pruning (`AutoReiv.Agents`, `AutoReiv.Skills` & `AutoReiv.Web` - CARD-050):
  - Consolidated built-in baseline agents down to two crystal-clear identities: `assistant` (daily workflow coordinator) and `autoreiv` (self-introspecting platform SRE and codebase expert).
  - Maintained backward-compatibility alias resolution across `SupervisorOrchestrator` and `BuiltinAgentRegistry` for legacy agent IDs (`general-assistant`, `linux-sysadmin`, `librarian`, `system-agent`).
  - Elevated Wiki into a first-class, reusable `WikiSkill` (`src/application/skills/wiki_skill.py`) attachable to both baseline agents and custom user agents in Agent Forge.
  - Pruned obsolete System Info / Docs Studio and associated backend services from the UI, focusing the control plane into a clean 6-studio suite.
  - Passed all 301 Pytest unit & integration tests, 50 Vitest frontend tests, Playwright multi-studio smoke tests, and unified pre-flight verification.
- SQLite State Store Decomposition into Focused Domain Repositories (`AutoReiv.Memory` - CARD-049):
  - Decomposed monolithic 1,559-line `src/infrastructure/memory/sqlite_store.py` into 7 focused domain repository mixins under `src/infrastructure/memory/repositories/` (`sessions.py`, `facts.py`, `settings.py`, `routines.py`, `telemetry.py`, `approvals.py`, `tasks.py`).
  - Isolated SQL DDL and index creation into `src/infrastructure/memory/schema.py` and thread-safe connection management into `src/infrastructure/memory/connection.py`.
  - Maintained 100% public method signatures and return types via `SQLiteStateStore` faΓö£┬║ade (~34 lines).
  - Verified 100% data persistence and backward compatibility across all 314 tests in under 19 seconds.
- FastAPI Router Decomposition & Architectural Modularization (`AutoReiv.Web` - CARD-048):
  - Decomposed monolithic 1,340-line `src/web/app.py` into 8 focused domain routers under `src/web/routers/` (`chat.py`, `agents.py`, `wiki.py`, `settings.py`, `routines.py`, `observability.py`, `hitl.py`, `system.py`).
  - Reduced `src/web/app.py` application factory to a lean ~170 lines managing lifespan, CORS, static mounts, and dependency attachments.
  - Consolidated multi-agent delegation under `SupervisorOrchestrator` as the unified delegation engine.
  - Verified 100% route and contract compatibility across 314 pytest tests, 50 Vitest unit tests, and Playwright multi-studio smoke suites.

### Added

- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation Orchestration (`AutoReiv.Orchestration`, `AutoReiv.Kernel` & `AutoReiv.Web`):
  - Standardized 5-Key A2A Handoff Envelope (`src/domain/orchestration/models.py`), defining `HandoffEnvelope` (`sender_agent_id`, `recipient_agent_id`, `session_id`, `task_intent`, `context_payload`, `correlation_id`, `depth`, `max_turns`, `timeout_seconds`) and `HandoffResult` (`[REQ-A2A-001]`).
  - Supervisor Orchestration Engine with Recursion & Self-Handoff Guardrails (`src/application/kernel/supervisor_orchestrator.py`), enforcing anti-recursion depth limits (max 2 tiers), circular self-handoff prevention, specialist alias resolution (`sysadmin`, `librarian`, `system`, `general`), and child session isolation (`[REQ-A2A-002]`).
  - Delegate Subtask Tool & Skill (`src/application/skills/delegate_skill.py`), exposing the `delegate_task` tool for registration in `ScopedToolRegistry` (`[REQ-A2A-003]`).
  - Inter-Agent Context Hydration (`src/application/kernel/supervisor_orchestrator.py`), hydrating working memory facts and parameters into delegated prompts (`[REQ-A2A-004]`).
  - Inter-Agent Telemetry & Correlation Tracing (`src/application/telemetry/collector.py`), recording `handoff` spans linking session IDs, correlation IDs, agent IDs, durations, and outcomes (`[REQ-A2A-005]`).
  - REST Multi-Agent Delegation API (`src/web/app.py`), exposing `POST /api/agents/delegate` for external invocation (`[REQ-A2A-006]`).
  - Chat Stream & UI Live Handoff Indicators (`src/application/kernel/agent_kernel.py`, `src/web/app.py`, `src/web/static/modules/studios/chat.js`), streaming `handoff_start` and `handoff_complete` SSE events and rendering animated delegation badges in Chat Studio (`[REQ-A2A-007]`).
  - Comprehensive Multi-Agent Handoff Test Suite (`tests/unit/orchestration/test_handoff_envelope.py`, `tests/unit/skills/test_delegate_skill.py`, `tests/unit/kernel/test_agent_kernel.py`, `tests/unit/web/test_agent_delegation_api.py`) (`[REQ-A2A-001]` - `[REQ-A2A-007]`).

- Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine (`AutoReiv.Kernel` & `AutoReiv.Web`):
  - Domain HITL Models (`src/domain/hitl/models.py`), defining `ApprovalStatus`, `PendingAction`, and `ApprovalDecision` (`[REQ-HITL-001]`).
  - Approval Manager State Parking & Resume (`src/application/hitl/approval_manager.py`), parking agent actions in an in-memory queue with `asyncio.Future` suspension and human-triggered resolution (`[REQ-HITL-002]`).
  - HITL REST API Endpoints (`src/web/app.py`), exposing `GET /api/hitl/pending` and `POST /api/hitl/decide` for human operator interaction (`[REQ-HITL-003]`).
  - Comprehensive HITL Unit & Integration Test Suite (`tests/unit/hitl/test_approval_manager.py`), verifying action parking, approval/rejection resolution, and REST endpoint integration across 6 tests (`[REQ-HITL-004]`).

- Dangerous Shell Command Safety Guardrails & Path Traversal Protection (`AutoReiv.Kernel` & `AutoReiv.Deploy`):
  - Domain Safety Risk Models (`src/domain/safety/models.py`), defining `RiskLevel`, `SafetyViolation`, and `CommandSafetyReport` (`[REQ-GUARD-001]`).
  - Deterministic Command Guardrail Engine (`src/application/safety/command_guardrail.py`), providing rule-based inspection across destructive recursive deletions, disk wiping tools, system shutdowns, fork bombs, and remote pipe-to-shell attacks (`[REQ-GUARD-002]`).
  - Workspace Path Traversal Protection (`src/application/safety/command_guardrail.py`), intercepting path traversal escapes and sensitive OS directory tampering (`[REQ-GUARD-003]`).
  - Subprocess Sandbox Guardrail Interception (`src/application/skills/sandbox_worker.py`), screening all subprocess execution requests and aborting dangerous operations prior to spawning child processes (`[REQ-GUARD-002]`).
  - Comprehensive Safety Guardrails Unit Test Suite (`tests/unit/safety/test_command_guardrail.py`), verifying safety evaluation across 6 tests (`[REQ-GUARD-004]`).

- Ephemeral Subprocess Execution Sandbox & Process Isolation (`AutoReiv.Skills` & `AutoReiv.Deploy`):
  - Workspace File Provisioning & Output Artifact Extraction (`src/application/skills/sandbox_worker.py`), supporting provisioning multi-file input payloads into ephemeral temporary workspaces and extracting generated output files prior to clean teardown (`[REQ-SANDBOX-001]`).
  - Sensitive Environment Variable Scrubbing & Stream Capping (`src/application/skills/sandbox_worker.py`), automatically filtering out host API keys, tokens, and credentials while enforcing standard stream output limits (`max_output_bytes = 1MB`) (`[REQ-SANDBOX-002]`).
  - Agent Sandbox Execution Skill (`src/application/skills/sandbox_skill.py`), exposing the `execute_code` tool for registration in `ScopedToolRegistry` with structured execution telemetry (`[REQ-SANDBOX-003]`).
  - Comprehensive Sandbox Unit & Integration Test Suite (`tests/unit/skills/test_sandbox_worker.py`), verifying workspace file provisioning, output artifact capture, secret scrubbing, timeout killing, and tool execution across 5 tests (`[REQ-SANDBOX-004]`).

- Gateway Resilience Hardening & Streaming Cycle Detection (`AutoReiv.Gateway` & `AutoReiv.Kernel`):
  - Decorrelated Exponential Backoff with Full Jitter (`src/application/gateway/gateway_service.py`), implementing `calculate_backoff` to eliminate synchronized retry storms during transient 5xx and rate-limit errors (`[REQ-RESIL-001]`).
  - Connection Pool Limits & Graceful Lifecycle Teardown (`src/infrastructure/gateway/openai_adapter.py` & `ollama_adapter.py`), standardizing keep-alive connection pools (`max_keepalive_connections=20`, `max_connections=50`, `keepalive_expiry=30.0`) and introducing `async def close()` (`[REQ-RESIL-002]`).
  - Dual-Mode Agent Reasoning & Streaming Cycle Detector (`src/application/kernel/cycle_detector.py` & `agent_kernel.py`), analyzing both repeated tool-call signatures and streaming text phrase loops to halt infinite model loops safely (`[REQ-RESIL-003]`).
  - Comprehensive Gateway Resilience Unit Test Suite (`tests/unit/gateway/test_resilience.py`), verifying backoff bounds, connection pool configuration, and cycle detection break conditions across 4 tests (`[REQ-RESIL-004]`).

- SQLite Episodic Fact Memory Store & Agent Auto-Recall (`AutoReiv.Memory`, `AutoReiv.Skills` & `AutoReiv.Gateway`):
  - Tokenized Substring Fact Search (`src/infrastructure/memory/sqlite_store.py`), implementing `search_facts` filtering across `entity`, `key`, and `value` fields with confidence thresholding and ranking (`[REQ-EPISODIC-001]`).
  - Dynamic Memory Context Formatting & Auto-Recall (`src/application/skills/memory_skill.py`), implementing `render_memory_context` and `auto_recall` generating clean Markdown context blocks for agents (`[REQ-EPISODIC-002]`).
  - Automated Kernel Memory Injection (`src/application/kernel/agent_kernel.py`), transparently enriching agent system instructions with matching cross-session episodic memory facts during synchronous and streaming turn execution (`[REQ-EPISODIC-003]`).
  - Episodic Memory Management REST API (`src/web/app.py`), exposing `GET`, `POST`, and `DELETE` endpoints under `/api/memory/facts` (`[REQ-EPISODIC-004]`).
  - Comprehensive Unit & Integration Test Suite (`tests/unit/memory/test_episodic_memory.py`), validating store CRUD, search filtering, Markdown rendering, kernel auto-recall injection, and REST endpoints across 4 test suites (`[REQ-EPISODIC-005]`).

- Context Window Compaction & Sliding Dynamic Token Budget Strategy (`AutoReiv.Kernel`):
  - Model-Aware Dynamic Token Budgeting (`src/application/kernel/context_compactor.py`), implementing `get_model_context_limit` mapping model families (8k, 32k, 128k, 1M) and enforcing a 75% safety ceiling to prevent context overflows (`[REQ-COMPACT-001]`).
  - Root User Intent Preservation (`src/application/kernel/context_compactor.py`), locking the initial user prompt alongside the system directive during sliding window summarization to eliminate task amnesia in long-running agentic loops (`[REQ-COMPACT-002]`).
  - Structured Compaction Telemetry (`src/application/kernel/context_compactor.py`), introducing `CompactionMetrics` and `compact_with_stats` tracking token savings, turn summarization counts, and tool truncation events (`[REQ-COMPACT-003]`).
  - Comprehensive Unit Test Coverage (`tests/unit/kernel/test_context_compactor.py`), validating pattern mapping, intent preservation, and metrics tracking across 5 tests (`[REQ-COMPACT-004]`).

- Error Boundary Toasts & Offline Backend Messaging (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Non-Blocking Accessible Toast Notification Subsystem (`src/web/static/modules/ui/toast.js` & `src/web/templates/index.html`), introducing `showToast` with `info`, `success`, `warning`, and `error` variants, ARIA live region announcements (`polite` / `assertive`), auto-dismiss timers, and dismiss actions (`[REQ-TOAST-001]`).
  - Studio Error Boundary Migration (`src/web/static/modules/studios/forge.js`, `routines.js`, `wiki.js`), eliminating 100% of intrusive browser `alert()` popups in favor of non-blocking visual toasts (`[REQ-TOAST-002]`).
  - Proactive Gateway Connectivity & Recovery Monitor (`src/web/static/modules/ui/toast.js` & `src/web/static/app.js`), polling `/api/health` in the background, rendering a top-level alert banner on disconnect, and triggering reconnect toasts (`[REQ-TOAST-003]`).
  - Toast Subsystem Unit & Smoke Test Suite (`tests/unit/frontend/toast.test.js`), introducing 6 unit tests verifying toast container creation, variant rendering, timer auto-dismissal, and connectivity state transitions (`[REQ-TOAST-004]`).

- Performance Budgets, Module Bundling & First-Paint Optimization (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Kinetic Energy Equilibrium Sleeping (`src/web/static/modules/utils/physics.js` & `src/web/static/modules/studios/wiki.js`), calculating total system kinetic energy on each simulation frame and pausing `requestAnimationFrame` when convergence drops below `0.005`, driving idle CPU consumption to 0% (`[REQ-PERF-001]`).
  - Strict Modal Animation Teardown (`src/web/static/modules/studios/wiki.js`), halting background animation runners immediately upon modal close, dismissal, or note selection (`[REQ-PERF-002]`).
  - First-Paint Module Preloading (`src/web/templates/index.html`), introducing `<link rel="modulepreload">` directives for core ES modules to optimize browser network waterfalls and Time-To-Interactive (`[REQ-PERF-003]`).
  - Performance & Simulation Lifecycle Unit Suite (`tests/unit/frontend/perf.test.js`), adding 7 unit tests verifying kinetic calculations, start/sleep/wake/stop runner state machines, and zero CPU leakage (`[REQ-PERF-004]`).

- Mobile & Keyboard Accessibility Architecture (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Semantic ARIA Roles & Screen Reader Landmarks (`src/web/templates/index.html` & `src/web/static/modules/utils/accessibility.js`), adding `role="tablist"` navigation, dynamic `aria-selected` toggling, `role="tabpanel"` views, `role="dialog"` modal wrappers, and `aria-live="polite"` chat stream announcements (`[REQ-A11Y-001]`).
  - Modal Focus Trapping & Global Escape Key Dismissal (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), trapping `Tab` and `Shift+Tab` within active modal dialogs, closing open modals on `Escape`, and restoring user focus (`[REQ-A11Y-002]`).
  - Studio Navigation Arrow-Key Keyboard Controls (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), enabling `ArrowDown`/`ArrowRight`/`ArrowUp`/`ArrowLeft`/`Home`/`End` cyclical tab switching (`[REQ-A11Y-003]`).
  - Automated Accessibility Test Suite (`tests/unit/frontend/accessibility.test.js`), introducing 10 pure unit tests verifying focus containment, keyboard navigation, and ARIA syncing (`[REQ-A11Y-004]`).

- Steering & Product Documentation Truth Synchronization (`AutoReiv.Docs`):
  - 7-Studio Product Architecture Specification (`steering/product.md`), detailing the operational capabilities of Chat, Routines, Observability, Agent Forge, Settings, Docs, and Wiki & Mind Map studios alongside local-first privacy boundaries (`[REQ-DOCS-005]`).
  - Dual-Runtime Environment & Topology Steering (`steering/tech.md` & `steering/structure.md`), formally documenting the zero-build ES Module frontend architecture, Python 3.12/FastAPI backend, and directory topology (`[REQ-DOCS-006]`).
  - Milestone 10 Formal Closure & Roadmap Alignment (`steering/roadmap.md`), certifying 100% completion of Milestone 10 (v0.10.0 - Quality & Testability) across all 4 work cards with 174 tracked requirements (`[REQ-DOCS-007]`).

- Gateway, Wiki & Settings End-to-End API Contract Integration Tests (`AutoReiv.Gateway`, `AutoReiv.Wiki`, `AutoReiv.Settings`):
  - Multi-Provider Gateway Model Discovery Contract Suite (`tests/integration/test_gateway_contract_api.py`), validating `/api/models/discover` and `/api/settings/presets` across mocked local and cloud providers with fallback resilience (`[REQ-API-001]`).
  - Wiki Studio Vault & Knowledge Graph Contract Suite (`tests/integration/test_wiki_contract_api.py`), exercising full note CRUD lifecycle (`GET/POST/PUT/DELETE /api/wiki/note`), tree traversal, search, mind map graph serialization, and direct chat thread inbox export (`[REQ-API-002]`).
  - Settings Studio Configuration & Secret Masking Contract Suite (`tests/integration/test_settings_contract_api.py`), verifying provider persistence, purpose-to-model matrix assignments, system documentation topics, and zero secret leakage (`[REQ-API-003]`).
  - Hermetic FastAPI Integration Test Fixtures & Runner Integration (`tests/integration/` & `preflight.py`), providing isolated in-memory SQLite and scratch vault testing executing 12 integration tests in < 5s (`[REQ-API-004]`).

- Comprehensive Unit Test Suite for Frontend Pure Logic (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - 2D Physics Layout Engine Extraction & Unit Testing (`src/web/static/modules/utils/physics.js` & `tests/unit/frontend/physics.test.js`), decoupling force-directed graph calculation algorithms from the DOM and validating repulsion, spring attraction, damping, and equilibrium convergence (`[REQ-UNIT-001]`).
  - Reactive State Store Implementation & Testing (`src/web/static/modules/state/store.js` & `tests/unit/frontend/store.test.js`), implementing a lightweight `createStore` factory with mutation isolation, updater callbacks, and listener subscription/teardown mechanics (`[REQ-UNIT-002]`).
  - Comprehensive Boundary Testing for Formatters & Sanitizers (`src/web/static/modules/utils/formatters.js` & `tests/unit/frontend/formatters.test.js`), hardening byte formatting, token counting, timestamp parsing, and HTML escaping against negative values, non-numeric strings, and XSS injection vectors (`[REQ-UNIT-003]`).
  - Fast-Feedback Pure Logic Test Runner Integration (`package.json` & `preflight.py`), scaling Vitest coverage across 27 pure unit tests running cleanly in < 400ms (`[REQ-UNIT-004]`).

- ESLint & Prettier Static Analysis Pipeline for Frontend (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - Flat Config ESLint 9 Integration (`eslint.config.js` & `package.json`), establishing automated static linting with browser/node globals, rules prohibiting unused identifiers, and full ES module validation (`[REQ-LINT-001]`).
  - Prettier Code Formatting Standard (`.prettierrc` & `package.json`), enforcing single quotes, trailing commas (`es5`), 2-space indentation, and 120 print width across frontend files (`[REQ-LINT-002]`).
  - Unified Pre-Flight & CI Frontend Lint Gate (`.agents/skills/rtm-sync/scripts/preflight.py` & `.github/workflows/ci.yml`), integrating `npm run lint:frontend` as stage 3 of the unified 6-stage pre-flight runner and continuous integration pipeline (`[REQ-LINT-003]`).
  - Zero Linting Errors Baseline Sweep (`src/web/static/` & `tests/`), formatting all frontend source modules and resolving all unused variables, empty catch blocks, and missing globals (`[REQ-LINT-004]`).

- Defensive DOM Query & Null-Safety Architecture Across Studio Interfaces (`AutoReiv.Web`):
  - Complete Helper Migration for All Studio Modules (`src/web/static/modules/studios/`), replacing all raw un-scoped `document.getElementById`, `document.querySelector`, and `document.querySelectorAll` queries across `docs.js`, `settings.js`, `observability.js`, `forge.js`, and `wiki.js` with defensive `$`, `$query`, and `$queryAll` helpers (`[REQ-DOM-001]`).
  - Defensive Event Binding & Helper Infrastructure (`src/web/static/modules/dom.js`), adding `$on(targetOrId, event, handler, options)`, `$show()`, `$hide()`, and `$toggle()` utilities with automated null-guarding (`[REQ-DOM-002]`).
  - Strict XSS Sanitization for Dynamic HTML Content (`src/web/static/modules/studios/chat.js` & `forge.js`), passing all dynamic note, agent, and routine attributes through `escapeHtml()` (`[REQ-DOM-003]`).
  - Automated DOM Architecture Static Lint Rule (`tests/unit/frontend/dom_audit.test.js`), establishing a Vitest static test that parses all frontend JavaScript modules and permanently prevents regressions of raw DOM queries outside `dom.js` (`[REQ-DOM-004]`).

- Playwright CI Pre-Flight Gate & Multi-Studio Navigation Smoke Suite (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - GitHub Actions Continuous Integration Workflow (`.github/workflows/ci.yml`), automating Python 3.12, Node 20, Astral UV caching, Ruff, Pytest, Vitest, and Playwright Chromium smoke gates on every push/PR to `main` and `qa` (`[REQ-SMK-001]`).
  - Multi-Studio Deep Navigation & Element Smoke Assertions (`tests/e2e/smoke.spec.js`), expanding Playwright end-to-end smoke coverage across all 7 studios (Chat, Routines, Observability, Forge, Settings, Docs, Wiki) verifying critical anchors attach without error (`[REQ-SMK-002]`).
  - Interactive Studio Mutation Smoke Checks (`tests/e2e/smoke.spec.js`), exercising non-destructive user interactions including manual topic search, 2D physics Mind Map modal launch/close, New Routine modal, and New Note modal (`[REQ-SMK-003]`).
  - Unified Local Pre-Flight CLI Harness (`.agents/skills/rtm-sync/scripts/preflight.py` & `npm run preflight`), providing a single CLI runner executing all 5 static, unit, integration, smoke, and RTM gates in sequence with formatted summary reporting (`[REQ-SMK-004]`).
  - Playwright Failure Artifacts & Diagnostics Capture (`playwright.config.js` & `.github/workflows/ci.yml`), capturing failure screenshots, console logs, and trace archives in `test-results/` uploaded automatically in CI on test failure (`[REQ-SMK-005]`).

- Frontend Modularization Foundation & Baseline Quality Gates (`AutoReiv.Web`):
  - Native ES Module Decomposition (`src/web/static/app.js`, `src/web/static/modules/`, & `src/web/templates/index.html`), deconstructing the 3,800+ line monolithic `app.js` into isolated ES modules partitioned by concern (`dom.js`, `services/api.js`, `state/store.js`, `utils/`, and individual `studios/` for Chat, Routines, Observability, Forge, Settings, Docs, and Wiki) loaded natively via `<script type="module">` (`[REQ-FE-001]`).
  - Isolated Subsystem Initialization (`src/web/static/app.js`), executing each studio initializer in an independent `try/catch` ring within `initApp()` to ensure faults in one studio cannot crash the primary UI or navigation (`[REQ-FE-002]`).
  - Defensive DOM Query Helpers (`src/web/static/modules/dom.js`), introducing `$(id)`, `$query()`, `$queryAll()`, and `safeCreateIcons()` that log informative console warnings on missing elements rather than throwing uncaught `TypeErrors` (`[REQ-FE-003]`).
  - Pure Logic Utility Extraction & Vitest Test Suite (`src/web/static/modules/utils/` & `tests/unit/frontend/`), isolating pure functions (`debounce`, `formatBytes`, `formatTokenCount`, `formatTimestamp`, `escapeHtml`, `storageGet`, `storageSet`) covered by automated unit tests running in < 300ms (`[REQ-FE-004]`).
  - Playwright Zero-Error Page Load & Multi-Studio Navigation Smoke Gate (`tests/e2e/smoke.spec.js` & `playwright.config.js`), establishing automated headless browser smoke testing asserting zero console errors, zero uncaught page errors, and active tab rendering across all 7 studios (`[REQ-FE-005]`).

- Comprehensive Web UI Tab Hydration & Rendering Hardening (`AutoReiv.Web`):
  - Agent Studio Skill Pack Grid Hydration (`src/web/static/app.js` & `src/web/templates/index.html`), ensuring `renderSkillsCatalog()` deterministically hydrates all 7 skill pack categories and 34 tools on initial and repeated visits regardless of memory caching state (`[REQ-FIX-001]`).
  - System Info Topic Navigation & Viewer Resilience (`src/application/web/system_info_service.py`, `src/web/app.py`, & `src/web/static/app.js`), expanding the topic categories index and displaying default architecture manuals with defensive error boundaries and mobile drawer controls (`[REQ-FIX-002]`).
  - Wiki Studio Vault Auto-Selection & Mobile Navigation (`src/web/templates/index.html` & `src/web/static/app.js`), auto-loading the first available note into Markdown preview on tab load, providing accessible mobile drawer toggles, and ensuring visible action buttons (`[REQ-FIX-003]`).
  - Wiki Mind Map & Graph Canvas Robustness (`src/web/static/app.js` & `src/web/templates/index.html`), introducing viewport bounding fallbacks for 2D canvas sizing and sanitized Mermaid diagram rendering (`[REQ-FIX-004]`).
  - Universal Tab Switching Error Quarantine (`src/web/static/app.js`), wrapping all tab loader triggers inside isolated try/catch boundaries within `switchTab()` (`[REQ-FIX-005]`).

- Chat Studio Agent Selection & Provider Model Discovery Fixes (`AutoReiv.Web` & `AutoReiv.Gateway`):
  - Chat Studio Persistent Multi-Surface Agent Switcher (`src/web/templates/index.html` & `src/web/static/app.js`), introducing an inline `#chatTopBarAgentSelect` dropdown directly in the chat topbar synchronized two-way with the sidebar, and persisting the active agent ID in browser `localStorage` across page reloads and tab navigations (`[REQ-UI-001]`).
  - Multi-Preset Model Discovery & Saved Model Retention (`src/infrastructure/gateway/openai_adapter.py`, `src/infrastructure/gateway/ollama_adapter.py`, `src/web/app.py`, & `src/web/static/app.js`), providing dynamic `provider_id` support across all presets (Ollama, OpenAI, OpenRouter, Anthropic, Groq, DeepSeek, Together, vLLM) and preserving saved custom models in dropdowns (`[REQ-UI-002]`).
- System Observability Live Event Stream, System Agent Root Cause Diagnostics & Librarian Inbox Organization (`AutoReiv.Observability`, `AutoReiv.Skills`, `AutoReiv.Wiki`, & `AutoReiv.Web`):
  - In-Memory System Event Logger & REST Log Buffer (`SystemLogBuffer` in `src/application/observability/log_buffer.py` & `GET /api/observability/logs` in `src/web/app.py`), maintaining a thread-safe 1,000-entry ring buffer capturing all server logs, gateway events, tool calls, and error traces (`[REQ-OBS-007]`).
  - Observability Studio Live Event Terminal UI (`src/web/templates/index.html` & `src/web/static/app.js`), featuring a real-time auto-scrolling log console with level filtering (`ALL`, `INFO`, `WARN`, `ERROR`), search filter, pause/resume toggle, and buffer clear action (`[REQ-OBS-008]`).
  - System Agent Diagnostic Skill Pack & Tooling (`SystemAgentSkill` in `src/application/skills/system_agent_skill.py` & `SYSTEM_AGENT_PROFILE` in `src/domain/agents/profiles.py`), equipping the System Agent with `get_recent_errors`, `get_session_transcript`, `get_agent_sessions`, `test_provider_connectivity`, and `get_system_logs` to diagnose agent failures and network timeouts directly in chat (`[REQ-AGENTS-007]`).
  - Librarian Inbox Triage & Organization Engine (`WikiStore.organize_note` in `src/domain/wiki/store.py`, `LibrarianSkill.organize_wiki_note` in `src/application/skills/librarian_skill.py`, & `LIBRARIAN_PROFILE` in `src/domain/agents/profiles.py`), empowering the Librarian to atomically move staged notes from `inbox/` to permanent `notes/<domain>/<topic>/` taxonomy with complete 35-field YAML frontmatter hydration (`[REQ-WIKI-010]`).
- Mobile-First Responsive Layout & Sticky Viewport Overhaul (`AutoReiv.Web`):
  - Dynamic `100dvh` Viewport & Sticky Chat Input Bar (`src/web/templates/index.html` & `src/web/static/app.js`), anchoring root layout height to `100dvh` across mobile browsers, preventing whole-page scroll bouncing, isolating message stream scrolling to `#messagesContainer`, and pinning the prompt textarea bar firmly at the bottom above virtual keyboards (`[REQ-RESP-001]`).
  - Responsive Off-Canvas Split Drawers for Wiki Studio & System Info (`#wikiDrawerPane` & `#docsDrawerPane`), converting desktop sidebars into slide-over mobile drawers with quick toggle buttons (`[Γëí╞Æ├┤├╝ Vault Tree]` / `[╬ô├┐Γûæ Topics]`) and automatic auto-collapse upon note/topic selection (`[REQ-RESP-002]`).
  - Mobile Touch Physics Canvas & Fullscreen Modal Sheets (`src/web/static/app.js`), providing single-finger touch drag, two-finger pinch-to-zoom for the 2D Mind Map, and responsive modal sheet sizing across all mobile viewports (`[REQ-RESP-003]`).
- Chat to Wiki Direct Inbox Export & Flat Staging Vault Structure (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Flat Inbox Staging Engine (`WikiStore` in `src/domain/wiki/store.py` & `WikiService` in `src/application/wiki/service.py`), eliminating priority subfolders (`need_to_do`, `should_do`, `want_to_do`) in favor of direct, zero-friction flat file staging under `data/wiki/inbox/<slug>.md` (`[REQ-WIKI-007]`).
  - Unified Chat-to-Wiki Inbox Artifact Generation (`POST /api/export/wiki` in `src/web/app.py` & `src/web/static/app.js`), routing single message "Save to Wiki" and full conversation "Export to Wiki" actions directly through `WikiService` to generate structured 35-field YAML frontmatter notes in `inbox/` (`[REQ-WIKI-008]`).
  - Flat Inbox Tree Navigation & Simplified New Note Modal (`src/web/static/app.js` & `src/web/templates/index.html`), rendering all staged inbox notes directly under `inbox (Staging) (X)` without intermediate priority group nesting (`[REQ-WIKI-009]`).
- Provider & Model Settings Persistence & Hydration (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Model Choice Persistence Contract (`ProviderSettingsRequest` & `GET /api/settings` / `POST /api/settings/providers` in `src/web/app.py`), persisting `default_model_id` in SQLite and synchronizing with Gateway fallback resolution (`[REQ-SET-007]`).
  - Settings Studio Model Selection Retention & Auto-Hydration (`src/web/static/app.js`), preserving selected model dropdown values across manual saves, provider switching, dynamic catalog queries, and page reloads (`[REQ-SET-008]`).
- Wiki Studio Interactive Obsidian-Style Mind Map & Tree Navigation (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Nested Degree & Subject Tree Expand/Collapse Engine (`src/web/static/app.js`), rendering Degree Level 1 (`<domain>`) and Subject Level 2 (`<topic>`) folders as independent interactive collapsible buttons with chevrons, open/closed folder indicators, note count badges, and auto-expanded initial discovery state (`[REQ-MIND-001]`).
  - Multi-Dimensional Knowledge Graph Engine & REST API (`WikiStore.get_mindmap()` in `src/domain/wiki/store.py` & `GET /api/wiki/mindmap` in `src/web/app.py`), extracting heterogeneous node entities (Notes, Tags `#tag`, Degree Domains, Subject Topics) and typed relation edges (`wikilink`, `has_tag`, `in_topic`, `in_domain`) (`[REQ-MIND-002]`).
  - Obsidian-Style Interactive 2D Physics Canvas Mind Map Explorer (`#wikiMindMapModal` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring velocity-Verlet Coulomb particle simulation, spring tension physics, live search filtering, entity dimension toggle pills (Notes, Tags, Domains, Topics), repulsion slider, smooth pan/zoom, interactive hover tooltips with note telemetry, and direct click-to-open note navigation (`[REQ-MIND-003]`).
- Wiki Document Management System & Librarian Architecture (`AutoReiv.Wiki`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Local-First Degree/Class Taxonomy & Scaffolding Engine (`WikiStore` in `src/domain/wiki/store.py`), organizing human documents into `inbox/` (`need_to_do`, `should_do`, `want_to_do`), `notes/<domain>/<topic>/` (Degree/Field Level 1, Subject/Class Level 2), and `resources/` (`operating_manuals`, `templates`) with path jailing (`[REQ-WIKI-001]`).
  - 35-Field Additive YAML Frontmatter Schema Standard & Telemetry Engine (`FrontmatterParser` & `WikiNoteMeta` in `src/domain/wiki/frontmatter.py`), auto-computing immutable timestamp UIDs (`YYYYMMDD-HHMMSS`), word count, and token telemetry ($round(max(chars / 4, words \times 0.75))$) (`[REQ-WIKI-002]`).
  - Non-Destructive Note Modification Engine (`WikiStore.write_note()`), preserving existing YAML metadata and relations while safely updating note content and bumping `last_updated` (`[REQ-WIKI-003]`).
  - Knowledge Graph & WikiLink Extraction Engine (`WikiStore.get_graph()`), parsing `[[wikilink]]` references across markdown bodies to build interconnected network nodes and edges (`[REQ-WIKI-004]`).
  - Upgraded Librarian Skill & Scoped Tool Grants (`LibrarianSkill` in `src/application/skills/librarian_skill.py`), providing tools for `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, and `wiki_graph` (`[REQ-WIKI-005]`).
  - Interactive Wiki Studio Web Interface & REST Endpoints (`#view-wiki` in `src/web/templates/index.html`, `src/web/static/app.js`, and `src/web/app.py`), featuring hierarchical tree navigation, markdown preview and editor, YAML Frontmatter Inspector card, new note modal, and knowledge graph visualization (`[REQ-WIKI-006]`).
- System Info Conceptual Knowledge Hub & Architectural Manual (`AutoReiv.Web` & `AutoReiv.Docs`):
  - Curated System Info Topic Catalog & Service (`SystemInfoService` in `src/application/web/system_info_service.py` & `GET /api/system-info/topics`, `GET /api/system-info/topic/{id}`), delivering structured, educational chapters with rich Markdown and interactive Mermaid diagrams (`[REQ-SYST-001]`).
  - System Info UI Sidebar & Interactive Reader (`[╬ô├ñΓòúΓê⌐Γòò├à System Info]` in `src/web/templates/index.html` and `src/web/static/app.js`), featuring categorized topic groups, real-time search filtering, deep links, and Mermaid Pan-Tilt-Zoom inspection (`[REQ-SYST-002]`).
  - Formal 5-Tier Architectural Hierarchy Reference Manual (`[REQ-SYST-003]`), clearly distinguishing and explaining the interactions between **Agents** (Autonomous Personas), **Workflows** (Multi-step Goal DAGs), **Routines** (Background Cron Jobs), **Skill Packs** (Domain Capability Bundles), and **Atomic Tools** (Pydantic / JSON-RPC Function Contracts).
- Lean Just-In-Time (JIT) Agent Discovery & Isolated Subagent Handoff Engine (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Just-In-Time (JIT) Agent Directory Indexer (`AgentDirectoryService` in `src/application/orchestration/directory_service.py`), dynamically searching and ranking built-in profiles and custom SQLite agents by capability keywords, specialization summaries, and authorized skill tags without pre-loading fleet manifests into system prompts (`[REQ-ORCH-001]`).
  - Ultralight 2-Primitive Orchestration Skill (`OrchestrationSkill` in `src/application/skills/orchestration_skill.py`), exposing `lookup_agents(query, limit=3)` returning compact Agent Cards (<60 tokens) and `handoff_to_agent(target_agent_id, task_directive, input_payload)` adhering to strict schema contracts (`[REQ-ORCH-002]`).
  - Isolated Context Execution & Anti-Recursion Engine (`HandoffIsolationEngine` in `src/application/orchestration/handoff_engine.py`), executing subagents in clean 0-turn contexts, bounding execution turns (1╬ô├ç├┤10), enforcing a maximum recursion depth limit of 2 tiers, and rejecting circular self-handoff deadlocks (`[REQ-ORCH-003]`).
  - Real-Time Handoff Telemetry & Chat UI Affordance (`src/web/app.py`, `src/web/templates/index.html`, `src/web/static/app.js`), emitting streaming events and rendering live subagent delegation status pills in Chat Studio showing the target agent, directive, and completion state (`[REQ-ORCH-004]`).
- System Documentation Folder Tree Navigation & Interactive Mermaid Pan-Zoom Inspector (`AutoReiv.Web`):
  - Nested Folder Tree Navigation API (`SystemDocumentationService.get_navigation_tree()` in `src/application/web/system_docs_service.py`), organizing platform specifications into milestone subfolders with `requirements.md`, `design.md`, and `tasks.md` children, ADRs, SDLC rules, and RTM metadata (`[REQ-DOCS-001]`).
  - Interactive Collapsible Folder Tree Sidebar UI (`#view-docs` & `renderDocsNav()` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring folder chevron toggles, open/closed folder icons, child file counts, active document highlighting, and real-time deep search filtering (`[REQ-DOCS-002]`).
  - Interactive Mermaid Diagram Hover Overlay & High-Resolution Modal Inspector (`#mermaidZoomModal` in `src/web/templates/index.html` & `src/web/static/app.js`), attaching hover action buttons (`[Γëí╞Æ├╢├¼ Inspect & Zoom]`) to all rendered Mermaid diagrams in documentation and chat streams (`[REQ-DOCS-003]`).
  - Smooth Pan-Tilt-Zoom (PTZ) Engine (`src/web/static/app.js`), supporting mouse-wheel zooming (20% to 500%), click-and-drag canvas panning, zoom toolbar controls (`+`, `-`, `╬ô├ÑΓòæ 100% Reset`), and fullscreen toggle (`[REQ-DOCS-004]`).
- Skill Pack Hierarchy, Deterministic Guardrails, and System Documentation Browser (`AutoReiv.Skills`, `AutoReiv.Agents`, & `AutoReiv.Web`):
  - Hierarchical Skill Pack Manifests and Catalog Aggregator (`src/application/skills/manifest.py`), clustering 20+ atomic tools into cohesive, categorized Skill Packs (`Sysadmin`, `Librarian`, `Verification`, `Planning`, `AgentBuilder`, `Orchestration`, `General & Custom`) (`[REQ-SKIL-001]`).
  - Agent Forge Hierarchical Skill Pack UI with Expandable Tool Cards (`#view-agents` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring one-click bundle checkboxes, automatic indeterminate state propagation, and granular tool-level RBAC (`[REQ-SKIL-002]`).
  - Deterministic Agent Specification Guardrail Engine (`AgentProfileGuardrail` in `src/domain/agents/guardrails.py`), enforcing strict invariants across `AgentBuilderSkill`, `POST /api/agents`, and `PUT /api/agents/{id}`: kebab-case regex slug validation, anti-hallucination tool catalog verification, `ModelPurpose` and `AgentTone` domain checking, and 1-50 turn bounding (`[REQ-SKIL-003]`).
  - System Documentation & Specs Navigation REST API (`SystemDocumentationService` in `src/application/web/system_docs_service.py` & `GET /api/docs/nav`, `GET /api/docs/content`), safely indexing repository specs (`docs/specs/`), Architecture Decision Records (`docs/adr/`), SDLC rules, and RTM matrices with strict directory traversal prevention (`[REQ-SKIL-004]`).
  - Control Plane System Documentation & Specs Browser View (`#view-docs` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring a searchable multi-section document tree, real-time query filtering, and rich Markdown rendering with GitHub alerts and code syntax blocks (`[REQ-SKIL-005]`).
- Routine Management, Dual Cron Humanization, and Agent Forge Binding (`AutoReiv.Routines` & `AutoReiv.Web`):
  - Dual Cron Schedule Humanizer & Next-Run Calculator (`src/application/routines/humanizer.py`) bidirectionally translating cron expressions (`0 * * * *`, `*/15 * * * *`, `0 8 * * *`) into clean English (e.g., _"Every 15 minutes"_, _"Daily at 08:00 UTC"_) with next execution ETA countdown calculations (`[REQ-ROUT-001]`).
  - Full Routine REST API CRUD, Toggle, and Trigger Endpoints (`POST /api/routines`, `PUT /api/routines/{id}`, `DELETE /api/routines/{id}`, `POST /api/routines/{id}/toggle`, `POST /api/routines/{id}/run`, `GET /api/routines?agent_id=...`) with built-in baseline routine protection (`[REQ-ROUT-002]`, `[REQ-ROUT-003]`).
  - Routines Studio Management UI (`#view-routines` in `src/web/templates/index.html` & `src/web/static/app.js`) with frequency presets, live humanizer preview, directive prompts, active status badges, and action controls (`[╬ô├╗ΓòóΓê⌐Γòò├à Run Now]`, `[╬ô┬ú├àΓê⌐Γòò├à Edit]`, `[╬ô├àΓòòΓê⌐Γòò├à Pause/Resume]`, `[Γëí╞Æ├╣├ªΓê⌐Γòò├à Delete]`) (`[REQ-ROUT-004]`).
  - Agent Forge "Assigned Routines" Character Sheet Integration (`#forgeAssignedRoutinesList` in `src/web/templates/index.html` & `src/web/static/app.js`) rendering all standing jobs led by the selected agent with direct run and edit triggers (`[REQ-ROUT-005]`).
- Dynamic Purpose-Based Model Cascade & "Agent Forge" Character Sheet Studio (`AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - 3-Tier Purpose-to-Model Resolution Cascade (`Agent Kernel -> Agent Profile Override -> Purpose Matrix Slot -> Global Default Model`) implemented in `AgentKernel._resolve_model()`.
  - SQLite Custom Agent Persistence & Scoped Registry (`custom_agents` table in `SQLiteStateStore` and `BuiltinAgentRegistry`), supporting full CRUD operations, built-in baseline agent protection, and operator override overlays.
  - System Agent Meta-Builder Skill (`AgentBuilderSkill` in `src/application/skills/agent_builder_skill.py`) exposing `list_available_skills_and_tools`, `propose_agent_specification`, and `save_agent_specification` to `system-agent`.
  - REST Agent Management Endpoints: `GET /api/skills/catalog`, `GET /api/agents`, `GET /api/agents/{id}`, `POST /api/agents`, `PUT /api/agents/{id}`, and `DELETE /api/agents/{id}`.
  - "Agent Forge" Studio Character Sheet SPA UI (`#view-agents` in `src/web/templates/index.html` and `src/web/static/app.js`) featuring compartmentalized RPG character sheet cards (Identity & Avatar, Persona & Tone, Operating Manual System Prompt, Purpose Matrix & Model Override, Authorized Skill Capability Checkboxes, Real-time Lifetime Telemetry Stats).
  - Embedded System Agent AI Architect Co-Pilot with live streaming advice, quick starter chips (K8s SRE, Postgres DBA, Security Auditor), and one-click `[╬ô┬ú┬┐ Apply to Sheet]` blueprint synthesis.
- Unified Settings Studio, Provider Presets & Model Matrix (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Standard `ProviderPresetRegistry` (`src/application/settings/presets.py`) providing built-in presets for Ollama, OpenAI, Anthropic Claude, OpenRouter, Groq Cloud, DeepSeek, Together AI, and vLLM / Local with auto-populated default base URLs.
  - Dynamic Model Discovery endpoint `GET /api/models/discover` querying installed and cloud models across active providers with live hardware RAM fit evaluation.
  - Active Default Model Picker in Settings Studio allowing operators to discover models and persist the default platform model.
  - Harmonized Purpose-Based Model Routing with auto-populated dropdowns bound directly to discovered models.
  - Live Hardware Fit & Sizing Table displaying model parameter size, quantization format, estimated RAM in GiB, and status classification tags (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`, `cloud`).
- Plan-and-Execute Graph Engine & Goal Mode (`AutoReiv.Kernel`, `AutoReiv.Planning`, & `AutoReiv.Web`):
  - Structured `ExecutionPlan` and `PlanStep` domain models (`src/domain/planning/models.py`) with lifecycle states (`pending`, `in_progress`, `completed`, `failed`).
  - `PlanAndExecuteEngine` (`src/application/kernel/plan_engine.py`) deconstructing complex multi-phase user goals into ordered 2-to-6 step milestone DAGs and executing them sequentially with intermediate synthesis.
  - `PlanningSkill` (`src/application/skills/planning_skill.py`) providing dynamic plan modification tools (`mark_plan_step_completed`, `append_plan_step`, `get_active_plan`).
  - REST endpoint `POST /api/chat/goal` for goal formulation and autonomous multi-step execution.
  - Companion Web UI controls (`[╬ô┬ú├┤] Γëí╞Æ├ä┬╗ Goal Mode (Plan Graph)`), `/goal <instruction>` slash command parser, and live visual milestone checklist rendering in chat.
- Reflexive Self-Verification Loops & SRE Health Auditing (`AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Agents`):
  - Deterministic `VerificationSkill` (`src/application/skills/verification_skill.py`) exposing ground-truth assertion tools: `verify_telemetry_consistency`, `assert_json_schema`, and `validate_metric_bounds`.
  - Iterative `ReflexionLoopEngine` (`src/application/kernel/reflexion_engine.py`) catching verification discrepancies, feeding structured critique notes back to the model, and orchestrating multi-turn autonomous refinement loops (up to 3 attempts).
  - Kernel verified execution methods `kernel.run_verified_turn` and integration into `AgentKernel`.
  - Built-in `auditor-critic` agent profile (`src/domain/agents/profiles.py`) specialized in zero-shot adversarial reviews, risk scoring (1-10), and assumption validation.
  - REST endpoints `POST /api/chat/verified` and `POST /api/agents/audit` for verified execution and external audit pipelines.
- Model Context Protocol (MCP) Client Adapter & Dynamic Skill Loader (`AutoReiv.MCP` & `AutoReiv.Skills`):
  - Standard JSON-RPC 2.0 `MCPClientAdapter` (`src/infrastructure/mcp/client_adapter.py`) managing stdio subprocess transports, tool discovery (`tools/list`), and execution (`tools/call`).
  - Dynamic `SKILL.md` parser `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) discovering YAML frontmatter and JSON tool manifests.
  - `mount_mcp_tool` integration in `ScopedToolRegistry` dynamically binding MCP tools with RBAC enforcement.
  - SQLite persistent MCP server registry and REST routes `GET /api/mcp/servers` and `POST /api/mcp/servers`.
- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation (`AutoReiv.Orchestration`):
  - Standardized 5-Key `HandoffEnvelope` domain model (`src/domain/orchestration/models.py`) transferring intent and hydrated context across agent boundaries.
  - `SupervisorOrchestrator` (`src/application/kernel/supervisor_orchestrator.py`) managing specialist agent dispatch, execution, and response synthesis.
  - `DelegateSubtaskSkill` (`src/application/skills/delegate_skill.py`) exposing `delegate_task` tool to allow coordinator agents to route sub-problems.
  - `handoff` telemetry spans linking parent session, sender, recipient, and correlation IDs.
  - REST endpoint `POST /api/agents/delegate` for direct external invocation of specialized workflows.
- Ephemeral Subprocess Sandbox & HITL Approvals (`AutoReiv.Safety` & `AutoReiv.Kernel`):
  - `DangerousCommandFilter` (`src/application/skills/command_filter.py`) statically rejecting destructive commands (`rm -rf /`, `dd`, `mkfs`, `format c:`, raw DB drop queries).
  - `SandboxedSubprocessWorker` (`src/application/skills/sandbox_worker.py`) executing CLI commands and Python scripts within isolated temporary directories with strict timeouts and cleanup.
  - `is_high_risk` tool metadata and `HITLApprovalEngine` (`src/application/kernel/hitl_engine.py`) parking execution awaiting human operator decisions.
  - SQLite `pending_approvals` table and REST endpoints (`GET /api/approvals/pending`, `POST /api/approvals/{id}/decision`) to approve or reject parked tool calls.
  - Real-time streaming cancellation endpoint (`POST /api/chat/stream/{session_id}/abort`) to abort in-flight agent reasoning loops.
- Context Window Compaction & Episodic Memory (`AutoReiv.Memory` & `AutoReiv.Kernel`):
  - `ContextCompactor` (`src/application/kernel/context_compactor.py`) implementing sliding-window message preservation, intermediate turn summarization, and large tool output pruning (>8000 chars) to prevent context window overflow.
  - `episodic_facts` SQLite table and `EpisodicMemorySkill` (`src/application/skills/memory_skill.py`) storing discrete cross-session facts (user preferences, environment settings).
  - Gateway transient error resilience with localized exponential backoff and randomized jitter in `MultiProviderGateway._execute_with_retry`.
  - HTTP persistent client connection pooling (`httpx.Limits(max_keepalive_connections=20)`) in `OllamaProviderAdapter` and `OpenAIProviderAdapter`.
  - `CycleDetector` (`src/application/kernel/cycle_detector.py`) enforcing repetition trap detection across both synchronous `run_turn` and real-time `stream_turn`.
- Multi-OS Packaging & Bare-Metal / Docker Deployment (`AutoReiv.Deploy`): Unified CLI tool (`autoreiv`), background routine engine server lifespan, Ubuntu systemd daemon, Windows service scripts, and Docker Compose with persistent volume mounts.
- Unified CLI entry point (`src/cli/main.py`) with commands:
  - `autoreiv serve`: Launches FastAPI web server and routine tick engine.
  - `autoreiv status`: Reports host CPU/RAM specs, database connectivity, and registered agents.
  - `autoreiv chat`: Interactive terminal chat loop with live token streaming.
  - `autoreiv routine [list|run]`: Direct terminal management and one-shot trigger of background routines.
- FastAPI `lifespan` context manager running `RoutineScheduler` background task concurrently with web request handling.
- Ubuntu / Debian `systemd` daemon unit file (`deploy/systemd/autoreiv.service`) and automated installer (`deploy/systemd/install_systemd.sh`) optimized for Mini PC bare-metal deployment.
- Windows PowerShell runner (`deploy/windows/run_autoreiv.ps1`), batch runner (`run_autoreiv.bat`), and service registration script (`install_windows_service.ps1`).
- Multi-stage production `Dockerfile` with non-root security user, health check, and `docker-compose.yml` with host volume mounts for persistent database (`./data/autoreiv.db`) and wiki documents (`./data/wiki`).
- Environment variable configuration template (`.env.example`) documenting `OLLAMA_HOST`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH`, and `PORT`.
- Responsive Web & Mobile Front-Door with Wiki Export (`AutoReiv.Web`): Complete zero-build Single-Page Application (SPA) with real-time SSE streaming, collapsible `<think>` tags, and one-click PARA-Wiki markdown export.
- FastAPI application backend (`src/web/app.py`) providing unified REST and SSE endpoints for agents, sessions, chat streaming, wiki note export, settings matrix, KPI dashboard metrics, and autonomous routine triggers.
- `WikiExportService` (`src/application/web/wiki_export_service.py`) generating formatted markdown documents with YAML frontmatter and enforcing path-jailed security.
- Modern responsive desktop and mobile interface (`src/web/templates/index.html`, `src/web/static/app.js`) with tabbed workflows:
  - Γëí╞Æ├å┬╝ **Interactive Chat**: Live token streaming, reasoning `<think>` toggle bubbles, and real-time tool execution status indicators.
  - Γëí╞Æ├┤├ñ **One-Click Action Buttons**: "Export to Wiki" and "Copy to Clipboard" buttons on both full threads and individual assistant replies.
  - ╬ô├àΓûæ **Routines Studio**: Active schedule monitoring, status indicators, and manual "Run Now" execution triggers.
  - Γëí╞Æ├┤├¿ **Observability Dashboard**: High-level platform KPI cards, per-agent resource consumption table, and tool reliability matrix.
  - ╬ô├£├ûΓê⌐Γòò├à **Settings Studio**: Live provider model picker, purpose matrix configuration, and interactive hardware RAM fit calculator (with custom specs input for 128GB Nimo PC).
- Observability & KPI Dashboard Backend (`AutoReiv.Observability`): Comprehensive telemetry aggregation, per-agent breakdowns, tool reliability matrices, timeline charts, and structured JSON export.
- `ObservabilityDashboardService` for unified platform KPI calculation (total turns, prompt/completion tokens, avg turn latency, error rate percentage).
- Per-agent segregated KPI breakdown reporting turns, token usage, tool invocations, and error counts.
- `ToolReliabilityMetric` matrix tracking tool call frequencies, failure rates, and average duration.
- Time-series metric aggregation into hourly and customizable timeline buckets.
- `TraceExporter` for structured JSON and session trace dumping without external SaaS dependencies.
- Indexed SQLite analytical queries on `telemetry_spans(agent_id, span_type, created_at)`.
- Settings Studio Engine (`AutoReiv.Settings`): Dynamic live model discovery, purpose matrix routing, and hardware fit estimation.
- Live model discovery on `OllamaProviderAdapter` (`/api/tags`) and `OpenAIProviderAdapter` (`/v1/models`) with parameter size and quant level extraction.
- Purpose-Based Model Routing (`ModelPurposeMatrix`) for `GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, and `FAST` operational roles.
- `HardwareFitCalculator` predicting model RAM footprint (weight bits + KV cache headroom) and classifying host fit (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`) with custom specs overrides (e.g. 128GB Nimo PC).
- `SettingsService` for unified settings key-value management and runtime agent persona/tone/prompt customizations (`AgentCustomization`).
- SQLite persistence tables (`settings` and `agent_overrides`) for zero-loss configuration storage across application restarts.
- Autonomous Routine Engine & Background Scheduler (`AutoReiv.Routines`).
- Declarative `Routine` and `RoutineRun` models with interval and cron schedule configurations.
- SQLite persistence for routine configurations and chronological execution run histories (`routines` and `routine_runs` tables).
- `ScheduleMatcher` for deterministic interval and cron due time calculations.
- `RoutineExecutor` for isolated autonomous session execution via `AgentKernel` and automatic telemetry span recording.
- `RoutineScheduler` with non-blocking async tick loop and manual out-of-schedule trigger API.
- 4 Day-1 default routine manifests: Morning Briefing, Daily System Info, Nightly Note Hygiene, and Hourly SRE Pulse.
- 4 Built-In Agent Manifests (`AutoReiv.Agents`): General Assistant, Linux Sysadmin, Librarian, and System Agent.
- `TaskTrackerSkill` with SQLite-backed task CRUD (`create_task`, `list_tasks`, `update_task_status`, `delete_task`).
- `SysadminSkill` with cross-platform host metrics (`get_system_info`) and asynchronous timeout-protected command execution (`cli_exec`).
- `LibrarianSkill` with YAML frontmatter parser and path-jailed PARA-Wiki note creator (`wiki_note_create`, `wiki_note_read`, `wiki_note_list`).
- `SystemAgentSkill` providing platform health diagnostics, database latency testing, and token usage summaries.
- `BuiltinAgentRegistry` for one-line ecosystem bootstrapping and automatic scoped tool binding.
- Agent Kernel & ReAct execution engine (`AutoReiv.Kernel`) supporting multi-turn tool loops, cycle detection, and max turn budgeting.
- Declarative `AgentProfile` manifest with configurable `AgentTone` prompt directive formatting.
- `ScopedToolRegistry` with strict Role-Based Access Control (RBAC) tool execution permissions.
- `SQLiteStateStore` with WAL mode (`AutoReiv.Memory`) for chronological conversation checkpointer and session management.
- `TelemetryCollector` and `TelemetrySpan` tracking per-agent token usage, tool reliability/error metrics, and global platform KPIs.
- Real-time streaming `KernelEvent` generator for tokens, tool execution starts, tool outputs, and turn completions.
- Multi-Provider LLM Gateway (`AutoReiv.Gateway`) with unified message schema (`ChatMessage`, `Role`, `ToolCall`).
- Abstract `LLMProviderPort` protocol and dynamic provider registry.
- `OllamaProviderAdapter` for local/LAN Ollama execution with streaming and tool calling.
- `OpenAIProviderAdapter` for OpenAI-compatible cloud/local endpoints with SSE streaming.
- `MultiProviderGateway` orchestrator with multi-model fallback execution chains.
- `ReasoningDemuxer` for splitting `<think>...</think>` tokens in real-time streams.
- `GatewayProviderFactory` for zero-boilerplate initialization from environment variables.
- 55 hermetic unit tests with mock HTTP transports and zero outbound network calls.
