---
id: CARD-699
title: "Token-verified context compaction and non-destructive archive links"
type: feature
status: Ready
priority: P1
milestone: M30
needs_decision: none
proof:
  journeys: [card-699-token-verified-context-compaction]
  checks: [tests/unit/chat/test_card699_token_verified_compaction.py]
branch: feat/card-699-token-verified-context-compaction
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-699 Token-verified context compaction and non-destructive archive links

## Intent
Adapted from `Agent-OS` (`agent_os/compaction.py`, `docs/architecture-comparison-crucible-agent-os.md` §4 & §7.1): local models summarizing older turns can drop file paths, numbers/timestamps, or snake_case/file identifiers, or accidentally continue the chat instead of summarizing. AutoReiv's context compaction should verify summaries deterministically before replacing older turns in active context and link compacted rows non-destructively via `archive_links`.

## Goal
Every context compaction pass validates the generated summary against a deterministic check (`Decisions`, `Open tasks`, `Key facts` sections + preservation of user paths, numbers/timestamps, and identifiers with Unicode dash normalization), retries once on failure with turn backoff if still failing, and preserves original transcript rows linked to the summary via `archive_links`.

## Change
- Add deterministic summary verification (`check_summary`: required headings `Decisions`, `Open tasks`, `Key facts` + extracted user/summary key tokens for paths, numbers/dates, and snake_case/file names + Unicode dash normalization + shorter-than-original check).
- Retry once on failed verification; if attempt 2 fails, leave active messages unchanged and set a turn backoff so compaction does not retry on every turn.
- Keep original message rows intact in SQLite and record `archive_links` mapping summarized message IDs to the summary row.

## What dies
- Unchecked one-shot compaction summaries that overwrite or hide older turns without token verification.

## Proof
- Journey `card-699-token-verified-context-compaction`:
  1. Drive a multi-turn session containing explicit file paths, numbers, and identifiers through compaction and verify the summary preserves all required tokens, links original messages via `archive_links`, and renders cleanly in Chat on desktop and phone.
- Checks:
  - `tests/unit/chat/test_card699_token_verified_compaction.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Added token-verified context compaction (`Decisions`, `Open tasks`, `Key facts` + path/number/identifier verification, retry/backoff, and non-destructive `archive_links`) [CARD-699].
