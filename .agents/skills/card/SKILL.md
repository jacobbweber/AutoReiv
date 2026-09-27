---
name: card
description: Create, find, dedupe and triage cards. Use at Pick, Dedupe and Plan, and for Sunday triage.
---
# Card

## Find work
```powershell
.venv\Scripts\python.exe .agents/skills/card/scripts/list_card_status.py --open            # Ready, In Progress, In Review
.venv\Scripts\python.exe .agents/skills/card/scripts/list_card_status.py --status Ready
.venv\Scripts\python.exe .agents/skills/card/scripts/list_card_status.py --card 556         # one card
.venv\Scripts\python.exe .agents/skills/card/scripts/list_card_status.py --open --json      # for a loop
```

## Dedupe before any new card or finding
1. Pick 2-3 keywords (symptom word, file or function name).
2. `list_card_status.py --open --search "<keyword>"` for each keyword.
3. `rg -n -i "<keyword>" docs/findings.md docs/cards`.
4. If a match exists, add your evidence to it. Do not create a new item.

## New card
```powershell
.venv\Scripts\python.exe .agents/skills/card/scripts/new_card.py "<title>" --type bug --priority P2 --milestone M22
```
- Templates: `.agents/skills/card/templates/bug.md` and `feature.md`.
- Fill every section. Put the journey id and check ids in `proof:`.
- `needs_decision:` is `none`, or one line per product, design or architecture decision with your recommendation.

## Status values (only these)
`Ready`, `In Progress`, `In Review`, `Done`, `Parked`, `Superseded`.

## Card log (fill at In Review)
`log: {minutes: <wall minutes>, qa_runs: <live-qa runs>, findings: <count>}`

## Sunday triage (about 30 minutes)
1. `list_card_status.py --open --json` and read `docs/findings.md`.
2. For each finding: make a card (template, dedupe first), attach it to a card, or delete it with a reason.
3. Close duplicates with `status: Superseded` and `superseded_by: CARD-N`.
4. Clear stale gates: if `needs_decision` is only technical, set it to `none`.
5. Keep Ready P3 at or below 30: park or supersede the rest.
6. Send Jacob one summary: counts (filed, closed, Ready by priority), decisions he owes, next milestone focus.
