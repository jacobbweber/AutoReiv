---
name: Session inspect
description: Search past chats across hot and archived sessions, read transcripts, list agent sessions, usage, and session artifacts.
tools:
- search_past_chats
- get_session_transcript
- get_agent_sessions
- get_agent_usage_summary
---

# Session inspect

Look at what agents and the operator discussed or did: provenance-badged past-chat search (`[Recent]` vs `[Archived]`), transcripts, session lists, usage, artifacts, batch scans.

## Order

1. `search_past_chats` when the user asks what was decided or discussed in earlier chats (cites `[Recent]` or `[Archived]` + session date; stops after 1-2 searches).
2. `get_agent_sessions` / `get_agent_usage_summary` to find the run.
3. `get_session_transcript` for the turn-by-turn record.
4. `get_session_artifact` when the run stored a file.
5. `batch_worker_scan` for large partitioned reads.

## Pitfalls

- Do not paste secrets from transcripts into Wiki or Chat unless the user asked.
- Promoting an artifact into Wiki is the Platform `wiki` skill (`promote_artifact_to_wiki`).

## Done-when

- The user has the session facts they asked for, with ids and dates they can reuse.
