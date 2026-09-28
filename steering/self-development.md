# Self-development (M25)

Status: in progress. Slice 1 (CARD-562) is built; later slices are design. AGENTS.md is what applies to work on this repo today.

## Goal
A general development agent and a light card process that work on any git repo. AutoReiv is only the first project:
Jacob clones a separate AutoReiv copy (its own dev port in `.env`) and selects it as the active project in Projects
Studio. There is no self-copy mechanism; the running AutoReiv never edits its own checkout.

## Two agents (the card is the hand-off)
| Agent | Model | Does |
|---|---|---|
| Architect (slice 2) | reasoning purpose (global default, DGX Spark vLLM) | brainstorms with Jacob, writes cards, hands one to Developer, reviews the result against the card (slice 3) |
| Developer | Agent Studio model override (coder model, Ollama on Nimo) | takes a Ready card to In Review: branch, plan, edit, AGENTS.md checks, commit, evidence; files gaps it finds as Proposed cards; never invents features, never pushes or merges |

## Platform vs project
- Platform skills: general know-how (orientation, card intake and writing, planning, implementing, tests, debugging, checks, git, review, audit).
- The project's own `AGENTS.md`: facts about that repo under fixed headings (`## Project`, `## Run`, `## Checks`, `## Branches`, `## Cards`, `## Rules`, `## Don't touch`). `run_project_checks` runs only the `## Checks` commands.
- Cards live in `.agents/cards/`, one file per card, in every project.

## Slices
1. Developer works one card to In Review on the active project (CARD-562).
2. Architect plans cards and hands off.
3. Architect reviews (Done or Returned).
4. Per-project approval level: edits and `## Checks` commands automatic; push and merge always ask.

## Settled decisions (2026-09-27)
- D1 cards in `.agents/cards/`. D2 Developer files Proposed cards. D3 Developer model via Agent Studio override. D4 Jacob approves every merge. D5 self-extension skills stay out of the SDLC skill set.
