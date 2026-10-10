# AGENTS.md - AutoReiv engineering playbook

The process exists to ship changes proven to work in the real app, with minimum paperwork.
Rules in `.agents/rules/` are always loaded and machine-checkable. Skills in `.agents/skills/` are opened when a step names them.
Nothing in this file is repeated elsewhere. This is the only root instruction file.

## People and words
- Jacob: sets milestones, answers product, design and architecture decisions, reads one check-in per card or batch, approves merges.
- Agent: owns engineering, design details, tests, live QA, finding bugs, and advising Jacob. One assistant does planning, building and verifying today; see `steering/self-development.md` for the future split.
- Jacob's reply words (exact):
  - `build`: approve a plan that had a product, design or architecture decision.
  - `merge to qa`: approve merging the named cards.
  - `continue`: go on. It never counts as `build` or `merge to qa`.
- Talk in plain sentences: what Jacob will see, real names, exact paths.
- A question to Jacob is 2-3 options with your recommendation. Never an open question.

## Hard rules
1. No product code without a card: `.agents/cards/CARD-N-slug.md`. Only card files live in `.agents/cards/`.
2. Never push, merge, tag, reset `qa`, force anything, or delete user data unless Jacob said so in this session.
3. Never work around a known bug. Mark it expected-fail with its card id (`.agents/rules/testing.md`).
4. Never weaken, skip or delete a valid assertion to go green.
5. Stay inside `.agents/rules/boundaries.md` (data locations, capability scoping).


## Card loop
1. **Pick.** Take the card Jacob names, or the highest-priority Ready card in the current milestone. Skill `card` (status queries).
2. **Dedupe.** Search open cards and `docs/findings.md` for the same problem (skill `card`, search). If one matches, work on or merge into it.
3. **Plan.** Fill the card from the template (skill `card`): Problem, Cause, Change, What dies (may be "nothing"), Proof. Name the journey and the checks in the `proof:` front matter.
4. **Gate.** If a decision is product, design or architecture, send the plan with options and stop until `build`. Otherwise record the decision in the card and go on.
5. **Branch.** `git switch -c feat/card-N-slug qa`. Several cards share a branch only when they change the same code; list all ids in the first commit.
6. **Build.** Root cause, failing test, fix (`.agents/rules/testing.md`). Write or update the named journey.
7. **In-area findings.** Same files or flow and about 30 minutes or less: fix now and list under Findings (fixed). Anything else: one line in `docs/findings.md` under the milestone. Never a new card from inside a card.
8. **Fast check.** Skill `preflight`, fast tier. Must be green.
9. **Verify.** Skill `live-qa` with the card's journeys, desktop and phone. "Model endpoint down" is not a card failure: wait and rerun.
10. **In Review.** Complete `.agents/rules/definition-of-done.md`, set `status: In Review`, fill `log:`.
11. **Check-in.** One message per card or batch: what changed, results table, findings, open decisions, 2-3 screenshots under `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\`. Stop.
12. **Merge.** Only after `merge to qa`: skill `merge-to-qa`.

At most 2 Build -> Verify rounds per card (steps 6-9). If round 2 still fails, stop and report to Jacob with the results.

## Findings and backlog
- One findings list: `docs/findings.md`, a section per milestone, one line per finding: date, area, symptom, source card, suspected files.
- Before adding, search it and the open cards. Add evidence to a match instead of a new line.
- Sunday triage (skill `card`, triage): turn worthwhile findings into cards, close duplicates, re-prioritise. Keep Ready P3 at or below 30.
- `steering/roadmap.md` holds milestones and goals only. Never one line per card; card front matter `milestone:` links cards to it.


## Product locks (do not reverse)
- Skill = one `SKILL.md` runbook. Tool = one callable. Pack = one agent. Say Platform, not Global.
- Chat shows the tools of the agent's ticked skills; the model sees at most 15 per turn (ADR-0061; cap raised from 8 by CARD-562, ADR-0054 amendment).
- An agent's own databases live under user data `agents/<id>/` (`memory.db`, `storage.db`).

## Where things live
| Place | Owns |
|---|---|
| `.agents/rules/` | boundaries, code-quality, testing, definition-of-done (always); frontend (glob `src/web/**`) |
| `.agents/skills/` | card, preflight, live-qa, merge-to-qa, serve-hygiene, ui-review, adr-manager, boundary-audit, lifecycle-audit, single-lever-audit |
| `steering/` | product, tech, structure, roadmap (milestones), self-development (future design note) |
| `docs/adr/` | decisions that constrain code, each with a guard test |
| `.agents/cards/` | cards (one file per card) |
| `docs/findings.md` | the findings list |
| `scratch/` | the only place for temporary files (gitignored) |
