---
id: CARD-572
title: "Chat runs a job only when Jacob asks: an explicit Run as a job action replaces keyword routing"
type: feature
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof: "Journey card-572-explicit-job: in Chat, a message full of old trigger words (numbered steps, 'first ... then ... finally', 'create a note that ...', 'done when: ...') runs as one normal turn with 0 Job/Phase rows; the same text sent with Run as a job creates one Job, the phase strip shows it, and the reply comes back in the chat. Checks: route_standing_chat is gone (guard test: no chat, routine or handoff path calls a text classifier to start a Job); existing Job tests re-pointed at the explicit flag."
branch: feat/card-572-explicit-job
created: 2026-09-29
related: [CARD-565, CARD-564, CARD-548, CARD-554, CARD-271, CARD-230, CARD-222, CARD-215]
---

# CARD-572 Chat runs a job only when Jacob asks

> **Status**: In Review

## Why
Chat decides "normal turn or two-phase Job" by matching words in the message. When it guesses Job, the work runs in
separate Formulate/Execute phase sessions and the chat only gets relayed text. CARD-565 fixed one misfire
("review CARD-3 against its acceptance criteria"), but the rest of the word list is still broad by design, so ordinary
asks can still become a Job. Jacob can't tell in advance which way a message will go, and there is no way to say
"just answer" or "run this as a job".

## What exists today (qa after CARD-571)

### Keyword triggers that start a special flow from a user's message
| # | Where | Words / pattern | What it starts |
|---|---|---|---|
| T1 | `standing_job_graph.py` `is_multi_step_outcome` | 2+ numbered lines (`1.` `2)` `(3)`); 2+ `step/phase/milestone/task N`; `first`/`step one`/`initially` plus `then/next/after that/secondly/afterwards` or `finally/lastly/in the end` (40+ chars) | standing Job (catalog resolve, Formulate then Execute phases in their own sessions) |
| T2 | `outcome_intake.py` `_GOAL_DELIVERABLE` via `is_outcome_shaped` (40+ chars) | `deliver/delivery/deliverable`; `build/create/produce/ship/implement/author/write/save/draft/add ... that/which/so that/until/when`; `create/write/... wiki/note(s)` either order; `done when`; `success when`; `success criteria/rule/condition:`; `acceptance criteria:`; `prove(s/n) ... exists/passes/returns/200`; `health ... 200` | same standing Job |
| T3 | `src/web/routers/chat.py` ~2229 `route_standing_chat(effective_content)` | T1 or T2 on every non-resume Chat message (all agents except `direct`) | mints the Job, runs phases, relays the phase reply (CARD-548) |
| T4 | `routines/executor.py` ~435 `route_standing_chat(routine.prompt)` | T1 or T2 on a routine's prompt | the routine runs as a standing Job instead of one turn (CARD-222) |

`ChatStreamRequest.goal_mode` still exists but is ignored (CARD-215 removed the old Goal mode toggle on purpose).

### Keyword matching that does not change the flow (out of scope, listed so nobody confuses them)
- `agent_kernel.py` ~750 fast-path intent domains (wiki, diagnostics, tasks/jobs/cron, coding, mcp, native tool): only rank tools inside the agent's allowed set.
- Reply-side detectors (they read the assistant's reply, not Jacob's message): `capability_detector.py` ("I cannot directly ..."), `render.js` `offersAskDeveloper`, `distillation_service.py` `_ANY_TOOL_RE`. They offer an Ask Developer button or a needs-tool proposal; nothing runs by itself.

### Paths that already start long work explicitly (no keywords)
- Architect `hand_off_card` (hand-off card, Jacob approves, Developer runs the card; CARD-563/566).
- `handoff_to_agent` (one agent asks another; child standing Job via `standing_a2a_handoff.py`, CARD-224).
- Routines (scheduled or Run now), Education retention routine, Tools Studio / Skill Studio Submit (developer/Toolsmith jobs), Ask Developer.
- The Chat composer already has the Auto-run approvals box (`approvalToggle`, "run" vs "ask"); it controls approvals, not Jobs.
- The Job phase strip in Chat (`formatJobPhaseStrip`) already shows a running Job.

## Known misfires
- CARD-564 round 1 / CARD-565: "Review CARD-3 against its acceptance criteria and record your verdict." became a Formulate/Execute Job; review tools ran in phase sessions (fixed for criteria mentions only).
- `docs/findings.md` 2026-09-28 (chat routing, product question): deliverable verbs, wiki writes, done-when, first/then/finally or numbered steps can still turn an ordinary ask into a two-phase Job.
- Examples that still route to a Job today by the rules above (not yet seen live): "First check the logs, then tell me what broke"; "Write a short note that explains X"; a pasted numbered list of questions; "add a test that covers Y" to Developer.
- CARD-554: Formulate did the work itself until its prompt changed; the split costs a second model pass on asks that did not need it.
- Tests that pin the keyword routing: `test_outcome_intake.py`, `test_standing_job_graph_runtime.py`, `test_chat_outcome_job_mint.py`, `test_card271_react_job_spine.py`, `test_catalog_resolve_chat_standing.py`, `test_card565_criteria_reference_stays_react.py`, `test_routine_standing_job_path.py`.

## How other harnesses decide (D:\Projects\research, brief)
- **Hermes**: no text classifier. The model calls `delegate_task` (goal or batch of tasks); `background=true` returns an id and the result comes back later. Long work is a tool call the model chooses; cron is explicit.
- **OpenClaw**: normal chat never creates a task. Background tasks come only from explicit starts: subagent spawns, automations (cron/heartbeat), ACP runs, CLI `agent exec`. Tasks are a ledger, not a router.
- **OpenHuman**: agent tools `spawn_subagent` / `spawn_worker_thread` and planning tools; the model decides, work shows as a tracked worker.
- **Odysseus**: closest to AutoReiv. `action_intents` has deterministic chat-to-agent promotion hints, but narrow (explicit web-search language), logged with a reason, and must not promote explanatory questions. Long bash work is detached with explicit background markers; scheduled tasks are separate.
- Common pattern: long work starts from an explicit action (user button/command, schedule) or a tool the model chooses; none of them regex the user's message into a multi-session job.

## Scope (if Jacob approves the recommendations)
1. Chat: a **Run as a job** control next to Send (checkbox or split button, off by default, resets after each send). The request sends `run_as_job: true`; only then does Chat mint the standing Job. Everything else is a normal turn.
2. Remove T1-T3 from Chat: delete `route_standing_chat` and the chat call; keep `derive_success_rule` / `is_testable_success_rule` (used when a Job is created).
3. Routines (T4): a routine setting "Run as a job" (default off) instead of reading its prompt.
4. Remove the dead `goal_mode` field.
5. Re-point the 7 test files at the explicit flag; guard test that nothing calls a message classifier to start a Job.

## What dies
- Routing any Chat message or routine prompt into a Job because of its words (T1-T4).
- `goal_mode` on the chat request (already ignored).
- It reverses CARD-215 REQ-JOBGRAPH-001a ("no Chat toggle or request flag") on purpose: that rule assumed the runtime could tell; CARD-565 shows it can't reliably.

## Decisions for Jacob
**D1. How does a Chat message become a Job?**
- A. Only when Jacob ticks **Run as a job** next to Send (off by default, resets after send). Keywords removed.
- B. The agent decides by calling a `start_job` tool (Hermes/OpenHuman style). Keywords removed; Jacob sees a Job start in the strip.
- C. Keep keywords but show "This will run as a job - Run normally instead?" before starting.
- **Recommend A.** Simplest and predictable; nothing starts without Jacob's click. B can come later if Jacob wants agents to start jobs themselves.

**D2. Routines whose prompt looks like steps (T4)?**
- A. Routine has a "Run as a job" setting, default off; the prompt is never scanned.
- B. Routines always run as a normal turn; no job option.
- **Recommend A.** Keeps the phase path for routines that really need it, without guessing.

**D3. Existing routines that run as Jobs today only because of their wording?**
- A. On upgrade, set "Run as a job" on for routines whose prompt matches today's rules (one-time, logged), then delete the rules.
- B. Leave them off; Jacob ticks the ones he wants.
- **Recommend B** (dev data, few routines, no migrations before 1.0); list the affected routines in the card results so Jacob can tick them.

**D4. What does Run as a job look like?**
- A. A small checkbox "Run as a job" beside the Auto-run approvals box.
- B. A split Send button: Send | Run as a job.
- **Recommend A.** Matches the existing approvals box; one click, no new button shape.

## Decisions (Jacob, 2026-09-29: all four recommendations)
- D1 A: a chat message becomes a job only when Jacob ticks **Run as a job**; off by default, resets after each send. All keyword triggers T1-T3 are deleted (`is_multi_step_outcome`, `_GOAL_DELIVERABLE`/`is_outcome_shaped`, `route_standing_chat`), and the dead `goal_mode` flag is replaced by `run_as_job`.
- D2 A: each routine has its own Run as a job setting (default off); the prompt is never scanned.
- D3 B: existing routines stay off. Affected (ran as a job only because of its wording, checked on the live DB before the change): built-in `weekly-note-rollover` ("create the new week's note ..."). All other routines already ran as one turn. Tick its box in Routines if it should stay a job.
- D4 A: the box sits beside the Auto-run box in Chat options; a "Run as a job" badge next to Send shows it is armed.
- This reverses CARD-215 REQ-JOBGRAPH-001a on purpose; recorded in ADR-0063.

## Done when
- A Chat message with any of the old trigger words runs as one normal turn (0 Job rows) unless Run as a job was ticked.
- Ticking Run as a job creates one standing Job and the phase strip and relayed reply work as today.
- Routines follow their setting only. No code path scans message text to start a Job (guard test).
- Per-agent tool/skill counts unchanged; fast preflight GREEN; journey card-572-explicit-job PASS.

## Results (2026-09-29, In Review)
- Chat: `ChatStreamRequest.run_as_job` (default false) replaces `goal_mode`; `chat.py` mints a standing Job only on `req.run_as_job`. Composer: **Run as a job** chip beside Auto-run (Options drawer) plus a "Run as a job" badge next to Send; never remembered, unticks after each send (kept if the send is refused with 409). Education Ask and pressure ask send `run_as_job: true`.
- Routines: `metadata.run_as_job` via `routine_runs_as_job()`; the routine form has its own box; the API saves it (an update that omits it keeps the saved value) and lists it.
- Deleted: `route_standing_chat`, `StandingRoute`, `is_multi_step_outcome`, `is_outcome_shaped`, `_GOAL_DELIVERABLE`, `goal_mode`. ADR-0063 records the reversal of CARD-215 REQ-JOBGRAPH-001a. The two chat-routing lines in docs/findings.md are closed by this card.
- Tests: removed `test_card271_react_job_spine.py` and `test_card565_criteria_reference_stays_react.py` (pure keyword tests); `test_outcome_intake.py`, `test_standing_job_graph_runtime.py` (unit), `test_catalog_resolve_chat_standing.py`, `test_chat_outcome_job_mint.py`, `test_routine_standing_job_path.py` re-pointed at the explicit flag; integration `test_chat_stream_modes.py` / `test_standing_job_graph_runtime.py` and 3 web tests updated. New: `test_card572_explicit_job.py` (guard: none of the removed names in src; flag default off; routine setting; API keeps the value), trigger-word stream tests (6 phrasings stay a normal turn; a short ask with the flag starts a job), routine step-words-without-setting test, vitest `card_572_run_as_job.test.js`.
- Checks: full not-slow suite 2035 passed, 13 skipped; vitest 945; fast preflight --base qa GREEN.

| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-572-explicit-job | desktop | PASS | "First check the system health, then tell me ..." without the box: run_as_job false, 0 jobs, 0 phase sessions; with the box: run_as_job true, box and badge reset after send, 1 job (done, Phase 2/2 Execute); routine form saved run_as_job true, that routine ran as a job, a step-worded routine without the box ran as one turn (no job) |

## Log
- 2026-09-29: Research on qa (read-only, ~15 min): triggers T1-T4, misfires, explicit paths, harness comparison; Draft with D1-D4.
- 2026-09-29: Jacob: build, all four recommendations. Ready; built on feat/card-572-explicit-job; checks green; journey PASS; In Review.
