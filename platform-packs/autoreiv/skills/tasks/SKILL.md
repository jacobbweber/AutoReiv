---
name: Daily Tasks & Weekly Organization
description: Weekly notes, task logging, completion tracking, and weekly task rollovers.
---

# Daily Tasks & Weekly Organization

Organize daily tasks, work items, and weekly review notes in AutoReiv's workspace.

## Available Tools

- `get_or_create_weekly_note`: Retrieve or scaffold the markdown weekly note for the specified ISO week.
- `log_daily_work_item`: Append a work item, task, or reminder to a specific day.
- `complete_weekly_task`: Mark a task complete with a timestamped checkmark.
- `rollover_weekly_tasks`: Carry over incomplete tasks from the previous week into the current week.
- `get_weekly_summary`: Generate a summarized markdown report of weekly completions, carried-over tasks, and progress.

## Workflow Order

1. Call `get_or_create_weekly_note` to ensure the current week's structure exists.
2. Log new action items or progress using `log_daily_work_item`.
3. Mark finished tasks complete with `complete_weekly_task`.
4. Run `rollover_weekly_tasks` during Monday planning or weekly reviews.
5. Generate end-of-week reviews with `get_weekly_summary`.
