---
id: CARD-500
title: "Teach: distill request and proposal card read the wrong fields (guidance lost, /learn 422, default slip text)"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-472
  - CARD-352
  - CARD-358
labels:
  - type:bug
  - area:chat
  - area:skills
  - P2
---

# [CARD-500] Teach: distill request and proposal card read the wrong fields

> **Status**: Ready
> **Created**: 2026-09-25 (found while building CARD-472)
> **Related**: CARD-472 (moved the Teach modal to `chat/teach_modal.js`), CARD-352, CARD-358
> **Labels**: `type:bug`, `area:chat`, `area:skills`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** What I type in Teach reaches the distiller, `/learn` works, and the proposal card shows what actually went wrong and the fix.

**Beat 2: What AutoReiv does now.**
- `chat/teach_modal.js` posts `/api/skills/distill` with `operator_guidance` and `target_agent_id`. `DistillSkillRequest` (`src/web/routers/skills.py` L262) only has `session_id`, `message_id`, `guidance`. Pydantic drops the extras, so **Jacob's guidance never reaches the distiller** and the target agent is ignored.
- `/learn <text>` in the composer (`chat/composer.js` L372) opens Teach with no `messageId`. `message_id` is required (`min_length=1`), so Distill returns 422 and the toast shows `Distillation failed: [object Object]` (the detail is a list).
- The distill response nests the text under `plain_summary.{observed_slip, remedy}` (`distillation_service.py` L293/L314). `renderSkillProposalCard` reads `proposal.observed_slip` / `proposal.remedy`, so every card shows the default "Operational friction detected during turn." text.

**Beat 3: What will change.**
- Send `guidance` (keep `target_agent_id` only if the router accepts it; otherwise add it as an optional field and use it for the proposal).
- `/learn` uses the latest assistant message id in the session, or the button is disabled with a plain reason when there is none.
- Error toast prints the readable detail (string, `detail.message`, or the first validation message).
- Proposal card reads `proposal.plain_summary.observed_slip/remedy` with the flat fields as fallback.

**Beat 4: What dies.** Silent loss of guidance; the `[object Object]` toast; the placeholder slip text.

## 2. Acceptance criteria (EARS)

- **[REQ-500-001]** WHEN Jacob submits Teach with guidance, THE SYSTEM SHALL send it in the field the router reads, and the distiller SHALL receive it.
- **[REQ-500-002]** WHEN Jacob types `/learn <text>` in a chat that has an assistant reply, THE SYSTEM SHALL distill against the latest assistant message. IF there is none, THEN THE SYSTEM SHALL say so in plain words and not call Distill.
- **[REQ-500-003]** WHEN Distill fails, THE SYSTEM SHALL show a readable reason, never `[object Object]`.
- **[REQ-500-004]** THE proposal card SHALL show the distiller's observed slip and remedy.

## 3. Tests (write first, see red)

- Vitest (`teach_modal.js`): request body has `guidance`; `/learn` path uses the latest assistant id; array `detail` yields readable text.
- Vitest (`render.js`): card shows `plain_summary` text.
- pytest router: `guidance` reaches `DistillationService`.
- Smoke: Teach from a reply shows a card with the fixture slip text (desktop + phone).

## 4. Runbook

1. Open Chat, send a message, click Teach on the reply, type "always cite the source", Distill. The card's "what went wrong" and "fix" lines are specific, not the generic sentence.
2. Type `/learn be shorter` in the composer and send. Teach opens and Distill works (or a plain message says there is no reply yet).
