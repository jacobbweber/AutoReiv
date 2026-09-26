---
id: CARD-502
title: "Adopted Teach skill is not used on the next message and is dropped on restart"
status: In Review
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-500
  - CARD-352
  - CARD-358
  - CARD-443
  - CARD-449
  - CARD-503
  - CARD-505
  - CARD-506
  - CARD-507
labels:
  - type:bug
  - area:skills
  - area:agents
  - P1
---

# [CARD-502] Adopted Teach skill is not used on the next message and is dropped on restart

> **Status**: In Review (built 2026-09-25 on `feat/card-502-adopt-skill-persists`, D1-D9 as recommended; not merged)
> **Created**: 2026-09-25 (found while refining CARD-500)
> **Related**: CARD-500 (Teach request and card, Done), CARD-352 / CARD-358 (Teach, proposal persistence), CARD-443 (platform pack promotion), CARD-449 (keep customizations, `user_modified`), CARD-503 (distill timeout, separate), CARD-505 (AutoReiv prompt looks edited on every restart), CARD-506 (dead duplicate agent-save paths)
> **Labels**: `type:bug`, `area:skills`, `area:agents`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 0. Reproduction (2026-09-25 7:45-7:55 PM ET, scratch server only)

Scratch app on 127.0.0.1:8767 with data in `scratch/c500_data` (guarded by `scripts/smoke_server.py`; the real AppData was never touched), fake model on 18434 that logs the skill list in each chat turn's system prompt. Scripts: `scratch/c502_run.ps1`, `scratch/c502_repro.cjs`, `scratch/c502_db.py` (read-only SQLite). Results: `scratch/c502_a.json`, `c502_db_a.json`, `c502_gateway_a.log` (before restart) and `c502_b.json`, `c502_db_b.json`, `c502_gateway_b.log` (after restart).

**Before restart** ("Keep my agent customizations" on, the default):
1. New chat, sent "C502 first question", clicked Teach on the reply, typed "always cite the source", clicked Distill: 200, card "Cite Sources" (`skill_id` `cite-sources`).
2. Clicked Adopt: `POST /api/skills/adopt` 200 `{"status":"adopted","skill_id":"cite-sources","file_path":"packs/autoreiv/skills/cite-sources/SKILL.md"}`; toast "Skill mounted to autoreiv. Active for your next message."
3. `GET /api/agents/autoreiv` `allowed_skill`: the same 13 platform skills as before. **No `cite-sources`.**
4. SQLite `custom_agents` row `autoreiv`: `allowed_skills_json` has the 13 skills, `user_modified` 0. No `agent_overrides` row for autoreiv.
5. User-data `packs/autoreiv/pack.json` `allowed_skill`: the 13 skills **plus** `cite-sources`. `packs/autoreiv/skills/cite-sources/SKILL.md` exists.
6. Sent "C502 next message after adopt": the system prompt's skill list had the same 18 lines as the first turn. **No "Cite Sources".**

**Agent Studio comparison** (same run, on Tutor): `PUT /api/agents/tutor` with one extra ticked skill (`build-agent-pack`) returned 200. `GET /api/agents/tutor` listed it; `agent_overrides` and `custom_agents` rows listed it; `user_modified` stayed **0**; `platform_operator_disabled_skills` = `{"tutor": []}`.

**After restart** (same data folder, `c502_run.ps1` without `-Wipe`):
7. Startup sync report: autoreiv `promoted_partial` ("skipped fields: system_prompt"), tutor `promoted`.
8. `GET /api/agents/autoreiv`: 13 skills, no `cite-sources`. `packs/autoreiv/pack.json`: 13 skills, **`cite-sources` removed**. The `SKILL.md` folder is still on disk, orphaned.
9. `GET /api/agents/tutor`: 7 skills. **The Agent Studio tick of `build-agent-pack` was also dropped** (override row and `pack.json` both reset to the seed list).
10. Sent "C502 message after restart": no "Cite Sources" in the skill list.

## 1. Root causes (file and line, qa `131eef2c`)

- **Not live on the next message.** `SkillDistillationService.adopt_skill` (`src/application/skills/distillation_service.py` L80-158) writes `SKILL.md` (L106-110) and adds the id to user-data `pack.json` (L112-141). Its only "live" step (L143-150) edits the profile returned by `agent_registry.get_agent()`, but `BuiltinAgentRegistry.get_agent` (`src/infrastructure/agents/registry.py` L73-168) builds a fresh copy from SQLite on every call (`state_store.get_agent_profile` plus the `agent_overrides` overlay, L104-166). The edit is thrown away. The chat turn reads the same SQLite-backed profile, and `render_skill_index` (`src/application/kernel/agent_kernel.py` L535-541, `src/application/skills/user_catalog.py` L44-84) lists only `allowed_skill`, so the new skill never appears.
- **Dropped on restart.** Startup promotion (`src/infrastructure/skills/platform_pack_promotion.py` `promote_one_platform_pack`, clean path L668-767) sets the allowlist to `merge_skills_respecting_disabled(...)` = platform seed skills minus operator-disabled (L132-146, L698-705) for any pack not `user_modified`, then rewrites `pack.json` from the seed (L740-748). Operator-**added** skills have no record, so they vanish. `should_set_content_lock` (L149-181) locks only on a system-prompt change; adding a skill never sets `user_modified`. That is why the Agent Studio tick on Tutor is lost too.
- **The toast is hard-coded.** "Active for your next message" is literal text in `src/web/static/modules/studios/chat/render.js` L294, L352, L357; the server answer is not checked.
- **Unknown agent id creates junk.** `adopt_skill` creates `packs/<id>/` when it does not exist (L103-104) instead of refusing.

## 2. Four Beats

**Beat 1: What Jacob means.** When I click Adopt and it says the skill is on, the agent lists and uses that runbook from my next message, it is still there after a restart, and a skill I tick by hand in Agent Studio also survives a restart.

**Beat 2: What AutoReiv does now.** Adopt writes the `SKILL.md` and edits `pack.json`, then says "Active for your next message". The agent's stored skill list does not change, so the next message does not list the skill. On restart, platform promotion resets the skill list and `pack.json` to the platform seed and drops the adopted skill; the same happens to any extra skill ticked in Agent Studio on a platform agent.

**Beat 3: What will change.** Adopt adds the skill to the agent's stored skill list through the same save Agent Studio uses, then re-reads the agent and only says the skill is on if the agent really lists it. Platform promotion keeps skills the operator added (by Adopt or by ticking in Agent Studio) as long as their `SKILL.md` is in that agent's user-data pack, the same way it already keeps skills the operator turned off. With "Keep my agent customizations" off, the message says the skill will be removed on the next restart. Unknown agents are refused.

**Beat 4: What dies.** The in-memory-only registry edit in `adopt_skill` (L143-150); the hard-coded "Active for your next message" text (three copies in `render.js`); the separate `pack.json` writer in `adopt_skill` (replaced by the shared save and projection); creating a pack folder for an unknown agent id.

## 3. Acceptance criteria (EARS)

- **[REQ-502-001]** WHEN Jacob adopts a proposal for agent A, THE SYSTEM SHALL add the skill id to A's stored `allowed_skill` (the same store records Agent Studio Save writes), write `SKILL.md` under the user-data `packs/A/skills/<id>/`, and never write under the checkout.
- **[REQ-502-002]** WHEN the next message is sent to A after Adopt, THE skill list in A's system prompt SHALL include the adopted skill's name and description.
- **[REQ-502-003]** WHEN the app restarts with "Keep my agent customizations" on, A SHALL still list every skill the operator added (by Adopt or by ticking in Agent Studio) whose `SKILL.md` exists in A's user-data pack, in the stored profile and in `pack.json`.
- **[REQ-502-004]** WHILE "Keep my agent customizations" is off, THE Adopt success message SHALL say the skill will be removed on the next restart, and the restart SHALL remove it from the list (as with other customizations) while leaving the `SKILL.md` folder on disk.
- **[REQ-502-005]** THE Adopt response SHALL report `active` (true only when a fresh read of A lists the skill), `already_adopted`, and `resets_on_restart`; THE card SHALL show "Cite Sources is on for autoreiv from your next message." only when `active` is true, and a readable error otherwise.
- **[REQ-502-006]** IF the same skill id is adopted again for A, THEN THE SYSTEM SHALL keep one entry and replace that adopted `SKILL.md` with the new text. IF the id matches one of A's platform (stock) skills, THEN THE SYSTEM SHALL return 409 "autoreiv already has a platform skill called cite-sources. Rename the lesson and try again." and change nothing.
- **[REQ-502-007]** IF the agent id does not exist, THEN THE SYSTEM SHALL return 404 and SHALL NOT create any folder. Ids with path characters stay rejected (`SAFE_ID_RE`).
- **[REQ-502-008]** Adopting SHALL NOT set `user_modified` on a platform agent (platform prompt and stock-skill updates keep flowing).

## 4. Decisions (accepted 2026-09-25 7:50 PM ET: all as recommended)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Which save path does Adopt use | (a) Reuse the Agent Studio save: extract the skill-list part of `PUT /api/agents/{id}` (`src/web/routers/agents.py` L381-611: `agent_overrides` for platform agents, `register_custom_agent` plus override for custom agents, `pack.json` projection) into one application function both call; (b) a second writer inside `adopt_skill` | **(a) one shared function.** No second writer |
| D2 | How an added skill survives restart | (a) Mark the agent `user_modified` on Adopt (freezes all platform prompt and skill updates for that agent); (b) record per-agent "operator-added skills" (a settings key next to `platform_operator_disabled_skills`) and have promotion use seed minus disabled **plus added** (only ids whose `SKILL.md` is in the user-data pack) | **(b) record added skills.** This changes the earlier draft (which said mark `user_modified`): the repro shows Agent Studio ticks are not locked either, and a lock would stop platform updates for AutoReiv |
| D3 | The Agent Studio "extra tick lost on restart" bug (step 9) | Fold into this card / separate card | **Fold in.** Same cause and same fix (D2); one test covers both |
| D4 | "Keep my agent customizations" off | (a) Keep adopted skills anyway; (b) treat them like other customizations: removed on restart, backup written, `SKILL.md` left on disk, and the Adopt message warns | **(b)**, matching CARD-449's promise that Off resets to platform defaults |
| D5 | Success wording | Keep "Skill mounted... Active for your next message" / server-driven text | **Server-driven:** "Cite Sources is on for autoreiv from your next message." when `active`; add " Keep my agent customizations is off, so it will be removed on the next restart." when `resets_on_restart`; history card after reload shows "On for autoreiv" |
| D6 | Adopting an id that already exists | (a) Adopted before: replace its `SKILL.md` with the new lesson, one list entry, message "Updated Cite Sources for autoreiv"; (b) matches a platform stock skill: 409, change nothing (promotion would overwrite a stock body anyway) | **(a) and (b) as stated** |
| D7 | Where the `SKILL.md` lives | User-data `packs/<agent>/skills/<id>/` (today) / shared `$DATA_DIR/skills/` | **Keep per-agent pack folder.** The lesson belongs to one agent; promotion never deletes operator-only skill folders (L417-425) |
| D8 | Custom (non-platform) agents | Same shared save (D1) / skip | **Same save.** Promotion never touches them; the stored list still has to change |
| D9 | Old orphaned `SKILL.md` folders from earlier adopts | Migrate them into the list / leave them | **Leave them.** Agent Studio can tick them, and after D2 that tick survives restart |

## 5. Failing-tests-first plan (write, run, see red, then fix)

**pytest unit** (new `tests/unit/skills/test_card502_adopt_persists.py`, real `SQLiteStateStore` on `tmp_path`, platform packs installed into a tmp data folder):
1. Adopt `cite-sources` for `autoreiv`: `registry.get_agent('autoreiv').allowed_skill` contains it (red today).
2. The kernel system message for the next turn lists "Cite Sources" in the skill list (red today).
3. After Adopt, `promote_one_platform_pack('autoreiv')` with keep-customizations on: the stored list and user-data `pack.json` still contain it (red today).
4. Agent Studio `PUT /api/agents/tutor` adding a skill, then promotion: still listed (red today).
5. Keep-customizations off: promotion removes it from the list, writes a backup, leaves the `SKILL.md` folder (control).
6. Adopting twice keeps one entry and the newer `SKILL.md` text; a stock id returns 409 and changes nothing; an unknown agent returns 404 and creates no folder (404 and 409 red today).
7. Response fields `active`, `already_adopted`, `resets_on_restart` (red today). `user_modified` stays false after Adopt on a platform agent.
8. Adopt for a custom agent: listed on the next read (red today).

**pytest integration** (new `tests/integration/test_card502_adopt_restart.py`): build the app on a tmp data folder, Adopt through `POST /api/skills/adopt`, build a second app on the same folder (startup promotion runs), `GET /api/agents/autoreiv` lists `cite-sources` (red today).

**Vitest** (new `tests/unit/frontend/adopt_status_502.test.js`): Adopt with `{active:true}` shows "Cite Sources is on for autoreiv from your next message."; `{active:true, resets_on_restart:true}` adds the restart warning; `{active:false}` shows a readable error; `render.js` no longer contains "Active for your next message" (red today). No net growth in `render.js` (CARD-456 cap).

**Smoke** (Playwright desktop + phone, routed fixtures): **TC-37** Adopt shows the server-driven success text; a routed `resets_on_restart:true` response shows the warning.

Then full Vitest, smoke, pytest unit and integration, ESLint, ruff (known CARD-454/456 failures only), and rerun `scratch/c502_repro.cjs` a/b.

## 6. Build order

1. Shared skill-list save (D1) in the application layer; `PUT /api/agents/{id}` calls it for its skill part.
2. Operator-added skills record and promotion merge (D2, D3); keep-customizations off clears it with a backup (D4).
3. `adopt_skill`: 404 unknown agent, 409 stock id, write `SKILL.md`, call the shared save, re-read, return `active` / `already_adopted` / `resets_on_restart`. Remove L143-150 and the separate `pack.json` writer.
4. `render.js` card text from the response (D5); no net line growth.
5. CHANGELOG `[Unreleased] ### Fixed`, Scavenger Pass, preflight, scratch repro rerun, In Review.

## 7. Runbook (Jarvis, after build)

Desktop (http://127.0.0.1:8000, Ctrl+F5):
1. Open Chat with AutoReiv, send a question, wait for the reply.
2. Click Teach on the reply, type "always cite the source", click Distill Skill Runbook, then click Adopt on the card.
3. The message reads "<skill name> is on for autoreiv from your next message."
4. Open Agent Studio, pick AutoReiv: the new runbook is ticked in the skill list.
5. Back in Chat, ask a factual question. The reply follows the runbook, or the Thinking drawer shows the agent opening it with `skill_view`. (A real model may not always open it; step 4 is the firm check.)
6. Restart serve: `powershell -ExecutionPolicy Bypass -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`. Ctrl+F5, open Agent Studio > AutoReiv: still ticked.
7. In Agent Studio, tick one extra runbook on Tutor, click Save, restart serve again: that tick is still there.
8. Click Teach on a reply again with the same lesson. If the new card has the same name, Adopt says "Updated <name> for autoreiv. It is used from your next message." and the skill list shows it once. A reloaded card shows "On for autoreiv." with no Adopt button (CARD-507).

Phone (http://192.168.1.99:8000):
1. Open Chat, send a question, tap Teach on the reply, type a lesson, tap Distill, tap Adopt: the "is on for autoreiv" message appears.
2. Send another message: no error; after the desktop restart in step 6, Agent Studio on the phone still shows the runbook ticked.

## 8. Out of scope

- Distill model timeout and silent fallback: **CARD-503**.
- AutoReiv's system prompt looking operator-edited on every restart (trailing newline): **CARD-505**.
- Dead duplicate agent-save paths (`POST /api/settings/agents/{id}`, `SettingsService.save_agent_customization`): **CARD-506**.
- Needs-tool card title: **CARD-504**. Factory wording in the AutoReiv skill list: **CARD-497**.
- Reloaded card text going stale after the skill is removed: **CARD-507**.

## 9. Build note (2026-09-25 8:20 PM ET, `feat/card-502-adopt-skill-persists`)

**Commits:** `c4489a50` card In Progress, `9f725200` failing tests (all red first), `9f5bab68` fix, `12766715` updates to the CARD-358 check and smoke TC-35 for the new text, then docs (CHANGELOG, this note, CARD-507).

**What changed:**
- `src/application/agent_packs/skill_list.py`: `persist_agent_profile` is the one save used by Agent Studio `PUT /api/agents/{id}` and by Adopt (via `add_skill_to_agent`, skills only, never sets the lock).
- `platform_pack_promotion.py`:
  - Settings key `platform_operator_added_skills` records, per agent, the skills beyond the platform seed.
  - Promotion re-applies them when a `SKILL.md` exists, skips the "unchanged" short-circuit while any are recorded, and projects them into `pack.json`.
  - It never prunes their folders. This was a second cause: the retired-stock check treated an added skill as retired and deleted its folder on restart.
  - Keep-customizations off, a locked force-reset, and Reset to platform defaults all back up the list and clear the record.
- `adopt_skill`: 404 unknown agent (no folder), 409 on a platform skill id, one entry on re-adopt. Returns `active`, `already_adopted`, `resets_on_restart` and `name`. The in-memory registry edit and the separate `pack.json` writer are gone.
- `render.js` (828 -> 815 lines) uses new `chat/adopt_message.js` (21 lines) for the text. `chat.js` stays at 1,004.

**Tests:**

| Suite | Result | Baseline |
|---|---|---|
| New CARD-502 pytest (8 unit + 1 integration) | 9 passed (all red before the fix) | - |
| New Vitest `adopt_status_502` | 7 passed (6 red before) | - |
| Vitest full | 914 passed, 5 failed (CARD-456 known) | 907 / 5 |
| pytest unit | 2059 passed, 11 skipped, 1 failed (CARD-454 linter, known) | 2051 / 11 / 1 |
| pytest integration | 108 passed | 107 |
| Smoke (Playwright) | 55 passed, including TC-37 desktop+phone (red before) | 53 |
| ESLint | 4 errors, 5 warnings (baseline, none new) | 4 / 5 |
| ruff | 9 (CARD-454 baseline, none new) | 9 |

**Repro after the fix** (scratch 8767, `c502_run.ps1 -Wipe`, then `c502_repro.cjs a`, restart without wipe, then `c502_repro.cjs b`):
- Adopt: 200 `{"active":true,"already_adopted":false,"resets_on_restart":false,"name":"Cite Sources"}`. The toast said "Cite Sources is on for autoreiv from your next message."
- `GET /api/agents/autoreiv` then listed 14 skills, including `cite-sources`. `platform_operator_added_skills` = `{"autoreiv": ["cite-sources"], "tutor": ["build-agent-pack"]}`.
- The next message's system prompt listed "cite-sources: Always cite the source".
- After restart, autoreiv still listed `cite-sources` (stored profile and `pack.json`), and the `SKILL.md` folder was still there. Tutor still listed the Agent Studio tick `build-agent-pack`. The message after restart listed "cite-sources: Always cite the source" again.

**Scavenger Pass:**
- The two copies of the 26-field `AgentCustomization` list and the lock code in `update_agent` were merged into `skill_list.py` (`agents.py` -127 lines).
- Removed: the `adopt_skill` in-memory edit, its separate `pack.json` writer, and the unused `readableError` import in `render.js`.
- The remaining dead duplicate save paths are CARD-506.
