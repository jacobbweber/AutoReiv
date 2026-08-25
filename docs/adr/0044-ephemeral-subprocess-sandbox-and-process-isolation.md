# ADR-0044: Ephemeral Subprocess Sandbox & Process Isolation

## Context
Agents need the capability to test, validate, and execute Python and shell scripts without compromising the host environment, persisting temporary clutter, exposing environment secrets, or consuming unbounded resources.

## Decision
1. **Isolated Ephemeral Workspaces**:
   - `SandboxedSubprocessWorker.run_sandboxed` provisions input files into a fresh `tempfile.mkdtemp` scratch workspace and safely collects requested output artifacts prior to hermetic directory destruction.
2. **Environment Sanitization & Secret Scrubbing**:
   - Scrub sensitive environment variables containing `*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `*AUTH*`, `*CREDENTIAL*`, or `*PRIVATE*`, maintaining only essential system execution paths.
3. **Stream Capping & Timeout Enforcement**:
   - Enforce hard execution timeouts with process killing and stream capping at `max_output_bytes = 1MB` to prevent memory exhaustion.
4. **Agent Skill Exposure**:
   - Packaged `SandboxExecutionSkill` exposing the `execute_code` tool for registration in `ScopedToolRegistry`.

## Status
Accepted

## Consequences
- **Positive**: Zero secret leakage to child processes, clean filesystem hygiene, memory-safe output capture, and standardized agent tool integration.
- **Negative**: Subprocess startup carries minimal Python interpreter startup overhead.
