---
id: CARD-483
title: "Only send images from the attachments folder, not any 'Local Path' written in a user message"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-475
  - CARD-143
labels:
  - type:security
  - area:gateway
  - P3
---

# [CARD-483] Only send images from the attachments folder, not any "Local Path" written in a user message

> **Status**: Ready
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
