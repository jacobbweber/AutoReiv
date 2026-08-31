# [CARD-127] Platform skills and agent pack studio layout

> **Status**: Done
> **Created**: 2026-08-31
> **Spec Reference**: CARD-117; CARD-118; CARD-119; CARD-121; CARD-124; CARD-126
> **Labels**: `type:feat`, `type:ui`, `type:docs`

---

## 1. Why / Intent

In Agent Studio, an agent's skills and tools must have a clear top-down logical organization with zero loose or unorganized checkboxes. 

Currently, tools that are not declared in an agent pack's own skill list (such as cross-assigned or shared tools like `handoff_to_agent`, `lookup_agents`, and `propose_skill`) get rendered at the bottom in an unorganized **"Also ticked"** section.

**The Solution:**
1. **Top-Down Hierarchy in Agent Studio**:
   - **Box 1 (Top): Platform Skills & Tools** — Shared platform capabilities available to any agent (e.g., Wiki, Agent Coordination / Handoff, Capability Proposals). Each skill nests its tools (default collapsed). Any agent can tick skills and individual tools here.
   - **Box 2 (Bottom): Agent Pack Skills & Tools** — Dedicated skills and nested tools owned specifically by this agent pack (e.g., `weekly-tasks` for Assistant, `build-agent-pack` and `platform-health` for AutoReiv, or custom skills on user packs).
2. **Promote Shared Capabilities to Platform**:
   - Move shared or cross-assigned skills/tools into Platform Skills & Tools so they are organized under proper skills and can be ticked on any agent profile.
3. **Zero Stray Tools**:
   - Completely eliminate the "Also ticked" loose tool list. Every single tool is nested under a skill.

---

## 2. What to Build

### 1. Platform Skills & Tools Definition
- Define the shared Platform Skills with their nested tools in `src/application/agent_packs/schema.py` and the catalog:
  - `wiki`: `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`, `promote_artifact_to_wiki`, `wiki_note_organize`
  - `coordination` (Agent Coordination): `handoff_to_agent`, `lookup_agents`, `propose_followup`
  - `proposals` (Capability Proposals): `propose_skill`, `propose_tool`, `propose_workflow`, `propose_agent_specification`, `list_available_skills_and_tools`, `skill_view`, `list_user_skill_packs`
  - Any other shared cross-agent tools promoted to corresponding Platform skills.

### 2. Clean Agent Packs
- **Assistant Pack (`platform-packs/assistant/pack.json`)**:
  - Dedicated Pack Skill: `weekly-tasks` (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`).
  - Allowed Platform Skills: `wiki`, `coordination`, `proposals` (with their corresponding tool ticks).
  - No orphan/stray tools in `pack_tool_names`.
- **AutoReiv Pack (`platform-packs/autoreiv/pack.json`)**:
  - Dedicated Pack Skills: `build-agent-pack`, `platform-health`, `session-inspect`.
  - Allowed Platform Skills: `wiki`, `coordination`, `proposals` (with their corresponding tool ticks).
- **User Agent Packs (`agent-packs/conductor`, `coding`, `review`)**:
  - Keep their dedicated pack skills; tick Platform skills as needed.

### 3. Agent Studio UI (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`)
- **Top Box: Platform Skills & Tools** (`#forgePlatformBox`):
  - Lists all Platform skills. Each skill row shows name, description, `Edit` button for the runbook, and `Tools` toggle button (default collapsed).
  - Expanding shows the nested tool checkboxes.
  - Ticking a skill grants the runbook; ticking tool checkboxes grants the tool callables.
- **Bottom Box: [Agent Name] Pack Skills & Tools** (`#forgePackBox`):
  - Dynamic title reflecting the selected agent (e.g., "Assistant Pack Skills" or "AutoReiv Pack Skills").
  - Lists the dedicated pack skills with their nested tools.
  - Remove `ungrouped_pack_tools` / "Also ticked" HTML completely.
- **Save & Load**:
  - Persisting agent profile accurately saves `allowed_skill` and `pack_tool_names` across both Platform and Pack boxes.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] Every tool in Agent Studio is nested under a skill. Zero "Also ticked" loose checkbox sections.
- [x] Agent Studio displays two organized sections:
  1. Top: **Platform Skills & Tools** (Shared skills: `wiki`, `coordination`, `proposals`, etc.).
  2. Bottom: **Agent Pack Skills & Tools** (Pack-owned dedicated skills).
- [x] `platform-packs/assistant/pack.json` and `platform-packs/autoreiv/pack.json` updated with dedicated pack skills and allowed platform skills.
- [x] Ticking/unticking platform skills, pack skills, and nested tools persists across page reload and saves to `$DATA_DIR/packs/`.
- [x] Chat still injects ticked tool schemas every turn (CARD-117 / CARD-121).
- [x] Automated tests (unit & vitest) pass cleanly.
- [x] Status In Review after code; local commit only on `qa`, no push.

---

## 4. Constraints & Honor Flags

- Work on `qa`. Do not push. Do not clone.
- Keep the name **Platform**, not Global.
- Zero stray tools: every tool belongs under a skill.
- Do not reverse CARD-117/121: Chat still lists this agent's ticked tools every turn.
- Do not implement CARD-125 (Wiki schema / YAML front matter) here.
- Do not start CARD-116 (memory) here.

---

## 5. Walked Lock (2026-08-31)

| Beat | Lock |
|------|------|
| Hierarchy | Top: Platform Skills & Tools. Bottom: Agent Pack Skills & Tools. |
| Zero Stray Tools | Remove "Also ticked" completely. All tools are nested under skills. |
| Shared Skills | Cross-assigned/shared tools are grouped into Platform skills (Wiki, Coordination, Proposals). |
| Dedicated Skills | Assistant owns `weekly-tasks`. AutoReiv owns `build-agent-pack`, `platform-health`, `session-inspect`. |
| Per-Agent Ticks | Any agent profile can tick Platform skills and their individual tools. |

---

## 6. Pickup

Status is **Ready**. Do not implement until Jacob says **build** / **continue**.
