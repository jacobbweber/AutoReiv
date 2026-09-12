"""CARD-248: Education Environment - study-session delivery profiles (presentation only)."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.environment import (
    DELIVERY_PROFILES,
    ENVIRONMENT_CATEGORY,
    ENVIRONMENT_ENTITY,
    PROFILE_ADHD_BITE,
    PROFILE_CALM_FOCUS,
    PROFILE_DEFAULT,
    PROFILE_POMODORO,
    apply_delivery_to_ask,
    assert_profile_does_not_touch_srs,
    build_environment_ask_clause,
    get_active_delivery_profile,
    get_delivery_profile,
    list_delivery_profiles,
    select_delivery_profile,
    shape_quiz_presentation,
    summarize_environment,
)
from src.application.education.srs import next_due_after_grade
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _seed(repo, item_id, topic, grade="unseen", miss_count=0, pass_count=0, next_due=None, prompt=None, expected="answer"):
    repo.upsert_education_mastery(
        item_id=item_id,
        topic=topic,
        wiki_path=f"notes/{topic}.md",
        prompt=prompt or f"Prompt for {item_id}?",
        expected_answer=expected,
        grade=grade,
        next_due=next_due,
    )
    if miss_count or pass_count or grade != "unseen":
        with repo.get_connection() as conn:
            conn.execute(
                "UPDATE education_mastery SET grade=?, miss_count=?, pass_count=?, next_due=COALESCE(?, next_due) WHERE item_id=?",
                (grade, miss_count, pass_count, next_due, item_id),
            )


def test_builtin_profiles_include_adhd_bite_and_timers():
    profiles = list_delivery_profiles()
    ids = {p["id"] for p in profiles}
    assert PROFILE_DEFAULT in ids
    assert PROFILE_ADHD_BITE in ids
    assert PROFILE_CALM_FOCUS in ids
    assert PROFILE_POMODORO in ids
    adhd = get_delivery_profile(PROFILE_ADHD_BITE)
    assert adhd["bite_size"] is True
    assert adhd["timer_seconds"] == 120
    assert adhd["tone"] == "short_supportive"
    assert "never replaces" in (adhd.get("research_note") or "").lower() or "delivery-only" in (
        adhd.get("research_note") or ""
    ).lower()


def test_unknown_profile_falls_back_to_default():
    p = get_delivery_profile("not-a-real-profile")
    assert p["id"] == PROFILE_DEFAULT


def test_environment_module_does_not_own_srs_or_llm():
    import src.application.education.environment as mod

    assert assert_profile_does_not_touch_srs(inspect.getsource(mod)) is True


def test_shape_quiz_presentation_does_not_mutate_ledger_fields(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    due = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    long_prompt = (
        "Explain in detail the full standing Job HITL park mastery ledger Routine to Job "
        "SRS resurfacing path including every edge case and operator step you can remember."
    )
    _seed(
        repo,
        "edu_env_1",
        "Env",
        grade="miss",
        miss_count=1,
        next_due=due,
        prompt=long_prompt,
        expected="ledger owns due",
    )
    row = repo.get_education_mastery("edu_env_1")
    assert row is not None
    before_due = row.get("next_due")
    before_stage = row.get("interval_stage")
    before_grade = row.get("grade")
    before_prompt = row.get("prompt")

    shaped = shape_quiz_presentation([row], PROFILE_ADHD_BITE)
    assert shaped["replaces_srs"] is False
    assert shaped["replaces_ledger"] is False
    assert shaped["due_source"] == "mastery_ledger_srs"
    assert shaped["bite_size"] is True
    assert shaped["timer_seconds"] == 120
    assert shaped["presented_count"] == 1
    presented = shaped["items"][0]
    assert presented["item_id"] == "edu_env_1"
    assert presented["next_due"] == before_due
    assert presented["interval_stage"] == before_stage
    assert presented["grade"] == before_grade
    # Display may truncate; ledger prompt field on the *row* must stay intact
    assert presented.get("presentation_prompt")
    assert len(presented["presentation_prompt"]) <= int(DELIVERY_PROFILES[PROFILE_ADHD_BITE]["max_prompt_chars"]) + 5
    # Original prompt still present on shaped copy (ledger truth)
    assert presented.get("prompt") == before_prompt

    # Re-read mastery: unchanged
    again = repo.get_education_mastery("edu_env_1")
    assert again.get("next_due") == before_due
    assert again.get("interval_stage") == before_stage
    assert again.get("grade") == before_grade
    assert again.get("prompt") == before_prompt


def test_adhd_bite_limits_presentation_wave_not_due_set(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    due = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(3):
        _seed(
            repo,
            f"edu_env_wave_{i}",
            "Wave",
            grade="miss",
            miss_count=1,
            next_due=due,
            prompt=f"Wave prompt {i}?",
            expected=f"a{i}",
        )
    rows = [repo.get_education_mastery(f"edu_env_wave_{i}") for i in range(3)]
    shaped = shape_quiz_presentation(rows, PROFILE_ADHD_BITE)
    assert shaped["ledger_count"] == 3
    assert shaped["presented_count"] == 1
    assert len(shaped["all_items"]) == 3
    # Due list from ledger still has all three regardless of profile
    due_rows = repo.list_due_education_mastery(as_of=now)
    due_ids = {r.get("item_id") for r in due_rows}
    assert "edu_env_wave_0" in due_ids
    assert "edu_env_wave_1" in due_ids
    assert "edu_env_wave_2" in due_ids


def test_select_profile_persists_preference_not_srs(tmp_path):
    repo = _repo(tmp_path)
    result = select_delivery_profile(repo, PROFILE_CALM_FOCUS)
    assert result["selected"] is True
    assert result["replaces_srs"] is False
    assert result["profile"]["id"] == PROFILE_CALM_FOCUS
    active = get_active_delivery_profile(repo)
    assert active["id"] == PROFILE_CALM_FOCUS
    summary = summarize_environment(repo)
    assert summary["entity"] == ENVIRONMENT_ENTITY
    assert summary["category"] == ENVIRONMENT_CATEGORY
    assert summary["replaces_srs"] is False
    assert summary["active_profile"]["id"] == PROFILE_CALM_FOCUS


def test_apply_delivery_to_ask_adds_tone_and_timer_clause():
    ask = '[Education Studio] Teach me about "Jobs".'
    out = apply_delivery_to_ask(ask, PROFILE_POMODORO)
    assert "Delivery profile `pomodoro`" in out["ask"]
    assert "1500" in out["ask"]
    assert out["replaces_srs"] is False
    assert "Do NOT change next_due" in out["ask"]
    clause = build_environment_ask_clause(get_delivery_profile(PROFILE_ADHD_BITE))
    assert "bite-size" in clause.lower() or "micro-prompt" in clause.lower()
    assert "SRS" in clause


def test_srs_schedule_unchanged_by_profile_selection(tmp_path):
    """Profile cannot alter next_due_after_grade math."""
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    stage_a, due_a = next_due_after_grade(correct=True, interval_stage=0, now=now)
    select_delivery_profile(repo, PROFILE_ADHD_BITE)
    stage_b, due_b = next_due_after_grade(correct=True, interval_stage=0, now=now)
    assert stage_a == stage_b == 1
    assert due_a == due_b
    # Miss still resets to stage 0 / 1 day regardless of profile
    stage_m, due_m = next_due_after_grade(correct=False, interval_stage=3, now=now)
    assert stage_m == 0
    assert (due_m - now).days == 1
