# Self-development (M25–M28)

Status: shipped and consolidated on `AutoReiv` ([ADR-0066](../docs/adr/0066-consolidate-architect-developer-and-toolsmith-into-agora-skill-folders-on-autoreiv.md), CARD-693). Slice 1 (`CARD-562`) proved the card workflow, and M28 retired the separate `Architect`, `Developer`, and `Toolsmith` agents into cohesive Agora skill folders (`project-cards`, `software-development`, `capability-authoring`) on `AutoReiv` that mount their tools on demand via `skill_view`. `AGENTS.md` is what applies to work on this repo today.

## Goal
A general development workflow and light card process that work on any git repo. AutoReiv is only the first project:
Jacob clones a separate AutoReiv copy (its own dev port in `.env`) into the projects folder and selects it as the active
project in Projects Studio. There is no self-copy mechanism; the running AutoReiv never edits its own checkout.

## Projects folder and process (ADR-0067, M32)
- Projects live in one user-data folder: `<data>/projects`, or `AUTOREIV_PROJECTS_DIR` set at deploy time. Docker mounts
  it from `AUTOREIV_PROJECTS_HOST_PATH`, so the same folder opens in VS Code on the host. There is no root setting in the UI.
- The app never pushes a template. `create_project` makes an empty git repository. `repo-onboarding` reads the repo's own
  rules (AGENTS.md, CLAUDE.md, Copilot or Cursor rules, build files) first and offers a starter AGENTS.md only when none exist.
- `spec-driven-development` writes requirements, design and tasks before code. `live-journeys` holds the journey tools.

## Consolidated skills on `AutoReiv` (ADR-0066)
| Skill Folder | Reference | Does |
|---|---|---|
| `project-cards` | `references/card-rubric.md` | Brainstorms with Jacob, writes/updates cards (`write_card`, `set_card_status`), and reviews cards (`review_card`, `finish_review`) |
| `software-development` | `references/workflow.md` | Inspect, edit, build, test and commit in the active project: branch, edit, `run_project_checks`, `cli_exec` (approval per call), commit |
| `repo-onboarding` | `references/conventions.md` | Creates or adopts a project and follows the repo's own conventions before AutoReiv's defaults |
| `spec-driven-development` | `references/templates.md` | Requirements, design and tasks before code |
| `live-journeys` | - | Runs and reads AutoReiv-style live QA journeys in repos that ship them |
| `capability-authoring` | `references/authoring-guide.md` | Authors and updates Agora skill folders (`SKILL.md`, `references/*.md`, `tools/*.py`) inline via `write_skill_file` |

## Platform vs project
- Platform skills: general know-how (orientation, card intake and writing, planning, implementing, tests, debugging, checks, git, review, audit).
- The project's own `AGENTS.md`: facts about that repo under fixed headings (`## Project`, `## Run`, `## Checks`, `## Branches`, `## Cards`, `## Rules`, `## Don't touch`). `run_project_checks` runs only the `## Checks` commands.
- Cards (`project-cards`) are opt-in: they live in `.agents/cards/` in projects that use them.

## Enforced in the tools (slice 1)
- Developer works only in the project selected in Projects Studio; with none selected, project tools refuse (a passed project_root cannot bypass or redirect).
- Commands run only through `cli_exec` from `software-development`: it runs in the active project, asks for approval on
  every call and blocks dangerous commands (ADR-0067 amends the CARD-562 "no shell" rule). No code runner.
- `git_commit` refuses main/master/qa; `git_create_branch` carries card edits from HEAD.
- `git_clone` clones into the projects folder (local sources only from inside it); `git_pull` only fast-forwards;
  `git_push` never forces and refuses main/master/qa. GitHub HTTPS auth comes from `GITHUB_TOKEN` in the git process
  environment only (CARD-730).
- `set_card_status` to In Review needs the card branch, a clean tree and a green check for HEAD, then writes the Evidence and commits the card.
- Cards are written only with `write_card` (next CARD-N id; Developer's new cards are Proposed); file tools refuse card folders.
- Tool building (Tools Studio, Ask Developer, scaffold_agent_pack) is parked until slice 2.

## Slices
1. Developer works one card to In Review on the active project (CARD-562). Done.
2. Architect plans cards and hands off.
3. Architect reviews (Done or Returned).
4. Per-project approval level: edits and `## Checks` commands automatic; push and merge always ask.

## Settled decisions (2026-09-27)
- D1 cards in `.agents/cards/`. D2 Developer files Proposed cards. D3 Developer model via Agent Studio override. D4 Jacob approves every merge. D5 self-extension skills stay out of the SDLC skill set.
