---
id: CARD-479
title: "Document attachments: tiny inline limits and Direct mode cannot read attached files"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-475
  - CARD-143
labels:
  - type:bug
  - area:chat
  - area:attachments
  - P2
---

# [CARD-479] Document attachments: tiny inline limits and Direct mode cannot read attached files

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-475 planning (code read, qa `8929a743`).
> **Related**: CARD-475, CARD-143
> **Labels**: `type:bug`, `area:chat`, `area:attachments`, `P2`

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
If Jacob attaches a PDF, spreadsheet or text file, the model should actually get its content (or a clear, fair excerpt) in both Direct and agent chats.

### Beat 2: What AutoReiv does now
`src/web/routers/chat.py` `format_prompt_with_attachments` (L130-187):
- It previews documents via `extract_document` only if they are **under 16 KB**, and inlines other text files only if **under 8 KB**. Otherwise the model gets only a file path.
- It always adds "read documents using `read_document_file`". Direct mode (`agent_id == "direct"`, L2070) runs with no tools, so the model cannot read the file and may pretend it did.
- Extraction failures are swallowed silently.

### Beat 3: What will change (decision needed)
- Decide limits by extracted text size, not file size. For example, extract up to about 8,000 characters (5 pages / 25 rows) whatever the file size, and say when it was cut short.
- In Direct mode, drop the tool note and always include the excerpt. In agent mode, keep the tool note.
- If extraction fails, tell the model and the user.

Tests first: unit tests for a large PDF (excerpt plus "truncated"), a text file over 8 KB, Direct vs agent note wording, and an extraction failure message.

### Beat 4: What dies
Size-based silent omission, and the false tool note in Direct mode.

## 2. Acceptance criteria (EARS)
- **[REQ-479-001]** WHEN a supported document is attached, THE SYSTEM SHALL include an extracted excerpt up to the character budget and mark any truncation.
- **[REQ-479-002]** WHILE in Direct mode, THE SYSTEM SHALL NOT tell the model to use tools to read attachments.
- **[REQ-479-003]** IF extraction fails, THEN THE SYSTEM SHALL say so to the model and the user.
