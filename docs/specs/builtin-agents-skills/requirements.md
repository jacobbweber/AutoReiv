# Requirements Specification: Built-in Agents & Scoped Skills

> **Spec Status**: Implemented  
> **Target Release**: Milestone 3 (v0.3.0)  
> **Primary Component**: `AutoReiv.Agents`, `AutoReiv.Skills`  
> **Applicable ADRs**: `docs/adr/0004-built-in-agent-manifests-and-standard-scoped-skills.md`

---

## 1. Executive Summary & Intent

Milestone 3 implements the 4 Day-1 built-in agent profiles (**General Assistant**, **Linux Sysadmin**, **Librarian**, **System Agent**) along with their dedicated, scoped skill implementations. It binds each agent strictly to its authorized tool catalog, allowing them to track user tasks, inspect host hardware, manage markdown documents with YAML frontmatter, and analyze system telemetry.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-AGENTS-001]: Built-in 4 Agent Manifests
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL define and register default agent profiles for 'general-assistant', 'linux-sysadmin', 'librarian', and 'system-agent' with tailored personas, tones, and scoped tool permissions.`
- **Acceptance Criteria**:
  - [ ] Given `BuiltinAgentRegistry`, when queried for agents, then it provides all 4 validated `AgentProfile` instances.
  - [ ] Given each profile, then `allowed_tool_names` contains only the tools authorized for that agent's domain.

### [REQ-AGENTS-002]: Task Tracker Skill (General Assistant)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent requests task operations (create, list, update, complete, delete) THE SYSTEM SHALL manage persistent task records in SQLite with status, priority, and timestamps.`
- **Acceptance Criteria**:
  - [ ] Given `create_task(title, priority="medium", due_date=None)`, when invoked, then a new task is persisted with status `"pending"`.
  - [ ] Given `list_tasks(status="pending")`, when invoked, then it returns matching active tasks ordered by priority and date.
  - [ ] Given `update_task_status(task_id, status="completed")`, when invoked, then the task is updated in SQLite.

### [REQ-AGENTS-003]: System Info & Inspection Skill (Linux Sysadmin)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent invokes system inspection THE SYSTEM SHALL collect host platform, CPU core count, memory utilization (total, available, used), disk capacity, and uptime.`
- **Acceptance Criteria**:
  - [ ] Given `get_system_info()`, when invoked, then it returns a structured payload containing OS name, architecture, CPU load/cores, RAM in GB/MB, disk usage, and host timestamp.
  - [ ] Given execution on Linux, Windows, or macOS, when executed, then it falls back gracefully to standard library / OS metrics without crashing.

### [REQ-AGENTS-004]: Safe CLI Command Execution Skill (Linux Sysadmin)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an authorized agent executes a shell command THE SYSTEM SHALL execute the command asynchronously with a strict timeout and maximum output buffer.`
- **Acceptance Criteria**:
  - [ ] Given `run_command(command="uname -a")`, when executed, then it returns `exit_code`, `stdout`, `stderr`, and `duration_ms`.
  - [ ] Given a command exceeding timeout (default 30s), when executed, then the process is terminated and returns a timeout error.

### [REQ-AGENTS-005]: YAML Frontmatter & PARA-Wiki Document Skill (Librarian)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN managing markdown documents THE SYSTEM SHALL parse, format, validate, and write files with structured YAML frontmatter (title, tags, date, status, category).`
- **Acceptance Criteria**:
  - [ ] Given markdown text with YAML frontmatter `--- title: Notes\ncategory: Projects --- Body text`, when `parse_frontmatter()` is called, then it separates frontmatter dictionary from markdown body.
  - [ ] Given `create_wiki_note(relative_path, title, category, tags, content)`, when invoked, then it formats valid YAML frontmatter and writes the file inside the configured Wiki root directory.
  - [ ] Given an attempt to write outside the wiki root (path traversal `../`), when detected, then it denies the operation.

### [REQ-AGENTS-006]: Telemetry Inspector & Health Check Skill (System Agent)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN inspecting platform health THE SYSTEM SHALL evaluate database connectivity, telemetry token totals, error rates, and per-agent activity.`
- **Acceptance Criteria**:
  - [ ] Given `inspect_system_health()`, when invoked, then it returns database status, total turns recorded, total tokens consumed, and global error rate.
  - [ ] Given `get_agent_usage_summary(agent_id=None)`, when invoked, then it returns per-agent token breakdown.

---

## 3. Non-Functional & Boundary Constraints

- **Zero Path Traversal**: The Wiki document skill must sanitize and jail all file writes to the configured Wiki base path.
- **Hermetic Testing**: Unit tests run against temporary directories and in-memory SQLite tables.
- **Process Isolation**: CLI runner uses `asyncio.create_subprocess_exec` with timeouts to prevent zombie processes.

---

## 4. Out of Scope

- Live background cron scheduler (Milestone 4).
- Web frontend UI views (Milestone 7).
