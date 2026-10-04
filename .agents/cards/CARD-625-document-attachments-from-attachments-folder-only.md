---
id: CARD-625
title: "Document and text attachments are read from any path the chat request names, not only the attachments folder"
type: security
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-625-docs-from-uploads-only]
  checks:
    - tests/unit/gateway/test_card625_doc_attachments_dir_only.py
    - tests/unit/gateway/test_card479_attachment_text.py
branch: feat/card-625-document-attachments-from-attachments-folder-only
log: {minutes: 30, qa_runs: 1, findings: 1}
created: 2026-10-03
related:
  - CARD-483
  - CARD-479
  - CARD-143
---

# CARD-625 Document and text attachments are read from any path the chat request names, not only the attachments folder

> **Status**: In Review (2026-10-04, branch `feat/card-625-document-attachments-from-attachments-folder-only`, not merged). Found while building CARD-483, 2026-10-03.

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

## Built
- `attachment_text.py`: `build_attachment_prompt(..., attachments_dir=...)`. With a folder given, a document or text file is read from the resolved path only when `inside_attachments_dir()` (CARD-483) finds it inside the folder (after `..` and links; a sibling such as `attachments-old` is outside). Anything else gets `*(Could not read `<name>`: not an uploaded file.)*` for the model and `Couldn't read `<name>`: not an uploaded file.` in `failures`, which the chat already sends as an `attachment_notice` (CARD-479) and saves as a chat note (CARD-482). The forged path is not repeated to the model (name only), and no extractor runs.
- An upload that is gone from inside the folder still says "the uploaded file is missing". An outside path always says "not an uploaded file", whether or not it exists, so the note does not reveal whether an outside file is there.
- An unknown folder (resolver returns nothing or raises) reads nothing (fail closed, like CARD-483).
- `routers/chat.py`: `/api/chat/stream` passes `attachments_dir=lambda: get_attachments_dir(request)` (the folder `/api/chat/upload` writes to). `format_prompt_with_attachments` takes `attachments_dir` and passes it on; without one it reads no document or text file.
- Images are unchanged here (the gateway checks them, CARD-483).

## Plan and decisions
- Check inside `build_attachment_prompt`, not in the router: one place reads the file, so the check sits next to the read.
- Leaving `attachments_dir` out skips the check, so the CARD-479 unit tests (files in `tmp_path`, no folder) stay unchanged as asked. A guard test (`test_every_src_caller_passes_the_upload_folder`) fails if any call in `src` leaves it out; passing `None` fails closed.
- No product decision needed.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit, failing first: outside text file not read | PASS | `test_an_outside_text_file_is_not_read`: secret not in prompt, note text exact, outside path not echoed, one failure line |
| Unit: real upload still read | PASS | `test_an_upload_inside_the_folder_is_still_read` |
| Unit: `..` escape, `attachments-old` sibling, outside .csv never extracted | PASS | extractor not called for the outside document |
| Unit: missing upload says missing; missing outside path says not uploaded | PASS | no existence oracle for outside paths |
| Unit: no folder / resolver None / resolver raises reads nothing | PASS | fail closed |
| Unit: every `src` caller passes `attachments_dir` | PASS | guard over `src/**/*.py` |
| Through `/api/chat/stream`, failing first: forged outside path | PASS | before the fix the secret reached the model; now not in the prompt, not in saved messages, one `attachment_notice` "Couldn't read `secret.txt`: not an uploaded file." |
| Through `/api/chat/stream`: real upload via `/api/chat/upload` | PASS | content in the prompt, no notice |
| CARD-479 tests unchanged | PASS | `test_card479_attachment_text.py` 8/8, no diff; CARD-483 tests 14/14; new CARD-625 tests 12/12 |
| Full suite on `c0cd8f17` | PASS | pytest 2514 passed / 12 skipped; release preflight GREEN (ruff, eslint 0 errors, vitest 1052, honesty, smoke 83/83) |
| Live :8770 (throwaway, Spark Nemotron `nemotron-3.5-lightning` from the start; model check ok), real UI upload of `launch-notes.txt` | PASS | file text inlined in the user message; reply "The code word is BLUEBIRD-625."; no notice |
| Live: forged attachment (UI upload of `decoy.txt`, the stream request's `path` rewritten to `%TEMP%\autoreiv-qa\c625-fixtures\outside-secret-625.txt`) | PASS | user message shows "📎 outside-secret-625.txt (Could not read outside-secret-625.txt: not an uploaded file.)"; blue notice "Couldn't read `outside-secret-625.txt`: not an uploaded file."; reply "I cannot read the file as it was not uploaded/attached..."; saved session has no `OUTSIDE-SECRET`/`PINEAPPLE` and no fixture folder path |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1004a\625-upload-inlined-*.png`, `625-forged-not-read-*.png` (desktop 1024x640 and phone 390x844; `-staged-` shows the attached chip before send; `-user-message-` shows the saved user message).

## Findings
- (to findings list) On a phone, a user message with an attachment line (long unbroken `Local Path`) is 602 px wide in a 390 px screen and runs 224 px off the left edge (`625-upload-inlined-phone.png`). Not from this card (the CARD-479 attachment text).
- (from the CARD-483/504 build and live check, 2026-10-03; docs/findings.md)

## Release note
Only files you actually uploaded are read into a chat message; any other file path gets "Couldn't read: not an uploaded file".
