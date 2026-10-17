---
id: CARD-699
title: "Token-verified context compaction and non-destructive archive links"
type: feature
status: In Review
priority: P1
milestone: M30
needs_decision: none
proof:
  journeys: [card-699-token-verified-context-compaction]
  checks: [tests/unit/chat/test_card699_token_verified_compaction.py]
branch: feat/card-699-token-verified-context-compaction
log: {minutes: 32, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-699 Token-verified context compaction and non-destructive archive links

## Intent
Adapted from `Agent-OS` (`agent_os/compaction.py`, `docs/architecture-comparison-crucible-agent-os.md` §4 & §7.1): local models or naive truncation summarizing older turns can drop file paths, numbers/timestamps, or snake_case/file identifiers past character 150, or overwrite the original message rows in SQLite. AutoReiv's context compaction should verify summaries deterministically before replacing older turns in active context and link compacted rows non-destructively via `archive_links`.

## Goal
Every context compaction pass validates the generated summary against a deterministic check (`Decisions`, `Open tasks`, `Key facts` sections + preservation of user paths, numbers/timestamps, and identifiers with Unicode dash normalization), retries once on failure with turn backoff if still failing, and preserves original transcript rows linked to the summary via `archive_links`.

## Cause
1. `ContextCompactor.compact_with_stats` previously truncated each intermediate message line to `[:150]` characters without extracting or verifying key user tokens (`paths`, `numbers`, `names`), dropping facts placed beyond character 150.
2. `SessionRepositoryMixin.replace_session_messages` executed `DELETE FROM messages WHERE session_id = ?` before re-inserting the compacted active message list, permanently destroying the pre-compaction message rows in SQLite.

## Change
- Created `src/application/kernel/compaction_verifier.py` implementing:
  - `normalize_text` (Unicode NFKC + look-alike dash folding `\u2010`..`\u2015`, `\u2212` -> `-` and format-char stripping),
  - `extract_key_tokens` and `required_fact_text` (extracting file paths, numbers/dates/times, and snake_case/file identifiers from user messages and earlier compaction summaries while ignoring assistant prose and tool outputs),
  - `check_summary` and `build_verified_summary` (requiring `Decisions`, `Open tasks`, and `Key facts` sections, preservation of required key tokens, and shorter-than-original verification),
  - Per-session compaction backoff (`set_compaction_backoff`, `consume_compaction_backoff`, `reset_compaction_backoff`) when 2 attempts fail `check_summary`,
  - Session route helpers (`serialize_session_messages`, `build_session_context_payload`, `run_session_compaction`).
- Updated `src/application/kernel/context_compactor.py` (`ContextCompactor.compact_with_stats`) to run `build_verified_summary` + `check_summary` with a 2-attempt retry and per-session turn backoff on verification failure.
- Updated `src/infrastructure/memory/schema.py` and `src/infrastructure/memory/repositories/sessions.py` to add the `archive_links` table, keep original rows in `messages` during `replace_session_messages`, link summarized message IDs to their summary message ID in `archive_links`, and support `get_messages(session_id, include_archived=True)` and `get_archive_links(session_id)`.
- Updated `src/web/routers/chat.py` (`GET /api/sessions/{session_id}/messages?include_archived=true`, `GET /api/sessions/{session_id}/context`, `POST /api/sessions/{session_id}/compact`) to expose `archive_links_count`, `archive_links`, and `archived` / `archived_by_summary_id` metadata.

## What dies
- Destructive `DELETE FROM messages WHERE session_id = ?` in `SessionRepositoryMixin.replace_session_messages`.
- Unverified 150-char slice summaries in `ContextCompactor.compact_with_stats` that dropped user file paths, numbers, and identifiers beyond character 150.

## Proof
- Journey `card-699-token-verified-context-compaction` (`tests/e2e/journeys/card-699-token-verified-context-compaction.mjs`):
  1. Seeds an 8-turn (16-message) `autoreiv` session where user messages place `/etc/orion-7/config.yaml`, `8770`, `2026-10-17`, and `max_retry_budget` beyond character 150.
  2. Opens the session in Chat, clicks `#chatManualCompactBtn` in Chat Options, and verifies the `"Compacted 10 turns"` toast, the 3 required summary sections (`Decisions`, `Open tasks`, `Key facts`), preservation of all key tokens, and non-destructive `archive_links` via `/context` and `/messages?include_archived=true`.
  3. Sends a live follow-up question in Chat and verifies `AutoReiv` recalls all 4 preserved tokens from the compacted summary on desktop and phone with zero horizontal overflow.
- Checks:
  - `tests/unit/chat/test_card699_token_verified_compaction.py` (4 passed)
  - `preflight.py --fast --base qa` (GREEN: ruff PASS, eslint PASS, 236 guard tests PASS, 4 changed tests PASS, 144 mapped tests PASS, 1121 vitest PASS)

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17) and `699 build`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-699-token-verified-context-compaction` | desktop (1280x800) | PASS | Compacted 10 messages (freed 232 tokens), verified `Decisions` / `Open tasks` / `Key facts` + `/etc/orion-7/config.yaml`, `8770`, `2026-10-17`, `max_retry_budget`, verified `archive_links_count=10` and `include_archived=true`, and verified live `AutoReiv` recall in Chat (`0px` overflow) |
| `card-699-token-verified-context-compaction` | phone (390x844) | PASS | Compacted 10 messages (freed 232 tokens), verified `Decisions` / `Open tasks` / `Key facts` + `/etc/orion-7/config.yaml`, `8770`, `2026-10-17`, `max_retry_budget`, verified `archive_links_count=10` and `include_archived=true`, and verified live `AutoReiv` recall in Chat (`0px` overflow) |

Screenshots:
- `/tmp/autoreiv-qa/card-699/card-699-token-verified-context-compaction-desktop-02-compact-session-via-chat-options-button-and-veri.png`
- `/tmp/autoreiv-qa/card-699/card-699-token-verified-context-compaction-desktop-03-ask-autoreiv-in-chat-to-recall-the-preserved-tok.png`
- `/tmp/autoreiv-qa/card-699/card-699-token-verified-context-compaction-phone-03-ask-autoreiv-in-chat-to-recall-the-preserved-tok.png`

## Release note
- Added token-verified context compaction (`Decisions`, `Open tasks`, `Key facts` + path/number/identifier verification, retry/backoff, and non-destructive `archive_links`) [CARD-699].
