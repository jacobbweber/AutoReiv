---
id: CARD-574
title: "Cleanup: honesty check rename, legacy escalation migration, Skill Studio authoring to Toolsmith, Settings reply limits"
type: chore
status: In Progress
priority: P2
milestone: M22
needs_decision: none
proof: "Settings > Models shows Reply limits fields that load the resolved limits (16384 / 600) and save through PUT /api/settings/reply-limits; POST /api/skill_studio/authoring/jobs opens a Toolsmith job (agent_id toolsmith); the startup tool_escalation migration is gone; the full-preflight honesty stage finds its script. Checks: test_card_520_tool_escalation.py, test_oc420_skill_studio_developer_authoring.py, vitest card_574_reply_limits_settings.test.js, card_420_skill_authoring.test.js, card_520_tool_escalation.test.js."
branch: feat/card-574-cleanup
created: 2026-09-29
related: [CARD-570, CARD-571, CARD-567, CARD-520, CARD-420, CARD-261, CARD-509]
---

# CARD-574 Cleanup: honesty check rename, legacy escalation migration, Skill Studio authoring to Toolsmith, Settings reply limits

> **Status**: In Progress

## Why
Leftovers after the pack removal (CARD-570) and the Toolsmith split (CARD-571), plus two findings.

## Scope
a. Rename `.agents/skills/preflight/scripts/honesty_smoke_pack_261.py` to `honesty_smoke_skill_261.py`. `preflight.py`
   and the preflight skill already named the new file, so the full-preflight honesty stage could not find its script;
   the rename fixes it. Docstring paths, fixture path (`notes/honesty-smoke-261-fixtures.json`) and "pack" wording fixed.
b. Remove the one-off startup migration `tool_escalation_migration.py` (factory_escalation -> tool_escalation) and its
   `app.py` block, and the legacy `factory_escalation` readers (domain model validator, observability router,
   distillation fallback, `tool_escalation.js` legacy key/attribute).
c. card509: `tests/unit/agent_packs/test_card509_unpilled_skills.py` (the 2 failing slow tests) was already deleted by
   CARD-570, so there is nothing to fix; the findings line is removed. vitest `card_509_unpilled_skills.test.js` stays.
d. Skill Studio authoring jobs go to Toolsmith (`TOOLSMITH_AGENT_ID = "toolsmith"`) instead of Developer, in
   `developer_authoring.py`, the router docstrings and `studios/skill_authoring.js`. Module and template names kept
   (same pattern as CARD-571 `developer_mediation.py`).
e. Settings > Models: **Reply limits** card (Max tokens per reply, Max seconds per reply, Save) on
   `GET/PUT /api/settings/reply-limits` (CARD-567). Empty or 0 clears back to the env/default. New module
   `studios/settings_reply_limits.js`, wired from `settings.js` `loadSettings()`.
f. Small "pack" leftovers: `steering/structure.md` (missing legacy_pack_tools.py), lifecycle-audit skill (agent files,
   app.py lifespan), boundary-audit skill and `boundary_check.py` comment.

## Done when
- Checks green (ruff, not-slow pytest, vitest, fast preflight --base qa); Settings fields load and save live on a
  throwaway serve; a Skill Studio authoring job is opened for toolsmith.

## Log
- 2026-09-29: Jacob asked for this cleanup (a-e). Building.
