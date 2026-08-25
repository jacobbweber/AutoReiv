# ADR-0042: SQLite Episodic Fact Store and Agent Auto Recall

## Context and Problem Statement
Autonomous agents across multi-turn sessions need to persist and recall cross-session facts (e.g. user preferences, environment configurations, deployment targets). Previously, facts were stored in `episodic_facts` but required manual tool calls by agents, resulting in lack of automatic contextual awareness.

## Decision Drivers
- **Tokenized Substring Search**: Enable keyword matching across `entity`, `key`, and `value` fields with confidence threshold filtering.
- **Dynamic Auto-Recall Injection**: Transparently enrich `AgentKernel` system instructions with relevant recalled facts (`[Episodic Memory - Recalled Facts]`) matching the incoming user prompt.
- **REST API Governance**: Expose `/api/memory/facts` endpoints (`GET`, `POST`, `DELETE`) for administrative inspection and programmatic memory management.

## Considered Options
1. **Option 1**: Require agents to always call `search_facts` tool manually during turn execution (adds turn latency and tool call overhead).
2. **Option 2 (Accepted)**: Automated pre-execution factual recall in `AgentKernel` combined with REST API endpoints and manual agent tool functions.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Zero-latency contextual recall for frequently referenced user and environment facts.
- Clean separation between working session memory and long-term episodic facts.
- 4 comprehensive unit/integration tests in `tests/unit/memory/test_episodic_memory.py`.

### Negative Consequences / Trade-offs
- Slight increase in system prompt token count when relevant facts match user keywords.
