"""
Unit tests for Cron Schedule Humanizer & Next Run Calculator [REQ-ROUT-001].
"""

from datetime import datetime, timezone

from src.application.routines.humanizer import compute_next_run_eta, cron_to_human


def test_cron_to_human_translation():
    """Verify common cron expressions translate to human-readable strings."""
    assert cron_to_human("* * * * *") == "Every minute"
    assert cron_to_human("*/5 * * * *") == "Every 5 minutes"
    assert cron_to_human("*/15 * * * *") == "Every 15 minutes"
    assert cron_to_human("*/30 * * * *") == "Every 30 minutes"
    assert cron_to_human("0 * * * *") == "Every hour at minute 0"
    assert cron_to_human("0 */2 * * *") == "Every 2 hours"
    assert cron_to_human("0 8 * * *") == "Daily at 08:00 UTC"
    assert cron_to_human("0 0 * * 0") == "Weekly on Sunday at 00:00 UTC"
    assert cron_to_human("0 0 1 * *") == "Monthly on the 1st at 00:00 UTC"


def test_compute_next_run_eta_hourly():
    """Verify next run time calculation for hourly cron."""
    # Given time: 2026-08-23 14:15:00 UTC
    now = datetime(2026, 8, 23, 14, 15, 0, tzinfo=timezone.utc)
    next_dt, eta_str = compute_next_run_eta("0 * * * *", from_time=now)

    assert next_dt == datetime(2026, 8, 23, 15, 0, 0, tzinfo=timezone.utc)
    assert "45m" in eta_str or "45 minutes" in eta_str


def test_compute_next_run_eta_step_minutes():
    """Verify next run calculation for */15 cron."""
    now = datetime(2026, 8, 23, 14, 12, 0, tzinfo=timezone.utc)
    next_dt, eta_str = compute_next_run_eta("*/15 * * * *", from_time=now)

    assert next_dt == datetime(2026, 8, 23, 14, 15, 0, tzinfo=timezone.utc)
    assert "3m" in eta_str or "3 minutes" in eta_str


def test_compute_next_run_eta_daily():
    """Verify next run calculation for daily cron."""
    now = datetime(2026, 8, 23, 14, 0, 0, tzinfo=timezone.utc)
    next_dt, eta_str = compute_next_run_eta("0 8 * * *", from_time=now)

    # Next 08:00 is next day (Aug 24)
    assert next_dt == datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)
    assert "18h" in eta_str or "18 hours" in eta_str
