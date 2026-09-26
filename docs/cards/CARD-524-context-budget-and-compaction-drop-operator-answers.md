---
id: CARD-524
title: "Multi-step chats lose the operator's latest answer: default context resolves to 8192 and compaction keeps only the last 8 messages"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-497
  - CARD-523
  - CARD-162
labels:
  - type:bug
  - area:kernel
  - P2
---

# [CARD-524] Context budget and compaction drop the operator's answers mid-task

> **Status**: Ready (found in the CARD-497 live retest on serve, 2026-09-26 ~11:22 AM ET). P2: it blocks any multi-turn, tool-heavy flow (AutoReiv capability intake re-asked the same questions three times).
> **Related**: CARD-497 (intake live test), CARD-523 (tool-argument robustness), CARD-162 (context limit cascade)
> **Labels**: `type:bug`, `area:kernel`, `P2`

## Evidence

The session was deleted after the CARD-497 retest (DB backup before cleanup: `scratch/autoreiv_pre_c497_cleanup.db` on Jarvis).

Session `86cc2ff2-2ea8-4629-8dc9-b15054c80792` (AutoReiv, "Teach AutoReiv to read IPMI sensor temperatures", model `nemotron-3.5-lightning` on vLLM):

- Turn 1 went well (`skill_view(pack_id="agent-authoring")`, `lookup_agents`, `inspect_agent_pack`, four questions).
- Turn 2 (11:22 AM ET) answered all four. AutoReiv made ~20 tool calls and then asked the **same four questions** again; turn 3 (11:23 AM ET) said "I answered those in my last message" and it asked a third time.
- `telemetry_spans.metadata_json.token_breakdown.compacted_history` per LLM call falls from 4331 to 830, 374 and ~450 tokens inside one turn, while the whole prompt stays under ~10.4k.
- `resolve_agent_context_limit` returns **8192** for AutoReiv on Jacob's install: `context_window` is null, `purpose_matrix.default_context_window` and `model_context_windows` are empty, and the default model is `nemotron-3.5-lightning` (vLLM does not report `max_model_len`, so there is no architecture default).
- `ContextCompactor.compact(max_tokens=int(8192*0.75), keep_last_n_turns=4)` keeps the system prompt, the **first** user message (`preserve_root_intent`), a summary of only the first 8 intermediate messages (150 chars each), and the last **8 messages**. In a tool-heavy turn those 8 are tool calls and results, so the operator's newest answer and the loaded runbook drop out, and the model only sees the root request again.

## Change (to refine)

1. Default context: pick a sane platform default (for example 32768) when nothing is configured, or read `max_model_len` / a per-model table for local vLLM models; show the resolved window in Settings Studio.
2. Compaction: always keep the **latest user message** and the most recent `skill_view` body, count "turns" as user turns (not message pairs), and summarize the most recent intermediate messages rather than the oldest 8.
3. Tests: a tool-heavy second turn keeps the second user message and the runbook in the compacted payload.

## Workaround for Jacob

Settings Studio: set the default context window (or a per-model window for `nemotron-3.5-lightning`) to the model's real window, or set AutoReiv's context window in Agent Studio.

## Done when

The IPMI intake on serve reaches "show the brief" without re-asking answered questions.
