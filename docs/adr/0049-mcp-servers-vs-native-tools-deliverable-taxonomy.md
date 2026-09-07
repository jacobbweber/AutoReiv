# ADR-0049: Model Context Protocol (MCP) Servers vs. Native Python Tools Deliverable Taxonomy

> **Date**: 2026-09-07  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, Antigravity Agent  
> **Consulted**: AutoReiv Core Architecture, Agent Training Factory  

---

## 1. Context & Problem Statement

As AutoReiv's Agent Training Factory (ATF) synthesizes capabilities for diverse specialist agents, a fundamental architectural dilemma emerges:
1. **System & Infrastructure Domains**: Agents managing hypervisors (e.g. Hyper-V), container runtimes (e.g. Docker), network appliances, or OS-level services require shell commands, PowerShell cmdlets, and native system libraries. When written as in-process Python tools, they risk cmdlet collisions (e.g. VMware PowerCLI intercepting Hyper-V cmdlets), unhandled exceptions crashing the main AutoReiv process, and host environment pollution.
2. **Local Pack Data Domains**: Agents managing private SQLite databases (e.g. Personal Finance Ledger, Task Tracker) perform fast, local, synchronous data operations. Spawning an external server process for every simple database query introduces unnecessary subprocess overhead and process management complexity.
3. **Procedural SOPs**: Neither script type solves the question of *when* and *in what order* to execute actions. Agents need structured runbooks that teach procedural workflows with progressive disclosure.

---

## 2. Decision Drivers

* **Process Isolation & Safety**: Host-mutating and infrastructure commands must run in an isolated process boundary.
* **Standardization**: Use the industry-standard Model Context Protocol (MCP) over JSON-RPC 2.0 stdio, rather than proprietary RPCs.
* **Zero Overhead for Local Data**: Keep atomic in-process Python tools for fast, private SQLite operations.
* **Progressive Disclosure**: Keep prompt tokens minimal by injecting only trigger descriptions on discovery, loading full `SKILL.md` runbooks on demand.
* **Portability**: All pack deliverables (MCP servers, native tools, skills) must live strictly inside `$DATA_DIR/packs/<agent_id>/`.

---

## 3. Decision Outcome

We establish a clear, tripartite deliverables taxonomy for the Agent Training Factory:

### 1. Agent Pack MCP Servers (`packs/<agent_id>/mcp/server.py`)
- **When Recommended**: System administration, hypervisors, virtualization, container orchestration, cloud APIs, and network management.
- **Why**: Quarantined in a dedicated background subprocess via standard JSON-RPC 2.0 `stdio`. Host cmdlet collisions, environmental variables, and third-party script crashes are completely isolated from AutoReiv.
- **Micro-Framework**: AutoReiv provides `src/infrastructure/mcp/pack_server.py`, a zero-dependency standard-library JSON-RPC MCP server base class.
- **Manifest Declaration**:
  ```json
  "mcp_server": {
    "enabled": true,
    "entrypoint": "mcp/server.py",
    "transport": "stdio"
  }
  ```

### 2. Atomic In-Process Python Tools (`packs/<agent_id>/tools/<tool_name>.py`)
- **When Recommended**: Pack-private database access (`<agent_id>_storage.db`), local text manipulation, JSON parsing, and pure calculation.
- **Why**: Zero subprocess overhead, instant synchronous execution, direct SQLite connection.

### 3. Skill Runbooks (`packs/<agent_id>/skills/<skill_id>/SKILL.md`)
- **When Recommended**: All procedural workflows.
- **Structure**:
  - YAML Frontmatter: `name` and trigger-oriented `description`.
  - 5-Section Imperative SOP: Purpose & Scope, Prerequisites & Tools, Standard Operating Procedure (Pre-flight, Input validation, Execution, Post-verification), Safety Guardrails, and Error Recovery.
- **Execution**: The agent turn reads only the frontmatter triggers; the full runbook is retrieved dynamically via `skill_view`.

---

## 4. Consequences & Benefits

### Positive Consequences
* **No Cmdlet Collisions**: Hyper-V and PowerShell tools execute in an isolated process with their own environment block.
* **Standard Interoperability**: Any MCP-compliant client or inspector can connect directly to `packs/<agent_id>/mcp/server.py`.
* **Zero Regressions**: Existing native tools (Finance SQLite, platform tools) remain untouched and performant.
* **Predictable Execution**: Skill runbooks enforce pre-flight discovery before state mutation, eliminating blind retries.

### Negative Consequences / Trade-offs
* Pack-scoped MCP servers require process lifecycle management (spawning, health-checks, clean shutdown) in `MCPClientManager`.
