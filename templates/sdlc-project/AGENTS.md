# Project Constitution

Language-agnostic rules for this repo. Humans own the idea. Agents implement one card at a time.

## Invariants

1. **SDD first.** No implementation until a card is Ready and `docs/specs/<slug>/` exists (requirements, design, tasks). Action -> route/event -> function must be in the design.
2. **TDD.** Red, green, refactor. Do not change a test just to make it pass.
3. **SOLID.** Smallest patch. No invented APIs or second engines when one already exists.
4. **Cards and specs.** Work lives in `.github/cards/CARD-NNN-*.md` and `docs/specs/<slug>/`. Statuses: Discuss, Ready, In Progress, In Review, Returned, Done.
5. **Conventional commits + semver.** Subjects look like `feat(scope): ...` / `fix` / `docs` / `chore` / `test` / `refactor`. VERSION and CHANGELOG move together.

## Loop

Jacob talks to Conductor. Conductor hands one Ready card to Coding. Coding implements and marks In Review. Review passes to Done or returns with a concrete gap.
