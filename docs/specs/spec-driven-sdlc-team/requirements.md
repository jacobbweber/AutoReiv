# Requirements

Program: Spec-Driven SDLC Team. Jacob talks only to Conductor. Wiki stays knowledge. Projects are a separate studio.

## Loop

- REQ-SDLC-001: Idea starts as a card in `Discuss`. No implementation in Discuss.
- REQ-SDLC-002: `Ready` requires a card plus a spec directory that exists (`docs/specs/<slug>/` with at least one of `requirements.md`, `design.md`, `tasks.md`).
- REQ-SDLC-003: Conductor hands off one Ready card at a time to Coding via existing `handoff_to_agent`.
- REQ-SDLC-004: Coding implements against that spec, then `set_card_status` to `In Review` and stops.
- REQ-SDLC-005: Review reads spec plus result. Pass -> `Done`. Fail -> `Returned` with `return_reason`, `review_rounds++`.
- REQ-SDLC-006: If `review_rounds` < `max_review_rounds` (default 3), Conductor hands the same card back to Coding. At max, Conductor asks Jacob. Do not invent a second HITL or workflow engine.
- REQ-SDLC-007: Reuse `handoff_to_agent`, `lookup_agents`, Goal Mode plan gate, self-verify, and existing HITL park. No second approval engine.

## Statuses and state machine

Statuses: `Discuss` | `Ready` | `In Progress` | `In Review` | `Returned` | `Done`.

Legal transitions:

- Discuss -> Ready (only if spec path exists) or stay Discuss
- Ready -> In Progress
- In Progress -> In Review
- In Review -> Done | Returned (Returned stores `return_reason`, increments `review_rounds`)
- Returned -> In Progress only if `review_rounds` < `max_review_rounds` (default 3)
- Returned at max: `set_card_status` to In Progress is denied; tool tells the caller to ask the operator

- REQ-SDLC-010: `set_card_status` enforces the table above. Illegal transitions fail with a clear error.
- REQ-SDLC-011: Card frontmatter includes Status, Spec Reference, `review_rounds`, `max_review_rounds`, `return_reason`, optional `github_issue`.
- REQ-SDLC-012: Card files live at `{project_root}/.github/cards/CARD-NNN-*.md`. Specs live at `{project_root}/docs/specs/<slug>/`.

## Tools (public names)

Until Projects (CARD-085), tools accept optional `project_root` and default to the AutoReiv checkout for self-host tests. After 085, omitted `project_root` uses the selected project.

Card / spec / steering (CARD-080), one skill:

- `list_cards`
- `read_card` / `write_card`
- `set_card_status`
- `read_spec` / `write_spec`
- `read_steering` (AGENTS.md and optional `.agents` / `.github` rules; path + excerpt or sections, not a huge dump)

Project files (CARD-081):

- `list_project_dir`
- `read_project_file`
- `write_project_file`

Git (CARD-087):

- `git_status`
- `git_diff`
- `git_branch`
- `git_commit` (conventional subject; refuse `git config`, `--no-verify`, force; no push this program)

GitHub issues (CARD-088):

- `sync_card_issue` (uses `gh` if present; clear error if missing; no invented tokens; no GitHub MCP)

Projects (CARD-085 / CARD-086):

- Settings `projects_root` (filesystem path; default empty + placeholder, do not hardcode only `D:\\Projects\\Active`)
- Studio: list / create / open (select) / delete (HITL / UI confirm)
- `create_project` copies `templates/sdlc-project/` into `projects_root/<slug>`

- REQ-SDLC-020: Mutating tools park in existing ask-mode HITL: `write_card`, `write_spec`, `set_card_status`, `write_project_file`, `git_commit`, `sync_card_issue` (create/update), project delete / `create_project`.
- REQ-SDLC-021: All project-scoped paths resolve under `project_root` (later the selected project). Reject `..` escapes and absolute paths outside the root.

## Allowlists (keep under ~12; Forge warns at 12)

- REQ-SDLC-030: Conductor (`id=conductor`) allowlist ONLY: `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering`, `list_project_dir`, `read_project_file`, `handoff_to_agent`, `lookup_agents`. Pin: `write_card`, `handoff_to_agent`. NO `execute_code`, `cli_exec`, `write_project_file`, git write.
- REQ-SDLC-031: Review (`id=review`) allowlist ONLY: `list_cards`, `read_card`, `read_spec`, `read_steering`, `list_project_dir`, `read_project_file`, `set_card_status`, `handoff_to_agent`, `lookup_agents`. Pin: `set_card_status`. NO `execute_code`, `write_card`, `write_spec`, `write_project_file`, `cli_exec`.
- REQ-SDLC-032: Assistant and AutoReiv do not receive `execute_code`. Conductor and Review do not receive `execute_code` or `cli_exec`.
- REQ-SDLC-033: Coding may `set_card_status` In Progress -> In Review only. After CARD-087, Coding allowlist stays <= 12: drop wiki reads if needed. Include git + card read + file read/write + `set_card_status` + `handoff_to_agent` (+ `lookup_agents` or `execute_code` as the 12th, not both if that exceeds 12).

## GitHub label map (CARD-088)

- REQ-SDLC-040: Status labels: `status:discuss` | `status:ready` | `status:in-progress` | `status:in-review` | `status:returned` | `status:done`.
- REQ-SDLC-041: Type labels come from the card Labels line (`type:feature`, `type:fix`, `type:chore`, `type:docs`, `type:test`, `type:refactor`).
- REQ-SDLC-042: Card frontmatter `github_issue` stores the issue number (and optional url) after sync.

## Default SDD scaffold (CARD-086)

Language-agnostic template `templates/sdlc-project/`:

- `AGENTS.md` (constitution: SDD, TDD, SOLID, cards+specs, no invented APIs, conventional commits, semver)
- `docs/specs/.gitkeep` + README
- `.github/cards/.gitkeep`
- `CHANGELOG.md`
- `VERSION` (`0.1.0`)
- `CONTRIBUTING.md` (conventional commits)
- `tests/.gitkeep`
- `README.md` (educational / WIP ok if it matches AutoReiv tone)

- REQ-SDLC-050: `create_project` (tool + studio) copies the template into `projects_root/<slug>` and cannot escape `projects_root`.

## Later (out of this program)

- Git push tool (HITL + safety) if allowlist room
- GitHub MCP
- Language-specific scaffolds
- Multi-remote / org issue routers
- A second HITL, handoff, or workflow engine
- Giving Conductor or Review `execute_code` or `cli_exec`
- Giving Assistant / AutoReiv `execute_code`
