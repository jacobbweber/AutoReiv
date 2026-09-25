---
id: CARD-502
title: "Adopted Teach skill is not used on the next message and is dropped on restart"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-500
  - CARD-352
  - CARD-358
  - CARD-443
  - CARD-449
labels:
  - type:bug
  - area:skills
  - area:agents
  - P1
---

# [CARD-502] Adopted Teach skill is not used on the next message and is dropped on restart

> **Status**: Ready
> **Created**: 2026-09-25 (found while refining CARD-500)
> **Related**: CARD-500 (Teach request and card), CARD-352 / CARD-358 (Teach, proposal persistence), CARD-443 (platform pack promotion), CARD-449 (keep customizations, user_modified)
> **Labels**: `type:bug`, `area:skills`, `area:agents`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** When I click Adopt and it says "Active for your next message", the agent uses that runbook from the next message on, and still has it after a restart.

**Beat 2: What AutoReiv does now.** Reproduced on the CARD-500 scratch server (`scratch/c500_ui.cjs`, `scratch/c500_ui2.cjs`, `scratch/c500_gateway.log`):
- Adopt returns 200 and writes `packs/<agent>/skills/<id>/SKILL.md` and adds the id to `packs/<agent>/pack.json` in the **user-data** folder (checkout untouched). Good.
- `GET /api/agents/autoreiv` `allowed_skill` does **not** include the new id, and the skill index in the **next** chat turn's system prompt (built by `render_skill_index`, `src/application/kernel/agent_kernel.py` L537-541, from the agent's `allowed_skill`) does **not** list it. The toast "Active for your next message" is false.
- After a restart with data kept, `pack.json` no longer lists the id: startup promotion refreshes `pack.json` and the stored allowlist from the platform seed for packs that are not `user_modified` (`src/infrastructure/skills/platform_pack_promotion.py` L9-14). The `SKILL.md` folder stays on disk, orphaned.
- Cause: `SkillDistillationService.adopt_skill` (`src/application/skills/distillation_service.py` L76-154) only edits `pack.json` and mutates the in-memory registry profile (L139-146). It never saves the allowlist to the agent store and never marks the agent `user_modified`, unlike ticking a skill in Agent Studio (`src/application/settings/settings_service.py` L74-119).

**Beat 3: What will change.** Adopt saves the new skill through the same path as ticking a runbook in Agent Studio (stored allowlist plus `user_modified`, CARD-449), refreshes the live agent, and keeps writing the `SKILL.md` into user-data packs. The success message only claims "active" after the agent really lists it. If "Keep my agent customizations" is off, the message warns that a restart will reset it.

**Beat 4: What dies.** The false "Active for your next message", and adopted runbooks silently disappearing on restart.

## 2. Acceptance criteria (EARS)

- **[REQ-502-001]** WHEN Jacob adopts a proposal for agent A, THE SYSTEM SHALL add the skill id to A's stored `allowed_skill`, mark A `user_modified`, and write `SKILL.md` under the user-data `packs/A/skills/<id>/`, never under the checkout.
- **[REQ-502-002]** WHEN the next message is sent to A, THE skill index in A's system prompt SHALL list the adopted skill.
- **[REQ-502-003]** WHEN the app restarts with "Keep my agent customizations" on, A SHALL still list the adopted skill (stored allowlist and `pack.json`).
- **[REQ-502-004]** WHILE "Keep my agent customizations" is off, THE Adopt success message SHALL say the skill resets on the next restart.
- **[REQ-502-005]** Adopt SHALL be idempotent (adopting the same id twice leaves one entry) and SHALL reject ids with path characters (existing `SAFE_ID_RE`).

## 3. Decisions (recommendations)

| # | Question | Recommendation |
|---|----------|----------------|
| D1 | Which save path | **Reuse the Agent Studio skill-tick save** (settings service), not a second writer |
| D2 | Mark `user_modified` | **Yes** (that is what protects it from promotion; CARD-449 backups still apply) |
| D3 | Custom (non-platform) agents | Same path; promotion never touches them, but the stored allowlist must still be updated |
| D4 | Existing orphaned SKILL.md folders from earlier adopts | **Leave them**; Agent Studio can tick them. No migration |

## 4. Failing-tests-first plan

- pytest service/router: after Adopt, the store's profile for A lists the id and `user_modified` is true (red today); the kernel's system prompt for A's next turn lists the skill (red today); running `promote_one_platform_pack` for A keeps the id (red today); idempotent; path characters rejected.
- pytest integration: adopt, rebuild the app on the same scratch data folder, `GET /api/agents/A` lists the id (red today).
- Vitest: success text uses the server's answer (`active: true` / `resets_on_restart: true`).
- Smoke desktop + phone: Adopt shows the correct message (routed fixture).

## 5. Runbook

1. Teach from a reply and Adopt. The message says the skill is active.
2. Agent Studio for that agent lists the runbook as ticked.
3. Ask something that matches the runbook: the reply follows it (or the Thinking drawer shows it opened the runbook with `skill_view`).
4. Restart serve (`scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`) and check Agent Studio again: still ticked.
