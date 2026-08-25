# ADR-0045: Dangerous Command Safety Guardrails & Path Traversal Protection

## Context
Agent reasoning routines and autonomous tools may synthesize shell or script commands. Execution of untrusted or hallucinatory commands presents risks of catastrophic host filesystem deletion (`rm -rf /`), disk formatting, host shutdown, fork bombs, pipe-to-shell payload execution, or workspace path escapes.

## Decision
1. **Deterministic Safety Model & Rule IDs**:
   - Introduced `RiskLevel` (`SAFE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `SafetyViolation`, and `CommandSafetyReport` domain models.
2. **Command Guardrail Engine**:
   - Implemented `CommandGuardrail.evaluate` evaluating pattern matches across destructive wipes, disk tools, fork bombs, remote pipe execution, and deep path traversal (`../../../`).
3. **Pre-Flight Subprocess Interception**:
   - Wired `CommandGuardrail.evaluate` directly into `SandboxedSubprocessWorker.run_sandboxed` to abort dangerous commands before spawning any child process.

## Status
Accepted

## Consequences
- **Positive**: Hard deterministic boundary against destructive commands and out-of-bounds workspace escapes with zero runtime LLM latency.
- **Negative**: Extremely complex or obfuscated shell syntax (e.g. base64-encoded strings decoded at runtime) requires additional sandbox isolation.
