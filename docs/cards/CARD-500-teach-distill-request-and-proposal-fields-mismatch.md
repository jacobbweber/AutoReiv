---
id: CARD-500
title: "Teach: typed lesson ignored, wrong turn distilled, /learn 422, proposal card shows placeholder text"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-472
  - CARD-352
  - CARD-358
  - CARD-497
  - CARD-502
  - CARD-503
labels:
  - type:bug
  - area:chat
  - area:skills
  - P1
---

# [CARD-500] Teach: typed lesson ignored, wrong turn distilled, /learn 422, proposal card shows placeholder text

> **Status**: Ready (refined 2026-09-25 after Jacob said **continue**; plan only, no code)
> **Created**: 2026-09-25 (found while building CARD-472)
> **Related**: CARD-472 (moved Teach to `chat/teach_modal.js`), CARD-352 / CARD-358 (Teach and proposal persistence), CARD-497 (renames `factory_escalation` to `tool_escalation`), CARD-502 (Adopt does not go live and is lost on restart), CARD-503 (distill timeout fallback is silent)
> **Labels**: `type:bug`, `area:chat`, `area:skills`, `P1` (raised from P2: every Teach today produces a lesson built from the wrong input)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 0. Reproduction (2026-09-25, scratch server only)

Setup: `scratch/c500_run.ps1` starts a fake Ollama (`scratch/c500_fake_gateway.py`, port 18434) that logs exactly what the distiller is told and answers with a fixed proposal whose slip starts "FAKE SLIP". The app runs from `scratch/c500_serve.py` on 127.0.0.1:8767 with every data path under `scratch/c500_data` (same guard as `scripts/smoke_server.py`; refuses live AppData). Drivers: `scratch/c500_ui.cjs` (desktop + phone UI), `scratch/c500_ui2.cjs` (correct-field control, needs-tool card, Ask Developer). Results: `scratch/c500_desktop.json`, `scratch/c500_phone.json`, `scratch/c500_ui2.json`, `scratch/c500_gateway.log`.

| # | Step | What happened |
|---|------|---------------|
| R1 | Teach on the **first** reply, type `ALWAYS-CITE-SOURCES`, Distill (desktop and phone) | Request body `{session_id, message_id, target_agent_id, operator_guidance}`. The model was told `Human Guidance / Correction: Auto-diagnose from turn context`: **the typed lesson never arrived** |
| R2 | Same step: which turn was distilled | Model was told `User Prompt: DESKTOP second question` (the **latest** turn, not the clicked one). On phone (session with 10 replies) Teach on the first reply distilled `SKILLCHECK one`, an arbitrary later turn |
| R3 | Proposal card | Title "Skill Proposal: **Synthesized Skill**", slip "Operational friction detected during turn.", remedy "Standardized procedure defined in runbook." The response had `name: "Cite Sources"` and `plain_summary.observed_slip: "FAKE SLIP: ..."`; none of it shown. The raw runbook is correct |
| R4 | Control: POST the same distill with `guidance` instead of `operator_guidance` | Model was told `Human Guidance / Correction: PROPER-GUIDANCE-FIELD`. Backend path works; only the field name is wrong |
| R5 | Adopt | 200, `file_path: packs/autoreiv/skills/cite-sources/SKILL.md`, written to `scratch/c500_data/packs/autoreiv/skills/cite-sources/SKILL.md` (user-data packs). `platform-packs/` in the checkout untouched (`git status` clean). Toast "Skill mounted to autoreiv. Active for your next message." |
| R6 | Next message after Adopt | The skill index in the next system prompt lists the pack's runbooks but **not** Cite Sources; `GET /api/agents/autoreiv` `allowed_skill` lacks it. After a restart (data kept) `pack.json` no longer lists it either. Filed as **CARD-502** |
| R7 | `/learn be shorter` | Teach opens with "be shorter" filled in. Distill returns **422** (`message_id: null`, "Input should be a valid string"); toast **"Distillation failed: [object Object]"**; modal stays open |
| R8 | Needs-tool proposal (made through the correct field, since R1 means the UI cannot produce one) | Card shows **Adopt Skill** + Ask Developer + Dismiss. Adopt posts `skill_id: "synthesized-skill"`, `runbook_markdown: ""`, `session_id: null` and gets **422**; history cards pass no toast function, so **nothing is shown** |
| R9 | Ask Developer on that card | `POST /api/tools_studio/authoring/talk` 200 with tool name, intent and objectives; chat switches to Developer. **No Factory request from the Teach flow**. The only Factory traffic is page load (`factory.js`, `GET /api/agent_training_factory/jobs`), removed by CARD-496 |

## 1. Root causes (file and line, qa `0e045c8a`)

1. **Guidance field name.** `chat/teach_modal.js` L83-84 sends `target_agent_id` and `operator_guidance`. `DistillSkillRequest` (`src/web/routers/skills.py` L262-265) has `session_id`, `message_id`, `guidance`; Pydantic drops unknown keys, so `payload.guidance` (L300) is `None`.
2. **Wrong turn.** `SkillDistillationService._extract_turn_history` (`src/application/skills/distillation_service.py` L156-214) never uses `message_id` to pick the turn. It loads `store.get_messages(session_id, limit=20)` (L172), which is `ORDER BY sequence_num ASC LIMIT 20` (`src/infrastructure/memory/repositories/sessions.py` L302-312), the **first** 20 messages, then walks them newest-first (L186) and takes the first user and assistant it meets. `message_id` is only used to read the agent id (L179). Tool results from the whole window are collected (L200-206), not only the clicked turn's.
3. **`/learn` has no message.** `chat/composer.js` L369-377 opens Teach with `{targetAgentId, guidance}` and no `messageId`; `message_id` is required (`skills.py` L264).
4. **Unreadable errors.** `teach_modal.js` L89 and `render.js` L347 do `new Error(err.detail || ...)`. A 422 `detail` is an array, which prints as `[object Object]`.
5. **Card reads flat fields.** `renderSkillProposalCard` (`chat/render.js` L245-248) reads `proposal.skill_name`, `proposal.observed_slip`, `proposal.remedy`. The service returns `name` and `plain_summary.{observed_slip, remedy}` (`distillation_service.py` L293-296, L347-357, L389-399).
6. **Needs-tool card offers Adopt.** `render.js` L298-302 always renders the Adopt button; for `needs_tool` the service returns `runbook_markdown: null`, `skill_id: null` (L310-320) and `AdoptSkillRequest` requires both (L269-271).
7. **History cards are second-class.** `render.js` L692 calls `renderSkillProposalCardFn(proposalData, { container })` with no `sessionId`, `activeAgentId` or `showToastFn`, so Adopt from history sends `session_id: null` and fails silently.

Factory retirement: the Teach flow already routes needs-tool proposals to the Developer (CARD-472). The payload key `factory_escalation` (service L245, L299, L315; card `data-factory-escalation`) is renamed by CARD-497 (REQ-497-005, reading the old name too). CARD-500 must not add any Factory call or new use of the name.

## 2. Four Beats

**Beat 1: What Jacob means.** When I teach an agent from a reply, it learns from that reply and from what I typed, the card tells me in plain words what went wrong and what the new rule is, and `/learn` works too.

**Beat 2: What AutoReiv does now.** It throws away what I typed, looks at the wrong turn (usually the latest one, sometimes a random older one in long chats), and shows a card with a generic title and placeholder sentences. `/learn` fails with "[object Object]". A needs-tool card offers an Adopt button that silently fails.

**Beat 3: What will change.** Teach sends my lesson in the field the server reads. The server distills the turn I clicked (that reply and the user message before it). `/learn` uses the latest reply, or says plainly there is none yet. The card shows the real skill name, slip and remedy. A needs-tool card only offers "Ask Developer to build this tool" and Dismiss. Errors read like sentences. History cards behave like live ones.

**Beat 4: What dies.** The ignored lesson, the wrong-turn diagnosis, the `[object Object]` toast, the placeholder card text, and the Adopt button that cannot work.

## 3. Acceptance criteria (EARS)

- **[REQ-500-001]** WHEN Jacob submits Teach, THE SYSTEM SHALL send `{session_id, message_id, guidance}` to `POST /api/skills/distill`, and the distiller SHALL receive the typed guidance verbatim.
- **[REQ-500-002]** WHEN Distill is called with a `message_id`, THE SYSTEM SHALL build the turn from that message and the user message immediately before it (plus that turn's tool calls and results), regardless of how many messages the session holds.
- **[REQ-500-003]** IF `message_id` is not an assistant message in that session, THEN THE SYSTEM SHALL return 404 with a plain reason and SHALL NOT fall back to another turn.
- **[REQ-500-004]** WHEN Jacob sends `/learn <text>` in a chat that has an assistant reply, THE SYSTEM SHALL open Teach for the latest assistant reply with `<text>` filled in. IF the chat has no assistant reply, THEN THE SYSTEM SHALL show "Send a message first, then teach from the reply." and SHALL NOT call Distill.
- **[REQ-500-005]** WHEN Distill or Adopt fails, THE SYSTEM SHALL show a readable reason (string `detail`, `detail.message`, or the first validation `msg`), never `[object Object]`.
- **[REQ-500-006]** THE proposal card SHALL show the skill `name`, and `plain_summary.observed_slip` / `plain_summary.remedy`, falling back to the flat fields and then to the current defaults.
- **[REQ-500-007]** WHILE a proposal has `needs_tool: true`, THE card SHALL NOT show Adopt; it SHALL show "Ask Developer to build this tool" and Dismiss.
- **[REQ-500-008]** THE proposal card rendered from history SHALL receive the session id, active agent and toast function, so Adopt and errors behave as on a live card.
- **[REQ-500-009]** THE Teach flow SHALL make no request to `/api/agent_training_factory/*` (guard for the Factory retirement).

## 4. Decisions (recommendations; Jacob to confirm or change)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Fix the field name where? | (a) Client sends `guidance`; (b) server also accepts `operator_guidance` as an alias; (c) both | **(a) client sends `guidance`**, plus a pytest that posts the exact body the UI builds. No alias: one name, and nothing else ever sent `operator_guidance` |
| D2 | `target_agent_id` in the request | Keep sending (ignored) / drop / make the server honour it | **Drop it.** The server already takes the agent from the clicked message (service L179), which is the agent that actually replied |
| D3 | Which turn is distilled | Latest turn / clicked turn / clicked turn plus N earlier turns | **Clicked turn** (that assistant message and the user message before it, with its tool calls and results) |
| D4 | Unknown `message_id` | Fall back to latest / 404 | **404 with a plain reason.** Never teach from a turn Jacob did not pick |
| D5 | `/learn` target | Latest assistant reply / disable `/learn` / open Teach with a reply picker | **Latest assistant reply**, with the plain "Send a message first" message when there is none |
| D6 | Needs-tool card actions | Keep Adopt disabled with a reason / hide Adopt | **Hide Adopt**; "Ask Developer to build this tool" and Dismiss remain |
| D7 | Scope boundaries | Fold Adopt persistence and timeout into this card / separate cards | **Separate:** CARD-502 (Adopt goes live and survives restart) and CARD-503 (timeout and silent fallback). The `factory_escalation` rename stays in CARD-497 |

## 5. Failing-tests-first plan (write, run, see red, then fix)

**Vitest** (new `tests/unit/frontend/teach_distill_contract_500.test.js`, node env, fake DOM like the CARD-472 test):
1. Teach submit posts exactly `{session_id, message_id, guidance}` (no `operator_guidance`, no `target_agent_id`). Red today.
2. `/learn be shorter` with `state.messages` holding two assistant replies opens Teach with the latest reply's id and guidance "be shorter". Red today (no id).
3. `/learn` with no assistant reply shows the "Send a message first" toast and makes no fetch. Red today.
4. A 422 with array `detail` produces a toast containing the validation `msg`, not `[object Object]` (Teach and Adopt). Red today.
5. `renderSkillProposalCard` with `{name, plain_summary: {observed_slip, remedy}}` shows those texts. Red today.
6. A `needs_tool` proposal renders no `.btn-adopt-skill`. Red today.
7. History render (`renderMessages` with a `skill_proposal` row) passes `sessionId` and a toast function to the card. Red today.
8. Guard: `teach_modal.js` contains no `agent_training_factory`.

**pytest** (extend `tests/unit/web/test_skills_distill_router.py` and `tests/unit/skills/test_skill_distillation_service.py`):
1. Posting the UI's body shape with `guidance` passes it to `distill_turn` (spy). Green today (control); stays green.
2. Session with 25 messages: Distill on the 2nd assistant message builds the prompt from the 1st user and 2nd assistant message only. Red today.
3. Distill on an id that is not an assistant message in the session returns 404. Red today.
4. The clicked turn's tool calls and results are included; other turns' are not. Red today.

**Smoke** (Playwright, desktop + phone, routes `/api/skills/distill` and `/api/skills/adopt` to fixtures, no model needed):
- **TC-35** Teach from the first reply with typed text: request carries that reply's id and `guidance`; card shows the fixture name, slip and remedy; Adopt shows the success toast. No `/api/agent_training_factory` request after page load.
- **TC-36** `/learn be shorter`: Teach opens for the latest reply; a routed 422 shows a readable toast; a needs-tool fixture shows Ask Developer and Dismiss only.

Run red, commit red, fix, then full Vitest, smoke, pytest unit and integration, ESLint, ruff (known CARD-454/456 failures only).

## 6. Build order

1. `teach_modal.js`: request body; shared `readableError(data, status)` (reuse `authoringErrorMessage` from `tools_studio_authoring.js` if it covers arrays, else extend it there).
2. `composer.js` `/learn`: pass the latest assistant id from `state.messages` or show the plain message. Keep `chat.js` from growing.
3. `render.js` card: name, `plain_summary`, hide Adopt for `needs_tool`, readable Adopt error, history call passes `sessionId`, `activeAgentId`, `showToastFn`. No net growth in `render.js` (CARD-499).
4. `distillation_service.py`: turn extraction by `message_id` (load the session's messages with ids, find the index, take the preceding user message and the tool rows between them); 404 path in the router.
5. CHANGELOG `[Unreleased] ### Fixed`, Scavenger Pass, preflight, rerun `scratch/c500_ui.cjs` and `scratch/c500_ui2.cjs`, In Review.

## 7. Runbook (Jarvis, after build)

Desktop (http://127.0.0.1:8000, Ctrl+F5):
1. Open Chat, send two different questions, wait for both replies.
2. Click Teach on the **first** reply, type "always cite the source", click Distill Skill Runbook.
3. The card title is a real skill name (not "Synthesized Skill"); "Observed Slip" and "Remedy" are specific sentences about the first question and your lesson.
4. Click Adopt: a green "Skill mounted" message appears. (Whether it is used on the next message is CARD-502.)
5. Type `/learn be shorter` and send: Teach opens with "be shorter" filled in; Distill makes a card.
6. In a brand-new chat, type `/learn test` and send: the message "Send a message first, then teach from the reply." appears.

Phone (http://192.168.1.99:8000):
1. Open Chat, send a question, tap Teach on the reply, type a lesson, tap Distill: the card shows a real name, slip and remedy.
2. Tap Adopt: the success message appears.
3. Type `/learn shorter answers` and send: Teach opens and Distill works.

## 8. Out of scope

- Adopted skills going live and surviving restart: **CARD-502**.
- Distill 4.5-second model timeout and silent fallback: **CARD-503**.
- `factory_escalation` rename and the Training Factory wording in the `agent-authoring` skill blurb: **CARD-497**.
