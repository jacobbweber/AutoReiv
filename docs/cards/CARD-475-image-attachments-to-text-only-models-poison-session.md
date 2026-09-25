---
id: CARD-475
title: "Image attachments are sent to text-only models; one image breaks the whole chat session"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-469
  - CARD-143
  - CARD-235
labels:
  - type:bug
  - area:chat
  - area:gateway
  - area:attachments
  - P1
---

# [CARD-475] Image attachments are sent to text-only models; one image breaks the whole chat session

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 live test on 2026-09-24 at 11:02 PM and 11:05 PM ET. Jacob attached a phone screenshot (812 KB PNG) in Chat on the phone and got no reply. After that, even a plain "Hi" in the same session got no reply.
> **Related**: CARD-469, CARD-143, CARD-235
> **Labels**: `type:bug`, `area:chat`, `area:gateway`, `area:attachments`, `P1`

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

Attaching a picture should never break the chat. If the model can't see images, AutoReiv should say so and still answer the text, and the rest of the conversation should keep working.

### Beat 2: What AutoReiv does now

1. `src/web/routers/chat.py` `format_prompt_with_attachments` (L130-187) writes each image into the user message as markdown plus `Local Path: \`...\``.
2. `src/infrastructure/gateway/openai_adapter.py` `_format_messages` (L139-181) scans **every user message in the history** for `Local Path:`. It base64-encodes any png/jpg/webp/gif it finds (up to 10 MB) and sends it as an `image_url` part. It does not check whether the model supports images.
3. Jacob's default provider is vLLM `nemotron-3.5-lightning` at `192.168.1.218:8099`. A direct probe with a 1x1 PNG returned **HTTP 400 `"nemotron-3.5-lightning is not a multimodal model"`**.
4. The stream then ends with only `event: error` (`[vllm] Provider HTTP error 400 ...`). No reply is saved. Live DB sessions `00178cc5...` (msg 8) and `c1509a00...` (msg 4) have **empty** assistant rows.
5. **The session is poisoned.** The image message stays in the history, so every later turn re-sends it and gets the same 400. In live session `00178cc5...`, "Hi" at 11:04 PM ET got an empty reply.
6. Reproduced on the scratch smoke server (CARD-467 launcher, port 8766) with a fake OpenAI-compatible text-only endpoint. The text turn replied. The image turn **and** the next "Hi" both got `event: error` with a 400.
7. This predates CARD-397. The split only touched the frontend; this path is backend.

### Beat 3: What will change (proposal)

1. Add a vision capability flag per provider/model (settings, with a preset default). Attach `image_url` parts only when the model supports images. Otherwise keep the text note ("image attached: name, size; this model cannot view images").
2. Attach image bytes only for the **current** turn's attachments, not every historical message. Alternatively, on a 400 that says "not a multimodal model", retry once without images and warn.
3. When the provider errors, save an honest assistant error message, never an empty assistant row.
4. Tests first: adapter unit tests covering a text-only model (no image parts; a text note instead), a vision model (current turn only), and history not re-sending old images. Plus an operator contract: an image turn to a text-only fake provider still replies, and the next turn works.

### Beat 4: What dies

Silent 400s from image parts, sessions that stop working after one picture, and empty assistant rows.

## 2. Acceptance criteria (EARS)

- **[REQ-475-001]** WHILE the active model is not marked vision-capable, WHEN a user message has image attachments, THE SYSTEM SHALL NOT send image parts, and SHALL tell the model and the user that the image could not be viewed.
- **[REQ-475-002]** WHEN a chat turn is sent, THE SYSTEM SHALL attach image bytes only for that turn's attachments, not for earlier messages in the history.
- **[REQ-475-003]** IF the provider rejects a turn, THEN THE SYSTEM SHALL save an assistant message that states the error, and SHALL NOT save an empty assistant message.
- **[REQ-475-004]** WHEN an image turn has failed, THE SYSTEM SHALL keep answering later text turns in the same session.

## 3. Runbook

In Chat on the phone with the default vLLM model, attach a screenshot and ask "what is this?". You get a reply that says the model can't view images. Then "Hi" gets a normal reply.
