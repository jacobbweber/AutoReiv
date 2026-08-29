# Design

Jacob covisions with Conductor only. Coding implements one Ready card. Review judges the spec, not product taste. Bounce-back is `set_card_status` plus existing `handoff_to_agent`. Projects are a studio, not wiki.

## Action to route to function

1. Jacob talks in Chat on Conductor -> model writes a Discuss card -> `write_card` -> `{project_root}/.github/cards/CARD-NNN-*.md` (HITL park in ask mode).
2. Jacob / Conductor write spec files -> `write_spec` -> `{project_root}/docs/specs/<slug>/{requirements,design,tasks}.md` (HITL).
3. Conductor `set_card_status` Discuss -> Ready -> `CardStatusMachine` checks Spec Reference exists -> frontmatter Status updates (HITL).
4. Conductor `lookup_agents` (aliases: product, plan, scrum, conductor) then `handoff_to_agent` target `coding` with one card id.
5. Coding `set_card_status` Ready -> In Progress, implements via project file tools (CARD-081) and later git (CARD-087), then In Progress -> In Review only, and stops.
6. Conductor `handoff_to_agent` target `review`. Review reads spec + files. Pass: In Review -> Done. Fail: In Review -> Returned (`return_reason`, `review_rounds++`).
7. If `review_rounds` < max, Conductor hands the same card back to Coding (Returned -> In Progress). At max, Conductor asks Jacob. No second engine.
8. After CARD-085, omitted `project_root` is the selected project under `projects_root`. Until then, omitted `project_root` is the AutoReiv checkout.
9. After CARD-086, studio / `create_project` copies `templates/sdlc-project/` into `projects_root/<slug>`.
10. After CARD-088, `sync_card_issue` maps card status to GitHub labels via `gh` (or a clear missing-`gh` error).

## Status machine (single implementation)

`src/domain/sdlc/models.py` owns statuses and legal transitions. `set_card_status` is the only mutator. CARD-084 adds the Coding-only In Progress -> In Review rule via `get_tool_context()` agent id, plus prompt text. Do not add a workflow runner.

## Jail

`src/application/sdlc/paths.py` resolves `project_root`, then joins relative paths with `Path.resolve()` + `relative_to(root)`. Reject `..` parts and absolute paths outside the root. Card, spec, steering, project-file, and git tools share this helper.

## HITL

Existing `HITLApprovalEngine.high_risk_tools` list. Add mutating SDLC names. Ask mode parks. Run mode still hard-denies dangerous `cli_exec`. No new approval UI.

## Allowlists

Conductor 11 tools (CARD-082). Review 9 tools (CARD-083). Coding stays under 12 after git is added (CARD-087): drop wiki reads.

## GitHub label map

| Card status | Label |
|---|---|
| Discuss | status:discuss |
| Ready | status:ready |
| In Progress | status:in-progress |
| In Review | status:in-review |
| Returned | status:returned |
| Done | status:done |

Type labels from the card Labels line. Store `github_issue` on the card after sync.

## Scaffold file list (CARD-086)

`templates/sdlc-project/AGENTS.md`
`templates/sdlc-project/docs/specs/.gitkeep`
`templates/sdlc-project/docs/specs/README.md`
`templates/sdlc-project/.github/cards/.gitkeep`
`templates/sdlc-project/CHANGELOG.md`
`templates/sdlc-project/VERSION`
`templates/sdlc-project/CONTRIBUTING.md`
`templates/sdlc-project/tests/.gitkeep`
`templates/sdlc-project/README.md`

## What is later

Git push. GitHub MCP. Language-specific scaffolds. Multi-org issue routers. Second HITL or handoff engine. Coding UI beyond tools. Hardcoding Jacob's lab path as the only default.
