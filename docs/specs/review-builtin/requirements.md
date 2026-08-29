# Requirements

- REQ-SDLC-031: Builtin Review (`id=review`) allowlist ONLY: list_cards, read_card, read_spec, read_steering, list_project_dir, read_project_file, set_card_status, handoff_to_agent, lookup_agents. Pin set_card_status. Deny execute_code, write_card, write_spec, write_project_file, cli_exec.
- REQ-SDLC-035: Aliases qa, tester, review resolve to Review. From In Review, Review can set Done or Returned (Returned requires return_reason).
