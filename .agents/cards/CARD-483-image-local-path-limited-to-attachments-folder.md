---
id: CARD-483
title: "Only send images from the attachments folder, not any 'Local Path' written in a user message"
status: In Review
created: 2026-09-25
branch: feat/card-483-504-attachments-only-and-needs-tool-title
related:
  - CARD-475
  - CARD-143
labels:
  - type:security
  - area:gateway
  - P3
needs_decision: none
milestone: M24
---

# [CARD-483] Only send images from the attachments folder, not any "Local Path" written in a user message

> **Status**: In Review (2026-10-03, branch `feat/card-483-504-attachments-only-and-needs-tool-title`, not merged)
> **Created**: 2026-09-25
> **Observed during**: the CARD-475 build.
> **Related**: CARD-475, CARD-143
> **Labels**: `type:security`, `area:gateway`, `P3`

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
Only pictures I actually attached should ever be sent to a model.

### Beat 2: What AutoReiv does now
Chat writes attachments into the user message as text (`Local Path: \`...\``, CARD-143). Before CARD-475, the adapters read any such path, from any user message in the history. CARD-475 narrowed this to the latest user message and to vision models (`src/application/gateway/attachment_images.py` `current_turn_images()`). It still trusts any readable `.png/.jpg/.jpeg/.webp/.gif` path written in that message, up to 10 MB. A typed path, or a USER-role message built from other content (a job assignment, a handoff), could make AutoReiv send a local image file that was never attached. Today the models are on your own Spark, so the exposure is low. It would matter with a cloud provider.

### Beat 3: What will change
Resolve the path and require it to sit under the data root's `attachments/` folder (`get_attachments_dir`). Otherwise skip it, as if it were missing. Tests first: a path outside `attachments/` is not attached, and a real upload still is.

### Beat 4: What dies
Arbitrary local image paths going to a model.

## 2. Acceptance criteria (EARS)
- **[REQ-483-001]** WHEN a user message names an image path outside the attachments folder, THE SYSTEM SHALL NOT send that file to any model.
- **[REQ-483-002]** WHEN the image was uploaded through `/api/chat/upload`, THE SYSTEM SHALL keep attaching it as in CARD-475.

## 3. Built (2026-10-03)

- `src/application/gateway/attachment_images.py`: `current_turn_images(content, attachments_dir)` resolves each named path (following `..` and links) and keeps it only when it sits inside the attachments folder (`inside_attachments_dir`, case-insensitive on Windows, `commonpath` so `attachments-old/` is outside). Anything else is treated as missing: no bytes, no "can't view images" note, no notice. With no folder known, nothing is attached (fail closed). The folder may be a callable and is only resolved when a message actually names a path.
- `MultiProviderGateway.set_attachments_dir_resolver()`; `_prepare_images` passes it on. `src/web/app.py` wires it to `data_dir_paths.root / "attachments"`, the folder `/api/chat/upload` writes to.
- This also covers the client-supplied `path` in a chat request's `attachments` list, which before was trusted as is.
- Tests: `tests/unit/gateway/test_card483_attachments_dir_only.py` (14) and `tests/integration/operator_contracts/test_oc483_attachments_dir_only.py` (3, through `/api/chat/stream` with a vision model). On the old code the forged attachment path and the typed path both reached the vision model ("images seen: 1"). The CARD-475/482 tests now pass the folder their images sit in.

## 4. Results (live :8770, Spark nemotron-3.5-lightning, text-only, 2026-10-03 ET)

Nemotron cannot view images, so the visible signal is the CARD-475 notice: an image AutoReiv treats as attached gets "This model can't view images, so it only saw the file name ...".

| Check | Result |
|---|---|
| API: real upload (`attachments\<session>\..._qa_photo.jpg`) | notice sent (attached) |
| API: forged attachment `path` = `C:\Windows\Web\Screen\img102.jpg` | no notice (not attached) |
| API: typed `Local Path: C:\Windows\Web\Screen\img101.jpg` | no notice (not attached) |
| UI desktop: attach a photo and send | notice under the message |
| UI desktop: typed outside path | no notice; the reply says it cannot reach the file |

Full suite on `8e38342c`: pytest 2460 passed, 12 skipped; preflight GREEN (ruff, eslint, vitest 1032 passed, smoke 79/79 incl. TC-36 desktop and phone).

Screenshots in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003j\`: `desktop-01`, `desktop-02`, `phone-03`.

## 5. Findings

- Document and text attachments still read whatever `path` the client sends (`attachment_text.py`), so any readable text file can be inlined into the prompt: CARD-625.
