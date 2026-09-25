---
id: CARD-475
title: "Image attachments are sent to text-only models; one image breaks the whole chat session"
status: Ready
created: 2026-09-24
updated: 2026-09-25
branch: qa
related:
  - CARD-469
  - CARD-143
  - CARD-235
  - CARD-479
  - CARD-480
labels:
  - type:bug
  - area:chat
  - area:gateway
  - area:attachments
  - P1
---

# [CARD-475] Image attachments are sent to text-only models; one image breaks the whole chat session

> **Status**: Ready (refined after Jacob's `continue`, 2026-09-25 ~1:15 AM ET, qa `8929a743`)
> **Created**: 2026-09-24
> **Observed during**: CARD-469 live test, 2026-09-24 at 11:02 PM and 11:05 PM ET. Jacob attached a phone screenshot in Chat (Direct mode) and got no reply. After that, even "Hi" in the same session got no reply.
> **Verified 2026-09-25 ET**:
> - Read-only look at the live DB and provider config.
> - Read-only probe of the Spark gateway.
> - Scratch smoke server (port 8766, data under `scratch/smoke_data`) with a fake text-only OpenAI-compatible model that mimics the Spark gateway.
> **Related**: CARD-469, CARD-143, CARD-235; follow-ups CARD-479, CARD-480
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

Attaching a picture must never break a chat. If the current model can't see images, AutoReiv should say so plainly, still answer the text, and the rest of the conversation should keep working. A failed reply must show as failed, never as silence.

### Beat 2: What AutoReiv does now (verified)

1. **How attachments become the message.** `src/web/routers/chat.py` `format_prompt_with_attachments` (L130-187; called at L1829) appends a text section to the user message, and that text is saved in history.
   - **Images** (`image/*` or png/jpg/jpeg/gif/webp/svg) become markdown `![name](url)` plus `(Attached Image: …, Local Path: \`C:\...\`)`. No bytes are stored in the message.
   - **Documents** (pdf/xlsx/xls/docx/doc/csv/tsv) become a link plus `Local Path`. A preview from `extract_document` (5 pages / 25 rows) is added only if the file is **under 16 KB**, which rules out almost every real PDF.
   - **Other files** (txt/md/code…) are inlined only if **under 8 KB**. Otherwise just the path.
   - Every attachment ends with the note "read documents using `read_document_file`". Direct mode has no tools, so that note is false there (CARD-479).
2. **Image bytes are rebuilt from history on every turn.**
   - `openai_adapter.py` `_format_messages` L130-181 (regex at L143-160) scans **every user message in the history** for `Local Path:`, base64-encodes any png/jpg/jpeg/webp/gif up to 10 MB, and sends it as `image_url` parts.
   - `ollama_adapter.py` `_format_messages` L88-125 (L96-110) does the same with Ollama `images`.
   - `anthropic_adapter.py` has no image support at all, so it sends text only.
   - `ChatMessage.images` (`src/domain/gateway/models.py` L34) is never set anywhere. Neither adapter checks whether the model can take images, and SVG is labelled as an image but never sent.
3. **Model capability metadata exists but is unused.**
   - `ModelDescriptor.is_multimodal` (`src/domain/settings/models.py` L36) is filled only by name guesses: OpenAI `"vision"` or `"4o"` in the id (`openai_adapter.py` L444), Ollama `"vision"` or `"llava"` in the name (`ollama_adapter.py` L321).
   - It is returned by Refresh Models (`src/web/routers/settings.py` L722, `settings.js` L905), but it is not saved and nothing reads it.
   - `ModelPurpose.VISION` exists in `purpose_matrix`, but the live value is `purposes: {}`.
4. **Jacob's setup (read-only).**
   - `provider_settings` has one provider, `vllm` at `http://192.168.1.218:8099/v1`, default `nemotron-3.5-lightning`.
   - The Spark gateway `/v1/models` lists 7 models, one loaded at a time. Each has a `description`; two say they take images: `gemma-4-26b-a4b` ("multimodal") and `nemotron-3-nano-omni` ("image/video/audio→text"). The default nemotron is text-only.
   - Spark also runs **Ollama** on `:11434` (not configured in AutoReiv). Its `/api/tags` returns `capabilities`; `vision` is listed for `gemma4:26b`, `qwen3.6:35b`, `qwen3.8:27b` and `qwen3.8:latest`.
   - So a vision model is available, but it is not the default, and switching to it swaps the model loaded on the GPU.
5. **Why the reply was silent and the row empty (new root cause).**
   - Read-only probe: the Spark gateway answers a streamed image request to nemotron with **HTTP 200 `text/event-stream`**, and the body is a bare JSON line: `{"error":{"message":"nemotron-3.5-lightning is not a multimodal model","code":400}}`.
   - `src/infrastructure/gateway/openai_stream_tool_calls.py` L100 only reads `data:` lines, and L110 skips frames without `choices`. So the error is **silently dropped** and the stream "finishes" with no content.
   - `agent_kernel.py` `stream_turn` (L1254) then saves `content=""` as a normal assistant reply (L1499-1510) and sends `turn_done` with empty content.
   - The CARD-469 "Reply failed" notice only fires on `error` events or zero events (`chat/stream.js` L266-279), so the UI shows nothing.
   - `run_turn` has the same empty save (L1144).
   - A real HTTP 400 (the plain fake) goes through the error path instead: `event: error`, no row saved.
6. **Live data (read-only).**
   - Three Direct-mode sessions are poisoned by the history replay: `00178cc5…` (msgs 7-10), `c1509a00…` (msgs 3-4) and `4e0f181c…`.
   - There are **4 empty assistant rows** in total: `00178cc5` #8 and #10, `c1509a00` #4, `4e0f181c` #2.
   - The screenshots are still on disk under `AppData\Local\AutoReiv\attachments\<session>\`, so every new turn in those sessions re-sends them.
7. **Reproduced on scratch** (fake model; returns 200 plus a bare error line for streams containing images, like the Spark gateway):
   - Direct mode: "What is this?" plus a 1×1 PNG gives `turn_done` with `""` and an empty assistant row. The next "Hi" gives the same.
   - The fake log shows the second turn still carrying `image_url`.
   - With a plain HTTP-400 fake, both Direct and `autoreiv` send `event: error` on the image turn **and** on the next text turn.
8. This predates CARD-397; it is all backend.

### Beat 3: What will change (proposal, tests first)

1. **Know whether the model can see images** (new `model_capabilities` helper in `src/application/gateway/`). Resolve per `provider/model`, in this order:
   1. An operator override in settings (`model_capabilities: {"vllm/gemma-4-26b-a4b": {"vision": true}}`).
   2. Provider metadata saved on Refresh Models: Ollama `capabilities` contains `vision`; for OpenAI-compatible providers, a `description`/`root` that says multimodal/vision/image/omni.
   3. The existing name guess.
   4. **Otherwise text-only.**
2. **Only this turn's images, only for vision models.**
   - The adapters stop scanning history. The request carries images only for the current user message, on the domain `images` field set by chat/kernel from `req.attachments`.
   - Earlier image messages replay as text: `(image from earlier: name)`. This fixes the poisoned live sessions automatically, with no data change.
3. **Text-only model plus image.** Send no image bytes. Add a note to the model ("The user attached image `name` (size). This model cannot view images; say so and answer from the text.") and send a visible `attachment_notice` SSE event to the user ("This model can't view images. It only saw the file name.").
4. **Failed replies are never silent or empty.**
   - `openai_stream_tool_calls.py` treats a bare JSON `{"error":…}` line or a `data: {"error":…}` frame as a `GatewayError`.
   - Both kernel paths refuse to save an empty assistant reply (no content and no tool calls). They send `error` "The model returned an empty reply" instead, which triggers the CARD-469 notice.
   - As a safety net, a "not a multimodal model" rejection on an image turn retries once without images, with the notice from item 3.
5. **Replay hygiene.** Skip empty assistant rows (no content, no tool calls) when building history, and don't render them in the thread. No migration.
6. **Tests first:**
   - Unit tests:
     - capability resolution (override, then Ollama capabilities, then gateway description, then name, then text-only default)
     - adapters: no history scan; current-turn images only for vision models; text note for text-only
     - stream parser: a bare JSON error and a `data: {"error"}` frame both raise
     - kernel: an empty stream sends `error` and saves no row
     - history replay skips empty assistant rows
   - Operator contract on a fake Spark-like provider:
     - image turn on a text-only model: a reply plus `attachment_notice`, and the next turn works
     - image turn on a vision-marked model: the image goes out once, and the next turn has none
   - Vitest: an `attachment_notice` shows in the bubble; empty rows are hidden.
   - Smoke: an intercepted `attachment_notice` renders.
7. **Proof:** the unit tests and operator contract fail on qa and pass after the fix. The scratch repro above flips to "reply plus notice; next Hi answers". Then a Jarvis runbook on the phone.

### Beat 4: What dies

- Replaying image bytes from history every turn.
- Silent HTTP-200 error streams.
- Empty assistant rows as fake replies.
- Sessions that never recover after one picture.
- The unused name-only `is_multimodal` guess as the only capability signal.

---

## 2. Acceptance criteria (EARS)

- **[REQ-475-001]** WHILE the active model is not vision-capable, WHEN a user turn has image attachments, THE SYSTEM SHALL NOT send image bytes, SHALL tell the model the image could not be viewed, and SHALL show the user an attachment notice.
- **[REQ-475-002]** WHEN a chat turn is sent, THE SYSTEM SHALL attach image bytes only for that turn's attachments and only to a vision-capable model. Earlier image messages SHALL be sent as text references.
- **[REQ-475-003]** THE SYSTEM SHALL decide vision capability from, in order: operator override, saved provider metadata (Ollama `capabilities`, gateway description), name heuristic, and otherwise text-only.
- **[REQ-475-004]** IF a provider stream carries an error payload (bare JSON or `data:` frame) or ends with no content and no tool calls, THEN THE SYSTEM SHALL send an `error` event and SHALL NOT save an empty assistant message.
- **[REQ-475-005]** IF the provider rejects an image turn as not multimodal, THEN THE SYSTEM SHALL retry once without images and show the attachment notice.
- **[REQ-475-006]** WHEN history is replayed or rendered, THE SYSTEM SHALL skip assistant rows with no content and no tool calls.
- **[REQ-475-007]** WHEN an image turn has failed or been downgraded, THE SYSTEM SHALL keep answering later turns in the same session, including sessions poisoned before this fix.

## 3. Decisions for Jacob (recommendations in bold)

- **D1: Text-only model plus image.** Options:
  - (a) drop the image, with a notice to the model and to you
  - (b) auto-route the turn to a vision model
  - (c) have a vision model describe the image and pass the description to the text model

  **(a) now.** (b) and (c) swap the Spark GPU model (only one is loaded) and add latency. **(c) goes to CARD-480**, driven by the existing `purpose_matrix.purposes.vision` slot, off by default.
- **D2: Unknown models.** **Treat them as text-only**, plus the retry safety net (REQ-475-005). You can mark a model vision-capable in Settings (a small checkbox per model after Refresh Models) or rely on Ollama capabilities.
- **D3: Images from earlier turns.** **Never re-send them**, even to vision models. They become text references, which saves tokens and heals poisoned sessions.
- **D4: The 4 empty live rows.** **Leave the data alone**, and skip them at replay and render time. No migration: it is 4 rows, and skipping handles any future ones.
- **D5: Poisoned live sessions.** **Heal automatically** through D3, no data change. The screenshot files stay on disk.
- **D6: Notice wording.** **"This model can't view images, so it only saw the file name `<name>`. Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures."**

## 4. Runbook (Jarvis, phone)

1. On the default vLLM nemotron, open Chat (Direct or AutoReiv), attach a screenshot and ask "what is this?".
   - You get a reply plus the notice "This model can't view images…".
   - Then "Hi" gets a normal reply.
2. Open old session `00178cc5…` ("If a doctor gives you") and send "Hi". It answers normally, and the empty rows no longer show.
3. (Optional, if you mark `gemma-4-26b-a4b` as vision-capable) Switch the model, attach the screenshot, and the reply describes it. The next turn does not re-send it.

## 5. Constraints

- Backend gateway/kernel plus a small frontend notice.
- `chat.js` stays at 1,045 lines or fewer, and `render.js` is at its 800-line cap, so any rendering change goes in a helper.
- No writes to live data.
- Follow-ups: CARD-479 (document attachments and Direct mode), CARD-480 (vision helper).
