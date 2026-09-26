---
id: CARD-505
title: "AutoReiv's system prompt looks operator-edited (trailing newline), so platform prompt updates never land and a Max Turns save locks it"
status: In Progress
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-443
  - CARD-449
  - CARD-450
  - CARD-502
  - CARD-506
  - CARD-508
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-505] AutoReiv's system prompt looks operator-edited (trailing newline), so platform prompt updates never land and a Max Turns save locks it

> **Status**: In Progress (Jacob said **build** 2026-09-25 9:31 PM ET, accepting D1-D8; branch `feat/card-505-prompt-normalize`)
> **Created**: 2026-09-25 (found in the CARD-502 scratch repro)
> **Related**: CARD-443 (platform promotion), CARD-449 (content lock, keep customizations), CARD-450 (Platform defaults badge, Reset), CARD-502 (shared save `persist_agent_profile`), CARD-506 (dead duplicate save paths that also call the lock check), CARD-508 (badge seen empty once while switching agents)
> **Labels**: `type:bug`, `area:agents`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 0. Reproduction (2026-09-25 9:19-9:40 PM ET, qa `2c8650ab`, scratch only)

Scratch server on 127.0.0.1:8767 with data in `scratch/c500_data`. It uses the `scripts/smoke_server.py` guard, and the real AppData was never written. Scripts:
- `scratch/c505_db.py <db> <data_root>`: read-only dump of prompts, locks, baselines and the sync report.
- `scratch/c505_ui.cjs <agent> maxturns|prompt`: saves through the real Agent Studio UI.
- `scratch/c505_badge2.cjs`: reads the Platform defaults section.
- `scratch/c505_update.py`: simulates a platform prompt update. It runs on a copy (`scratch/c505_copy`) with a temp copy of `platform-packs/`, so the checkout is never edited.

Results are in `scratch/c505_d0..d4.json`, `c505_ui_*.json` and `c505_update_log.txt`.

1. **Fresh install (first start).**
   - The seed `platform-packs/autoreiv/pack.json` `system_prompt` is 3,161 characters and ends with a newline.
   - The stored copy in SQLite `custom_agents` is 3,160 characters, because the first import runs the guardrail, which strips it.
   - The shipped baseline hash in `platform_shipped_prompt_hashes` is the hash of the seed *with* the newline: it equals hash(stored + "\n") and not hash(stored).
   - Direct (36), Developer (1,498) and Tutor (3,963) seeds have no trailing or leading whitespace and no CR, so stored equals seed for them.
2. **Second start.** The sync report says autoreiv `promoted_partial`, "skipped fields: system_prompt". The others say `unchanged`. By the CARD-450 badge code, Agent Studio then says "Platform update partly applied. Kept your edited system prompt." even though nobody edited it. This repeats on every restart.
3. **Platform update simulation.** One extra line was added to every seed prompt in a temp copy, then the app was started once.
   - Direct, Developer and Tutor got the new line.
   - **AutoReiv did not** (`promoted_partial`, `system_prompt` skipped), even though it is not locked.
4. **Max-Turns-only save in Agent Studio (real UI).** Max Turns 50 to 51 on AutoReiv, then Save. Studio sent the prompt trimmed (3,160 characters; `forge.js` L459 `.trim()`).
   - **Confirmed:** `custom_agents.user_modified` = 1, and an `agent_overrides` row was created with `user_modified` = 1.
   - The same save on Tutor (control) left `user_modified` = 0 and kept max turns 51.
5. **Restart after that save.**
   - AutoReiv is `skipped_user_modified`, so stock-skill and tool updates are frozen too, not only the prompt.
   - The lock repair `migrate_false_content_locks` reported "kept_locked: prompt diverged from shipped baseline", so the existing repair does not fix it.
   - Agent Studio says "You edited the system prompt, so platform updates will skip this agent until you reset it."
6. **Real edit (control).** One line was appended to Developer's prompt in Studio and saved: it locked. After restart it was still `skipped_user_modified`, the text was kept, and the badge said the prompt was edited. This is correct and must stay.
7. **Jacob's live install (read-only look at `%LOCALAPPDATA%\AutoReiv\database\autoreiv.db`, nothing written).**
   - AutoReiv's stored prompt is 3,161 characters *with* the newline (a promotion wrote it, not the guardrail), is unlocked, and matches the baseline. So it is not falsely locked today.
   - The first Agent Studio Save on AutoReiv (any field) will send the trimmed prompt and lock it, as in step 4.
   - Developer is locked by a **real** edit: "Always follow SOLID and DRY principles." was added (stored 1,538 vs seed 1,498). The repair must keep this one.
   - Tutor has an override with max turns 100 and `user_modified` 0 (fine).
8. Reset to platform defaults (CARD-450) writes the seed prompt back *with* the newline (force-reset path). So after a Reset, the next Studio Save locks AutoReiv again (read from the code; the build's failing test covers it).

## 1. Root causes (file and line, qa `2c8650ab`)

- **Two versions of the same text.**
  - The guardrail strips prompts (`src/domain/agents/guardrails.py` L58), and Agent Studio trims them (`src/web/static/modules/studios/forge.js` L459).
  - Promotion stores and hashes the raw seed text: `prompt_content_hash` (`src/infrastructure/skills/platform_pack_promotion.py` L81-82) hashes the bytes as given, and `_set_shipped_prompt_hash` (L413-418) is called with the raw seed at first import (L581) and after a clean apply (L833).
  - The clean-apply path writes the raw seed into the profile (L749-756).
- **Every comparison is exact.**
  - Clean path: `prompt_at_baseline` (L744-747) and `stored_prompt != new_prompt` (L754, L757) give "skipped fields: system_prompt".
  - Idempotent short-circuit (L695-697) never matches, so AutoReiv runs the full apply on every start.
  - First-boot cutover (L708-715) would mark a pre-hash install `user_modified` for the newline alone.
  - `should_set_content_lock` (L210-242, check at L225-230) is called from the shared Agent Studio save `persist_agent_profile` (`src/application/agent_packs/skill_list.py` L58, lock call L84-92). It is also called from the dead CARD-506 paths: `src/application/settings/settings_service.py` L64-71 and `src/web/routers/settings.py` L849-854.
  - `pack_content_diverged_from_seed` (L245-259), used by `migrate_false_content_locks` (L337-400), makes the same exact check, so a whitespace-only lock is never repaired.
- **The AutoReiv seed has a trailing newline.** The other three platform seeds do not.

## 2. Four Beats

**Beat 1: What Jacob means.** If I never edited AutoReiv's system prompt, platform updates to it reach my AutoReiv. Saving Max Turns or the model in Agent Studio never counts as editing the prompt. Agent Studio tells me the truth about whether I customized it.

**Beat 2: What AutoReiv does now.** AutoReiv's shipped prompt ends with a newline. The copy that gets saved (by the first import, or by any Agent Studio Save) has it stripped. Promotion compares exact bytes, so:
- On a fresh install, every restart reports the prompt as kept, and platform prompt updates never land.
- On any install, one Agent Studio Save of any field (for example Max Turns) locks AutoReiv. That freezes prompt, stock-skill and tool updates.
- The startup lock repair does not undo it.
- Agent Studio then says "You edited the system prompt".

The other platform agents are not affected today, only because their seeds happen to have no outer whitespace.

**Beat 3: What will change.**
- All prompt comparisons (baseline hash, stored vs seed, content-lock check, repair check) use the same normalized text: line endings unified and outer whitespace trimmed.
- Promotion stores the seed prompt already trimmed, so it matches what Agent Studio sends.
- On startup, a one-time repair unlocks any platform agent whose only "edit" is whitespace. It saves a backup first and writes an entry to the lock-migration report. Real edits stay locked and kept.
- The AutoReiv seed loses its trailing newline, and a test keeps every platform seed trimmed.

**Beat 4: What dies.**
- The false "skipped fields: system_prompt" for AutoReiv on every restart.
- False content locks from a scalar-only save.
- The bytes-exact prompt hash.
- The every-restart full re-apply and `pack.json` rewrite for AutoReiv.

## 3. Acceptance criteria (EARS)

- **[REQ-505-001]** THE SYSTEM SHALL compare platform prompts through one `normalize_prompt()` (CRLF and CR to LF, outer whitespace trimmed). This covers the shipped baseline hash, `should_set_content_lock`, `pack_content_diverged_from_seed`, the promotion short-circuit, the cutover check and the clean-apply check.
- **[REQ-505-002]** WHEN a platform pack is installed fresh and the app starts a second time, THE sync report SHALL NOT list `system_prompt` as skipped for a pack whose stored prompt equals its seed after normalizing.
- **[REQ-505-003]** WHEN Jacob saves only scalar fields (Max Turns, model, provider, retention, Show in Chat) for any platform agent in Agent Studio, THE SYSTEM SHALL NOT set `user_modified`.
- **[REQ-505-004]** WHEN the platform ships a new prompt for a pack whose stored prompt is at the previous shipped version (after normalizing), THE next start SHALL apply it. This holds both for installs whose stored prompt kept the newline and for installs where it was stripped.
- **[REQ-505-005]** WHEN the app starts and a platform pack is locked but its stored prompt equals the current seed or matches the previous shipped baseline after normalizing, THE SYSTEM SHALL save a backup and unlock it. THE lock-migration report SHALL say "unlocked: prompt matched the platform version apart from spacing".
- **[REQ-505-006]** WHILE a platform agent's prompt differs from its shipped baseline after normalizing (a real edit), THE SYSTEM SHALL keep it locked, keep the text, and keep the CARD-450 "You edited the system prompt" badge. This is the existing CARD-449 behavior, for example Jacob's Developer line "Always follow SOLID and DRY principles."
- **[REQ-505-007]** WHEN promotion or Reset to platform defaults writes a seed prompt into the profile, THE stored text SHALL be the normalized text. A later Studio Save of an unchanged prompt SHALL NOT lock.
- **[REQ-505-008]** Every `platform-packs/*/pack.json` `system_prompt` SHALL equal its normalized form (seed hygiene test).

## 4. Decisions (recommendations; Jacob to confirm or change)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | How to normalize | (a) Trim outer whitespace and unify line endings; (b) also collapse inner whitespace; (c) compare only after the guardrail's `.strip()` | **(a).** It matches what the guardrail and Studio already do. Inner spacing can be a real edit (Markdown lists), so leave it |
| D2 | Where to normalize | Only in the lock check / in every comparison and in the stored text | **Everywhere, through one function in `platform_pack_promotion.py`**. `prompt_content_hash` hashes the normalized text, and promotion and Reset store the normalized seed. One rule, no second copy |
| D3 | Old baseline hashes (raw seed bytes) already saved on every install | (a) Re-hash on startup when the baseline equals the raw hash of the current seed; (b) also accept a legacy match: hash(stored), hash(stored + "\n") or hash(stored + "\r\n") equals the old baseline, meaning "stored is the old stock text"; (c) drop all baselines and re-seed | **(a) + (b)**, one time, recorded in a settings key `platform_prompt_baseline_normalized`. (c) would lose track of real edits made against an older seed |
| D4 | Repairing installs already falsely locked | (a) Extend `migrate_false_content_locks` with the normalized and legacy match, backup first; (b) leave them for Reset to platform defaults | **(a).** It already runs at every start and writes a report. A backup (reason `card505_whitespace_unlock`) costs nothing, and real edits (Developer) fail the match and stay locked |
| D5 | May a settings-only save ever set the content lock | Yes if the prompt field differs by whitespace / never | **Never.** Only a prompt that differs from the shipped baseline after normalizing locks. Scalars and skill ticks never lock (CARD-449, CARD-502) |
| D6 | Also fix the AutoReiv seed | Code only / code and seed | **Both.** Strip the trailing newline in `platform-packs/autoreiv/pack.json`, plus a hygiene test over all seeds. The seed hash changes once, so one normal promotion runs on the next start |
| D7 | What the operator sees | New notice / existing screens only | **Existing screens only.** AutoReiv's Platform defaults shows "This agent has the latest platform update" again. A repaired install shows `unlocked` in the sync status lock-migration report and gets a backup in the Backups list ("before spacing fix"). A CHANGELOG line explains it. No toast |
| D8 | CARD-506 dead paths that also call `should_set_content_lock` | Fix here / leave to CARD-506 | **Covered automatically.** Normalizing inside `should_set_content_lock` covers them. Deleting them stays CARD-506 |

## 5. Failing-tests-first plan (write, run, see red, then fix)

**pytest unit** (new `tests/unit/agent_packs/test_card505_prompt_normalize.py`, real `SQLiteStateStore` and per-test data folder; the "restart" is a second `create_app`, as in CARD-502):
1. `prompt_content_hash("abc\n") == prompt_content_hash("abc") == prompt_content_hash("abc\r\n")` (red).
2. Fresh boot twice: autoreiv sync status is not `promoted_partial` and `skipped_fields` has no `system_prompt` (red).
3. `PUT /api/agents/autoreiv` with the GET body, max_turns + 1 and the prompt trimmed (as Studio sends): `store.get_agent_profile('autoreiv').user_modified` is false and there is no locked override (red).
4. Platform update: `promote_one_platform_pack(checkout_root=tmp)` with a temp seed whose prompt gained a line; autoreiv's stored prompt contains it. Case A: stored stripped (fresh install). Case B: stored with newline (Jacob's install) (A red, B green).
5. Legacy false lock: stored stripped, `user_modified` true, old raw-seed baseline. Promotion unlocks it, writes a backup and records the migration action; the next update applies (red).
6. Real edit control: a prompt with one extra line stays locked and kept, and the badge-feeding sync entry is `skipped_user_modified` (green, must stay green).
7. Reset to platform defaults, then a scalar-only save: no lock (red).
8. Seed hygiene: every `platform-packs/*/pack.json` prompt equals its normalized form (red until the AutoReiv seed is fixed).

**pytest integration** (new `tests/integration/test_card505_prompt_restart.py`): app start, second start, Max Turns PUT, third start. `/api/platform-packs/sync-status` autoreiv is not `skipped_user_modified` and not `promoted_partial` (red).

**Vitest / smoke:** no UI change planned (D7), so no new Vitest or smoke case. The existing CARD-450 Vitest and smoke cover the badge wording. Full suites still run at preflight.

Then full Vitest, smoke, pytest unit and integration, ESLint, ruff (known CARD-454/456 failures only), and rerun `scratch/c505_*` steps 1-6.

## 6. Build order

1. `normalize_prompt()` and a normalized `prompt_content_hash`; use it at every comparison site in section 1.
2. Store the normalized seed in promotion and force-reset (REQ-505-007).
3. One-time baseline re-hash plus legacy match (D3); extend `migrate_false_content_locks` with backup and report (D4).
4. Strip the AutoReiv seed newline and add the hygiene test (D6).
5. CHANGELOG `[Unreleased] ### Fixed`, Scavenger Pass, preflight, scratch repro rerun, In Review.

## 7. Runbook (Jarvis, after build)

Desktop (http://127.0.0.1:8000, Ctrl+F5):
1. Open Agent Studio and pick AutoReiv. Platform defaults says "This agent has the latest platform update."
2. Open Agent Preferences, change Max Turns (for example 50 to 51) and click Save.
3. Restart serve: `powershell -ExecutionPolicy Bypass -File scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000` (or ask the agent to do it). Press Ctrl+F5.
4. Agent Studio > AutoReiv: it still says "This agent has the latest platform update" (not "You edited the system prompt"), and Max Turns shows the new value.
5. Agent Studio > Developer: it still says "You edited the system prompt...", and the line "Always follow SOLID and DRY principles." is still in the prompt.
6. Put AutoReiv's Max Turns back if you like and Save. Nothing else changes.

Phone (http://192.168.1.99:8000):
1. Open Agent Studio and pick AutoReiv. The Platform defaults section says "This agent has the latest platform update."
2. Change Max Turns and tap Save. After the desktop restart (step 3 above), reload: still up to date, with the new Max Turns.

## 8. Out of scope

- Deleting the dead save paths: **CARD-506**.
- Platform defaults badge seen empty once while a script switched agents quickly: **CARD-508**.
- User (non-platform) packs: at startup their `pack.json` prompt overwrites the stored prompt when they differ (`src/infrastructure/skills/platform_packs.py` L741-745). Studio keeps them in sync, so no fix is planned here.
