# Requirements Specification: Weekly Notes Rollover Routine & Markdown Task Skill

> **Card ID**: [`CARD-057`](file:///d:/Projects/Active/AutoReiv/.github/cards/CARD-057-weekly-notes-rollover-routine-and-markdown-task-skill.md)  
> **Milestone**: 21  
> **Status**: Approved

---

## 1. User Story

As an **AutoReiv user using Chat Studio and an Obsidian-compatible Wiki Vault**,  
I want my **`assistant` agent to maintain a Markdown-first Weekly Note with daily work logs, project references, and automatic task rollover across weeks**,  
so that **I can effortlessly track my to-dos, reminders, and daily progress via natural conversation while keeping an automated background routine to initialize new weeks.**

---

## 2. EARS Requirements

### `[REQ-WNOTE-001]`: Weekly Note Template & Dynamic Date Interpolation
- **Type**: Ubiquitous
- **Requirement**: The system SHALL maintain a standard Weekly Note template seeded at `data/wiki/03_Resources/templates/weekly_notes.md`, supporting ISO week computation and dynamic date placeholders (`{{monday:dddd D}}` $\to$ `Monday 24`, ..., `{{sunday:dddd D}}` $\to$ `Sunday 30`).

### `[REQ-WNOTE-002]`: Conversational Weekly Notes & To-Dos Skill
- **Type**: Event-Driven
- **Requirement**: When invoked by an agent turn, `WeeklyNotesSkill` SHALL expose tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`) capable of reading, updating, and formatting markdown weekly notes in `data/wiki/01_Notes/weekly/YYYY-Www.md`.

### `[REQ-WNOTE-003]`: Automated Incomplete Task Carry-Over Engine
- **Type**: Event-Driven
- **Requirement**: When rolling over from week $W_{N-1}$ to $W_N$, the system SHALL parse all uncompleted task items (lines with `- [ ]` or items lacking `✅`) from the previous week's Daily Logs and Carry-Over sections, and SHALL inject them into the new week note under `### 🔄 Carry-Over`.

### `[REQ-WNOTE-004]`: Autonomous Monday Midnight Rollover Routine
- **Type**: Ubiquitous
- **Requirement**: The system SHALL register a built-in background routine `weekly_note_rollover` with cron schedule `0 0 * * 1` (Mondays at 00:00:00) bound to the `assistant` agent, automatically creating the new weekly note and performing task carry-over without requiring manual user prompting.

### `[REQ-WNOTE-005]`: Comprehensive Verification Gate
- **Type**: Ubiquitous
- **Requirement**: All unit tests, routine execution tests, API integrations, and Playwright smoke tests SHALL pass 100% green with zero regressions across the Wiki Vault and Agent Forge.
