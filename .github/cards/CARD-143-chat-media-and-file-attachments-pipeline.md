# [CARD-143] Chat Media and File Attachments Pipeline

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Users currently have no mechanism to attach images, videos, audio files, PDFs, or documents to their chat conversations. Introducing a secure, high-performance file attachment pipeline enables users to share screenshots, datasets, documents, and media with AutoReiv agents directly from mobile and desktop devices.

---

## 2. What to Build

### A. Backend Attachment Ingestion & Serving APIs
1. `POST /api/chat/upload`:
   - Accepts `multipart/form-data` with `file: UploadFile` and optional `session_id: str`.
   - Sanitizes filenames against directory traversal attacks.
   - Saves file into `data/attachments/{session_id}/{file_id}_{safe_filename}`.
   - Returns `{ "id": file_id, "filename": safe_filename, "size_bytes": size, "content_type": content_type, "url": f"/api/chat/attachments/{file_id}/{safe_filename}" }`.
2. `GET /api/chat/attachments/{file_id}/{filename}`:
   - Streams the file with proper `Content-Type` (image, video, audio, pdf, text).
3. Chat Stream Integration:
   - Extend `ChatStreamRequest` to accept `attachments: Optional[List[Dict[str, Any]]] = None`.
   - Store attachments in session history (`ChatMessage.metadata["attachments"]`).
   - Format attachment summary context for LLM prompt ingestion so the agent can reference file contents/paths.

### B. Frontend UI & Staging Workflow
1. `#chatAttachBtn`:
   - Replaces the disabled placeholder in `#chatOptionsDrawer`.
   - Binds to hidden `<input type="file" id="chatFileInput" multiple>`.
2. `#chatAttachmentsPreviewList`:
   - Positioned directly above `#promptInput` inside `#chatForm`.
   - Renders interactive preview chips with thumbnail/icon, filename, formatted file size, and remove button (`✕`).
3. Message Thread Rendering:
   - User messages with attachments display responsive media grids (clickable image thumbnails, video preview players, and file download pills).

---

## 3. Wireframes

### Staging Attachments in Chat Input Dock
```text
+-------------------------------------------------------------------+
| [ 🖼️ screenshot.png (240 KB) ✕ ]   [ 📄 annual_report.pdf (1.2 MB) ✕ ]|
|-------------------------------------------------------------------|
| Type a message or instruction...                                  |
|                                                                   |
| [ + Options ]                                                 [ ✈️ ]|
+-------------------------------------------------------------------+
```

### Rendered User Message in Thread
```text
+-------------------------------------------------------------------+
| User                                                     10:02 AM |
| Here are the test results and error screenshot:                   |
|                                                                   |
| +-------------------------+   +---------------------------------+ |
| | [Thumbnail: error.png]  |   | 📄 results.csv (45 KB) [⬇]       | |
| +-------------------------+   +---------------------------------+ |
+-------------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (EARS & DoD)
- [ ] `[REQ-ATTACH-001]`: `POST /api/chat/upload` must validate, sanitize, and store uploaded files in session storage with path traversal protection.
- [ ] `[REQ-ATTACH-002]`: `GET /api/chat/attachments/{file_id}/{filename}` must stream the stored attachment with accurate MIME type headers.
- [ ] `[REQ-ATTACH-003]`: Tapping `#chatAttachBtn` in `#chatOptionsDrawer` opens native file picker and stages files in `#chatAttachmentsPreviewList`.
- [ ] `[REQ-ATTACH-004]`: Each staged attachment chip must display an icon/thumbnail, filename, file size, and interactive remove button (`✕`).
- [ ] `[REQ-ATTACH-005]`: Sending a message must upload staged attachments, deliver attachment descriptors in `ChatStreamRequest`, and render them in the message bubble.
- [ ] Automated tests green via `pytest tests/unit/web/test_chat_attachments_api.py` and `npm run test:unit:frontend`.
- [ ] Zero lint errors via `npm run lint:frontend`.
