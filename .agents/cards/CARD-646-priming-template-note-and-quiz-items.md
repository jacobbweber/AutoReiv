---
id: CARD-646
title: "Priming writes a template note and two template quiz items"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build approval
proof:
  journeys: []
  checks: []
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-646 Priming writes a template note and two template quiz items

## Intent
The priming step (`priming_schema.py`) writes the same outline for every topic and two quiz items: "In one sentence, what is <topic>?" answered with "<topic> is a durable concept learned via Priming schema (outline + prerequisites + goals) before deep detail.", and "Where should Priming write durable knowledge for <topic>?" answered with "Wiki schema/outline note and memory.db ledger anchors". Neither tests anything about the topic.

## Goal
Priming writes only content grounded in the topic and Jacob's notes (as CARD-640 does for dual coding), or records progress only.

## Plan and decisions
- Backlog: found in the CARD-641 live course run. Do not build until Jacob approves.
