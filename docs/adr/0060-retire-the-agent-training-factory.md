# ADR-0060: Retire the Agent Training Factory

> **Date**: 2026-09-25  
> **Status**: Accepted  
> **Accepted**: 2026-09-25 (Jacob product lock. At 3:44 PM ET: "We built Agent, Skill and Tool Studios so we no longer need the Factory, but we have other mechanisms for training and improvement". At 11:39 PM ET: accepted the CARD-495 audit and decisions D1-D8 as recommended. That counts as acceptance under the same convention as ADR-0056 and ADR-0059, a dated Jacob lock.)  
> **Deciders**: Jacob Weber, coding assistant  
> **Consulted**: CARD-495 gap and dependency audit (qa `10f2bc75`, scratch server checks); CARD-472 revised report  
> **Related Cards**: [CARD-495](../cards/CARD-495-retire-factory-adr-and-docs.md), [CARD-496](../cards/CARD-496-retire-factory-ui-shell-and-redirects.md), [CARD-511](../cards/CARD-511-developer-native-tool-check-before-register.md), [CARD-497](../cards/CARD-497-retire-factory-backend-routes-orchestrator-and-pack-tools.md), [CARD-512](../cards/CARD-512-retire-agent-training-optimization-scaffold-queue.md), [CARD-498](../cards/CARD-498-retire-factory-data-export-then-drop.md), CARD-472, CARD-418, CARD-386  
> **Supersedes**: [ADR-0048](./0048-autonomous-agent-pack-factory-and-capability-loop.md) (autonomous agent pack factory and capability loop)  
> **Amends**: [ADR-0056](./0056-durable-runtime-registry-hybrid-c-plus.md) 4.7 (Skill Studio, not the Factory, writes skill bodies and tool bindings); [ADR-0057](./0057-three-studios-and-developer-mediated-authoring.md) (completes the "transitional Factory" retirement); [ADR-0049](./0049-mcp-servers-vs-native-tools-deliverable-taxonomy.md) (the native/MCP taxonomy now applies to Developer's lanes, not the Factory)

---

## 1. Context & Problem Statement

ADR-0048 made the Agent Training Factory the way AutoReiv builds and improves agents: an 8-step background loop (intent, ground, blueprint, author, verify, scenario verify, optimize, promote) with its own screen, Lab Monitor and training popup. ADR-0057 then split authoring into three Studios (Agent, Skill, Tools) with Developer doing the building, and called the Factory screen "transitional". CARD-386 removed the Factory runs and pipeline views. CARD-418 moved skill writing into Skill Studio.

What is left is a Factory that nobody uses but that still has a screen, background orchestrator, routes, chat tools, database tables and docs describing it as current. Jacob's install has 0 rows in every `factory_*` table. Meanwhile Skill Studio quietly depends on Factory routes and on a file whose docstring calls it "Factory workshop persistence". Deleting the Factory carelessly would break Skill Studio.

The CARD-495 audit (card section 1) lists everything the Factory does, what replaces each part, whether that works today (with file:line evidence and scratch server checks), and everything that depends on Factory code.

---

## 2. Decision Drivers

* One way to do each job (ADR-0057): Agent Studio for agents, Skill Studio for skills, Tools Studio plus Developer for tools, Teach and Observability for improvement.
* No screens without durable state behind them.
* Nothing that works today may break: Skill Studio save, the operator skill list (CARD-509 pills), gap recording, Teach.
* Real users' data is handled properly: export before any table is dropped, with migrations written for upgrades as well as fresh installs. This applies even though Jacob's AppData is not production before v1.0.

---

## 3. Considered Options

* **Option 1**: Keep a thin Factory shell (screen and routes) that forwards to the Studios.
* **Option 2**: Move the 8-step loop behind Developer as a background "train this agent" job.
* **Option 3**: Retire the Factory. Keep and move the pieces other features use, close the one real gap with a new card, and drop the rest (chosen).

---

## 4. Decision Outcome

Chosen option: **Option 3, retire the Factory**, because every job it did has a working replacement except the tool code check (handled by CARD-511) and scenario replay (dropped for now, D3). Keeping a shell or re-homing the loop would keep about 4,760 lines of unused code alive and give two ways to do the same job.

### 4.1 What replaces what

| Factory job | Replacement | Works today? |
|---|---|---|
| Intent (question list) | Tools Studio form and "talk to Developer"; Skill Studio Build job; agent-authoring intake as a Developer handoff | Yes |
| Ground (research, Wiki manual) | Ask AutoReiv in chat, using its wiki skills | Yes, chat only (D2) |
| Blueprint (plan skills and tools) | Skill Studio Build proposals | Yes |
| Author skills | Skill Studio save | Yes (checked on scratch), through routes that move in CARD-497 |
| Author tools | Developer native and MCP lanes (Tools Studio) | Yes |
| Verify tool code before it goes live | **CARD-511**: sandbox smoke check before a Developer-built native tool is registered | No, gap closed by CARD-511 |
| Scenario verify (replay "done when" scenarios) | None. Teach and Observability friction cover part of the need | Dropped for now, no card (D3) |
| Optimize (merge, split, regroup skills) | Observability architectural proposals | Yes |
| Promote (human approval) | Skill Studio decision step, Tools Studio jobs, Teach Adopt | Yes |
| Edit phase instructions | Not needed | n/a |
| Train from a capability gap | Agent Studio gap backlog: **Open in Skill Studio** and **Ask Developer** (CARD-496) | Parts exist; wiring in CARD-496 |
| Teach "factory_escalation" remedy | "Ask Developer" (CARD-472); renamed `tool_escalation` (CARD-497) | Yes |
| Chat tool `launch_factory_training` | Developer handoff | Yes |
| Chat tool `inspect_agent_pack` | Kept and moved (D4) | Yes |
| Lab Monitor, training popup, Factory screen | Observability traces and sessions; the three Studios | Yes |
| Update "busy" check on Factory jobs | Studio jobs are already counted separately | Yes |
| Agent Studio "Agent Training Optimization" queue | Nothing; it is always empty. UI goes in CARD-496, backend in CARD-512 (D8) | n/a |

### 4.2 Decisions (D1-D8, accepted 2026-09-25)

* **D1**: The CARD-495 audit is the basis of this ADR.
* **D2**: Wiki research has no automatic job. It is a chat request to AutoReiv.
* **D3**: Scenario replay and agent evaluation are dropped for now, with no card. Revisit only if a real need appears.
* **D4**: `inspect_agent_pack` stays as a read-only chat tool, moved next to the orchestration tools (`orchestration_tools.py`), with its pack grant kept.
  * *Note (CARD-497 D6, 2026-09-26)*: it landed in `AgentPackTools` (`application/skills/agent_pack_tools.py`), next to export/import/scaffold, instead of `orchestration_tools.py`; same name, output and pack grant.
* **D5**: Skill Studio's `factory*` element ids stay (about 150 ids inside `#view-skill-studio`). Renaming them adds churn with no user benefit. Only `#view-factory` goes.
* **D6**: CARD-511 lands before CARD-497 and may reuse the parts of `verification_battery.py` it needs. CARD-497 deletes only what CARD-511 does not keep.
* **D7**: The unused auto-training pieces are deleted in CARD-497: the `allow_autonomous_training` and `max_training_retries` fields in the API and UI, the `JitToolSynthesizer` built in `agent_kernel.py` but never used, and the `AUTO_TRAIN_PROGRESS` event, which is never sent. The DB columns stay.
* **D8**: The "Agent Training Optimization" panel is removed from Agent Studio in CARD-496. Its backend (`/api/capabilities/scaffold/*`, `SelfScaffoldSpine`, `scaffold_spine` table) is retired in CARD-512, not folded into Tools Studio.

### 4.3 Keep or move (other features depend on these)

* `src/application/skills/workshop.py`: Skill Studio persistence and the operator skill list (`routers/agents.py` pills and catalog, `skill_authoring.py`, `routers/skills.py`, `user_catalog.py`). Kept; only the docstring changes.
* Skill Studio routes now under `/api/agent_training_factory`: `/capabilities`, `/scaffold/runbook`, `/scaffold/save`, `/skills`, `/skills/{id}`. Moved to `routers/skill_studio.py` (`/api/skill_studio/*`, `/api/tools_studio/capabilities`) in CARD-497, with 308 redirects from the old paths for one release. The redirects are removed in CARD-498.
* Helpers those routes need: `llm.phase_llm_text` and `phases/promote.check_tool_collisions`. Moved with the routes.
* `inspect_agent_pack` (D4).
* Skill Studio's `factory*` ids (D5); the shared agent picker (only its `factory` storage key goes). `factory/workshop_meta.js` and `factory/skill_scope.js` move to `studios/skill_studio/` (CARD-496).
* Gap recording by the kernel, gap listing and gap dismiss stay.

### 4.4 Delete

* The Factory screen (`#view-factory`, `factory.js`), Lab Monitor, training popup and chat promotion card buttons (CARD-496). The text of old chat history stays.
* `src/application/agent_training_factory/`, including the orchestrator, phases, prompt registry, gap_link, failure classes and SOP rubric (CARD-497).
* The Factory router's job, gap and phase routes, and `POST /api/agents/{id}/gaps/{gap}/train`. These return 404 after CARD-497.
* `launch_factory_training` and its pack grant; the agent-authoring skill is rewritten as a Developer handoff.
* `capability_graph.py`, `jit_synthesizer.py`, `domain/orchestration/factory_packets.py`, and the parts of `tool_synthesizer.py` / `verification_battery.py` that CARD-511 does not keep.
* Startup and shutdown wiring in `app.py` and the Factory checker in the busy detector.
* Factory-only tests, pruned under ADR-0055.
* The scaffold spine backend (CARD-512).
* Data (CARD-498): `factory_jobs`, `factory_graphs`, `factory_packets`, `factory_eval_runs`, `factory_phase_instructions`, the `factory_jobs` column migrations, and `scaffold_spine` if CARD-512 retires it.

### 4.5 Order

CARD-495 (this ADR and docs), then CARD-496 (UI), CARD-511 (tool check), CARD-497 (backend), CARD-512 (scaffold spine backend), CARD-498 (data). Each card is built on its own branch and merged to qa before the next starts.

### 4.6 Data rule

* No `factory_*` or `scaffold_spine` table is dropped until its rows have been exported to JSON under the data folder on startup (CARD-498). The drop comes a release later.
* Migrations must work for a fresh install and for an upgrade from a DB that still has the tables and rows, with tests for both.
* Jacob's AppData is not production before v1.0 and may be wiped, but that is never a reason to skip the export or the upgrade path.

### Positive Consequences

* One way to build each thing; about 4,760 lines of unused Factory code and its tests leave.
* Skill Studio stops depending on routes named after a retired feature.
* Developer-built tools get an automatic check (CARD-511) that did not exist outside the Factory.

### Negative Consequences / Trade-offs

* No scripted scenario replay (D3). Mitigation: Teach and Observability friction; revisit on real need.
* No automatic wiki research job (D2). Mitigation: chat with AutoReiv's wiki skills.
* Old Factory URLs break after one release of redirects. Mitigation: 308 redirects in CARD-497; no external callers are known.
* Skill Studio keeps `factory*` element ids (D5), which is confusing in code only.

---

## 5. Pros and Cons of Options

### Option 1: Thin shell

* Good, because it is the least work now.
* Bad, because it keeps a screen and routes with no durable purpose and two ways to reach Skill Studio.

### Option 2: Loop behind Developer

* Good, because it keeps scenario replay and automatic research.
* Bad, because it keeps the largest unused subsystem alive for needs nobody has shown. The background loop was never used on Jacob's install.

### Option 3: Retire (chosen)

* Good, because it removes the most code, gives one way per job, and the audit shows the replacements work.
* Bad, because it drops scenario replay and needs six cards done in order.

---

## 6. Superseded cards (history only; files stay)

CARD-159 (autonomous agent pack factory), CARD-164 (Lab training monitor and background runner), CARD-171 (Factory orchestrator), CARD-182 (Lab Monitor retry and activity feed), CARD-195 (dedicated Factory Studio), CARD-351 (Factory intake and steering workbench), and CARD-306's promise to keep the Factory Train button (already undone by CARD-386).
