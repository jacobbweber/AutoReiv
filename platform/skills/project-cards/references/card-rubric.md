# Card Template & Review Rubric

## 1. Card Frontmatter & Sections
Every card in `.agents/cards/CARD-N-slug.md` carries:
- Frontmatter: `id`, `title`, `type` (`feature` | `bug`), `status` (`Proposed` | `Ready` | `In Progress` | `In Review` | `Done`), `priority` (`P0`-`P3`), `milestone`, `needs_decision`, `proof: {journeys: [...], checks: [...]}`.
- Body sections:
  - `## Problem` (or `## Intent` / `## Goal`)
  - `## Cause` (for bugs)
  - `## Change` (exact files and functions touched)
  - `## What dies` (retired code/controls deleted on the same card, or "nothing")
  - `## Proof` (named journey and guard/unit/integration checks)
  - `## Findings`
  - `## Results`
  - `## Release note`

## 2. Mechanical Status Rules
- Never change `status:` by rewriting a card with `write_card`; always use `set_card_status` or `finish_review`.
- Moving to `In Review` requires:
  1. Being checked out on the card branch (never `main`, `master`, or `qa`).
  2. A clean git working tree.
  3. A green `run_project_checks` record for the current `HEAD` commit.
- `finish_review` records `Done` (all acceptance items met and checks green) or `Returned` (specific file and behaviour changes needed).
