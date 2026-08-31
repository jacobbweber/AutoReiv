---
name: Weekly tasks
description: Weekly note, daily work items, complete, rollover, summary.
---

# Weekly tasks

Keep the user's week current. One weekly note, daily work items, complete when done, rollover leftovers, summarize.

## Order

1. `get_or_create_weekly_note` if this week has no note yet.
2. `log_daily_work_item` when the user names work for today.
3. `complete_weekly_task` when they mark something done.
4. `rollover_weekly_tasks` at week boundary or when they ask to carry unfinished work.
5. `get_weekly_summary` when they ask how the week looks.

## Pitfalls

- Do not invent tasks the user did not state.
- Wiki notes are the Platform `wiki` skill, not this runbook.
- Do not run host-shell `cli_exec` or platform diagnostics; hand those to AutoReiv.

## Done-when

- This week's note exists.
- Daily items the user stated are logged.
- Completions and rollovers match what they asked.
