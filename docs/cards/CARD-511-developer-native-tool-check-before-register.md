---
id: CARD-511
title: "A Developer-built native tool is registered without any automatic check (Factory Verify was the only one)"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-497
  - CARD-472
labels:
  - type:product
  - area:tools
  - P2
---

# [CARD-511] Check a Developer-built native tool before it is registered

> **Status**: Ready (found in the CARD-495 audit, 2026-09-25 ET). Not next: queue is Factory retirement CARD-495, CARD-496, then this card **before CARD-497**, then CARD-497, CARD-512, CARD-498.
> **Related**: CARD-495 audit F6 and decision D6, CARD-497 (deletes `verification_battery.py` / `tool_synthesizer.py`), CARD-472 (Ask Developer)
> **Labels**: `type:product`, `area:tools`, `P2`

## Problem

The Factory's Verify phase (`agent_training_factory/phases/verify.py` with `orchestration/verification_battery.py`) is the only automatic check on generated tool code. The Developer native tool lane (`routers/native_tools.py` L61, `application/tools/native_packaging.py`) packages and registers a tool, and runs it in the sandbox only when an agent calls it. `developer_mediation.py` L375 passes `verify_checker=None`, so nothing checks the tool before it goes live. CARD-497 deletes the Factory, which removes the last check.

## Four Beats

- **Want:** when Developer builds a native tool, AutoReiv runs it once in the sandbox with a sample input before registering it, and tells the user if it fails.
- **Today:** the tool is registered without a run.
- **Change:** wire a `verify_checker` into `developer_mediation` (L375): import check plus one sandbox smoke call with the tool's example input; on failure, don't register, and show the error to Developer so it can fix and retry. Reuse whatever part of `verification_battery.py` fits; don't pull in the Factory.
- **Done when:** a broken tool (syntax error, import error, raises on the sample input) is refused with a clear message; a good tool registers as today.

## Acceptance (EARS)

- WHEN Developer submits a native tool, THE system SHALL run an import check and one sandbox call before registering it.
- IF the check fails, THEN THE system SHALL NOT register the tool and SHALL return the error text to the chat.
- THE check SHALL NOT import `agent_training_factory`.

## Tests

- Unit: good tool registers; syntax error, import error and raising tool are refused.
- Integration: native tool route with a failing tool returns the error and no registry entry.

## Runbook (scratch server)

1. Ask Developer for a tiny native tool; it registers and works in chat.
2. Ask for a deliberately broken one; the chat shows the error and the tool is not in the catalog.
