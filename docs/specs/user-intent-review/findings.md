# User intent review — findings (SSOT)

Audience: Jacob. You are new to software. Each item is a **plain name** for something AutoReiv already has, plus what the code actually does today (verified on branch qa, 2026-08-30).

Severity:
- **blocks the homelab story** — you cannot do the thing the product story promised
- **confuses** — the UI or names lie, or two things share a word
- **debt** — leftover code, stale cards, or a second path nobody should use

This is not a build order. It is a map for the next conversation.

---

## How we will use this

Jacob will next set a **plain-language dialogue**, then walk features one by one. Grok compares what Jacob says he wants to these findings **and** the current code. If a finding is wrong, update this file. Do not sneak product fixes on CARD-114.

Suggested discussion order (not a mandate):

1. Words: skill vs tool vs workflow vs job vs card vs routine vs agent
2. Talking in Chat (Goal, Verify, Stop, Approve)
3. Homelab Okta ("add Okta")
4. Skills Studio vs built-in Python tools vs Forge
5. Agent Builder vs Agent Forge (making a new specialist)
6. Self-improve (Approve vs actually writing a file)
7. Routines (what is paused vs what already runs)
8. Where your data lives (wiki, backup, leftover checkout ./data)
9. SDLC Conductor / Coding / Review vs Jobs in Chat
10. The CARD board pile (Ready vs In Review vs Parked)

---

## Talk to the product (Chat / Goal / Verify / HITL)

### Finding 1 — "Done" just means the model stopped calling tools
- **Plain name**: The job/phase finished successfully.
- **In the code**: AgentKernel.stream_turn / run_turn sets ReactState.DONE when the model returns no tool calls.
- **What we meant**: A phase is done when its success rule (done_when) is true, optionally after Verify.
- **What it actually does today**: If the model replies with words and no tool calls, the kernel marks DONE. success_rule is stored on the phase and copied into handoff packets and prompts. Nothing checks the output against that rule.
- **Why that's a problem**: Incomplete. The strip can say DONE while the work is unfinished. Goal Mode "done when" lines are decoration.
- **Severity**: blocks the homelab story (you cannot trust "done").

### Finding 2 — Goal and Verify are checkboxes, not playbooks
- **Plain name**: "Goal Mode" and "Self-Verify" in Chat.
- **In the code**: ChatStreamRequest.goal_mode / self_verify; UI goalToggle / verifyToggle; badge "Multi-phase job".
- **What we meant**: Pick a job template (a named playbook: phases, who does them, how to check). Checkboxes were a stand-in.
- **What it actually does today**: Goal asks a no-tool planner for 2 to 6 linear phases, parks HITL plan review, then runs each phase as its own stream_turn. Verify runs a named checker tool after the phase. If you did not name a checker, it honestly skips (not a pass). Skills Studio says job templates are "Later."
- **Why that's a problem**: Poor design / incomplete. Two mystery checkboxes instead of "run the Okta unlock playbook." The Goal badge says "Multi-phase job" even though default Chat is already one job.
- **Severity**: confuses (and blocks the homelab story until templates exist).

### Finding 3 — Every chat already creates a job
- **Plain name**: Sending a normal chat message.
- **In the code**: chat_stream -> JobPhaseOrchestrator.create_single_phase_job (name "Chat").
- **What we meant**: A Job is a real piece of work with phases. Chat is just talking.
- **What it actually does today**: Unless resume, every send creates one job + one phase, then stream_turn. Goal Mode creates many phases. Follow-up drafts are a separate queued job (template_id=followup_job) that Approve does not start.
- **Why that's a problem**: Overlap. "Job" in the status strip is not a special mode — it is every message. The word Job now means both "chat turn" and "multi-phase goal."
- **Severity**: confuses.

### Finding 4 — Stop / abort does not stop the model
- **Plain name**: Stop the running answer.
- **In the code**: POST /api/chat/stream/{session_id}/abort.
- **What we meant**: Cancel the live turn (stop GPU work, mark the phase cancelled/failed).
- **What it actually does today**: The route writes a telemetry span "Stream aborted by user" and returns status aborted. It does not cancel the background worker. Chat JS does not call this route.
- **Why that's a problem**: Theatre. The API pretends to abort.
- **Severity**: confuses (debt if you never wired a Stop button).

### Finding 5 — Two chat APIs disagree
- **Plain name**: Goal from Chat vs a hidden Goal API.
- **In the code**: UI uses POST stream with goal_mode. Leftover POST /api/chat/goal still exists.
- **What we meant**: One path: plan -> persist Job/Phases -> stream_turn each phase.
- **What it actually does today**: Stream+Goal is the live UI path. /api/chat/goal still calls PlanAndExecuteEngine.execute_plan, which uses run_turn (nested 32k cap), then marks persisted phases complete in a loop. Chat also has leftover /api/chat/verified (reflexion via run_turn) unused by the checkboxes.
- **Why that's a problem**: Conflict. Same product word, two engines.
- **Severity**: debt.

### Finding 6 — Two approval APIs
- **Plain name**: Approve / Reject in Chat.
- **In the code**: Live UI: /api/approvals/pending and /api/approvals/{id}/decision. Leftover: /api/hitl/pending and /api/hitl/decide.
- **What we meant**: One human-in-the-loop inbox.
- **What it actually does today**: Chat talks to /api/approvals (SQLite). /api/hitl talks to an in-memory ApprovalManager constructed in app.py and is not the Chat buttons. Skill drafts, goal plans, and tool parks all share the approvals table but behave differently after Approve (see Findings 18-20).
- **Why that's a problem**: Overlap / leftover. A script hitting /api/hitl does not see Chat parks.
- **Severity**: debt (confuses if both appear in docs).

### Finding 7 — Verify badge says "Reflexion Active" even when nothing checks
- **Plain name**: Self-Verify checkbox.
- **In the code**: _apply_verify_gate + ReflexionLoopEngine.run_named_checker; UI verifyBadge text "Reflexion Active".
- **What we meant**: After the work, a checker proves it (or a critic says fail). Missing checker is never a pass.
- **What it actually does today**: Honest skip if no named checker — good. The builtin JSON critic exists but Chat Verify does not use it (use_builtin_critic defaults false). The badge still lights "Reflexion Active." Reflexion's own loop still calls run_turn, not stream_turn.
- **Why that's a problem**: Theatre + incomplete. Skip vs critic are easy to mix up. Checkbox does not equal "it checked my work."
- **Severity**: confuses.

### Finding 8 — Job strip and Goal/Verify copy talk like an operator console
- **Plain name**: The thin bar above chat (Job / Phase / agent / THINKING) and the three checkboxes.
- **In the code**: jobPhaseStatusStrip; goalBadge "Multi-phase job"; Auto-run "Tools run without asking".
- **What we meant**: Show whether work is running, parked, or failed, in human words.
- **What it actually does today**: The strip is real (CARD-100). Labels are engineer words (Job running, Phase 1/4, PARKED). Auto-run is approval_mode=run (skip HITL). Default Chat still shows a Job because of Finding 3.
- **Why that's a problem**: Confuses a new user. "Job" / "Phase" / "PARKED" are not the words Jacob would use for "the assistant is waiting on you."
- **Severity**: confuses.


## Workers and handoff

### Finding 9 — Child workers get a packet, then stream — except several leftover paths
- **Plain name**: Handing work to another agent.
- **In the code**: HandoffIsolationEngine.execute_handoff -> stream_turn with HandoffPacket (goal, facts, constraints, done_when, budget).
- **What we meant**: The child sees only the packet, uses its full context window, streams tokens, depth capped at 2.
- **What it actually does today**: The main child path does that (CARD-098). done_when is required on the packet but still not enforced (Finding 1). Leftover run_turn (32k nested cap, 8k max tokens) is still used by: routines, HITL routine resume, /api/chat/goal, reflexion, /api/agents/audit, PlanAndExecuteEngine.execute_plan, nested resume fallback, SupervisorOrchestrator.
- **Why that's a problem**: Conflict. "Workers stream with full context" is true only for the new handoff path.
- **Severity**: debt (blocks the homelab story if a routine/child silently uses the small window).

### Finding 10 — "Parallel workers" vs one GPU slot
- **Plain name**: Do several specialists at once.
- **In the code**: GenerationSemaphore default 1 (cap 1-3). Parallel handoff batch > cap errors (not truncated). BatchWorkerSkill.batch_worker_scan still says "parallel isolated worker loops" and asyncio.gather.
- **What we meant**: Extra work queues so Nimo VRAM does not stampede. A true parallel batch must fail closed if it asks for more than the cap.
- **What it actually does today**: Serial handoffs queue. A batch bigger than the cap raises HandoffBatchExceedsCapError. The batch-worker skill still advertises parallel scans.
- **Why that's a problem**: Conflict / theatre. UI/docs can promise parallel; the box runs one generation.
- **Severity**: confuses.

### Finding 11 — Three "orchestrators" for handing work around
- **Plain name**: Who is in charge of a multi-agent task?
- **In the code**: JobPhaseOrchestrator (Chat jobs), HandoffIsolationEngine (child packet), SupervisorOrchestrator (still constructed as app.state.orchestrator). Also DelegateSubtaskSkill.delegate_task exists but is not mounted at bootstrap.
- **What we meant**: One control plane: Job -> Phase -> assigned agent. Handoff is how a phase calls a specialist.
- **What it actually does today**: Chat uses Job/Phase. SDLC Conductor uses handoff_to_agent (packet engine). Supervisor is still wired. Delegate is dead code. PlanningSkill (get_active_plan) is still registered against the old in-memory ExecutionPlan.
- **Why that's a problem**: Overlap / leftover engines. Same user story, three bosses.
- **Severity**: debt.

### Finding 12 — Nested size caps still sit on the old path
- **Plain name**: Child calls should not steal Chat's huge window.
- **In the code**: NESTED_COMPLETE_MAX_CTX = 32768 and NESTED_COMPLETE_MAX_TOKENS = 8192 used only in run_turn. stream_turn uses the model's full context. No NESTED_WRITE symbol (CARD-095 is marked Done).
- **What we meant**: Children stream with full context; a write budget keeps them from dumping novels; old complete() caps die.
- **What it actually does today**: New path is uncapped (good for CARD-098). Old path still capped. Two behaviors.
- **Why that's a problem**: Incomplete migration.
- **Severity**: debt.

---

## Packs and Studio

### Finding 13 — "Add Okta" is a brochure, not working tools
- **Plain name**: Homelab Okta admin (list users, groups, MFA, assign apps).
- **In the code**: Seed pack okta-admin (src/infrastructure/skills/seeds/okta-admin/SKILL.md copied into $DATA_DIR/skills if missing). Declared JSON tools okta_list_users, okta_list_groups, okta_reset_or_unlock, okta_assign_app.
- **What we meant**: AutoReiv can operate Okta in the homelab.
- **What it actually does today**: The SKILL.md says stubs, no live API, no tokens, no HTTP. Invoking a declared tool returns "not an executable Python builtin" (Finding 14). Boot does not need Okta env vars. This is CARD-108, still In Review.
- **Why that's a problem**: Theatre relative to the homelab story. A playbook you can read, not tools that do Okta.
- **Severity**: blocks the homelab story.

### Finding 14 — Pack "tools" are labels, not programs
- **Plain name**: A skill pack with JSON tool blocks in SKILL.md.
- **In the code**: DynamicSkillLoader parses JSON; UserSkillCatalog._playbook_tool_handler registers them; handler always returns success false, "schema, not an executable Python builtin."
- **What we meant**: User packs teach the model a playbook. Real power stays in Python builtins (wiki, execute_code, handoff). JSON is a declaration.
- **What it actually does today**: That is honest in code. Easy to miss in the UI — Skills Studio shows tool names as if they were callable. skill_view loads the body on demand (progressive disclosure). Python builtins are never replaced.
- **Why that's a problem**: Confuses. "Tool" means (a) Python builtin, (b) JSON stub, (c) Forge checkbox.
- **Severity**: confuses (blocks the homelab story together with Finding 13).

### Finding 15 — Three places that look like "skills"
- **Plain name**: Skills Studio vs built-in tools vs Forge allowlist.
- **In the code**: Skills Studio (skills.js) lists user packs under $DATA_DIR/skills only. Python builtins (WikiSkill, execute_code, handoff, and friends) stay out. Forge (forge_allowlist.js) warns at 12 checked tools. Agent Builder allowlist uses the same 12-tool warning.
- **What we meant**: Studio edits playbooks. Forge assigns which real tools a specialist may call. Builder talks to Jacob about both.
- **What it actually does today**: Mostly that split. Forge can still look like a skill picker. Studio archive/delete is live (CARD-113) for user packs only; bundled okta-admin needs extra confirm.
- **Why that's a problem**: Overlap of names. Jacob can think Forge "installed Okta" when it only ticked boxes.
- **Severity**: confuses.

### Finding 16 — Workflows / job templates are missing
- **Plain name**: Saved playbook you can run again ("unlock this user").
- **In the code**: propose_workflow parks a HITL draft whose "how" is a SKILL.md SOP. Skills Studio copy: "Job templates / Later. Playbook SOP is the SKILL.md body. Job-template YAML is a different object." $DATA_DIR/templates/jobs is created empty. Repo templates/ is an SDLC project scaffold, not job YAML.
- **What we meant**: Workflow = named Job template with phases. Playbook SOP = the words in SKILL.md.
- **What it actually does today**: propose_workflow does not start a Job. jobs.template_id is nullable (follow-ups use followup_job). No YAML runner.
- **Why that's a problem**: Incomplete. Goal checkbox is standing in (Finding 2).
- **Severity**: blocks the homelab story.

### Finding 17 — Packs are listed, then opened — they are not auto-run
- **Plain name**: The catalog of user skills.
- **In the code**: list_user_skill_packs (frontmatter only) + skill_view (load body + stubs).
- **What we meant**: Progressive disclosure so the model is not stuffed with every SKILL.md.
- **What it actually does today**: That mechanism works. Opening a pack still does not make Okta live (Findings 13-14). Last-used is a .last_used file for the curator.
- **Why that's a problem**: Incomplete relative to "I added a skill, so it works now."
- **Severity**: confuses.


## Builder

### Finding 18 — Making a new agent is easier than making a new skill
- **Plain name**: Agent Builder "save this specialist" vs "propose a skill."
- **In the code**: save_agent_specification is HITL high-risk; Approve runs the tool and the agent exists. propose_skill / propose_tool / propose_workflow create a draft; Approve marks approved and does not write SKILL.md.
- **What we meant**: Sprawl of specialists is dangerous on a small local model; prefer adding a skill to an existing agent. Skill writes should be harder, not easier.
- **What it actually does today**: Opposite friction. New agent: one Approve. New skill: Approve then another tool (commit_skill_pack). Allowlist >= 12 is a warning, not a block. Forge can also PUT agent settings.
- **Why that's a problem**: Conflict with the product rule. Agent sprawl is the easy button.
- **Severity**: blocks the homelab story (you will get more agents than working Okta tools).

### Finding 19 — Two builders: Forge Studio and Agent Builder chat
- **Plain name**: Agent Forge page vs picking "Agent Builder" in Chat.
- **In the code**: Forge UI (forge.js) edits profiles/allowlists. Chat agent agent-builder has AgentBuilderSkill tools. Profile text: "Not Conductor: does not write SDLC cards."
- **What we meant**: Forge is the form. Agent Builder is the conversation that researches and parks drafts.
- **What it actually does today**: Both can change who exists and which tools they get. Builder is wired to Job/Phase (CARD-107). Forge still feels like the "make an agent" product.
- **Why that's a problem**: Overlap. Jacob will not know which door to use.
- **Severity**: confuses.

### Finding 20 — Approve does not write the skill file
- **Plain name**: Hitting Approve on a skill/tool/workflow card.
- **In the code**: apply_skill_proposal_decision + HITL message "SKILL.md and src/ were not written. Agent Builder may call commit_skill_pack now." commit_skill_pack requires status=approved, writes via UserSkillCatalog.save_pack, never writes Python under src/.
- **What we meant**: Human Approve is consent. Writing the playbook is a second, explicit commit. Python builtins are never auto-written.
- **What it actually does today**: That two-step is real. Easy to think Approve = saved. commit_skill_pack is not in the HITL high-risk list, so the second write may not even park.
- **Why that's a problem**: Incomplete UX / conflict with "I approved it." Also Finding 18's imbalance.
- **Severity**: confuses.

---

## Self-improve

### Finding 21 — Self-improve is drafts unless you Approve and commit
- **Plain name**: AutoReiv learns / improves a skill overnight or after a failure.
- **In the code**: ACE online (ace_online.py) and nightly eval (skill_eval_sleep.py) both call propose_skill (or propose_tool for Python-shaped deltas). auto_commit is false. No commit_skill_pack on that path.
- **What we meant**: The machine may draft a tiny playbook note. A human still Approves. Live SKILL.md does not rewrite itself mid-chat.
- **What it actually does today**: Matches the intent. Failures can also append sidecar PLAYBOOK_NOTES.md / notes.jsonl without changing SKILL.md. Promotion into the playbook is still propose_skill.
- **Why that's a problem**: None if Jacob wants drafts. Theatre if the story was "it got better by itself."
- **Severity**: confuses (unless named honestly in the UI).

### Finding 22 — ACE notes are snapshots, not a second brain
- **Plain name**: "ACE" / playbook notes / rollback.
- **In the code**: ace_online.py + UserSkillCatalog.snapshot_pack / rollback_pack. Generator is the existing kernel. No vendor ACE, no LangGraph.
- **What we meant**: One tiny delta after a failed turn; snapshot before apply; rollback restores bytes.
- **What it actually does today**: Online path parks HITL or appends sidecar. Snapshot I/O failure skips apply. Python-shaped deltas stay propose_tool with "requires human/code card."
- **Why that's a problem**: Overlap of the word ACE with a research paper. Behavior is a draft + backup folder.
- **Severity**: debt / confuses (naming).

### Finding 23 — Nightly eval and curator are paused on purpose
- **Plain name**: Nightly skill eval; stale pack archive.
- **In the code**: Routines skill-eval-sleep and skill-curator, both enabled=False. Weekday 21:00 America/New_York when enabled. Eval does not attach stream_turn. Curator never auto-archives okta-admin.
- **What we meant**: Do not surprise the GPU at 2am. Harvest + gate + draft only.
- **What it actually does today**: Seeds exist, paused. Routines UI can enable them. Empty harvest is a success no-op.
- **Why that's a problem**: None if paused is the product. Confuses if the UI lists them like live jobs.
- **Severity**: confuses (if the Routines list looks "on").

### Finding 24 — Other builtin routines are already on
- **Plain name**: Routines page (morning briefing, hourly SRE pulse, and friends).
- **In the code**: BUILTIN_ROUTINES: morning-briefing, daily-sysinfo, nightly-hygiene, hourly-sre-pulse, weekly-note-rollover are enabled=True. Only the two self-improve siblings are paused.
- **What we meant**: Background jobs Jacob opted into.
- **What it actually does today**: Several run by default (executor still uses run_turn). Auto-run tools on a routine is a separate checkbox, default ask/fail-closed.
- **Why that's a problem**: Conflict with "paused defaults." Homelab may get hourly model calls it did not ask for.
- **Severity**: confuses (possible surprise GPU load).

---

## Data / backup

### Finding 25 — Your real files are in the Windows data dir; checkout ./data is leftover
- **Plain name**: Where AutoReiv keeps the database, wiki, and skills.
- **In the code**: DataDirResolver -> %LOCALAPPDATA%\AutoReiv (or AUTOREIV_DATA_DIR). Checkout ./data is a migrate source, not the default. Launcher CARD-109 no longer passes --db-path ./data. Repo still has data/autoreiv.db and data/wiki.
- **What we meant**: User state lives outside git (Hermes-style). Copy-migrate once, never wipe.
- **What it actually does today**: New boots use LocalAppData. Nightly eval refuses checkout ./data when LocalAppData is live. Old ./data can still confuse "which wiki am I looking at?"
- **Why that's a problem**: Overlap of two folders. Easy to edit the wrong wiki.
- **Severity**: confuses (blocks backup story if you zip the checkout by mistake).

### Finding 26 — Wiki follows the data dir (with leftover defaults in code)
- **Plain name**: Wiki Studio notes.
- **In the code**: Wiki root = $DATA_DIR/wiki unless AUTOREIV_WIKI_PATH is a non-legacy override. app.py still has a default argument wiki_path="./data/wiki" which is then treated as legacy and replaced. Wiki Graph / mind map is the note-link graph (/api/wiki/graph) — not a job DAG.
- **What we meant**: One vault, in the data dir. Graph is "how notes link," not LangGraph.
- **What it actually does today**: Live path is data-dir wiki. Checkout data/wiki can remain as migrate leftover. Graph UI is real.
- **Why that's a problem**: Leftover path strings. Graph is not leftover job-graph theatre — do not delete it thinking it is CARD-014.
- **Severity**: debt (wiki folder); Graph itself is fine.

### Finding 27 — Backup exists as a feature, still sitting in the In Review pile
- **Plain name**: Backup / restore my AutoReiv folder.
- **In the code**: CARD-103 + src/infrastructure/data/backup.py + CLI zip of db/wiki/skills.
- **What we meant**: One zip of the data dir. Not a git commit of ./data.
- **What it actually does today**: Implemented on qa, card still In Review (096-113 pile).
- **Why that's a problem**: Board hygiene. The product may already work while the card says otherwise.
- **Severity**: debt.


## SDLC / cards

### Finding 28 — Two ways to "run a project": Chat jobs vs Conductor->Coding->Review
- **Plain name**: Cards on the board vs Jobs in Chat.
- **In the code**: SDLC agents conductor, coding, review hand off with handoff_to_agent and set_card_status. Chat uses JobPhaseOrchestrator. Coding max_turns=10, "one card, then In Review."
- **What we meant**: Conductor covisions cards/specs. Coding implements one card. Review judges the spec. Chat jobs are user goals, not the CARD board.
- **What it actually does today**: Both exist. They do not share a Job row. A CARD is a markdown file under .github/cards/. A Job is a SQLite row. Same English word "card/job/phase" in different worlds.
- **Why that's a problem**: Overlap. Jacob can think Goal Mode is how AutoReiv builds AutoReiv.
- **Severity**: confuses.

### Finding 29 — Conductor->Coding was never re-proven on CARD-001
- **Plain name**: "Let Conductor hand CARD-001 to Coding and see it work."
- **In the code**: CARD-001 (LLM gateway) is Done from Milestone 1, not from the new SDLC loop. Conductor prompt says hand one Ready card to Coding. Bounce-back (CARD-084) is also Done as code.
- **What we meant**: The team loop is proven on a real card, end to end.
- **What it actually does today**: The agents and tools exist. Nobody re-ran CARD-001 through Conductor->Coding->Review after that loop shipped. Ready cards 009-045 may already be shipped under later numbers (Finding 30).
- **Why that's a problem**: Incomplete proof. The SDLC story is untested as a product ritual.
- **Severity**: debt (blocks trust in "the team builds the product").

### Finding 30 — The CARD board is lying about what's shipped
- **Plain name**: .github/cards statuses.
- **In the code**: Count on qa: Done 65, Ready 29 (009-013, 015, 020-045), Parked 1 (CARD-014 DAG/Goal graph — superseded by Job/Phase), In Review 18 (096-113). CARD-114 is this review (Ready).
- **What we meant**: Ready = not built. In Review = just implemented, waiting on Jacob. Done = in the product. Parked = do not build.
- **What it actually does today**: Many Ready cards (compaction, HITL, wiki, settings, sandbox, tests) were later implemented as 041-095 and marked Done without closing 009-045. Slice A-D (096-113) is a pile of In Review. CARD-014 correctly parked.
- **Why that's a problem**: Theatre of the board. Jacob cannot see "what's left" by status.
- **Severity**: confuses.

### Finding 31 — Agent list test is only slightly behind the cast
- **Plain name**: Which agents exist.
- **In the code**: Builtins: assistant, autoreiv, coding, conductor, review, agent-builder (plus aliases). test_list_agents asserts assistant, autoreiv, coding, agent-builder (>= 3). Does not assert conductor/review. Old names (sysadmin, librarian) are aliases.
- **What we meant**: Tests match the live cast.
- **What it actually does today**: Does not fail. Mild drift. Conductor/Review can vanish from a future cleanup without this test noticing.
- **Why that's a problem**: Debt / hygiene.
- **Severity**: debt.

### Finding 32 — Builtin purpose save was a real bug; code now stores it
- **Plain name**: Changing Coding's "purpose" in Forge snaps back after refresh.
- **In the code**: CARD-093 Done. AgentCustomization.purpose is persisted; registry overlay applies ModelPurpose.
- **What we meant**: Forge save sticks.
- **What it actually does today**: Code path looks fixed. Not re-clicked in the UI for this review. If snap-back still happens, it is a regression, not "never built."
- **Why that's a problem**: Only if the UI still lies. Otherwise close the worry.
- **Severity**: debt (verify in the app once).

---

## Debt / hygiene / names

### Finding 33 — Too many words for "a piece of work"
- **Plain name**: skill vs tool vs workflow vs job vs card vs routine vs agent vs phase vs pack vs template.
- **In the code**: All of these are real types. Example collisions: card (SDLC markdown) vs Chat job; workflow (SOP draft) vs job template (missing); tool (Python vs JSON stub vs Forge tick); agent (builtin specialist vs Forge custom vs Agent Builder); routine (scheduler row) vs job (chat work).
- **What we meant**: Each word is one thing Jacob can point at.
- **What it actually does today**: Several words share a feeling. This is why Goal, Studio, Forge, and Conductor feel like the same product four times.
- **Why that's a problem**: Overlap. The next dialogue should pick Jacob's words and retire the rest in the UI.
- **Severity**: confuses.

### Finding 34 — Leftover engines still boot
- **Plain name**: Old planners / supervisors / HITL managers.
- **In the code**: Still constructed or registered: SupervisorOrchestrator, in-memory ApprovalManager + /api/hitl, PlanAndExecuteEngine.execute_plan, PlanningSkill tools, DelegateSubtaskSkill (unmounted). CARD-014 parked but planner JSON still says "do not emit a DAG" (harmless leftover wording).
- **What we meant**: Job/Phase + packet handoff + /api/approvals replace those.
- **What it actually does today**: New path is used by Chat. Old objects still exist so tests and aliases keep working.
- **Why that's a problem**: Debt. Docs or a future agent can call the wrong API.
- **Severity**: debt.

### Finding 35 — UI Graph leftover is the wiki map, not a job DAG
- **Plain name**: "Graph" button in Wiki.
- **In the code**: Wiki knowledge graph + mermaid in Chat for fenced diagrams. Parked CARD-014 was the plan DAG. Chat Goal no longer draws a DAG; it draws a plan review card + job strip.
- **What we meant**: Kill the job-graph idea. Keep note maps.
- **What it actually does today**: Matches. Do not rip Wiki Graph thinking it is LangGraph.
- **Why that's a problem**: None if named "note map." Confuses if someone says "we still have Graph."
- **Severity**: debt (naming only).

---

## Already-known gaps (re-checked against code)

These seven were named before this review. They are **still true**:

1. Homelab "add Okta" is a brochure pack — Findings 13, 14
2. Self-improve is drafts unless Approve + commit — Findings 21, 20
3. Phase DONE is still "model stopped calling tools" — Finding 1
4. Goal/Verify checkboxes instead of job templates — Findings 2, 16
5. save_agent_specification vs propose_skill HITL (agent sprawl easier) — Finding 18
6. Conductor->Coding CARD-001 never re-proven — Finding 29
7. Approve != write file (two-step) — Finding 20

---

## Count

**35 findings** (the 7 known gaps are folded into them).

---

## How we will use this (end note)

Jacob will next set a **plain-language dialogue**, then walk features one by one. Grok compares his intent to these findings and the current code. This file is the map, not a mandate. A suggested discussion order is at the top. Do not treat the finding numbers as an implementation queue.
