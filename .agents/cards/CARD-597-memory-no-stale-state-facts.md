---
id: CARD-597
title: "Memory: don't save short-lived state, drop the newest-15 fallback, date facts and mark them as possibly stale"
status: In Review
created: 2026-10-01
branch: feat/card-597-memory-no-stale-state-facts
related:
  - CARD-546
  - CARD-116
  - CARD-405
labels:
  - type:bug
  - area:memory
  - area:kernel
  - P2
needs_decision: none
milestone: M24
proof:
  journeys:
    - card-597-memory-no-stale-state-facts
  checks:
    - preflight-fast
log:
  - 2026-10-01 Branch feat/card-597-memory-no-stale-state-facts created.
  - 2026-10-01 MemoryExtractor: added validator refusing short-lived transient state facts (due_today, queue counts, empty/not found results); added observed_at and expires_at.
  - 2026-10-01 AgentMemoryRepository: added observed_at and expires_at columns with schema migration; filtered out expired facts; added deactivate_short_lived_facts startup cleanup.
  - 2026-10-01 MemoryContextAssembler: removed unconditional newest-15 fallback when queries don't match; formatted facts with (seen YYYY-MM-DD); changed header to plain warning; filtered boilerplate milestones.
  - 2026-10-01 Added unit tests in test_card597_memory_no_stale_facts.py; updated test_memory_assembler.py, test_episodic_memory.py, test_agent_memory_universal_readiness.py, test_agent_memory_lifecycle_walkthrough.py.
  - 2026-10-02 Preflight fast GREEN; fixed test_card554_553_phase_handoff_tools.py binding for CARD-596 handoff decoupling.
  - 2026-10-02 Live QA: card-597-memory-no-stale-state-facts verified on desktop and phone with Spark nemotron-3.5-lightning (PASS 2/2). Status -> In Review.
---

# [CARD-597] Memory: don't save short-lived state, drop the newest-15 fallback, date facts and mark them as possibly stale

> **Status**: In Review
> **Labels**: `type:bug`, `area:memory`, `area:kernel`, `P2`

## Problem

CARD-546 (2026-09-30): after one due-review run, post-turn memory extraction stored transient runtime states such as `user.flashcard_review_due_today: false` and `system.srs_due_items_queued: false`. On subsequent turns, `MemoryContextAssembler` loaded these as undated "Recalled Relevant Facts", causing models (e.g. Tutor) to answer from stale memory without invoking required tools (e.g. `education_due_review_list`).

## Cause

1. `MemoryExtractorService.process_turn` lacked rules against short-lived or transient state, storing "due today", queue counts, and empty query results as enduring facts.
2. `AgentMemoryRepository` had no concept of observation dates or expiry timestamps on facts.
3. `MemoryContextAssembler.assemble` unconditionally fell back to injecting the newest 15 facts whenever FTS search had no match on the user prompt, guaranteeing irrelevant and stale facts were injected into every prompt.
4. Facts were rendered without observation timestamps under an authoritative header `[Agent Brain - Recalled Relevant Facts]`, leading the model to treat old state as ground truth.
5. Turns automatically created content-free episodic summaries ("Turn completed with N durable facts compiled").

## Change

1. **Extraction Hygiene:**
   - Introduced `is_short_lived_fact(entity, attribute, value)` in `src/application/memory/extractor.py` to reject transient states (`due`, `queued`, `count`, `today`, `empty`, etc.).
   - Added explicit anti-transient instructions in the extraction prompt.
   - Added `observed_at` and `expires_at` support to `CandidateMemoryFact`.
2. **Schema & Repository:**
   - Added `observed_at TEXT` and `expires_at TEXT` columns to `semantic_facts` table in `src/infrastructure/memory/repositories/agent_memory.py` with automatic schema evolution.
   - Updated `search_facts` and `list_semantic_facts` to filter out expired facts (`expires_at > current_timestamp`).
   - Added `deactivate_short_lived_facts()` method to purge existing transient state facts on startup across all `agents/*/memory.db`.
3. **Assembly & Rendering:**
   - Removed the newest-15 fallback in `MemoryContextAssembler.assemble`; an empty search returns no facts block.
   - Added ` (seen YYYY-MM-DD)` suffix to each rendered fact line.
   - Updated block header to: `"[Saved notes (may be out of date; check with tools before relying on them)]"`.
   - Filtered out boilerplate "Turn completed with N durable facts..." milestone summaries.
4. **App Startup:**
   - Hooked `deactivate_short_lived_facts()` into application startup in `src/web/app.py`.
   - Removed generation of boilerplate session summary rows in `src/web/routers/chat.py`.

## What dies

- Unconditional newest-15 fallback in `MemoryContextAssembler.assemble`.
- Legacy header `[Agent Brain - Recalled Relevant Facts]`.
- Content-free milestone rows ("Turn completed with N durable facts compiled").

## Findings

- Fixed: `tests/unit/orchestration/test_card554_553_phase_handoff_tools.py` needed an orchestration skill fixture binding after `handoff_to_agent` was removed from `REQUIRED_PLATFORM_TOOLS` in CARD-596.
- Fixed: Spark `vllm-nemotron-lightning` container was holding a 100% CPU deadlock; cleanly restarted the container and confirmed `nemotron-3.5-lightning` responded healthy.
- Fixed: Live QA throwaway environment previously lacked matrix context window settings for vLLM, defaulting to 8192 which capped thinking model reply tokens to 2048 (`8192 // 4`). Added 262k matrix and reply limits to journey run.

## Results

### Preflight Fast Tier
- `ruff check`: PASS (0 errors)
- `eslint`: PASS (0 errors)
- `pytest guard`: PASS (188 passed)
- `pytest changed tests`: PASS (39 passed)
- `pytest mapped tests`: PASS (541 passed)
- `vitest`: PASS (944 passed)
- Total time: 41 s. Result: **GREEN**.

### Live QA (`card-597-memory-no-stale-state-facts`, Spark `nemotron-3.5-lightning`, throwaway :8770)

| Journey | Viewport | Outcome | Note |
|---|---|---|---|
| card-597-memory-no-stale-state-facts | desktop | PASS | Turn 1: `education_due_review_list`, Turn 2: `education_due_review_list` |
| card-597-memory-no-stale-state-facts | phone | PASS | Turn 1: `education_due_review_list`, Turn 2: `education_due_review_list` |

Screenshots:
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-597\card-597-memory-no-stale-state-facts-desktop-01-turn-1-tutor-due-review-checks-live-queue-with-t.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-597\card-597-memory-no-stale-state-facts-desktop-02-turn-2-in-a-new-chat-tutor-again-checks-live-que.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-597\card-597-memory-no-stale-state-facts-phone-01-turn-1-tutor-due-review-checks-live-queue-with-t.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-597\card-597-memory-no-stale-state-facts-phone-02-turn-2-in-a-new-chat-tutor-again-checks-live-que.png`

## Release note

Memory extraction no longer records short-lived runtime state (such as due flashcards, queue counts, or empty queries) as durable facts. Facts now track observation and expiration dates, the newest-15 fallback injection is removed, and recalled notes are clearly marked with their seen date and a warning to verify live state with tools before relying on them.
