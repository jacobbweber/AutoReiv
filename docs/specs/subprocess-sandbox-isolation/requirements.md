# Requirements Specification: Ephemeral Subprocess Execution Sandbox & Process Isolation

> **Spec Status**: Approved  
> **Target Release**: Milestone 13 (v0.13.0)  
> **Card Reference**: [CARD-044](file:///.github/cards/CARD-044-ephemeral-subprocess-execution-sandbox-and-process-isolation.md)  

> **Primary Component**: AutoReiv Skills & Infrastructure (`src/application/skills/sandbox_worker.py`, `src/application/skills/sandbox_skill.py`)

---

## 1. Executive Summary & Intent

**CARD-044** enhances `SandboxedSubprocessWorker` with input file provisioning, output artifact collection, environment variable secret sanitization, output stream byte capping, and exposes a high-level `SandboxExecutionSkill` agent tool.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-SANDBOX-001] Ephemeral File Workspace Provisioning & Output Artifact Extraction
- **EARS Pattern**: Ubiquitous
- **Requirement**: The `SandboxedSubprocessWorker` **shall** write provided input files (`files: Dict[str, str]`) into the ephemeral temporary directory prior to subprocess execution, and extract requested output file paths (`read_outputs: List[str]`) after execution completes before hermetic directory deletion.

### [REQ-SANDBOX-002] Sensitive Environment Secret Scrubbing & Output Stream Capping
- **EARS Pattern**: Ubiquitous
- **Requirement**: The `SandboxedSubprocessWorker` **shall** scrub execution environments of sensitive keys matching patterns (`*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`) unless explicitly overridden, and cap stdout/stderr streams to `max_output_bytes` (default 1MB) with truncation indicators.

### [REQ-SANDBOX-003] Sandbox Execution Agent Skill & Tool Registration
- **EARS Pattern**: Event-Driven
- **Requirement**: When registered in `ScopedToolRegistry`, the `SandboxExecutionSkill` **shall** expose `execute_code(language, code, timeout_seconds, files)` supporting Python and Shell code execution with structured JSON status outputs.

### [REQ-SANDBOX-004] Comprehensive Sandbox Unit & Integration Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify file provisioning, output artifact extraction, environment variable sanitization, timeout killing, and tool registry execution with 100% passing tests.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `run_sandboxed` creates files before execution and reads requested outputs before teardown.
- [ ] `AC-2`: Sensitive host env vars (`OPENAI_API_KEY`, `GITHUB_TOKEN`, etc.) are not accessible by child processes.
- [ ] `AC-3`: Outputs $> 1\text{MB}$ are truncated cleanly without crashing memory.
- [ ] `AC-4`: `SandboxExecutionSkill` executes valid code and catches syntax/runtime errors.
- [ ] `AC-5`: `npm run preflight` passes all 6 quality gates cleanly.
