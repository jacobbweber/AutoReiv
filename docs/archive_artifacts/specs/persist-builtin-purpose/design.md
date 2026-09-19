# Design

`AgentCustomization` gains `purpose`. Builtin `PUT /api/agents/{id}` stores it. `BuiltinAgentRegistry.get_agent` applies `ModelPurpose(override.purpose)` when the value is valid.
