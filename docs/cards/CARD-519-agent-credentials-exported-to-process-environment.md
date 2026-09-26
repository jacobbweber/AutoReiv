---
id: CARD-519
title: "Agent credentials are exported to the whole server process during every tool call, so other agents' tools can read them"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-511
  - CARD-423
labels:
  - type:bug
  - area:tools
  - area:security
  - P2
---

# [CARD-519] Agent credentials leak into the process environment during tool calls

> **Status**: Ready (found while building CARD-511, 2026-09-26 ~2:30 AM ET, branch `feat/card-511-tool-check`). Not recommended as next by the queue rule (it does not damage data or block current work), but it is a real cross-agent secret leak on a shared server, so Jacob may want it soon after CARD-511. The CARD-511 tool check already strips these variables from its own sandbox.
> **Related**: CARD-511 (`tool_check.py` passes `drop_env_prefixes=("AUTOREIV_CRED_",)`), CARD-423 (native tools run in `sandbox_worker`)
> **Labels**: `type:bug`, `area:tools`, `area:security`, `P2`

## Problem

`ScopedToolRegistry.execute` (`src/application/kernel/tool_registry.py` L190-221) writes each of the calling agent's allowed credentials into the **process-global** `os.environ` as `AUTOREIV_CRED_<ID>` for the whole tool call, then removes them in `finally`. While that call runs:

- Any other tool call in the same server process (another agent, another chat, a routine) sees the variables in `os.environ`.
- Native custom tools run through `SandboxWorker.run_sandboxed`, whose `sanitize_environment` (`sandbox_worker.py` L56-79) drops keys containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `AUTH` or `CREDENTIAL`. `AUTOREIV_CRED_<ID>` contains none of those unless the credential id happens to, so the secret is **passed into the subprocess** of any native tool that starts during the window, including tools from agents that were never granted that credential.
- If the variable already exists (two calls from agents sharing a credential id), it is not overwritten and not removed by the second call, so the timing is harder to reason about.

The credentials are also already passed properly through the tool context (`_tool_context["credentials"]`), which is per-task.

## Change

Stop writing credentials to `os.environ`. Give a tool its own agent's credentials explicitly: the context value that already exists, and, for sandboxed native tools, an `env_overrides` built from that context for that one subprocess. Add `CRED_` (or the `AUTOREIV_CRED_` prefix) to the sanitizer. Check which tools, if any, read `AUTOREIV_CRED_*` from the environment today (rg) and move them to the context.

## Done when

- A test runs two concurrent tool calls from agents with different credentials and shows neither can see the other's secret (in `os.environ` or in a native tool's subprocess environment).
- `sanitize_environment` drops `AUTOREIV_CRED_*` by default.
- A native tool granted a credential still receives it.
