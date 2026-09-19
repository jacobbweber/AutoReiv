# Technical Design: Chat Stream Bubble Preservation and Error Persistence

> **Spec Reference**: `docs/specs/chat-stream-bubble-and-error-preservation/requirements.md`  
> **Card Reference**: `docs/cards/CARD-380-fix-chat-stream-bubble-removal-and-preserve-error-state.md`

---

## 1. Architecture Overview

```mermaid
flowchart TD
    subgraph Frontend["Chat Studio (chat.js)"]
        StreamBubble["streamBubble<br/>[data-stream-bubble='true']<br/>[data-job-chrome='inline']"]
        PaintChrome["paintInlineJobChrome()"]
        ResetChrome["resetInlineJobChrome()"]
        Guard{"is streamBubble?"}
        HidePhases["Hide .job-chrome-phases<br/>inside streamBubble"]
        RemoveStandalone["Remove standalone<br/>[data-job-chrome='inline']:not([data-stream-bubble='true'])"]
    end

    subgraph Backend["Chat Router (chat.py)"]
        Worker["worker() background task"]
        TryBlock["Stream execution<br/>(kernel / orch)"]
        ExceptBlock["except Exception as e:"]
        SaveErrorDB["store.save_message(ASSISTANT, '⚠️ **Error**: ...')"]
        EmitSSEError["_sse('error', ...)<br/>_sse('turn_done', ...)"]
    end

    PaintChrome --> Guard
    Guard -- "Yes" --> HidePhases
    Guard -- "No" --> RemoveStandalone

    ResetChrome --> RemoveStandalone

    Worker --> TryBlock
    TryBlock -- "Unhandled Error" --> ExceptBlock
    ExceptBlock --> SaveErrorDB
    ExceptBlock --> EmitSSEError
```

---

## 2. Component Design

### 2.1 Chat Studio (`src/web/static/modules/studios/chat.js`)
- In `paintInlineJobChrome()`:
  When `!shouldMountInlineJobChrome(inlineJobChromeModel)`:
  Query `messagesContainer.querySelector('[data-job-chrome="inline"]')`.
  Check if `existing.getAttribute('data-stream-bubble') === 'true'`:
  - If `true`, do **not** call `existing.remove()`. Instead, hide `.job-chrome-phases` inside it (`classList.add('hidden')`).
  - If `false` (or not a stream bubble), call `existing.remove()`.
- In `resetInlineJobChrome()`:
  Only remove elements where `n.getAttribute('data-stream-bubble') !== 'true'`.
- In `executeChatTurn()`:
  Track `let turnHasError = false;`
  In `catch (err)` or when `eventType === 'error'`: set `turnHasError = true`.
  In `finally`: if `turnHasError` is true and SQLite does not yet have an assistant message, do not wipe `messagesContainer` with `renderMessages()`.

### 2.2 Chat Router (`src/web/routers/chat.py`)
- In `worker()`:
  In `except Exception as e:`:
  ```python
  err_msg = f"⚠️ **Error**: {e}"
  try:
      store.save_message(
          session_id=req.session_id,
          agent_id=profile.id,
          message=ChatMessage(role=Role.ASSISTANT, content=err_msg),
      )
  except Exception:
      pass
  await queue.put(_sse("error", {"error": str(e)}))
  await queue.put(_sse("turn_done", {"content": err_msg, "error": str(e)}))
  ```
  This guarantees that all failures are durable in the session transcript.

---

## 3. Interfaces & Data Contracts
No database schema changes are required. Messages table continues to store standard `ChatMessage` entities with `Role.ASSISTANT`.
Existing SSE event contracts (`error`, `turn_done`, `react_state`, `reasoning`, `token`) remain intact.
