---
id: CARD-597
title: "Memory: don't save short-lived state, drop the newest-15 fallback, date facts and mark them as possibly stale"
status: Ready
created: 2026-10-01
branch: qa
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
---

# [CARD-597] Memory: don't save short-lived state, drop the newest-15 fallback, date facts and mark them as possibly stale

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:bug`, `area:memory`, `area:kernel`, `P2`

## Why

CARD-546 (2026-09-30): after one due-review run, post-turn extraction stored `user.flashcard_review_due_today: false` and `system.srs_due_items_queued: false`. Later turns were given these as undated "Recalled Relevant Facts" and replied from them with no tools (1/10 vs 2/10 with a fresh env).

## What happens today (qa `ad2e994f`)

- **Extraction:** `chat._background_extract_turn_memory` → `MemoryExtractorService.process_turn` runs after every turn.
  - The prompt (`memory/extractor.py build_extraction_prompt`) asks for "enduring facts" but has no notion of short-lived state, dates or expiry.
- **Injection** (`AgentKernel._build_effective_system_message`):
  1. `state_store.search_facts`: top 4.
  2. `MemoryContextAssembler.assemble`, "broad" tier at 262k: pinned items, 3 episodic milestones, and 15 facts. Facts are an FTS match on the user text; **with no match, the newest 15 go in regardless of relevance** (`assembler.py` line 107).
  - Facts render as `entity.attribute: value` with no date.
  - Milestones carry no content ("Turn completed with 5 durable facts compiled").

## Scope

1. **Extractor:**
   - Do not store short-lived state: today/now flags, queue or due counts, "not found / empty" results, current status.
   - Keep preferences, environment, constraints and decisions.
   - If state must be kept, store it with `observed_at` and an expiry (for example 24 h), and never inject it after expiry.
2. **Assembler:** remove the "newest N" fallback; no match means no facts block.
3. **Rendering:**
   - Each fact shows its date (`(seen 2026-09-30)`).
   - The block header says plainly: "Saved notes (may be out of date; check with tools before relying on them)".
4. **Drop content-free milestones**, or replace them with a one-line summary of what was done.
5. **Migration:** on startup, deactivate stored facts that match the short-lived patterns (logged count).

## Out of scope

Agent scopes (CARD-596), new memory stores, embeddings.

## Acceptance criteria

- **Unit:** a turn whose reply says "no flashcards are due today" stores no fact. A stored preference still is.
- **Unit:** with a query that matches nothing, the assembled block has no facts section.
- **Unit:** the rendered facts carry a date, and the header has the "may be out of date" wording.
- **Live** (throwaway :8770, nemotron): run the CARD-546 due-review prompt to Tutor twice in one env. The second run checks the live due queue with tools and does not answer from memory.
- Fast preflight is green.
