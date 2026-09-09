---
name: Batch Worker & Artifacts
description: Parallel batch worker scans and session artifact retrieval.
---

# Batch Worker & Artifacts

Use this runbook to manage background batch workloads, collect artifact deliverables, and process batch queues.

## Tools

- batch_worker_scan — scan and retrieve status across ongoing batch tasks and workers
- get_session_artifact — inspect generated session files, data snapshots, and reports

## Order

1. Trigger or identify target batch tasks or background jobs.
2. Poll and inspect job status and completion metrics with `batch_worker_scan`.
3. Retrieve resulting deliverable files or data snapshots using `get_session_artifact`.
4. Present verified deliverables to the operator.

## When

- Long-running batch operations or multi-file processing pipelines.
- Verifying deliverables generated during training or automation runs.

## Pitfalls

- Do not poll batch status in tight synchronous loops; allow appropriate backoff.
- Ensure retrieved artifact IDs match the current session context.

## Done-when

- Batch scan reports 100% completion and generated artifacts are successfully loaded.
