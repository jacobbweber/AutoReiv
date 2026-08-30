"""
Pre-configured Day-1 Routine Manifests [REQ-ROUTINE-006].
"""

from typing import Dict, List, Optional

from src.domain.routines.models import Routine, ScheduleType

MORNING_BRIEFING_ROUTINE = Routine(
    id="morning-briefing",
    name="Morning Briefing",
    description="Compiles a daily summary of pending tasks and priorities.",
    agent_id="assistant",
    prompt="Review my active tasks in the task tracker and compile a concise morning briefing with top priorities.",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=86400,
    cron_expression="0 8 * * *",
    enabled=True,
)

DAILY_SYSINFO_ROUTINE = Routine(
    id="daily-sysinfo",
    name="Daily System Info",
    description="Inspects host hardware metrics (CPU, RAM, disk, uptime).",
    agent_id="autoreiv",
    prompt="Run a system information inspection, check CPU, RAM, and disk utilization, and summarize host health status.",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=86400,
    cron_expression="0 9 * * *",
    enabled=True,
)

NIGHTLY_HYGIENE_ROUTINE = Routine(
    id="nightly-hygiene",
    name="Nightly Note Hygiene",
    description="Reviews wiki documents, validates YAML frontmatter, and indexes notes.",
    agent_id="assistant",
    prompt="Scan all markdown notes in the Wiki, check that YAML frontmatter is structured with titles and tags, and summarize the library index.",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=86400,
    cron_expression="0 23 * * *",
    enabled=True,
)

HOURLY_SRE_PULSE_ROUTINE = Routine(
    id="hourly-sre-pulse",
    name="Hourly SRE Health Pulse",
    description="Monitors platform database, tool error rates, and token consumption.",
    agent_id="autoreiv",
    prompt="Inspect platform health, database responsiveness, tool reliability rates, and token consumption.",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=3600,
    cron_expression="0 * * * *",
    enabled=True,
)

WEEKLY_NOTE_ROLLOVER_ROUTINE = Routine(
    id="weekly-note-rollover",
    name="Weekly Note Rollover & Task Carry-Over",
    description="Automated Monday Rollover: creates the new weekly work log from template, interpolates Monday–Sunday calendar dates, and carries over unfinished tasks from the previous week.",
    agent_id="assistant",
    prompt="Perform the weekly rollover: create the new week's note from the template in 03_Resources/templates/weekly_notes.md, interpolate Monday through Sunday dates, and carry over any uncompleted tasks from the previous week's note into the Carry-Over section.",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 0 * * 1",
    enabled=True,
)

# CARD-111: paused by default. 02:00 local is wrong for this operator (surprise GPU load).
# 21:00 UTC is 17:00 EDT -- also wrong. next_run_at is weekday 21:00 America/New_York.
SKILL_EVAL_SLEEP_PROMPT = (
    "Harvest failed turns from telemetry/sqlite in the lookback window. "
    "Mine pack gaps. Replay only if metadata.replay is true. "
    "Run the Verify checker. If it passes, propose_skill the bounded delta. "
    "Do not write SKILL.md. Do not write Python under src/. "
    "Do not archive bundled packs. Do not commit_skill_pack."
)

SKILL_EVAL_SLEEP_ROUTINE = Routine(
    id="skill-eval-sleep",
    name="Nightly skill eval (SkillOpt-Sleep shape)",
    description=(
        "Paused-by-default weekday 21:00 America/New_York skill eval. "
        "02:00 local / 2am user-local is wrong for this operator (surprise GPU load). "
        "21:00 UTC is 17:00 EDT -- also wrong. Harvest + gate + propose_skill HITL only."
    ),
    agent_id="agent-builder",
    prompt=SKILL_EVAL_SLEEP_PROMPT,
    schedule_type=ScheduleType.CRON,
    cron_expression="0 21 * * 1-5",
    enabled=False,
    metadata={
        "timezone": "America/New_York",
        "hour": 21,
        "minute": 0,
        "weekdays_only": True,
        "lookback_hours": 72,
        "replay": False,
        "auto_commit": False,
        "auto_archive": False,
    },
)


# CARD-112: paused Hermes curator. Auto-archive only when this sibling is enabled.
# skill-eval-sleep hook stays off (metadata.auto_archive false) so harvest is not destructive.
SKILL_CURATOR_PROMPT = (
    "Classify unused user skill packs (active -> stale at 30d -> archive at 90d). "
    "Archive means move to $DATA_DIR/skills/_archive/<id>/. Do not delete SKILL.md. "
    "Do not auto-archive bundled seeds including okta-admin. "
    "Do not delete repo src/infrastructure/skills/seeds/. "
    "Unknown last-used fails closed. Dest-exists fails closed."
)

SKILL_CURATOR_ROUTINE = Routine(
    id="skill-curator",
    name="Skill pack curator (Hermes stale/archive)",
    description=(
        "Paused-by-default weekday 21:00 America/New_York curator. "
        "Moves unused user packs to $DATA_DIR/skills/_archive/ after 90 days. "
        "Never deletes SKILL.md or bundled/okta-admin seeds. "
        "Enable only when you want auto-archive."
    ),
    agent_id="agent-builder",
    prompt=SKILL_CURATOR_PROMPT,
    schedule_type=ScheduleType.CRON,
    cron_expression="0 21 * * 1-5",
    enabled=False,
    metadata={
        "timezone": "America/New_York",
        "hour": 21,
        "minute": 0,
        "weekdays_only": True,
        "stale_days": 30,
        "archive_days": 90,
        "auto_archive": True,
    },
)

BUILTIN_ROUTINES: List[Routine] = [
    MORNING_BRIEFING_ROUTINE,
    DAILY_SYSINFO_ROUTINE,
    NIGHTLY_HYGIENE_ROUTINE,
    HOURLY_SRE_PULSE_ROUTINE,
    WEEKLY_NOTE_ROLLOVER_ROUTINE,
    SKILL_EVAL_SLEEP_ROUTINE,
    SKILL_CURATOR_ROUTINE,
]

_ROUTINES_MAP: Dict[str, Routine] = {r.id: r for r in BUILTIN_ROUTINES}


def get_builtin_routine(routine_id: str) -> Optional[Routine]:
    """Retrieve a built-in routine manifest by its ID."""
    return _ROUTINES_MAP.get(routine_id)
