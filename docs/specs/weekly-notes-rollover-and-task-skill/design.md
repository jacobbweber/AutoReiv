# Technical Design: Weekly Notes Rollover Routine & Markdown Task Skill

> **Card ID**: [`CARD-057`](file:///d:/Projects/Active/AutoReiv/.github/cards/CARD-057-weekly-notes-rollover-routine-and-markdown-task-skill.md)  
> **Milestone**: 21  
> **Status**: Approved  
> **Requirements**: `[REQ-WNOTE-001]` to `[REQ-WNOTE-005]`

---

## 1. Architectural Overview & C4 Flow

```mermaid
graph TD
    User[User in Chat Studio] -->|1. Chat Prompt| Assistant[Assistant Agent]
    Assistant -->|2. Invoke Tool| Skill[WeeklyNotesSkill]
    
    Scheduler[RoutineScheduler (0 0 * * 1)] -->|1. Scheduled Trigger| Executor[RoutineExecutor]
    Executor -->|2. Run Rollover| Skill
    
    Skill -->|3. Read Template| Template["data/wiki/03_Resources/templates/weekly_notes.md"]
    Skill -->|4. Parse Incomplete Tasks| PrevNote["data/wiki/01_Notes/weekly/2026-W34.md"]
    Skill -->|5. Write & Inject Carry-Over| NextNote["data/wiki/01_Notes/weekly/2026-W35.md"]
    Skill -->|6. Render in Wiki Studio / Obsidian| Vault[Local Wiki Vault]
```

---

## 2. Default Weekly Note Template (`weekly_notes.md`)

```markdown
---
tags:
  - worklog
  - weekly_notes
week: {{week}}
date_start: {{date_start}}
date_end: {{date_end}}
---
[[My Dashboard]]

## Projects
- **Server Currency** - Work through Windows OS In-Place Upgrades/Migrations for all systems.
- **AQS Migration** - Migrate app from server 2000 to 2022.
- **Leaders Life** - Child Domain permissions delegation.

---

## {{week_title}} Summary

### 🎯 Focusing
- 

### ⚡ Ad-Hoc
- 

### 🔄 Carry-Over
{{carry_over_tasks}}

### ✅ Done
- 

---

## 📅 Daily Work Logs

### {{monday:dddd D}}
- 

### {{tuesday:dddd D}}
- 

### {{wednesday:dddd D}}
- 

### {{thursday:dddd D}}
- 

### {{friday:dddd D}}
- 

### {{saturday:dddd D}}
- 

### {{sunday:dddd D}}
- 
```

---

## 3. Carry-Over Algorithm

```python
def extract_incomplete_tasks(markdown_content: str) -> List[str]:
    """
    Scans a weekly note for tasks that were NOT completed.
    Criteria for incomplete:
      - Line starts with '- [ ] ' (unchecked markdown task), OR
      - Line starts with '- ' and does NOT contain '✅'
      - Ignores empty bullet points ('- ')
      - Ignores lines inside '### ✅ Done' section
    """
```

---

## 4. Routine Definition

```python
RoutineDefinition(
    id="weekly_note_rollover",
    name="Weekly Note Rollover & Task Carry-Over",
    description="Automated Monday Rollover: creates the new weekly work log from template, interpolates Monday–Sunday calendar dates, and carries over unfinished tasks from the previous week.",
    cron_schedule="0 0 * * 1",  # Every Monday at midnight
    target_agent_id="assistant",
    action_type="custom_task",
    parameters={
        "action": "rollover_weekly_notes",
    },
    is_builtin=True,
    is_active=True,
)
```
