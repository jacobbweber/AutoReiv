---
id: CARD-702
title: "Provenance-badged search_past_chats across hot and cold sessions"
type: feature
status: Ready
priority: P2
milestone: M30
needs_decision: none
proof:
  journeys: [card-702-provenance-badged-search-past-chats]
  checks: [tests/unit/chat/test_card702_search_past_chats.py]
branch: feat/card-702-provenance-badged-search-past-chats
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-702 Provenance-badged search_past_chats across hot and cold sessions

## Intent
Adapted from `Crucible` (`ADR-0009`) and `Agent-OS` (`agent_os/recipes.py`, `agent_os/retention.py`, `docs/architecture-comparison-crucible-agent-os.md` §4 & §7.2): when the user asks about decisions or facts from earlier conversations, the companion should be able to search across active (hot) and archived/compacted (cold) chat messages with explicit provenance badges (`[Recent]` vs `[Archived]`), local dates, and a per-turn call cap (`answer_now`) so it never loops or confuses old archived chats with active instructions.

## Goal
Provide a `search_past_chats` tool and hot/cold archive retention support that searches FTS5/lexical chat history across active and archived messages, tags each match with `[Recent]` or `[Archived]` + session date, and caps searches per turn with a deterministic `"Answer now from what you have"` stop trailer.

## Change
- Add cross-session & archived message search (`search_past_chats`) excluding the current turn and prior `search_past_chats` tool outputs.
- Tag matches with `[Recent]` (active uncompacted hot session) or `[Archived]` (compacted via `archive_links` or archived session) and local-timezone date.
- Enforce a per-turn search budget (`max_searches_per_turn = 2`) and append the deterministic `answer_now` directive so the model answers immediately once matches are returned.

## What dies
- Nothing.

## Proof
- Journey `card-702-provenance-badged-search-past-chats`:
  1. Seed an earlier session with a specific project codename and decision, start a new Chat session, ask `AutoReiv` what was decided in the earlier chat, and verify `search_past_chats` is called once, returns provenance-badged matches, and `AutoReiv` cites the session date on desktop and phone.
- Checks:
  - `tests/unit/chat/test_card702_search_past_chats.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Added provenance-badged `search_past_chats` across active and archived chat sessions with per-turn search budgets [CARD-702].
