"""
Unit tests for Weekly Note Rollover Routine [REQ-WNOTE-004].
"""

from src.domain.routines.manifests import BUILTIN_ROUTINES, WEEKLY_NOTE_ROLLOVER_ROUTINE
from src.domain.routines.models import ScheduleType


def test_weekly_note_rollover_routine_manifest():
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE in BUILTIN_ROUTINES
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.id == "weekly-note-rollover"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.agent_id == "assistant"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.schedule_type == ScheduleType.CRON
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.cron_expression == "0 0 * * 1"
    assert WEEKLY_NOTE_ROLLOVER_ROUTINE.enabled is True
    assert "weekly" in WEEKLY_NOTE_ROLLOVER_ROUTINE.prompt.lower()
