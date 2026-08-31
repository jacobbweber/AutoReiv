# Requirements

- REQ-SDLC-060: Tools `git_status`, `git_diff`, `git_branch`, `git_commit` run git in `project_root` only. `git_commit` subject must match `feat|fix|docs|chore|test|refactor(scope): ...`. Refuse `git config`, `--no-verify`, force, and amend.
- REQ-SDLC-061: `git_commit` is high-risk HITL. Coding allowlist includes the four git tools plus read_card, read_spec, set_card_status, list_project_dir, read_project_file, write_project_file, execute_code, handoff_to_agent (12 tools). No push tool.
