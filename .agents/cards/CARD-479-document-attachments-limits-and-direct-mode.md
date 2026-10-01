---
id: CARD-479
title: "Document attachments: tiny inline limits and Direct mode cannot read attached files"
status: Done
completed: 2026-09-30
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
needs_decision: none
milestone: M24
---

# [CARD-479] Document attachments: tiny inline limits and Direct mode cannot read attached files

> **Status**: Done (merged into qa 2026-09-30)
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

## Decision (Jacob, 2026-09-30)
- Approved the class-b recommendation: the inline attachment limit is **sized from the model's context window**, and **Direct mode reads attachments** (their text is included; no tool note).

## Outcome (2026-09-30, branch `card/479-attachments-context-sized`)
- New `src/application/gateway/attachment_text.py`:
  - `attachment_char_budget(context_tokens)` = a quarter of the window at ~4 chars/token, kept between 8,000 and 400,000 characters (nemotron 262,144 tokens -> 262,144 characters; an 8k model -> 8,192).
  - `build_attachment_prompt(...)` extracts every document (PDF, Excel, Word, CSV) and text file whatever its file size (the 16 KB / 8 KB cut-offs are gone), shares the budget between the turn's files, and marks a cut: agent mode "read the rest with `read_document_file`", Direct mode "the rest was not included".
  - Direct mode ends with "Their text is included here; there are no tools in this chat" instead of the `read_document_file` note [REQ-479-002].
  - A file that cannot be read is named in the prompt and returned in `failures` [REQ-479-003].
- `chat.py` stream worker: budget from `resolve_agent_context_limit(profile, store)`; each failure is also sent to the user as an `attachment_notice` (the sky line from CARD-475; saved as a chat note once CARD-482 is merged). `format_prompt_with_attachments` stays as a thin wrapper.
- Tests: `tests/unit/gateway/test_card479_attachment_text.py` (budget from window, 56 KB text inlined on 262k, cut + marker on a small window, Direct wording, 3,000-row CSV over 16 KB extracted, missing file told to both, shared budget, image line unchanged).

## Human Verification Runbook (2 minutes)
1. Pull qa, restart the serve, Ctrl+F5.
2. Chat Studio -> **Direct**: attach a text or CSV file over 20 KB and ask "What is the last line of the file?" The answer quotes the real last line (no "I'll read it with a tool").
3. Any agent chat: attach the same file; the answer uses the content. Attach a broken PDF (rename a .txt to .pdf): the sky line says it couldn't be read.

## Live check
- 2026-09-30 ~3:00 PM ET, throwaway :8770 (clone data, Direct on nemotron): a 36,967-byte text file (was path-only above 8 KB) -> the prompt carries the text and no `read_document_file` note; asked for the last line, Direct answered `LAST LINE: the blue heron lands at 7:42` (exact). Screenshots: `scratch/ui0930/479-direct-attachment-desktop.png` / `-phone.png` (Jarvis).
- 2026-09-30: preflight --fast --base qa GREEN. Jacob: merge to qa (small engineering fix). Done; merged into qa.
