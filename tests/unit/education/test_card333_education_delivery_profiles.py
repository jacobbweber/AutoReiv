"""CARD-333: Education delivery profiles.

Verifies:
- [REQ-EDU-DELIVERY-001]: Selectable presentation / delivery profile (e.g. ADHD/focus, Pomodoro, Calm Focus, Default) exists.
- [REQ-EDU-DELIVERY-002]: Delivery profile is separate from academic depth (kindergarten->graduate); does not replace CARD-327 depth model.
- [REQ-EDU-DELIVERY-003]: Studio control / snapshot for delivery profile is visually and structurally separate from academic depth.
- [REQ-EDU-DELIVERY-004]: Empty / unset states are honest (no fake "profile applied" theatre; clean default fallback).
- [REQ-EDU-DELIVERY-005]: Reopen/restart safety for active delivery profile fact in memory.db.
"""

from __future__ import annotations

from pathlib import Path

from src.application.education.course import course_chrome_snapshot
from src.application.education.depth import calculate_topic_depth, record_topic_depth
from src.application.education.environment import (
    PROFILE_ADHD_BITE,
    PROFILE_CALM_FOCUS,
    PROFILE_DEFAULT,
    PROFILE_POMODORO,
    get_active_delivery_profile,
    get_delivery_profile,
    list_delivery_profiles,
    select_delivery_profile,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _assert_memory_db_path(db: Path) -> None:
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_req_edu_delivery_001_selectable_delivery_profiles():
    """[REQ-EDU-DELIVERY-001] Built-in delivery profiles include default, calm_focus, adhd_bite, pomodoro."""
    profiles = list_delivery_profiles()
    p_ids = {p["id"] for p in profiles}
    assert {PROFILE_DEFAULT, PROFILE_CALM_FOCUS, PROFILE_ADHD_BITE, PROFILE_POMODORO}.issubset(p_ids)

    # Check ADHD bite-size parameters
    adhd = get_delivery_profile(PROFILE_ADHD_BITE)
    assert adhd["bite_size"] is True
    assert adhd["max_prompt_chars"] == 160
    assert adhd["max_items_per_wave"] == 1
    assert adhd["timer_seconds"] == 120

    # Check Pomodoro parameters
    pomodoro = get_delivery_profile(PROFILE_POMODORO)
    assert pomodoro["timer_seconds"] == 1500
    assert pomodoro["bite_size"] is False


def test_req_edu_delivery_002_delivery_profile_separate_from_academic_depth(tmp_path: Path):
    """[REQ-EDU-DELIVERY-002] Selecting delivery profile adjusts presentation only; never mutates depth ladder or mastery ledger."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Quantum Teleportation"

    # Seed 6 passing mastery items -> Level 2 (Practitioner / High School)
    for i in range(6):
        repo.upsert_education_mastery(
            item_id=f"qt_item_{i}",
            topic=topic,
            prompt=f"Quantum teleportation prompt {i}",
            expected_answer=f"Answer {i}",
            grade="pass",
        )
    record_topic_depth(repo, topic=topic)
    depth_before = calculate_topic_depth(repo, topic=topic)
    assert depth_before["level"] == 2
    assert depth_before["name"] == "practitioner"
    assert depth_before["academic_rank"] == "High School"

    # Select ADHD bite-size delivery profile
    res = select_delivery_profile(repo, PROFILE_ADHD_BITE)
    assert res["success"] is True
    assert res["profile"]["id"] == PROFILE_ADHD_BITE

    # Verify academic depth remains completely unchanged
    depth_after = calculate_topic_depth(repo, topic=topic)
    assert depth_after["level"] == 2
    assert depth_after["name"] == "practitioner"
    assert depth_after["academic_rank"] == "High School"

    # Select Pomodoro profile and verify depth remains untouched
    res2 = select_delivery_profile(repo, PROFILE_POMODORO)
    assert res2["success"] is True
    depth_after2 = calculate_topic_depth(repo, topic=topic)
    assert depth_after2["level"] == 2



def test_req_edu_delivery_003_chrome_snapshot_contains_separate_depth_and_delivery(tmp_path: Path):
    """[REQ-EDU-DELIVERY-003] Chrome snapshot returns both 'depth' and 'delivery_profile' as distinct top-level keys."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Distributed Systems"
    select_delivery_profile(repo, PROFILE_CALM_FOCUS)

    snapshot = course_chrome_snapshot(repo, topic_id=topic)
    assert "depth" in snapshot, "snapshot must contain depth"
    assert "delivery_profile" in snapshot, "snapshot must contain delivery_profile"

    # Depth owns academic rank & ladder
    assert snapshot["depth"]["academic_rank"] in ["Kindergarten", "Elementary", "High School", "Undergraduate", "Masters"]

    # Delivery profile owns presentation tone, timer, and bite_size
    delivery = snapshot["delivery_profile"]
    assert delivery["id"] == PROFILE_CALM_FOCUS
    assert delivery["timer_seconds"] == 600
    assert "tone" in delivery


def test_req_edu_delivery_004_honest_unset_and_fallback(tmp_path: Path):
    """[REQ-EDU-DELIVERY-004] Unset or unknown profile cleanly and honestly resolves to 'default' (no fake theatre)."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    # Brand new repo with no profile set
    active = get_active_delivery_profile(repo)
    assert active["id"] == PROFILE_DEFAULT
    assert active["label"] == "Default"

    # Selecting unknown profile gracefully resolves to default
    unknown = get_delivery_profile("non_existent_profile_xyz")
    assert unknown["id"] == PROFILE_DEFAULT


def test_req_edu_delivery_005_restart_safety(tmp_path: Path):
    """[REQ-EDU-DELIVERY-005] Active profile selection is durable across process restarts."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()

    select_delivery_profile(repo1, PROFILE_ADHD_BITE)
    active1 = get_active_delivery_profile(repo1)
    assert active1["id"] == PROFILE_ADHD_BITE

    # Re-open database from disk simulating app restart
    repo2 = AgentMemoryRepository(db_path=db)
    active2 = get_active_delivery_profile(repo2)
    assert active2["id"] == PROFILE_ADHD_BITE
    assert active2["bite_size"] is True
    assert active2["max_prompt_chars"] == 160
