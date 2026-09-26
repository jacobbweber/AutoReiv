---
id: CARD-503
title: "Teach distill gives the model 4.5 s, then silently uses a canned fallback"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-500
  - CARD-352
labels:
  - type:bug
  - area:skills
  - P2
---

# [CARD-503] Teach distill gives the model 4.5 s, then silently uses a canned fallback

> **Status**: Ready
> **Created**: 2026-09-25 (found while refining CARD-500)
> **Related**: CARD-500, CARD-352
> **Labels**: `type:bug`, `area:skills`, `P2`
> **Measured (CARD-520 live test, 2026-09-26 ~2:05 PM ET):** on Jarvis, `nemotron-3.5-lightning` over vLLM took **6.4 s** for the weather Teach and returned **empty content** (`finish_reason: length`, 800/800 completion tokens spent on reasoning). Raising the timeout alone will not fix it; the 800-token `max_tokens` (or reasoning control) must change too. Replay script: `scratch\c520_distill_probe.py` (runs on a DB copy). CARD-520 REQ-520-015 now makes the fallback return Needs a tool when the guidance says a tool is missing.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** When I teach an agent, a real model writes the lesson, and if it could not, the card tells me.

**Beat 2: What AutoReiv does now.** `SkillDistillationService._run_llm_distillation` waits `asyncio.wait_for(..., timeout=4.5)` for an 800-token JSON answer (`src/application/skills/distillation_service.py` L263-273). On timeout or any error it logs a warning and returns `None`, and `distill_turn` builds a canned runbook from the guidance or the user prompt (L50-54, L359-399). The response and the card look the same either way. Not measured on Jarvis with a real model (the CARD-500 repro used an instant fake), but a local model writing about 800 tokens of JSON will often take longer than 4.5 s, so the canned path is likely the common one.

**Beat 3: What will change.** Distill uses the same model timeout as a chat turn (settings value, not a hard-coded 4.5 s), shows "Distilling..." until then, and returns `source: "model"` or `source: "fallback"` with a plain reason. The card shows "Written without the model: <reason>" for the fallback.

**Beat 4: What dies.** A lesson that looks model-written but is a template.

## 2. Acceptance criteria (EARS)

- **[REQ-503-001]** THE distill model call SHALL use the configured model timeout (D1), not a hard-coded 4.5 s.
- **[REQ-503-002]** WHEN the model call fails or times out, THE response SHALL include `source: "fallback"` and a plain `fallback_reason`, and THE card SHALL show it.
- **[REQ-503-003]** WHEN the model answers with valid JSON, THE response SHALL include `source: "model"`.

## 3. Decisions (recommendations)

| # | Question | Recommendation |
|---|----------|----------------|
| D1 | Timeout value | **Reuse the chat turn's model timeout if one is configured; otherwise a new setting, default 60 s** (check at build time which exists) |
| D2 | Keep the canned fallback at all | **Keep it, labelled**, so Teach still does something when the model is down |

## 4. Failing-tests-first plan

- pytest: slow fake gateway (5 s) within the configured timeout produces `source: "model"` (red today: fallback after 4.5 s); failing gateway gives `source: "fallback"` with a reason (red today: no field).
- Vitest: card shows the fallback label.
- Smoke desktop + phone: routed fallback fixture shows the label.

## 5. Runbook

1. With the normal model, Teach from a reply: the card has no "Written without the model" label.
2. Stop the model provider (or pick an unreachable one), Teach again: the card shows the label and the reason.
