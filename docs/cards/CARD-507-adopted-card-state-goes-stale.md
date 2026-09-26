---
id: CARD-507
title: "Reloaded Teach card still says \"On for <agent>\" after the skill is removed"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-502
  - CARD-358
  - CARD-449
labels:
  - type:bug
  - area:skills
  - area:chat
  - P3
---

# [CARD-507] Reloaded Teach card still says "On for <agent>" after the skill is removed

> **Status**: Ready (follow-up filed while building CARD-502, 2026-09-25 8:15 PM ET)
> **Related**: CARD-502 (Adopt persists), CARD-358 (proposal state saved in chat history), CARD-449 (Keep my agent customizations)
> **Labels**: `type:bug`, `area:skills`, `area:chat`, `P3`

## Problem

After Adopt, the chat message holding the proposal is saved with `adoption_state: "adopted"` (CARD-358). A reloaded card always shows "On for autoreiv." and no Adopt button. That text is not checked against the agent. It goes stale when:

1. "Keep my agent customizations" is off and the app restarts. CARD-502 then drops the adopted skill on purpose (D4).
2. The operator unticks the skill in Agent Studio.

In both cases the card still says "On for autoreiv." and gives no way to adopt it again. The only route back is a new Teach that produces the same skill id, or ticking it in Agent Studio (the `SKILL.md` stays on disk).

## Direction (to refine)

- When a reloaded card renders, check the target agent's `allowed_skill`, or have the history endpoint mark the proposal. Show "Not on for autoreiv any more" with an **Adopt again** button when the skill is missing.
- Keep `render.js` from growing (CARD-456). The helper lives in `chat/adopt_message.js`.

## Out of scope

- Migrating orphaned `SKILL.md` folders from before CARD-502 (CARD-502 D9: leave them).
