---
id: CARD-506
title: "Remove the unused duplicate agent-save paths (POST /api/settings/agents/{id}, SettingsService.save_agent_customization)"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-449
  - CARD-502
labels:
  - type:chore
  - area:agents
  - P3
---

# [CARD-506] Remove the unused duplicate agent-save paths

> **Status**: Ready
> **Created**: 2026-09-25 (found while tracing CARD-502)
> **Related**: CARD-449 (content lock rules), CARD-502 (shared skill-list save)
> **Labels**: `type:chore`, `area:agents`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** There is one way an agent's settings get saved, so a rule fixed in one place is fixed everywhere.

**Beat 2: What AutoReiv does now.** The CARD-449 lock rule (`should_set_content_lock` then `save_agent_override` then `mark_agent_user_modified`) is copied in four places: `PUT /api/agents/{id}` twice (`src/web/routers/agents.py` L468-494 for platform agents, L527-555 for custom agents), `POST /api/settings/agents/{id}` (`src/web/routers/settings.py` L844-870), and `SettingsService.save_agent_customization` (`src/application/settings/settings_service.py` L61-88). Agent Studio uses only `PUT /api/agents/{id}` (`src/web/static/modules/studios/forge.js` L511). Nothing in `src/web/static` calls `POST /api/settings/agents/{id}`; `save_agent_customization` is called only by `tests/unit/settings/test_agent_settings_manager.py` L107. `SettingsService.get_effective_agent_profile` (L94-123), a second, partial copy of the override overlay in `BuiltinAgentRegistry.get_agent`, is also called only by that test (L95, L110).

**Beat 3: What will change.** Delete `POST /api/settings/agents/{id}`, `SettingsService.save_agent_customization` and `get_effective_agent_profile`, move their tests to the shared save introduced by CARD-502, and fold the two lock blocks in `PUT /api/agents/{id}` into one helper.

**Beat 4: What dies.** One unused route, one unused service method, and two copy-pasted lock blocks.

## 2. Acceptance criteria (EARS)

- **[REQ-506-001]** `POST /api/settings/agents/{id}` SHALL return 404 (route removed) and no file in `src/web/static` SHALL reference it.
- **[REQ-506-002]** THE CARD-449 lock rule SHALL exist in one function, called by every agent save path.
- **[REQ-506-003]** Existing CARD-449 / CARD-450 tests SHALL pass unchanged in behavior.

## 3. Decisions (recommendations)

| # | Question | Recommendation |
|---|----------|----------------|
| D1 | Order with CARD-502 | **After CARD-502**, which introduces the shared skill-list save this card reuses |
| D2 | `get_effective_agent_profile` | **Remove** (test-only caller); the test moves to `registry.get_agent` |

## 4. Failing-tests-first plan

- pytest: `POST /api/settings/agents/autoreiv` returns 404 (red today); a grep-style guard that `should_set_content_lock(` is called from one module only (red today); existing CARD-449 lock tests stay green.

## 5. Runbook

1. Agent Studio: change a tool tick and Max Turns on AutoReiv, Save, reload: both kept.
2. Change only Max Turns on Tutor, Save, restart serve: Tutor shows no customized badge.
