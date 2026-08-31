---
name: Session inspect
description: Transcripts, agent sessions, usage, session artifacts, and batch worker scans.
---

# Session inspect

Look at what agents actually did: transcripts, session lists, usage, artifacts, batch scans.

## Order

1. `get_agent_sessions` / `get_agent_usage_summary` to find the run.
2. `get_session_transcript` for the turn-by-turn record.
3. `get_session_artifact` when the run stored a file.
4. `batch_worker_scan` for large partitioned reads.

## Pitfalls

- Do not paste secrets from transcripts into Wiki or Chat unless the user asked.
- Promoting an artifact into Wiki is the Platform `wiki` skill (`promote_artifact_to_wiki`).

## Done-when

- The user has the session facts they asked for, with ids they can reuse.
