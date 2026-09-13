# [CARD-126] Platform packs, Wiki skill stub, nested Agent Studio

> **Status**: Done
> **Created**: 2026-08-31
> **Spec Reference**: CARD-117; CARD-118; CARD-119; CARD-121; CARD-124; CARD-125
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
Agent Studio still shows two flat lists (Tools, then Skills). Assistant and AutoReiv are still Python builtins in `profiles.py`. Wiki tools are a flat Platform pile with no skill. Adding a new Platform skill, Platform pack, or user pack mixes those homes.

**Walked (2026-08-31 Jacob t195u–t202u):** Keep the name **Platform**. Three homes. Assistant and AutoReiv become Platform Agent Packs (always seeded). Wiki is a Platform skill with a `SKILL.md` stub Jacob will fill. Assistant pack owns weekly/daily/task. AutoReiv pack owns pack/recommend plus two Observability skills. Studio nests tools under skills. Do not reverse CARD-117/121.

This is a **product card**. Do not implement until Jacob says build. Do not name inspiration products. Do not start CARD-116 (memory) or CARD-125 (Wiki schema/front matter revisit).

---

## 2. Three homes (locked)

Keep the name **Platform**, not Global.

1. **Platform skills and tools** — ship with the product. Any agent can tick them in Agent Studio (shared pool).
2. **Platform Agent Packs** — **Assistant** and **AutoReiv** only. Come with the product, already configured. Have their own dedicated skills/tools. Can also tick Platform skills/tools. Always installed (seed into `$DATA_DIR/packs/` on launch if missing). Not the optional catalog.
3. **User Agent Packs** — same Agent Studio as platform packs. Live in `$DATA_DIR/packs/`. Optional git catalog is repo-root **`agent-packs/`** (not auto-loaded on startup). Conductor / Coding / Review stay here (CARD-124).

### Folder split
- Product Platform packs: `platform-packs/assistant`, `platform-packs/autoreiv` (seed `$DATA_DIR/packs/` if missing).
- User catalog: `agent-packs/` (optional import; README says so).
- Live installs: `$DATA_DIR/packs/<id>/`.

Foundation/refactor so a new Platform skill, Platform pack, or user pack goes in the matching home without mixing is **in scope**.

---

## 3. What to Build

### Platform Agent Packs (Assistant + AutoReiv)
- Add `platform-packs/assistant/` and `platform-packs/autoreiv/` as schema **1.1** packs (tools nested under skills).
- Drop `ASSISTANT_PROFILE` and `AUTOREIV_PROFILE` as Python builtins once those packs seed. **Do not** rip Agent Builder (hidden builtin: Chat/Studio skip `agent-builder` by id).
- On launch, if `$DATA_DIR/packs/assistant` or `autoreiv` is missing, copy from `platform-packs/`. Do **not** auto-load `agent-packs/`.
- `platform-packs/README.md` (and a root README pointer): these two always install; `agent-packs/` remains optional user catalog.
- Tests that assumed Assistant / AutoReiv were builtins must load them as platform packs (or fixtures).

### Platform skill `wiki` (stub only)
- Create Platform skill `wiki` with a `SKILL.md` stub (name + short blurb + empty/placeholder body). Jacob fills the operating manual later.
- Nest Wiki tools under it: `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`, `promote_artifact_to_wiki`, and `wiki_note_organize` if it is in the catalog.
- Any agent ticks `wiki` in the Platform box. Assistant and AutoReiv **seed with `wiki` ticked** so today’s Chat does not lose notes. Untick in Studio to drop it.
- **Do not** redesign Wiki schema, YAML front matter, or the operating manual here. That is **CARD-125**.

### Assistant pack (`id="assistant"`)
- **Job:** day-to-day assistant, weekly/daily task loop. Wiki is Platform, not pack-owned.
- **Show in Chat:** on.
- **Pack skill:** `weekly-tasks` — `get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`.
- Keep today’s other Assistant ticks that are not wiki and not weekly-tasks (handoff, lookup, propose_*, `skill_view`, artifacts). Do not silently drop them. Do not invent a new Assistant skill for them on this card.

### AutoReiv pack (`id="autoreiv"`)
- **Job:** platform SRE, pack scaffold/import/export, HITL recommend when stuck.
- **Show in Chat:** on.
- **Pack skills:**
  - `build-agent-pack` — `export_agent_pack`, `import_agent_pack`, `scaffold_agent_pack`, plus today’s pack-list/commit helpers (`list_user_skill_packs`, `list_available_skills_and_tools`, `commit_skill_pack`, `skill_view` if they stay on AutoReiv).
  - `recommend-capability` — `propose_skill`, `propose_tool`, `propose_workflow`, `propose_agent_specification`, `propose_followup`.
  - `platform-health` — `system_info`, `inspect_system_health`, `get_tool_health_matrix`, `get_recent_errors`, `get_system_logs`, `test_provider_connectivity`, `cli_exec`.
  - `session-inspect` — `get_session_transcript`, `get_agent_sessions`, `get_agent_usage_summary`, `get_session_artifact`, `batch_worker_scan`.
- Wiki is Platform (seed ticked). `save_agent_specification` stays off AutoReiv.

### Agent Studio (nested skills)
- After Operating Manual & Constitution (`#forgeSystemPrompt`): **Platform** box, then **this pack** box.
- Each skill is a row: tick the skill (runbook), **Edit**, collapse/expand for its tools. **Default collapsed**.
- Tick a skill to give the agent the runbook. Expand to tick its tools. Unticked skill does not put its tools in Chat.
- Same UI for Platform packs and user packs.
- Files today: `src/web/templates/index.html`, `src/web/static/modules/studios/forge.js` (filename kept; Forge is not a place name).
- Do **not** reverse CARD-117/121: Chat still lists this agent’s ticked tools every turn. Do not hide tool schemas behind skills at turn time.

---

## 4. Acceptance Criteria (Definition of Done)

- [x] `platform-packs/assistant` and `platform-packs/autoreiv` exist as schema 1.1 packs with the skills and tool ticks above.
- [x] Launch seeds those two into `$DATA_DIR/packs/` if missing. `agent-packs/` is still not scanned on startup.
- [x] `profiles.py` no longer registers Assistant or AutoReiv as builtins. Agent Builder stays (hidden).
- [x] Platform skill `wiki` exists as a stub `SKILL.md`; wiki tools nest under it. CARD-125 is not done here.
- [x] Assistant pack-owned skill is `weekly-tasks` (those five tools). AutoReiv pack-owned skills are the four named above.
- [x] Agent Studio: Platform box then this pack; skill rows with Edit + collapsed tools.
- [x] Chat still injects ticked tool schemas every turn (117/121).
- [x] Unit/vitest updated. Status **In Review** after code. Not Done until live test. Local commit only. No push.

---

## 5. Constraints & Honor Flags
- Work on `qa`. Do not push. Do not clone.
- Name is **Platform**, not Global.
- Pack = one agent. Assistant and AutoReiv are Platform packs, not user catalog.
- Do not reverse CARD-117/121.
- Do not implement CARD-125 (Wiki schema / deterministic YAML / extensive metadata).
- Do not start CARD-116 or CARD-122.
- Do not rip Agent Builder internals.
- Do not auto-load `agent-packs/` on startup.
- Do not put Python tool implementations in the pack. Existing catalog only.

---

## 6. Pickup
Status stays **In Review**. Not Done until Jacob live-tests (he cannot from the airport).

Live-test leftovers:
- CARD-124: reload, Chat shows Conductor not Coding/Review, Studio lists all three.
- CARD-126: reload, nested Studio (Platform box then this pack, skill rows default collapsed), Chat still has wiki and weekly tools.

CARD-125 stays Ready later (Wiki schema / YAML front matter). Do not start CARD-116 (memory) unless Jacob says so.
