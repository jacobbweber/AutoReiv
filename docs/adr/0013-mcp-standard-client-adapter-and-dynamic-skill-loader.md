# ADR-0013: Model Context Protocol (MCP) Client Adapter and Dynamic Skill Loader

## Status
Accepted

## Date
2026-08-23

## Context
AutoReiv previously bundled fixed, built-in Python skills. However, the AI engineering ecosystem relies heavily on:
1. **Model Context Protocol (MCP)**: Standard JSON-RPC 2.0 protocol over stdio/HTTP connecting models to external databases, devtools, browser automation, and enterprise APIs.
2. **Dynamic Skill Manuals**: Loading portable `SKILL.md` instruction files and custom tool definitions at runtime without modifying application source code.

## Decision Drivers
- **Open Standards Compliance**: Support the official Model Context Protocol 1.0 JSON-RPC stdio specification.
- **Dynamic Tool Mounting**: Expose external MCP tools seamlessly within `ScopedToolRegistry` prefixed with `mcp_<server>_<tool>`.
- **Runtime Skill Extensibility**: Enable operators to mount user-defined skill directories containing `SKILL.md` manuals and dynamic schemas.

## Decision Outcome
Adopt `MCPClientAdapter` (stdio JSON-RPC client) and `DynamicSkillLoader` (directory watcher and skill parser).

## Consequences
- **Positive**: AutoReiv can leverage any existing MCP server (e.g. GitHub, PostgreSQL, Brave Search, FileSystem) and custom local skills dynamically.
- **Negative**: Subprocess management overhead for external stdio MCP processes.
