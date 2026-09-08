# ADR 0050: Single Platform Developer Agent and SDLC Consolidation

- **Status**: Accepted
- **Date**: 2026-09-07
- **Deciders**: Jacob Weber, Antigravity AI Agent
- **Consulted**: Anthropic AI-Native SDLC Playbook
- **Informed**: AutoReiv Contributors

## Context & Problem Statement

In CARD-124, AutoReiv established an SDLC specialist trio (`conductor`, `coding`, `review`) that used multi-agent handoffs to manage software development tasks. In practice, this handoff relay introduced significant latency, nuance and conversation loss through serialized handoffs, and unnecessary complexity. 

With the emergence of single-agent Plan Mode, autonomous Auto Mode, and automated Reflexion / verification loops (CARD-179), a single engineer persona can explore the codebase, plan changes, implement code via TDD, execute multi-language tests, and self-correct errors in a continuous context window without requiring external reviewer personas.

## Decision Drivers

1. **Eliminate Handoff Latency & Context Starvation**: Single-agent execution preserves rich conversation nuances and conversation history.
2. **First-Class Platform Capability**: Software engineering is a core capability of AutoReiv; development capabilities must be available out of the box without manual pack imports.
3. **Multi-Language Test Execution**: Need for real test and linter execution across PowerShell (Pester, PSScriptAnalyzer), Python (pytest, ruff), and TypeScript (vitest) via `cli_exec`.
4. **Information Architecture Alignment**: Cards track backlog/lifecycle; Specs in `docs/specs/` track permanent engineering blueprints; ADRs in `docs/adr/` track global architectural decisions.

## Considered Options

1. **Option A: Multi-Agent Trio (Conductor $\rightarrow$ Coding $\rightarrow$ Review)**: Continue passing tasks between three specialized agents.
2. **Option B: Unified Platform Developer Agent (Selected)**: Seed a first-class `developer` agent with three modular skills (`plan`, `build`, `test`), a full engineering toolset (`read_project_file`, `write_project_file`, `cli_exec`, `execute_code`, git tools, card tools), and retire the legacy trio from active catalog and chat pickers.

## Decision Outcome

Chosen Option: **Option B**.
AutoReiv ships with a built-in `platform-packs/developer` pack seeded into `$DATA_DIR/packs/developer/` on startup. Developer is equipped with three modular skills (`plan`, `build`, `test`) and the unified engineering toolset. Legacy personas `conductor`, `coding`, and `review` are retired from the active catalog and hidden from chat pickers.

### Consequences

- **Positive**:
  - Immediate software engineering capability out of the box.
  - Faster development turns with zero handoff latency.
  - Multi-language support through host shell execution via `cli_exec`.
  - Clean, uncluttered Chat and Agent Studio interfaces.
- **Negative / Neutral**:
  - Deprecated legacy packs (`conductor`) are retired and hidden from chat.
