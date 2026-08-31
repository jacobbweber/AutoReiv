# Requirements

- REQ-SDLC-006: Bounce-back is `set_card_status` plus existing `handoff_to_agent`. No second workflow engine. Conductor hands Returned cards back to Coding while review_rounds < max; at max Conductor asks Jacob.
- REQ-SDLC-033: Coding may `set_card_status` In Progress -> In Review only. Coding is granted read_card, read_spec, set_card_status, list_project_dir, read_project_file, write_project_file. Wiki reads are dropped so the allowlist stays under 12.
