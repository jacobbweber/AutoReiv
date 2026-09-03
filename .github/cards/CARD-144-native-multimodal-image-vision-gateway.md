# [CARD-144] Native Multimodal Image Vision Gateway

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Gateway`, `AutoReiv.Web`

---

## 1. Why / Intent

When users upload screenshots or photos from their phone or desktop in Chat Studio, vision-capable LLMs (such as Google Gemini 2.0/1.5 Flash, OpenAI GPT-4o, and local Qwen2-VL) must be able to visually inspect and analyze the image directly (reading text in UI, recognizing charts, buttons, and diagrams) rather than only seeing a plain text file path on disk.

---

## 2. What to Build

1. **Domain Model Extension (`src/domain/gateway/models.py`)**:
   - Extend `ChatMessage` to support multimodal image payloads: `images: Optional[List[Dict[str, Any]]] = None` (containing `media_type`, `data_base64`, `filename`, `url`).
2. **OpenAI & Gemini Gateway Adapter (`src/infrastructure/gateway/openai_adapter.py`)**:
   - In `_format_messages()`, when a user message includes images, serialize `content` into standard OpenAI multimodal format:
     ```json
     {
       "role": "user",
       "content": [
         {"type": "text", "text": "What do you think of this image?"},
         {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
       ]
     }
     ```
3. **Ollama Gateway Adapter (`src/infrastructure/gateway/ollama_adapter.py`)**:
   - In `_format_messages()`, support Ollama's native multimodal parameter: `"images": ["<base64_payload>"]`.
4. **Chat Stream Pipeline Integration (`src/web/routers/chat.py`)**:
   - When attachments contain image files (`image/png`, `image/jpeg`, etc.), read the stored bytes, encode to Base64, and pass them into the `ChatMessage` images array.
   - For text-only fallbacks or agents without vision, preserve the filesystem path notice.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-VISION-001]`: `ChatMessage` supports optional image payloads with mime type and Base64 data.
- [ ] `[REQ-VISION-002]`: `OpenAIProviderAdapter` serializes images to standard `{"type": "image_url", "image_url": {"url": "data:..."}}` blocks.
- [ ] `[REQ-VISION-003]`: `OllamaProviderAdapter` formats images into Ollama's native `images` array.
- [ ] `[REQ-VISION-004]`: Uploaded image attachments are automatically Base64-encoded and passed to vision-capable models in `/api/chat/stream`.
- [ ] Automated tests green via `pytest tests/unit/gateway` and `pytest tests/unit/web`.
- [ ] Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing passing tests.
- Local `qa` branch is source of truth.
- Local files remain accessible on disk for non-vision tools (e.g. `PIL`, python).
