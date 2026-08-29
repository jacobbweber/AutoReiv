# Design

Add a profile. Reuse registry + lookup. No new engine.

## Action to route to function

1. App start -> `BUILTIN_PROFILES` includes Conductor -> `GET /api/agents` lists it.
2. Chat turn on Conductor -> kernel mounts the 11-tool allowlist. `execute_code` / `cli_exec` / `write_project_file` return not authorized.
3. Coordinator / Assistant `lookup_agents` query "plan" / "scrum" / "product" / "conductor" -> `get_builtin_profile` alias or directory score -> Conductor card.
4. Conductor `handoff_to_agent` target `coding` with one Ready card id.

## System prompt

Jacob covisions with you. You write cards and specs. You do not code. You hand off one Ready card at a time. You ask Jacob when review_rounds is at max or the idea is still Discuss.

## Out of this slice

Review builtin. Coding allowlist edits. Projects studio.
