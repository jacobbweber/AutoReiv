# Requirements

- REQ-SDLC-030: Builtin Conductor (`id=conductor`) allowlist ONLY: list_cards, read_card, write_card, set_card_status, read_spec, write_spec, read_steering, list_project_dir, read_project_file, handoff_to_agent, lookup_agents. Pin write_card and handoff_to_agent. Deny execute_code, cli_exec, write_project_file.
- REQ-SDLC-034: `lookup_agents` / `get_builtin_profile` aliases product, plan, scrum, conductor resolve to Conductor. Chat and Forge list Conductor without a Forge save. SQLite overrides still win.
