---
name: honesty-smoke-gate
description: >-
  Use before merging a control-plane feat into qa — check honesty/stress smoke classes so Done-on-FAILED theatre cannot pass.
---

# Honesty / stress smoke merge gate (CARD-261)

Any **red** class blocks merge: `done_on_failed`, `honesty_theatre`, `silent_sse_death`.

Stress classes (informational when honesty holds): `timeout`, `gate`, `tool`, `honesty`, `kill_resume`, `pass`.

Run the project’s honesty/stress tests or scripts for CARD-261. Prefer failing closed over theatre. Checklist lives in `.agents/rules/definition-of-done.md`.
