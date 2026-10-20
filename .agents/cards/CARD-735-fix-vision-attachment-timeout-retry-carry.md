---
id: CARD-735
title: "Fix vision attachment timeout, retry carry-forward, and image prompt note"
type: bug
status: Done
priority: P2
milestone: M32
needs_decision: none
proof:
  journeys: [card-735-fix-vision-attachment-timeout-retry-carry]
  checks:
    - tests/unit/gateway/test_card735_vision_retry_and_note.py
    - tests/integration/operator_contracts/test_oc475_image_turn_text_only_model.py
branch: feat/card-735-fix-vision-attachment-timeout-retry-carry
log: {minutes: 12, qa_runs: 1, findings: 0}
created: 2026-10-20
completed: 2026-10-20
---

# CARD-735 Fix vision attachment timeout, retry carry-forward, and image prompt note

## Problem
When sending multiple screenshot attachments (16 PNGs, ~22.4 MB) to a vision-capable model (`ollama/qwen3.8:latest`) in Docker:
1. Turn 1 times out at 180 seconds (`[ollama] Ollama timed out at http://192.168.1.29:11434:`) because `docker-compose.yml` still sets `GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180.0`, overriding the 1800s default from CARD-592.
2. When the operator follows up with `"Looks like we hit a timeout. Let's try it again"` without re-uploading the images, `prepare_image_turn` only inspects the very last `Role.USER` message and sends 0 images on the retry turn.
3. `build_attachment_prompt` appends `AGENT_NOTE` (`You can read documents using read_document_file...`) even when all attachments are images, prompting the model to call `read_document_file` on `.png` files and fail with `Error: Unsupported document format: .png`.

## Cause
1. `docker-compose.yml` line 51 still sets `GATEWAY_DEFAULT_TIMEOUT_SECONDS=${GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180.0}`, and `provider_read_timeout()` in `src/infrastructure/gateway/timeouts.py` checks `LEGACY_ENV_KEY` (`GATEWAY_DEFAULT_TIMEOUT_SECONDS`) before falling back to `DEFAULT_PROVIDER_READ_TIMEOUT` (`1800.0`).
2. `prepare_image_turn()` in `src/application/gateway/attachment_images.py` only looks for `Local Path:` in `messages[last_user]`, even when the preceding user message had image attachments and every assistant message after it was a failure/timeout/stopped turn (`Job ... FAILED`, `⚠️ **Error**:`, or `*[Stopped.]*`).
3. `build_attachment_prompt()` in `src/application/gateway/attachment_text.py` unconditionally appends `AGENT_NOTE` in agent mode even when `readable` (non-image attachments) is empty.

## Change
- `docker-compose.yml`: replace `GATEWAY_DEFAULT_TIMEOUT_SECONDS=${GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180.0}` with `AUTOREIV_PROVIDER_IDLE_SECONDS=${AUTOREIV_PROVIDER_IDLE_SECONDS:-}` so Docker uses the 1800s (30-minute) default from CARD-592 unless overridden.
- `src/application/gateway/attachment_images.py`: in `prepare_image_turn()`, when `messages[last_user]` has no images of its own, carry forward images from the most recent prior `Role.USER` message if every intervening `Role.ASSISTANT` message is a failed, error, or stopped turn (`Job ... FAILED`, `⚠️ **Error**:`, `*[Stopped.]*`).
- `src/application/gateway/attachment_text.py`: add `IMAGE_ONLY_NOTE` and emit it when `not direct` and all attachments are images (`not readable`), instructing the agent that vision models receive image bytes directly in the turn and not to call `read_document_file` on image files.

## What dies
- The stale `GATEWAY_DEFAULT_TIMEOUT_SECONDS=${GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180.0}` default in `docker-compose.yml`.

## Proof
- Journey `card-735-fix-vision-attachment-timeout-retry-carry`: upload a PNG screenshot in Chat, verify the attachment chip and sent turn succeed on desktop and phone without `read_document_file` `.png` errors.
- Checks: `tests/unit/gateway/test_card735_vision_retry_and_note.py` and `tests/integration/operator_contracts/test_oc475_image_turn_text_only_model.py` (asserting `docker-compose.yml` no longer clamps timeout to 180s, image-only turns do not tell the agent to call `read_document_file`, and a follow-up retry after a failed/error/stopped image turn carries the images forward while normal answered turns never re-send old images).

## Plan and decisions
- Approved by Jacob in session (`Let's go with recommended`): fix all three compounding causes (Docker 180s timeout override, retry carry-forward after failed/error/stopped turns, and image-only attachment note).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `preflight.py --fast --base qa` | — | GREEN | ruff PASS, eslint PASS, 322 guard tests PASS, 13 changed tests PASS, 41 mapped tests PASS, 1142 vitest tests PASS (15s) |
| `card-735-fix-vision-attachment-timeout-retry-carry` | desktop | PASS | Verified `IMAGE_ONLY_NOTE` and clean image attachment turn on `qwen3.8:latest` |
| `card-735-fix-vision-attachment-timeout-retry-carry` | phone | PASS | Verified `IMAGE_ONLY_NOTE` and clean image attachment turn on `qwen3.8:latest` |

Screenshots:
- `/tmp/autoreiv-qa/card-735/card-735-fix-vision-attachment-timeout-retry-carry-desktop-01-attach-a-png-image-in-chat-send-the-turn-and-ver.png`
- `/tmp/autoreiv-qa/card-735/card-735-fix-vision-attachment-timeout-retry-carry-phone-01-attach-a-png-image-in-chat-send-the-turn-and-ver.png`

## Release note
Fixed vision image attachments timing out at 180s in Docker, losing attached images on a follow-up retry after a failed turn, and instructing agents to call `read_document_file` on image-only turns.

