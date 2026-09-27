---
id: CARD-538
title: "Developer reply can end with \"Reply failed: The model returned an empty reply\" right after registering a tool"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-532
  - CARD-520
labels:
  - type:bug
  - area:chat
  - P3
---

# [CARD-538] Empty model reply after register_native_tool shows Reply failed

> **Status**: Ready (found by the CARD-532 live QA runner's error-banner watcher, 2026-09-26 ~6:45 PM ET). P3: the tool was registered and granted; only the closing reply failed. Seen once in four CARD-520 runs.
> **Related**: CARD-532 (journey `card-520-teach-needs-tool`), CARD-520
> **Labels**: `type:bug`, `area:chat`, `P3`

## Evidence

- Run `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-532-520b` (throwaway env, real vLLM `nemotron-3.5-lightning`): `get_weather` granted to autoreiv, then the Developer chat showed `.chat-stream-error` "Reply failed: The model returned an empty reply." Screenshot `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-532-520b\card-520-teach-needs-tool-desktop-04-the-developer-builds-the-tool-and-grants-it-to-a.png`.

## Change (decide at refinement, technical)

When the model returns an empty final message after a successful tool call, retry once or close the turn with a short summary of the tool results instead of a red failure; keep the red error for a real failure.

## Done when

An empty final model message after successful tool calls no longer shows "Reply failed"; a unit test covers it; the CARD-520 journey shows no error banner in step 4.
