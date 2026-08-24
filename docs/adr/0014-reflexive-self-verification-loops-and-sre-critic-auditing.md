# ADR-0014: Reflexive Self-Verification Loops and SRE Critic Auditing

## Status
Accepted

## Date
2026-08-23

## Context
Standard ReAct loops generate output sequentially. On complex, mutative, or diagnostic tasks (e.g. SRE platform assessments, mathematical consistency checks, file edits), models can produce hallucinations or invalid data without verifying intermediate assertions. Running verification universally on all turns introduces latency and token overhead ("Verification Tax").

## Decision Drivers
- **3-Tier Verification Hierarchy**: Apply verification selectively on mutative/diagnostic/high-stakes tasks while preserving single-turn fast paths for trivial chat.
- **Deterministic Verification Skill**: Expose programmatic assertion tools (`verify_telemetry_consistency`, `assert_json_schema`, `validate_metric_bounds`) that execute Python code for 100% ground-truth validation.
- **Reflexion Loop Engine**: Allow agents to reflect on verification failures, feeding back structured critique notes into subsequent reasoning iterations.
- **Critic Agent Profile**: Allow high-stakes diagnostics to be handed off to an independent critic agent (`auditor-critic`) using the 5-key A2A envelope.

## Decision Outcome
Adopt `ReflexionEngine`, `VerificationSkill`, and `CriticAgentProfile` within AutoReiv.

## Consequences
- **Positive**: Eliminates unverified hallucinations on high-stakes tasks; programmatic ground truth; autonomous error recovery.
- **Negative**: Adds 1-2 extra model turns when verification fails and triggers refinement.
