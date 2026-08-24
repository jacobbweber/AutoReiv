# [CARD-003] Built-In Agents & Specialized Skills

> **Status**: Completed (Merged to `qa`)  
> **Milestone**: Milestone 3 (v0.3.0)  
> **Primary Component**: `AutoReiv.Agents` & `AutoReiv.Skills`  
> **Spec Reference**: `docs/specs/builtin-agents-and-scoped-skills/`  
> **ADR Reference**: [`docs/adr/0004-builtin-agents-and-scoped-skill-architecture.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0004-builtin-agents-and-scoped-skill-architecture.md)  
> **Requirements**: `[REQ-AGENT-001]` to `[REQ-AGENT-006]`

---

## 1. Why / Intent
AutoReiv ships on Day 1 with 4 specialized personas equipped with domain-specific skills:
1. **General Assistant**: Daily workflow coordinator with task tracking.
2. **Linux Sysadmin**: Host server engineer with safe command execution and system telemetry.
3. **Librarian**: Technical writer and PARA-Wiki documentation manager with YAML frontmatter management.
4. **System Agent**: SRE and telemetry analyzer maintaining platform health.

---

## 2. What Was Built
- **`TaskTrackerSkill`**: Scoped SQLite CRUD for tasks (`create`, `list`, `update`, `delete`).
- **`SysadminSkill`**: Safe host inspection (`system_info`, CPU/RAM metrics) and command execution with timeout/sandboxing.
- **`LibrarianSkill`**: Strict YAML frontmatter parsing/validation and PARA-Wiki markdown document management with path jailing.
- **`SystemAgentSkill`**: Platform health monitoring and telemetry inspection.
- **`BuiltinAgentRegistry`**: Automated bootstrap wiring all 4 agents and tool bindings.

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-AGENT-001]`: General Assistant task management verified.
- [x] `[REQ-AGENT-002]`: Linux Sysadmin host inspection verified.
- [x] `[REQ-AGENT-003]`: Librarian YAML frontmatter parsing and note management verified.
- [x] `[REQ-AGENT-004]`: System Agent SRE diagnostics verified.
- [x] `[REQ-AGENT-005]`: Automated unit test suite passing (`tests/unit/agents/`, `tests/unit/skills/`).
- [x] `[REQ-AGENT-006]`: 100% RTM traceability compliance.
