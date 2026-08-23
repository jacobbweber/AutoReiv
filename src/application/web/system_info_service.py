"""
System Information & Conceptual Knowledge Hub Service [REQ-SYST-001, REQ-SYST-003].
Provides structured, educational overviews, concept breakdowns, and reference guides.
"""

from typing import Any, Dict, List, Optional


class SystemInfoService:
    """
    Curated repository of architecture overviews, conceptual hierarchies,
    skill pack manuals, and system reference guides.
    """

    def __init__(self):
        self._topics_data: Dict[str, Dict[str, Any]] = self._build_knowledge_base()

    def get_topics_index(self) -> List[Dict[str, Any]]:
        """
        Return structured categories and topics for sidebar navigation.
        """
        categories_map: Dict[str, Dict[str, Any]] = {
            "core-concepts": {
                "id": "core-concepts",
                "title": "Core Architecture & Concepts",
                "icon": "layers",
                "topics": [],
            },
            "capabilities": {
                "id": "capabilities",
                "title": "Capabilities & Tooling",
                "icon": "package",
                "topics": [],
            },
            "models-and-safety": {
                "id": "models-and-safety",
                "title": "AI Models & System Safety",
                "icon": "shield-check",
                "topics": [],
            },
        }

        for topic_id, topic in self._topics_data.items():
            cat_id = topic.get("category", "core-concepts")
            if cat_id in categories_map:
                categories_map[cat_id]["topics"].append({
                    "id": topic_id,
                    "title": topic["title"],
                    "summary": topic["summary"],
                    "icon": topic.get("icon", "file-text"),
                })

        return list(categories_map.values())

    def get_topic_content(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Return full Markdown content and metadata for a specific topic.
        """
        topic = self._topics_data.get(topic_id)
        if not topic:
            return None
        return {
            "id": topic_id,
            "title": topic["title"],
            "category": topic["category"],
            "summary": topic["summary"],
            "content": topic["content"],
        }

    def _build_knowledge_base(self) -> Dict[str, Dict[str, Any]]:
        """Build the structured knowledge base documents."""
        topics = {}

        # -------------------------------------------------------------
        # 1. Platform Overview
        # -------------------------------------------------------------
        topics["platform-overview"] = {
            "title": "Platform Overview & Architectural Tenets",
            "category": "core-concepts",
            "icon": "cpu",
            "summary": "Core philosophy, hybrid local-first design, and system topology.",
            "content": """# AutoReiv Platform Architecture & Core Tenets

AutoReiv is an enterprise-grade, **Local-First Hybrid AI Agent Control Plane & Assistant Platform**. It bridges small local LLMs (1B–8B parameter models running on consumer hardware) with frontier cloud providers through an ultra-lean, deterministic architecture.

---

## 🏛️ Core Design Principles

1. **Local-First Privacy & Autonomy**:
   - Zero external cloud dependencies required for core operations.
   - All conversation state, custom agent profiles, telemetry traces, and wiki documents are stored locally in an atomic SQLite engine.
2. **Zero-Bloat Context Management**:
   - Small models degrade rapidly when system prompts exceed 1,000 tokens.
   - AutoReiv keeps turn-0 system prompts ultralight (<350 tokens) by employing **Just-In-Time (JIT) capability discovery** and **isolated child execution contexts**.
3. **Deterministic Purpose-Based Model Cascade**:
   - Instead of locking agents to a single model, agents route to purpose-specific models (`general`, `coding`, `reasoning`, `sysadmin`) with automatic provider fallbacks.
4. **Non-Destructive Human-in-the-Loop (HITL) Controls**:
   - Autonomous execution bounded by turn limits, anti-recursion depth caps, and approval gates for high-risk operations.

---

## 🧩 High-Level System Topology

```mermaid
flowchart TD
    subgraph Client_Layer ["Client & Interface Layer"]
        UI["Web SPA Control Plane (Vanilla JS + Tailwind)"]
        CLI["Rich Terminal CLI (Interactive Chat & Server)"]
    end

    subgraph Control_Plane ["AutoReiv Control Plane (FastAPI)"]
        ChatAPI["/api/chat/stream (SSE Streaming)"]
        ForgeAPI["/api/agents (Agent Forge CRUD)"]
        RoutinesAPI["/api/routines (Background Scheduler)"]
        SettingsAPI["/api/settings (Purpose Matrix & Presets)"]
        ObsAPI["/api/observability (Sub-ms Telemetry)"]
    end

    subgraph Execution_Engine ["Agent Kernel & Orchestration"]
        Kernel["AgentKernel (ReAct Loop + Tool Dispatch)"]
        Compactor["ContextCompactor (Sliding Window + Summary)"]
        HandoffEngine["HandoffIsolationEngine (A2A Multi-Agent)"]
        PlanEngine["PlanAndExecuteEngine (Milestone DAGs)"]
    end

    subgraph Storage_Gateway ["Storage & Provider Layer"]
        SQLite[("Local SQLite State Store")]
        PARA[("PARA-Wiki Markdown Knowledge")]
        Gateway["MultiProviderGateway"]
        Ollama[("Ollama (Local Models)")]
        Cloud[("Cloud Providers (OpenAI, Claude, Groq)")]
    end

    UI <--> Control_Plane
    CLI <--> Control_Plane
    Control_Plane --> Execution_Engine
    Execution_Engine --> Storage_Gateway
    Gateway --> Ollama
    Gateway --> Cloud
```
""",
        }

        # -------------------------------------------------------------
        # 2. Concept Breakdown Hierarchy
        # -------------------------------------------------------------
        topics["concept-hierarchy"] = {
            "title": "Concept Breakdown: The 5-Tier Architecture Hierarchy",
            "category": "core-concepts",
            "icon": "layers",
            "summary": "Formal definitions and relationship between Agents, Workflows, Routines, Skill Packs, and Tools.",
            "content": """# The 5-Tier Architectural Hierarchy

To build scalable, reliable AI systems, AutoReiv strictly differentiates between **Agents**, **Workflows & Goals**, **Routines**, **Skill Packs**, and **Atomic Tools**.

---

## 📐 Conceptual Hierarchy Diagram

```mermaid
flowchart TD
    subgraph Tier1 ["Tier 1: Autonomous Personas"]
        Agent["🤖 Agent Profile (Identity, Tone, Persona, System Prompt)"]
    end

    subgraph Tier2 ["Tier 2: Execution Directives"]
        Workflow["🎯 Goal Workflow (Multi-Step Milestone DAG)"]
        Routine["⏰ Standing Routine (Cron / Interval Triggered Job)"]
    end

    subgraph Tier3 ["Tier 3: Capability Bundles"]
        SkillPack["📦 Skill Pack (Domain Capability Cluster)"]
    end

    subgraph Tier4 ["Tier 4: Schema Contracts"]
        Tool["🔧 Atomic Tool (Pydantic / JSON-RPC Function Call)"]
    end

    subgraph Tier5 ["Tier 5: Coordination"]
        Handoff["🔄 Multi-Agent Handoff (Isolated Child Context)"]
    end

    Agent --> Workflow
    Agent --> Routine
    Agent --> SkillPack
    SkillPack --> Tool
    Workflow --> Agent
    Routine --> Agent
    Agent -.-> Handoff
    Handoff -.-> Agent
```

---

## 🔍 Detailed Tier Breakdown

### 1. 🤖 Agents (Autonomous Personas)
- **What it is**: An AI persona defined by an identity, tone of voice, purpose slot, and scoped capabilities.
- **Components**: `id`, `name`, `system_prompt`, `tone` (`concise`, `technical`, `academic`, `friendly`), `purpose` (`general`, `coding`, `reasoning`, `sysadmin`), and `allowed_tools`.
- **Examples**: `general-assistant`, `linux-sysadmin`, `librarian`, `system-agent`, `auditor-critic`.

### 2. 🎯 Workflows & Goals (Multi-Step Milestone DAGs)
- **What it is**: Deterministic, multi-phase execution plans that deconstruct complex user objectives into sequential milestones.
- **How it executes**: The `PlanAndExecuteEngine` generates a 2–6 step graph, executing each step with intermediate synthesis and self-correction.
- **State**: Tracked in `ExecutionPlan` with step states (`pending`, `in_progress`, `completed`, `failed`).

### 3. ⏰ Routines (Background Scheduled Jobs)
- **What it is**: Standing background tasks triggered on cron expressions or intervals (e.g. daily at 08:00 UTC or every 15 minutes).
- **How it executes**: The background `RoutineScheduler` awakens the assigned agent, executes the directive, logs telemetry, and records the outcome.
- **Examples**: `daily-system-health-audit`, `para-wiki-index-maintenance`.

### 4. 📦 Skill Packs (Domain Capability Bundles)
- **What it is**: Logical clusters of related atomic tools representing an entire skill domain (e.g. Sysadmin, Librarian, Verification).
- **How it works**: Checked on or off in **Agent Forge**. Enabling a skill pack automatically authorizes all its underlying atomic tools.

### 5. 🔧 Atomic Tools (Schema-Validated Functions)
- **What it is**: The lowest-level executable primitives exposed to the model via JSON Schema / Function Calling contracts.
- **How it works**: Validated with Pydantic schemas, dispatched by the Kernel, and executed in safe sandboxes.

---

## 📊 Concept Comparison Matrix

| Concept | Trigger | Execution Loop | Context Lifecycle |
|---|---|---|---|
| **Agent** | User Prompt / Chat | Single or Multi-turn ReAct | Persisted in SQLite session |
| **Workflow** | Complex Goal Intent | Multi-phase Milestone DAG | Carried across milestone steps |
| **Routine** | Cron / Timer Interval | Bounded Background Turn | Ephemeral child session |
| **Skill Pack** | Configuration (Agent Forge) | N/A (Authorization Group) | Static capability declaration |
| **Atomic Tool** | Model Tool Call | Single function invocation | Injected into tool result turn |
""",
        }

        # -------------------------------------------------------------
        # 3. Skill Packs Reference
        # -------------------------------------------------------------
        topics["skill-packs-guide"] = {
            "title": "Skill Packs & Tool Catalog Reference",
            "category": "capabilities",
            "icon": "package",
            "summary": "Exhaustive documentation for all built-in Skill Packs and atomic tools.",
            "content": """# Skill Packs & Tool Catalog Reference

Skill Packs cluster individual atomic tools into intuitive capability domains. Below is the complete catalog of built-in skill packs available in AutoReiv.

---

## 📦 1. Linux Sysadmin Pack (`sysadmin`)
- **Icon**: `terminal`
- **Scope**: Operating system inspection, host metrics, process health, and safe shell command execution.
- **Atomic Tools**:
  - `cli_exec(command: str)`: Executes shell commands in a safe, working-directory-bounded subprocess.
  - `system_info()`: Retrieves CPU utilization, RAM usage, disk headroom, and OS kernel version.
  - `check_port(host: str, port: int)`: Tests TCP port reachability and socket latency.

---

## 📦 2. Librarian & Knowledge Pack (`librarian`)
- **Icon**: `book-open`
- **Scope**: PARA-Wiki note management, YAML frontmatter parsing, semantic indexing, and knowledge archiving.
- **Atomic Tools**:
  - `wiki_note_create(title: str, content: str, category: str)`: Creates path-jailed Markdown wiki documents.
  - `wiki_note_read(path: str)`: Reads Markdown notes and parses structured YAML frontmatter.
  - `wiki_note_search(query: str)`: Performs full-text keyword searches across the local knowledge base.
  - `wiki_note_list(category: str)`: Lists notes under Projects, Areas, Resources, or Archives.

---

## 📦 3. SRE Verification & Critic Pack (`verification`)
- **Icon**: `shield-check`
- **Scope**: Programmatic schema validation, regex boundary assertion, and adversarial action audits.
- **Atomic Tools**:
  - `assert_json_schema(data: dict, schema: dict)`: Validates structured payloads against JSON Schema specifications.
  - `assert_regex_match(text: str, pattern: str)`: Confirms outputs strictly conform to required regex patterns.
  - `audit_action(action_type: str, payload: dict)`: Records cryptographic compliance audits for sensitive operations.

---

## 📦 4. Planning & Goal Execution Pack (`planning`)
- **Icon**: `list-checks`
- **Scope**: Formulates, decomposes, tracks, and dynamically adjusts multi-milestone execution graphs.
- **Atomic Tools**:
  - `formulate_plan(goal: str, steps: list[str])`: Creates an ordered milestone DAG for long-running tasks.
  - `mark_plan_step_completed(step_index: int)`: Records progress on active milestones.
  - `append_plan_step(description: str)`: Dynamically inserts new milestone steps when scope expands.
  - `get_active_plan()`: Inspects current goal execution progress.

---

## 📦 5. Orchestration & Subagent Delegation Pack (`orchestration`)
- **Icon**: `network`
- **Scope**: Just-in-time peer capability discovery and isolated subagent task handoffs.
- **Atomic Tools**:
  - `lookup_agents(query: str, limit: int = 3)`: Searches the agent directory for peer specialists without prompt bloat.
  - `handoff_to_agent(target_agent_id: str, task_directive: str, input_payload: dict)`: Dispatches a subtask to an isolated specialist session.

---

## 📦 6. System Architect Meta-Builder Pack (`agent-builder`)
- **Icon**: `sparkles`
- **Scope**: Meta-tooling allowing the System Agent to inspect capabilities and construct new custom agents.
- **Atomic Tools**:
  - `list_available_skills_and_tools()`: Lists all system capabilities and tool definitions.
  - `propose_agent_specification(role: str, objective: str)`: Generates complete RPG character sheets.
  - `save_agent_specification(profile: dict)`: Validates and persists new custom agents to SQLite.
""",
        }

        # -------------------------------------------------------------
        # 4. Purpose Matrix & Models
        # -------------------------------------------------------------
        topics["purpose-matrix-and-models"] = {
            "title": "Purpose-Based Model Matrix & Hardware Sizing",
            "category": "models-and-safety",
            "icon": "cpu",
            "summary": "How purpose routing works, 3-tier model cascades, and local RAM sizing formulas.",
            "content": """# Purpose Matrix & Model Routing

AutoReiv eliminates vendor lock-in and model hardcoding through **Purpose-Based Model Routing**.

---

## 🔄 3-Tier Purpose Cascade Resolution

When an agent executes a turn, AutoReiv resolves the target model through a 3-tier cascade:

```mermaid
flowchart TD
    Start["Agent Turn Triggered"] --> Check1{"Tier 1: Explicit Agent Override?<br>(e.g. model != 'default')"}
    Check1 -- Yes --> UseExplicit["Use Agent Explicit Model Override"]
    Check1 -- No --> Check2{"Tier 2: Purpose Matrix Mapping?<br>(purpose == 'coding' / 'reasoning')"}
    Check2 -- Yes --> UseMatrix["Use Purpose Slot Model"]
    Check2 -- No --> UseGlobal["Tier 3: Use Global Default Provider Model"]
```

---

## 🎯 Model Purpose Classifications

1. **General Chat (`general`)**: Fast, conversational models (e.g. `llama3.2:3b`, `qwen2.5:3b`, `gpt-4o-mini`).
2. **Code Generation (`coding`)**: High-accuracy coding models (e.g. `qwen2.5-coder:7b`, `codellama:7b`).
3. **Reasoning & Planning (`reasoning`)**: Deep-thinking chain-of-thought models (e.g. `deepseek-r1:8b`, `o3-mini`).
4. **Sysadmin & OS Ops (`sysadmin`)**: Deterministic, tool-following models for CLI operations.

---

## 💾 Hardware Memory (RAM/VRAM) Sizing Formula

To guarantee local models run smoothly without out-of-memory (OOM) crashes, AutoReiv calculates memory requirements using:

\\[
M = P \\times \\left( \\frac{b}{8} \\right) \\times 1.25
\\]

Where:
- \\(M\\) = Estimated Memory in Gigabytes (GiB)
- \\(P\\) = Parameter count in billions (e.g. 3B, 7B, 14B)
- \\(b\\) = Quantization bits (e.g. Q4_K_M = 4.5 bits, Q8 = 8 bits, FP16 = 16 bits)
- \\(1.25\\) = 25% KV-cache and runtime inference headroom

### 📊 Sizing Reference Table

| Model Class | Parameter Count | Quantization | Est. RAM / VRAM | Sizing Classification |
|---|---|---|---|---|
| **Llama 3.2 1B** | 1.2B | Q4_K_M (4.5 bit) | **0.8 GiB** | `OPTIMAL` (Fits all systems) |
| **Qwen 2.5 3B** | 3.1B | Q4_K_M (4.5 bit) | **2.2 GiB** | `OPTIMAL` (Ultra-fast) |
| **Qwen 2.5 7B** | 7.6B | Q4_K_M (4.5 bit) | **5.4 GiB** | `RUNNABLE` (Standard 8GB+ GPU) |
| **DeepSeek-R1 8B** | 8.0B | Q4_K_M (4.5 bit) | **5.6 GiB** | `RUNNABLE` (Reasoning baseline) |
| **Qwen 2.5 14B** | 14.7B | Q4_K_M (4.5 bit) | **10.3 GiB** | `OFFLOADED` (16GB+ RAM) |
""",
        }

        # -------------------------------------------------------------
        # 5. Multi-Agent Orchestration
        # -------------------------------------------------------------
        topics["multi-agent-orchestration"] = {
            "title": "Multi-Agent Orchestration & Isolated Handoffs",
            "category": "core-concepts",
            "icon": "network",
            "summary": "Zero-bloat JIT discovery, structured HandoffEnvelopes, and anti-recursion safety.",
            "content": """# Multi-Agent Orchestration & Isolated Handoffs

AutoReiv uses a **Zero-Bloat Multi-Agent Architecture** designed specifically to keep context windows lean and eliminate hallucinations on local models.

---

## ⚡ The Zero-Bloat Principle

Traditional multi-agent systems inject full fleet rosters and dozens of tool schemas into every agent's system prompt (consuming 2,000–4,000 tokens on turn 0).

AutoReiv replaces this with **Just-In-Time (JIT) Discovery + Isolated Child Loops**:
1. Base system prompts stay under **350 tokens**.
2. Agents discover specialist peers on demand via `lookup_agents(query)`.
3. Subagents execute in private, 0-turn isolated child sessions.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operator (Chat Studio)
    participant Parent as General Assistant
    participant Dir as AgentDirectoryService
    participant Isolator as HandoffIsolationEngine
    participant Child as Isolated Linux Sysadmin

    Operator->>Parent: "Check server disk usage and free memory"
    Parent->>Dir: tool: lookup_agents("linux disk memory")
    Dir-->>Parent: [{"id": "linux-sysadmin", "name": "Linux Sysadmin"}]

    Parent->>Isolator: tool: handoff_to_agent("linux-sysadmin", "Inspect df -h and clean cache")
    Isolator->>Child: Spawns Isolated Subagent (Clean 0-turn context)
    Child->>Child: Executes 'cli_exec' and 'system_info' (<= 5 turns)
    Child-->>Isolator: Synthesizes subtask conclusion

    Isolator-->>Parent: Tool Output: "Disk freed 3.4GB, memory 64% normal"
    Parent-->>Operator: Final synthesized answer for Operator
```

---

## 🛡️ Anti-Recursion & Execution Safety

1. **Anti-Recursion Depth Cap**: Maximum delegation depth is strictly capped at **2 tiers** to prevent infinite handoff chains.
2. **Circular Deadlock Prevention**: Subagents cannot hand off back to themselves (`recipient != sender`).
3. **Turn Bounding**: Child sessions are strictly bounded to a maximum of 10 turns (default 5).
4. **Context Isolation**: Child sessions do not inherit messy parent history, preventing context pollution.
""",
        }

        # -------------------------------------------------------------
        # 6. Safety & Guardrails
        # -------------------------------------------------------------
        topics["safety-and-guardrails"] = {
            "title": "Safety, Sandboxing & Human-in-the-Loop Guardrails",
            "category": "models-and-safety",
            "icon": "shield",
            "summary": "Safe CLI execution, deterministic regex bounds, agent spec guardrails, and HITL approval gates.",
            "content": """# Safety, Sandboxing & Human-in-the-Loop (HITL)

AutoReiv employs multi-layered deterministic guardrails to ensure safe and reliable agent execution.

---

## 🛡️ 4 Layers of System Defense

```mermaid
flowchart TD
    subgraph Layer1 ["Layer 1: Input & Spec Guardrails"]
        G1["AgentProfileGuardrail (Kebab-case IDs, Bound Turns 1-50, Purpose validation)"]
    end

    subgraph Layer2 ["Layer 2: Tool Execution Sandboxing"]
        G2["Safe Subprocess Execution (Directory Jailing, Banned Command Blocks)"]
    end

    subgraph Layer3 ["Layer 3: Orchestration Guardrails"]
        G3["Anti-Recursion Depth Limits (<=2) & Circular Self-Handoff Rejection"]
    end

    subgraph Layer4 ["Layer 4: Human-in-the-Loop (HITL) Gates"]
        G4["Approval Tokens & Interactive Park/Resume State Machine"]
    end

    Layer1 --> Layer2 --> Layer3 --> Layer4
```

---

## 🔒 Specific Safety Mechanisms

1. **Deterministic Agent Specification Guardrail (`AgentProfileGuardrail`)**:
   - Rejects hallucinated tool names not in the master platform catalog.
   - Enforces kebab-case identifier naming rules (`^[a-z0-9]+(-[a-z0-9]+)*$`).
   - Caps max execution turns between 1 and 50.
2. **Path-Jailed Knowledge Base**:
   - Wiki documents and notes are strictly restricted to `data/wiki/` to prevent directory traversal attacks (`../`).
3. **Safe Subprocess Bounding**:
   - `cli_exec` executes inside workspace boundaries with configurable execution timeouts.
""",
        }

        return topics
