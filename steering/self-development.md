# Self-development (M25)

Status: in progress. Slice 1 (CARD-562) is done and merged to qa (2026-09-28); slices 2-4 are design. AGENTS.md is what applies to work on this repo today.

## Goal
A general development agent and a light card process that work on any git repo. AutoReiv is only the first project:
Jacob clones a separate AutoReiv copy (its own dev port in `.env`) and selects it as the active project in Projects
Studio. There is no self-copy mechanism; the running AutoReiv never edits its own checkout.

## Two agents (the card is the hand-off)
| Agent | Model | Does |
|---|---|---|
| Architect (slice 2) | reasoning model on DGX Spark (vLLM, global reasoning default) | brainstorms with Jacob, writes cards, hands one to Developer, reviews the result against the card (slice 3) |
| Developer | coder model on Nimo (Ollama, set by Agent Studio model override; today `qwen3.6:35b-a3b-65k`) | takes a Ready card to In Review: branch, plan, edit, AGENTS.md checks, commit, evidence; files gaps it finds as Proposed cards; never invents features, never pushes or merges |

## Platform vs project
- Platform skills: general know-how (orientation, card intake and writing, planning, implementing, tests, debugging, checks, git, review, audit).
- The project's own `AGENTS.md`: facts about that repo under fixed headings (`## Project`, `## Run`, `## Checks`, `## Branches`, `## Cards`, `## Rules`, `## Don't touch`). `run_project_checks` runs only the `## Checks` commands.
- Cards live in `.agents/cards/`, one file per card, in every project.

## Enforced in the tools (slice 1)
- Developer works only in the project selected in Projects Studio; with none selected, project tools refuse (a passed project_root cannot bypass or redirect).
- No shell or code runner on Developer; checks run only through `run_project_checks`.
- `git_commit` refuses main/master/qa; `git_create_branch` carries card edits from HEAD.
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
