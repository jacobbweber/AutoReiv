---
name: Write Tests
description: "Add or adjust tests that prove the card's acceptance criteria; for a bug, write the failing test first."
version: 1.0.0
tier: platform
requires_tools:
  - read_project_file
  - write_project_file
  - patch_project_file
  - run_project_checks
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "Every acceptance criterion has a test, a bug fix has a test that failed before the fix, and the fast check passes."
---

# Write Tests

Add or adjust tests that prove the card's acceptance criteria; for a bug, write the failing test first.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Steps
1. Find the project's existing tests for the area and copy their style and helpers.
2. Bug: write a test that fails for the reported reason, run it and watch it fail, then fix the code.
3. Feature: one test per acceptance criterion, named after the behaviour it proves.
4. Run the fast check until green.

## Good tests
- Test behaviour through public functions, not private details.
- No sleeps, no network, no real user data; use temp folders.
- Never weaken, skip or delete a valid assertion to go green. If a test is wrong, say why in the card.

## Done when
Every acceptance criterion has a test, a bug fix has a test that failed before the fix, and the fast check passes.
