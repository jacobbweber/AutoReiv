"""
Unit tests for Weekly Note Rollover Routine [REQ-WNOTE-004].
"""

from src.domain.routines.manifests import BUILTIN_ROUTINES, WEEKLY_NOTE_ROLLOVER_ROUTINE
from src.domain.routines.models import ScheduleType


def test_weekly_note_rollover_routine_manifest():
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE in BUILTIN_ROUTINES
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.id == "weekly-note-rollover"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.agent_id == "autoreiv"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.schedule_type == ScheduleType.CRON
    # CARD-636: Mondays 04:00 America/New_York (was midnight UTC = 20:00 ET Sunday)
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.cron_expression == "0 4 * * 1"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.metadata["timezone"] == "America/New_York"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.metadata["weekdays"] == [1]
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.enabled is True
    assert "weekly" in WEEKLY_NOTE_ROLLOVER_ROUTINE.prompt.lower()
