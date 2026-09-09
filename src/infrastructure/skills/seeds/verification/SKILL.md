---
name: Logic Verification (Critic)
description: JSON schema assertions, metric bounds, and action auditing.
---

# Logic Verification (Critic)

Use this runbook to validate payloads, audit agent actions, and assert structural correctness before state transitions.

## Tools

- assert_json_schema — validate data envelopes against formal JSON schemas
- validate_metric_bounds — assert numerical health thresholds, SLAs, and performance metrics
- assert_regex_match — verify string tokens, semantic versions, and output patterns
- audit_action — record verifiable audit log entries for sensitive changes
- verify_telemetry_consistency — assert telemetry counter consistency across agent sessions

## Order

1. Identify the deliverable or data payload to verify.
2. Validate structural integrity with `assert_json_schema`.
3. Check numerical constraints or SLAs with `validate_metric_bounds`.
4. Log an audit entry with `audit_action` for tracking and compliance.

## When

- Pre-flight validation before committing changes, saving agent packs, or applying system configurations.
- Auditing sensitive operations and verifying operational telemetry.

## Pitfalls

- Never bypass schema validation when ingesting external or user-supplied JSON payloads.
- Ensure bound checks account for valid edge cases (e.g. 0 retries or empty lists).

## Done-when

- All assertion checks pass cleanly with zero validation errors.
