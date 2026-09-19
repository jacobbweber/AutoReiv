# Design

`AgentKernel._resolve_active_tools` returns `tool_registry.get_tools_for_agent(agent)`.
Assistant `pinned_tool_names` is `handoff_to_agent`, `lookup_agents`.
Forge continues to use `tool_reg.list_tools()` for the human catalog.
