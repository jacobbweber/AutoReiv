"""
Shipped routine manifests [REQ-ROUTINE-006] [CARD-636].

Five maintenance routines, all at night on America/New_York wall-clock time (02:00-04:30).
The three that call the model (Spark) are an hour apart, longer than the 40-minute model timeout,
so they never queue behind each other. The cron strings mirror the local slot for the Studio
form; the scheduler uses metadata timezone/hour/minute (see ScheduleMatcher.compute_next_run).
"""

from typing import Dict, List, Optional, Tuple

from src.domain.routines.models import Routine, ScheduleType

LOCAL_TIMEZONE = "America/New_York"


def _local_slot(hour: int, minute: int, *, weekdays: Optional[List[int]] = None) -> Dict[str, object]:
    """Wall-clock slot in LOCAL_TIMEZONE; weekdays use cron convention (0=Sun .. 6=Sat), None = daily."""
    meta: Dict[str, object] = {"timezone": LOCAL_TIMEZONE, "hour": hour, "minute": minute, "weekdays_only": False}
    if weekdays:
        meta["weekdays"] = list(weekdays)
    return meta


# 02:00 daily, Spark.
SRE_PULSE_ROUTINE = Routine(
    id="hourly-sre-pulse",  # id kept so run history and Jacob's settings carry over
    name="Nightly SRE Health Pulse",
    description="Once a night: platform database, tool error rates, and token consumption over the last day.",
    agent_id="autoreiv",
    prompt="Inspect platform health over the last 24 hours: database responsiveness, tool reliability rates, and token consumption.",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 2 * * *",
    enabled=True,
    metadata=_local_slot(2, 0),
)

# 02:30 daily, no model (deterministic ledger scan).
EDUCATION_RETRIEVAL_RETENTION_ROUTINE = Routine(
    id="education-retrieval-retention",
    name="Education Retrieval + Retention",
    description="Resurface due Education quiz reviews as standing Jobs on the 1-3-7-30 mastery schedule (memory.db ledger). Chat toast is not Done.",
    agent_id="tutor",
    prompt="Resurface due Education quiz reviews from the mastery ledger as standing Jobs. Prefer wiki_note_read for grounding. Do not use chat-only toast reminders.",
    schedule_type=ScheduleType.CRON,
    cron_expression="30 2 * * *",
    enabled=True,
    metadata={
        **_local_slot(2, 30),
        "kind": "education_retention",
        "srs_intervals_days": [1, 3, 7, 30],
        "approval_mode": "ask",
    },
)

# 03:00 daily, Spark. Absorbs the retired Nightly Note Hygiene pass.
WIKI_CURATION_ROUTINE = Routine(
    id="wiki-curation",
    name="Wiki Inbox Curation Routine",
    description=(
        "Inspects 00_Inbox/, validates frontmatter, checks and self-registers tag authority, deduplicates against "
        "01_Notes/, scrubs conversational fluff, and graduates notes to the warehouse; then checks every note's "
        "frontmatter and summarizes the library index."
    ),
    agent_id="autoreiv",
    prompt=(
        "Curate the Wiki inbox: inspect all notes in 00_Inbox, validate frontmatter, check and self-register tags with "
        "tag-authority.md, deduplicate against 01_Notes, and graduate notes to their domain/topic warehouse. "
        "Then scan all markdown notes in the Wiki, check that YAML frontmatter is structured with titles and tags, "
        "and summarize the library index."
    ),
    schedule_type=ScheduleType.CRON,
    cron_expression="0 3 * * *",
    enabled=True,
    metadata=_local_slot(3, 0),
)

# Mondays 04:00, Spark.
WEEKLY_NOTE_ROLLOVER_ROUTINE = Routine(
    id="weekly-note-rollover",
    name="Weekly Note Rollover & Task Carry-Over",
    description="Automated Monday Rollover: creates the new weekly work log from template, interpolates Monday-Sunday calendar dates, and carries over unfinished tasks from the previous week.",
    agent_id="autoreiv",
    prompt="Perform the weekly rollover: create the new week's note with wiki_note_create using template weekly_notes, interpolate Monday through Sunday dates, and carry over any uncompleted tasks from the previous week's note into the Carry-Over section.",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 4 * * 1",
    enabled=True,
    metadata=_local_slot(4, 0, weekdays=[1]),
)

# 04:30 daily, no model. Last, so it sees the night's routine turns. Absorbs the retired skill eval.
TELEMETRY_FRICTION_AUDITOR_ROUTINE = Routine(
    id="telemetry-friction-auditor",
    name="Autonomous Telemetry Auditor",
    description=(
        "Audits the last day's conversation spans for redundant verification loops, payload bloat, and search "
        "thrashing and stages runbook recommendations; then harvests failed turns and stages skill proposals "
        "(both wait for your approval; nothing is applied or committed)."
    ),
    agent_id="autoreiv",
    prompt=(
        "Audit recent telemetry spans and conversation transcripts for procedural friction. Synthesize runbook "
        "recommendations for identified patterns. Then harvest failed turns, mine skill gaps, run the Verify checker, "
        "and propose_skill the bounded delta. Do not write SKILL.md or Python under src/; do not commit_skill."
    ),
    schedule_type=ScheduleType.CRON,
    cron_expression="30 4 * * *",
    enabled=True,
    metadata={
        **_local_slot(4, 30),
        "lookback_hours": 24,
        "auto_apply": False,
        "replay": False,
        "auto_commit": False,
        "auto_archive": False,
    },
)

BUILTIN_ROUTINES: List[Routine] = [
    SRE_PULSE_ROUTINE,
    EDUCATION_RETRIEVAL_RETENTION_ROUTINE,
    WIKI_CURATION_ROUTINE,
    WEEKLY_NOTE_ROLLOVER_ROUTINE,
    TELEMETRY_FRICTION_AUDITOR_ROUTINE,
]

# CARD-636: shipped routines retired from BUILTIN_ROUTINES; the one-time migration deletes their rows and runs.
REMOVED_BUILTIN_ROUTINE_IDS: Tuple[str, ...] = (
    "daily-sysinfo",
    "morning-briefing",
    "skill-curator",
    "nightly-hygiene",
    "skill-eval-sleep",
)


_ROUTINES_MAP: Dict[str, Routine] = {r.id: r for r in BUILTIN_ROUTINES}


def get_builtin_routine(routine_id: str) -> Optional[Routine]:
    """Retrieve a built-in routine manifest by its ID."""
    return _ROUTINES_MAP.get(routine_id)
