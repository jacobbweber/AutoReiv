---
id: CARD-625
title: "Document and text attachments are read from any path the chat request names, not only the attachments folder"
type: security
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-625-docs-from-uploads-only]
  checks: []
branch: feat/card-625-document-attachments-from-attachments-folder-only
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-483
  - CARD-479
  - CARD-143
---

# CARD-625 Document and text attachments are read from any path the chat request names, not only the attachments folder

## Problem
Found while building CARD-483 (2026-10-03). `POST /api/chat/stream` takes an `attachments` list whose `path` comes from the client (the upload answer is echoed back). For documents and text files, `src/application/gateway/attachment_text.py` `build_attachment_prompt()` reads that path directly (`_extract` -> `extract_document` or `Path.read_text`) and inlines up to a quarter of the context window into the prompt. A request naming `C:\Users\jacob\...\some-file.txt` as an attachment would put that file's text in front of the model, and in the thread. CARD-483 closed this for images only.

## Cause
`build_attachment_prompt` checks only that the path exists; it never checks that it sits under the data root's `attachments/` folder.

## Change
- Read a document or text attachment only when its path resolves inside the attachments folder, reusing `inside_attachments_dir()` from `attachment_images.py` (CARD-483). Otherwise tell the model and the user it could not be read ("not an uploaded file"), like a missing file.
- Tests first: an outside path is not read (unit, and through `/api/chat/stream`); a real upload still is (CARD-479 tests unchanged).

## What dies
Inlining arbitrary local files through a forged attachment.

## Proof
- Journey `card-625-docs-from-uploads-only`: upload a .txt and send (content inlined); send a forged attachment pointing at a file outside the folder (not read, a "could not read" note).

## Plan and decisions

## Findings
- (from the CARD-483/504 build and live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Only files you actually uploaded are read into a chat message.
