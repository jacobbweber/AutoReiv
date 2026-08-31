---
name: Alignment
description: Diff vs locked intent including UI-to-code. Mushy card goes to Conductor.
---

# Alignment

Does the diff match what was locked, including a UI click to the function?

## Order

1. `read_card` and `read_spec` for locked intent.
2. `git_diff` (and file reads) for what actually changed.
3. If the card is still mushy, hand off to Conductor.
4. If the code missed locked intent, hand off to Coding with a concrete list (including UI-to-code misses).

## Pitfalls

- Do not write product files.
- Do not "improve" beyond the locked intent.

## Done-when

- Diff matches locked intent, or a concrete miss list is in the handoff.
