# Self-development: design note (future milestone)

Status: design note, not in force. AGENTS.md is what applies today (one assistant plans, builds and verifies).
Moved here from the draft AGENTS.md by CARD-559 so the playbook stays short.

## Goal
AutoReiv's own agents follow the same playbook (AGENTS.md, `.agents/rules`, `.agents/skills`) to fix and live-test AutoReiv itself.

## Roles (the card is the hand-off)
| Role | Model | Does | Writes on the card |
|---|---|---|---|
| Plan | reasoning (qwen3.8) | pick, dedupe, root cause, short plan, define the proof (journey + checks) | Goal, Plan and decisions, `proof:` |
| Build | coder (qwen3.6) | branch, change, pass the proof locally | code, tests, journey, Release note |
| Verify | reasoning, independent of Build | live journeys on real models, desktop and phone | Results, Findings, `log:` |

- A loop controller runs at most 2 Build -> Verify rounds per card, then stops and reports (the same limit AGENTS.md applies today).
- Batch cards by role so the model swap (about 6 minutes) happens once per batch: plan several cards, build them all, verify them all.

## Overnight runs
- Bug-fix and cleanup cards only (`type: bug`, `needs_decision: none`); never features or decisions.
- One branch per card. Nothing merges or pushes; Jacob still says `merge to qa`.
- Uses `preflight.py --nightly` for the full tier and all journeys.
- Leaves a morning summary: cards attempted, proof results, branches, findings, and each card's `log:`.

## Open questions (decide when the milestone starts)
- Where the loop controller runs (an AutoReiv routine or a script) and how it is scheduled.
- Which tools the Developer needs to run `preflight.py` and `live_qa.py` inside capability scoping (ADR-0061).
