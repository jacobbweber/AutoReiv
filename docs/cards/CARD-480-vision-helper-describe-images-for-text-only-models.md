---
id: CARD-480
title: "Vision helper: describe images with a configured vision model when the chat model is text-only"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-475
labels:
  - type:feature
  - area:chat
  - area:gateway
  - P3
---

# [CARD-480] Vision helper: describe images with a configured vision model when the chat model is text-only

> **Status**: Ready (depends on CARD-475)
> **Created**: 2026-09-25
> **Observed during**: CARD-475 planning, decision D1(c).
> **Related**: CARD-475
> **Labels**: `type:feature`, `area:chat`, `area:gateway`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means
Keep the fast text model for chat, but still let it "see" a screenshot by asking a vision model for a description first.

### Beat 2: What AutoReiv does now
- `purpose_matrix.purposes` supports a `vision` slot (`ModelPurpose.VISION`, `src/domain/settings/models.py` L17), but nothing uses it, and the live value is empty.
- Vision-capable models are available on Spark: `gemma-4-26b-a4b` and `nemotron-3-nano-omni` on the vLLM gateway, and `gemma4:26b`, `qwen3.6:35b` and `qwen3.8:*` on Ollama. Only one gateway model is loaded at a time, so using one means a GPU swap and extra latency.

### Beat 3: What will change (decision needed)
- When `purposes.vision` is set and the chat model is text-only, call the vision model once per image. It gets a short prompt ("describe this image for another assistant; include any text you can read").
- Insert the description as text into the current user turn, labelled "(image described by <model>)". Show a notice with the extra time.
- Off by default.

Tests: a fake vision provider gets the image once; the text model gets only the description; failures fall back to the CARD-475 notice.

### Beat 4: What dies
"Switch models just to read a screenshot".

## 2. Acceptance criteria (EARS)
- **[REQ-480-001]** WHILE a vision purpose model is configured and the chat model is text-only, WHEN an image is attached, THE SYSTEM SHALL send the image to the vision model and pass its description to the chat model.
- **[REQ-480-002]** IF the vision helper fails or times out, THEN THE SYSTEM SHALL fall back to the CARD-475 notice.
