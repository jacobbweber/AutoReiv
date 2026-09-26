---
id: CARD-495
title: "Retire the Agent Training Factory (1/4): ADR-0060 and steering docs"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-496
  - CARD-511
  - CARD-512
  - CARD-513
  - CARD-497
  - CARD-498
  - CARD-472
  - CARD-417
  - CARD-418
  - CARD-386
  - CARD-368
  - CARD-306
labels:
  - type:product
  - area:factory
  - area:docs
  - P1
---

# [CARD-495] Retire the Agent Training Factory (1/4): ADR-0060 and steering docs

> **Status**: Ready for `build` (2026-09-25 11:39 PM ET: D1-D8 accepted; ADR-0060 drafted as Accepted; ADR-0048/0049/0056/0057 and steering amended on local qa. `build` = mark Done after Jacob reads the ADR, section 8)
> **Created**: 2026-09-25 (replaces the earlier CARD-495 "training loop has no front door", written the same day)
> **Series**: CARD-495 (ADR and docs), then CARD-496 (UI shell), CARD-497 (backend), CARD-498 (data). Revised by the audit (section 1.4): CARD-495, CARD-496, CARD-511, CARD-497, CARD-512, CARD-498. Each lands on its own branch.
> **Related**: CARD-472 (keep-and-fix chat wiring), CARD-417/418 and ADR-0057 (three Studios), CARD-386 (already deleted the Factory runs and pipeline views), CARD-368 (gaps to the backlog), CARD-306
> **Labels**: `type:product`, `area:factory`, `area:docs`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Gap and dependency audit (2026-09-25 ET, qa `10f2bc75`)

Done before the ADR, as Jacob asked. Evidence is code (file:line on qa `10f2bc75`) plus a scratch server (`scratch\c495_audit`, port 8767, fresh data; never Jacob's AppData). Jacob's install was wiped for CARD-509 and has 0 rows in every `factory_*` table.

### 1.1 What the Factory does today, what replaces it, and does the replacement work

| # | What the Factory does | Where | Replacement | Works today? (evidence) | Gap |
|---|---|---|---|---|---|
| F1 | Runs an 8-phase training loop as background jobs (intent, ground, blueprint, author, verify, scenario verify, optimize, promote) | `src/application/agent_training_factory/` (~4,760 non-blank lines); orchestrator started in `src/web/app.py` L336-378; `/api/agent_training_factory/jobs*` in `routers/agent_training_factory.py` L237-439 | No single loop. Each part maps to F2-F9 | Scratch: every Factory GET returns 200; job list empty | None by itself |
| F2 | **Intent distill**: a question battery turns a request into a structured intent | `phases/intent_distill.py` | Tools Studio form + `/api/tools_studio/authoring/talk`; Skill Studio Build job; agent-authoring Socratic intake (becomes a Developer handoff, CARD-497) | Routes present on scratch (authoring jobs are POST routes, 405 on GET) | None |
| F3 | **Ground**: researches and writes a Wiki operating manual | `phases/ground.py` | Chat with AutoReiv's wiki skills (wiki-knowledge, wiki-inbox) | Platform wiki skills are in the scratch catalog | No automatic research job; it becomes a chat request. Decision D2 |
| F4 | **Blueprint**: plans which skills and tools to build | `phases/blueprint.py` | Skill Studio Build proposals (`/api/skill_studio/authoring/jobs/{id}/proposals`) | Route present; CARD-420 tests pass on qa | None |
| F5 | **Author**: writes SKILL.md and tool code | `phases/author.py` | Skill Studio Save (skills); Developer native tool lane `routers/native_tools.py` L61 + `application/tools/native_packaging.py`, and the MCP lane (tools) | Scratch: `POST /api/agent_training_factory/scaffold/save` wrote a skill; `GET .../skills/{id}` returned it; it showed in the catalog's operator skills | Works, but **Skill Studio calls Factory routes** (see 1.2). CARD-497 moves them |
| F6 | **Verify**: runs a verification battery on generated tool code, with retries ("rinses") | `phases/verify.py`, `orchestration/verification_battery.py`, `orchestration/tool_synthesizer.py` | None. Native tools run in the sandbox when called, but nothing checks a Developer-built tool before it is registered: `developer_mediation.py` L375 passes `verify_checker=None` | No | **Real gap: CARD-511** |
| F7 | **Scenario verify**: replays "done when" scenarios against the agent, with an SOP rubric and failure classes | `phases/scenario_verify.py`, `sop_rubric.py`, `failure_class.py` | Partly: Teach (learn from a real bad turn) and observability friction (`/api/observability/friction/*`, 200 on scratch) | Teach and friction work; no scripted replay | No "does the agent still pass these scenarios" check. Decision D3 (recommend drop) |
| F8 | **Optimize**: merges, splits and regroups skills | `phases/optimize.py`, `capability_graph.py` | Observability architectural proposals (`/api/observability/architectural/*`; Agent Studio `forge/proposals.js`) | 200 on scratch (empty list on fresh data) | None |
| F9 | **Promote**: human approval gate, then writes the pack | `/jobs/{id}/promote` L439; chat promotion cards `chat/training.js` L48 | Skill Studio decision (`/api/skill_studio/authoring/jobs/{id}/decision`), Tools Studio jobs, Teach Adopt (`/api/skills/adopt`) | Routes present; CARD-420/500 tests pass | None |
| F10 | Lets you edit each phase's instructions | `/phases*` L796-815; `prompt_registry.py` L170 (`factory_phase_instructions`) | None needed; dies with the loop | n/a | None |
| F11 | Trains from a capability gap ("Open Training Factory" in the gap backlog; `POST /api/agents/{id}/gaps/{gap}/train`) | `forge/tools.js` L80-101; `routers/gaps.py` L117-176 | Gaps are still recorded by the kernel (`agent_kernel.py` L1120, L1544) and listed. Backlog gets **Open in Skill Studio** (`openSkillStudio`, `app.js` L288) and **Ask Developer** (CARD-496) | Scratch: `POST/GET /api/agents/autoreiv/gaps` 200. Buttons are CARD-496 wiring | None beyond CARD-496 |
| F12 | Chat tools: `launch_factory_training`, `inspect_agent_pack` | `infrastructure/tools/factory_dispatch_tools.py`; registered `infrastructure/agents/registry.py` L325-333; granted `platform-packs/autoreiv/pack.json` L93-94, L164-165 and agent-authoring `SKILL.md` L7-8, L51, L58 | launch: Developer handoff. inspect: partly `lookup_agents` (`orchestration_tools.py` L51) | launch is replaced; `lookup_agents` does not show a pack's skills and tools | `inspect_agent_pack` is useful read-only. Decision D4 (recommend keep, move) |
| F13 | Lab Monitor, training popup, Factory screen | `forge/lab_monitor.js` L220-642, `chat/training.js`, `factory.js`, `#view-factory` (`index.html` L3941) | Observability traces and sessions; the three Studios | Yes | None (CARD-496) |
| F14 | Teach remedy named `factory_escalation` | `observability/models.py` L95, `tool_skill_resolver.py` L215, `distillation_service.py` L244-397, `render.js` L267, `observability.js` L835 | "Ask Developer" (CARD-472) | Yes | Rename only (CARD-497) |
| F15 | Software-update "busy" check counts running Factory jobs | `application/system/busy.py` L122-134; `app.py` L357-358 | Studio jobs are already counted separately (`busy.py` L103-120, the `jobs` table) | Yes | None; drop the Factory checker in CARD-497 |
| F16 | Agent Studio panel "Agent Training Optimization" (candidate queue plus an "Open Training Factory" button) | `index.html` L1615-1642; `forge/scaffold.js` L159-210, L366-380; `/api/capabilities/scaffold/*` (`routers/capabilities.py` L258, L282); `SelfScaffoldSpine` (`app.py` L533-555); `scaffold_spine` table (`schema.py` L474) | Tools Studio | The only thing that adds candidates is the panel's own `POST /scaffold/draft`; no UI or agent calls it (rg). So the queue is always empty | **Not in CARD-496/497 scope today. CARD-512** (UI removal folded into CARD-496) |
| F17 | Factory-era leftovers that do nothing | `JitToolSynthesizer` built per kernel, never used (`agent_kernel.py` L136-138); `allow_autonomous_training` / `max_training_retries` saved and passed around (`guardrails.py` L190, `registry.py` L157, `agents.py` L166, `forge.js` L493-496) but nothing acts on them; `AUTO_TRAIN_PROGRESS` handled (`models.py` L185, `chat.py` L412-414, `chat.js` L851) but never sent | None needed | n/a | Delete in CARD-497 (keep DB columns). Decision D7 |

### 1.2 Dependency inventory

**Non-Factory code that relies on Factory code (must be kept or moved, not deleted):**

- `src/application/skills/workshop.py`: its docstring says "Factory workshop persistence", but it is **Skill Studio's persistence and the operator skill list**. Users: `routers/agents.py` L123 (`operator_store_skills`, the CARD-509 Studio pills) and L247 (skills catalog); `skill_authoring.py` L11 (`catalog_tool_ids`); `routers/skills.py` L172 (`clear_operator_skill_side_effects`); `user_catalog.py` L406 (`locate_skill_markdown`); Factory router L1037, L1173, L1181. **Keep**; fix the docstring in CARD-497.
- Skill Studio calls Factory routes: `/capabilities` (`skill_studio.js` L389, `tools_studio_catalog.js` L513); `/scaffold/runbook` and `/scaffold/save` (`skill_studio.js` L259, L338; `skill_authoring.js` L12); `/skills` (`factory/workshop_meta.js` L164, `factory/skill_scope.js` L197). CARD-497 moves the routes (308 redirects); CARD-496 moves the two JS files.
- Factory router helpers used by those routes: `llm.phase_llm_text`, `phases/promote.check_tool_collisions`. Move with the routes.
- Skill Studio DOM: `#view-skill-studio` (`index.html` L4049) has about 150 `factory*` ids (e.g. `factorySkillIdInput` L4125). They are not tied to `#view-factory`. Decision D5 (keep).
- `agent_picker.js` L13 key `factory: 'autoreiv_factory_selected_agent_id'`; the picker is shared by `app.js`, `agent-desktop.js`, `tools_studio.js`, `forge.js`. CARD-496 drops only the `factory` entry.
- `orchestration/tool_synthesizer.py` L82 imports `phases/blueprint._scrub_negated_phrases`; `verification_battery.py` L304, L440 use tool_synthesizer; `jit_synthesizer.py` L15 uses the battery and `domain/orchestration/factory_packets.EvalPacket`. All only serve the Factory or the dead JIT path. Keep only what CARD-511 reuses.

**Factory-only code (safe to delete in CARD-497):** `agent_training_factory/` (phases, orchestrator, prompt_registry, gap_link, failure_class, sop_rubric, llm), `routers/agent_training_factory.py` job/gap/phase routes, `routers/gaps.py` L117-176 (`/train`, gap_link with `agent_training_factory_v1`), `factory_dispatch_tools.py` (except `inspect_agent_pack`, D4), `capability_graph.py`, `jit_synthesizer.py`, `factory_packets.py`, app wiring (`app.py` L49, L336-378, L443-446, L498, L515).

**Pack and skills:** `platform-packs/autoreiv/pack.json` L93-94, L164-165; `platform-packs/autoreiv/skills/agent-authoring/SKILL.md` (named "Agent Capability Architecture & Training Intake"; L7-8, L28, L51, L58).

**DB:** `factory_jobs`, `factory_graphs`, `factory_packets`, `factory_eval_runs` (`schema.py` L381, L407, L416, L429); `factory_phase_instructions` (`prompt_registry.py` L170); `factory_jobs` column migrations (`connection.py` L125-130). CARD-498 must also delete the migrations and the prompt table creation. `scaffold_spine` (`schema.py` L474) depends on CARD-512.

**Frontend:** `factory.js`, `factory/*`, `forge/lab_monitor.js`, `chat/training.js`, training popup; Factory mentions in `app.js` (18), `render.js` (14), `forge/scaffold.js` (12), `stream.js`, `observability.js`, `agent-desktop.js`, `window.js`, `presets.js`, `teach_modal.js`, `event-bus.js`, `store.js`; gap dismiss `forge/tools.js` L108 stays.

**Tests CARD-497 deletes (all Factory-only):** `test_capability_loop`, `test_factory_api`, `test_factory_runner`, `test_factory_packets`, `test_factory_dispatch_tools`, `integration/factory/test_dogfood_factory_pipeline`, `integration/capabilities/test_dogfood_capability_gap_loop`.

### 1.3 Gaps and new cards

- **CARD-511 (P2, Ready):** check a Developer-built native tool automatically (a sandbox smoke call) before it is registered. Must land **before CARD-497**, which deletes the only code check (F6).
- **CARD-512 (P3, Ready):** the "Agent Training Optimization" candidate queue in Agent Studio is always empty (F16). CARD-496 removes the panel; CARD-512 retires `/api/capabilities/scaffold/*`, `SelfScaffoldSpine` and the `scaffold_spine` table (export first), unless Jacob wants it folded into Tools Studio.
- Scope added to CARD-496, CARD-497, CARD-498: see "Audit revisions" at the end of each card.

### 1.4 Revised order

CARD-495 (audit, then ADR-0060) → CARD-496 (UI, now including the F16 panel) → **CARD-511** (tool check) → CARD-497 (backend) → **CARD-512** (scaffold spine backend) → CARD-498 (data export, then drop). CARD-510 and Education Studio (CARD-463 etc.) come after, as before.

### 1.5 Decisions for Jacob

**Decided 2026-09-25, 11:39 PM ET: Jacob accepted D1-D8 exactly as recommended (see section 7).**

| # | Decision | Recommendation |
|---|---|---|
| D1 | Accept this audit as the basis for ADR-0060 | Yes; then draft the ADR on `continue` |
| D2 | Wiki research (F3) has no automatic job; it becomes a chat request | Accept |
| D3 | Scenario replay / agent evaluation (F7) has no replacement | Drop for now; the ADR records it. Revisit only if a real need shows up |
| D4 | `inspect_agent_pack` chat tool | Keep; move it into `orchestration_tools` in CARD-497 |
| D5 | Skill Studio's `factory*` DOM ids | Leave them in this series; renaming is churn with no user value |
| D6 | CARD-511 before CARD-497, reusing the parts of `verification_battery` it needs | Yes |
| D7 | Remove the dead auto-training fields, JIT synthesizer and `AUTO_TRAIN_PROGRESS` event in CARD-497; keep DB columns | Yes |
| D8 | F16 panel: remove the UI in CARD-496; retire the backend in CARD-512 | Yes (retire rather than fold into Tools Studio) |

---


## 2. Four Beats

**Beat 1: What Jacob means.** "We built Agent, Skill and Tool Studios so we no longer need the Factory." The Factory concept is retired: no Factory screen, no autonomous training loop, no Lab Monitor. Improvement happens through the Studios, the Developer, Teach and Observability.

**Beat 2: What the docs say now.**
- ADR-0057 L54 calls the Factory scaffolder "transitional", and L37 rejects "Keep all-in-one Factory". But no ADR retires it.
- ADR-0056 L144 still says "Factory is the sole writer of skill bodies and tool bindings", which has been false since CARD-418 moved that to Skill Studio.
- `steering/product.md` L53 lists "factory" as a current studio. `roadmap.md` L81-82 frames CARD-386/387 as the Factory overhaul. `structure.md` L41 is silent.
- CARD-306 L9/L17 promise "Factory Train button + handshake modal retained", which CARD-386 already undid.

**Beat 3: What will change.**
- A new **ADR-0060 "Retire the Agent Training Factory"**. It amends ADR-0056 L144 (Skill Studio is the writer), completes ADR-0057 §4.1 (L54), and supersedes ADR-0048 (autonomous pack factory) and ADR-0049's Factory framing.
- It records the replacement path and the order of CARD-496..498.
- Update `steering/product.md` (studio list without "factory"; Agent Forge Studio described as Agent Studio), `roadmap.md` (a retirement entry), and `structure.md`.
- Mark CARD-159/164/171/182/195/351 as superseded in the ADR's table (the card files stay as history).

**Status of Beat 3 (2026-09-25):** all of it is drafted (ADR-0060, ADR-0056/0057/0049 notes, ADR-0048 Superseded, product.md, roadmap.md). `structure.md` has no Factory line; its stale studio list is CARD-513.

**Beat 4: What dies.** The idea that the Factory owns training, in any doc.

## 3. Acceptance criteria (EARS)

- **[REQ-495-001]** THE docs SHALL contain `docs/adr/0060-retire-the-agent-training-factory.md`, status Accepted, naming what is replaced by what, the gaps and how each is handled, decisions D1-D8, the keep/move list, the delete list, the order CARD-495, CARD-496, CARD-511, CARD-497, CARD-512, CARD-498, and the data rule.
- **[REQ-495-002]** `steering/product.md` SHALL NOT list a Factory studio as current. `steering/roadmap.md` SHALL list the retirement cards.
- **[REQ-495-003]** ADR-0056 SHALL carry a dated amendment saying Skill Studio (not the Factory) writes skill bodies and tool bindings, pointing to ADR-0060.
- **[REQ-495-004]** ADR-0048 SHALL be marked Superseded by ADR-0060. ADR-0049 and ADR-0057 SHALL carry a dated note pointing to ADR-0060.
- **[REQ-495-005]** WHEN CARD-495 is Done, THE product code SHALL be unchanged (docs only).

## 4. Background for ADR-0060 (planning notes, kept)


**Memory note (keep):** On 2026-09-25 at 3:44 PM ET, Jacob confirmed retiring the Factory concept ("We built Agent, Skill and Tool Studios so we no longer need the Factory, but we have other mechanisms for training and improvement") and accepted every recommendation in the CARD-472 revised report:
- CARD-472 is keep-and-fix only.
- The retirement is CARD-495..498.
- Teach stays as a Skills feature.
- Needs-tool escalation goes to a Developer chat (Tools Studio fallback).
- Factory data is exported on startup, then the tables are dropped a release later.

Evidence gathered in that planning pass:
- Factory Studio (`factory.js`, 251 lines) saves nothing; its only call is `GET /api/agents`.
- The Lab Monitor and training popup are reachable only from an existing job.
- Jacob's live DB has 0 rows in all `factory_*` tables and 0 capability gaps (read-only check).
- The `autoreiv` pack's `agent-authoring` skill still grants `launch_factory_training`.

**Replacement path for the ADR:**

| Need | Before (Factory) | After |
|------|------------------|-------|
| Agent identity, prompt, skill on/off | Factory col 1 (unsaved) and Agent Studio | **Agent Studio** |
| Author or refine a skill | Factory workshop | **Skill Studio** (Developer-mediated Build/Review, CARD-420/422) |
| New tool | 8-phase loop / `launch_factory_training` | **Tools Studio** form, then Developer (native or MCP lane, CARD-423) |
| A failed turn becomes a lesson | Teach escalation to Factory | **Teach** proposal (skill), or "Ask Developer to build this tool" (CARD-472) |
| Capability gap | Backlog "Open Training Factory" | Agent Studio backlog: **Open in Skill Studio** or **Ask Developer** (CARD-496) |
| Operational tuning | Factory phases | **Observability** friction and architectural proposals |

**ADR outline:** Context (ADR-0057 transitional; CARD-386 already removed runs/pipeline) → Drivers ("no theatre Studios without durable state", ADR-0057 L28) → Options (keep the thin shell / re-home the loop / retire; **retire chosen**) → Consequences (routes moved, tables exported then dropped, tests pruned under ADR-0055).

## 5. Tests

**None. This card changes docs only.** Earlier this section planned a Vitest/pytest check on `steering/product.md`. I recommend dropping it (decision D9). It would only test prose, which ADR-0055 counts as theatre. The real checks live where behaviour changes:
- CARD-496 smoke: no Factory in the dock; the gap backlog opens Skill Studio.
- CARD-497 integration: Factory job, gap and phase routes return 404; the old Skill Studio paths give 308 redirects.
- CARD-498 migration tests: fresh install and upgrade.

The runbook's `rg` check below is the gate for this card.

## 6. Runbook

1. Read `docs/adr/0060-retire-the-agent-training-factory.md`.
2. Read the diffs: ADR-0056 (header and 4.7), ADR-0048 (status), ADR-0049 and ADR-0057 (notes), `steering/product.md` (L41, L53), `steering/roadmap.md` (Milestone 21).
3. Run `rg -n -i "factory" steering docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md`. Every hit should be historical (roadmap Done items), the "factory seed" wording for `platform-packs/`, `createStore` factory in tech.md, or a pointer to ADR-0060. Nothing should describe the Factory as current.
4. `git diff --stat 10f2bc75..HEAD` should show only `docs/` and `steering/` files.

## 7. Decisions (decided 2026-09-25, 11:39 PM ET)

Jacob accepted D1-D8 exactly as recommended in section 1.5. They are recorded in ADR-0060 section 4.2.

| # | Decision | Decided |
|---|---|---|
| D1 | The audit is the basis for ADR-0060 | Yes |
| D2 | Wiki research is chat-only | Yes |
| D3 | Scenario replay / agent evaluation | Dropped for now, no card |
| D4 | `inspect_agent_pack` | Keep, move to orchestration tools (CARD-497) |
| D5 | Skill Studio `factory*` ids | Leave |
| D6 | CARD-511 before CARD-497, may reuse `verification_battery` parts | Yes |
| D7 | Delete dead auto-training fields, JIT synthesizer, `AUTO_TRAIN_PROGRESS`; keep DB columns | Yes (CARD-496 UI, CARD-497 backend) |
| D8 | "Agent Training Optimization" panel: UI in CARD-496, backend retired in CARD-512 | Yes |

**Still open (recommendation in bold):**
- **D9**: No automated docs test for this card (section 5). **Accept.**
- **D10**: What "build" means for this card (section 8). **Accept: "build" = mark Done after Jacob has read the ADR.**

## 8. What "build" does (and definition of done)

The ADR and all doc amendments were drafted in the 2026-09-25 "continue" pass and committed on local qa (not pushed). **The ADR plus the amendments are the whole deliverable.** There is no product code, no test code and no feature branch.

So on **`build`**:
1. Apply any wording changes Jacob asks for after reading ADR-0060.
2. Run the runbook (section 6) and paste the `rg` result into this card.
3. Set CARD-495 `status: Done` in a `docs(cards)` commit on qa.

On **`merge to qa`**: there is no branch to merge. It means push qa to origin, carrying the CARD-495 commits. They can also ride along with CARD-496's merge.

**Definition of done:**
- ADR-0060 is Accepted and committed.
- ADR-0048 is Superseded; ADR-0049, ADR-0056 and ADR-0057 point to ADR-0060.
- `steering/product.md` and `roadmap.md` are updated.
- The runbook `rg` check is clean.
- The only files changed are in `docs/` and `steering/`.
- CARD-496..498, CARD-511 and CARD-512 statuses reflect the decisions.
- The `status: Done` commit is on qa.
