---
id: CARD-520
title: "Rename the Teach/Observability remedy factory_escalation to tool_escalation, and replace Observability's always-failing Apply with Ask Developer"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-497
  - ADR-0060
  - CARD-472
  - CARD-354
labels:
  - type:product
  - area:observability
  - area:skills
  - P2
---

# [CARD-520] `tool_escalation`: one name for "this needs a tool", and a working Ask Developer in Observability

> **Status**: Ready (split from CARD-497 on `continue`, 2026-09-26 ~9:50 AM ET, qa `51b6402b`; carries CARD-497's old decision D3 plus a new finding). Suggested right after CARD-497, because it removes the last operator-visible "Factory" words and fixes an HTTP 500. Needs `continue` refinement (EARS, tests, runbook) before `build`.
> **Related**: CARD-497 (D3, D14), ADR-0060 section 4.1 ("Teach factory_escalation remedy"), CARD-472 (Teach Ask Developer), CARD-354 (friction recommendations)
> **Labels**: `type:product`, `area:observability`, `area:skills`, `P2`

## Problem

1. **Old name.** The remedy for "the agent needs a tool, not a runbook" is still called `factory_escalation`, although the Factory is retired (ADR-0060):
   - distill prompt and output: `distillation_service.py` L244, L298, L314, L355, L397;
   - Teach card attribute `data-factory-escalation`: `chat/render.js` L267, `chat/teach_modal.js` L13;
   - Observability remedy kind: `domain/observability/models.py` L95, `tool_skill_resolver.py` L215;
   - Observability badge "Factory Escalation": `observability.js` L835-837.
   - The recommendation text says "Escalate <tool> to Factory Studio" (`tool_skill_resolver.py` L211-214).
2. **Apply always fails (new finding, CARD-497 sweep).** An Observability friction card of that kind shows the same **Apply** button as a runbook patch. `ToolSkillResolver.apply_recommendation` returns `False` for anything but `runbook_patch` (L248), and `POST /api/observability/friction/recommendations/{rec_id}/apply` turns that into **HTTP 500 "Failed to apply recommendation to '<skill path>'"** (`routers/observability.py` L374, L419-424), even though nothing went wrong. The operator gets an error for the one action the card offers. Teach already has the right action for this case: **Ask Developer** (CARD-472).

Stored data carries the old name: distill results saved as `SKILL_PROPOSAL` chat messages, and friction recommendations in the proposals table and `skills/_friction_recommendations.json`.

## Change (to refine)

- **Writers** use `tool_escalation` (distill output key and prompt, remedy kind, badge "Needs a tool"). The text says "Ask Developer to add pagination/filter parameters to <tool> ..." instead of Factory Studio.
- **Readers** accept both names: the render and teach modal (`data-tool-escalation`, falling back to the old attribute and key), the Observability badge, and `RunbookRecommendation`.
- **Observability:** a `tool_escalation` card offers **Ask Developer**, built from the recommendation the same way Teach does (`buildDeveloperToolDraft`, `POST /api/tools_studio/authoring/talk`), and **Dismiss**, but no Apply. The Apply route answers 409 with a clear message, not 500, for a non-patch remedy.
- **Tests:**
  - update `test_tool_skill_resolver.py` L98-114, `test_card354_developer_simulations.py` L253, `test_skill_distillation_service.py` L162-182, `test_skill_proposal_persistence.py` L152, Vitest `card_496_retire_factory_ui` L232, `chat_workbench_teach_wiring_472` L226 and `teach_distill_contract_500` L182, and smoke TC-32 / TC-34 (L1038, L1136);
  - add old-name reader tests.

## Done when

New distills and recommendations say `tool_escalation`; old stored ones still render and still offer Ask Developer; the Observability card for a tool gap never shows an Apply that fails; no operator-visible text names the Factory.
