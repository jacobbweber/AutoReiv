"""CARD-436: Tutor Learning OS named skills resolve (pack + SKILL.md + inventory)."""

from __future__ import annotations

from pathlib import Path

from tests.unit.agent_skills.catalog import REPO_PLATFORM, load_platform_manifest, pack_dict

SKILLS_ROOT = REPO_PLATFORM / "skills"

LEARNING_OS_SKILL_IDS = (
    "start-resume-topic",
    "quiz-turn",
    "flashcard-turn",
    "due-review",
    "education-wiki-curation",
    "progress-summary",
)

ALL_TUTOR_SKILL_IDS = ("socratic-tutoring",) + LEARNING_OS_SKILL_IDS

INVENTORY_PATH = Path("docs/education/tutor-learning-os-inventory.md")


def test_tutor_pack_lists_learning_os_skills():
    manifest = load_platform_manifest("tutor")
    skill_ids = {s.id for s in manifest.skills}
    allowed = set(manifest.allowed_skill)
    assert set(ALL_TUTOR_SKILL_IDS) <= skill_ids
    assert set(ALL_TUTOR_SKILL_IDS) <= allowed
    for sid in LEARNING_OS_SKILL_IDS:
        assert sid in skill_ids
        assert sid in allowed


def test_tutor_learning_os_skill_md_files_resolve():
    skills_root = SKILLS_ROOT
    for sid in ALL_TUTOR_SKILL_IDS:
        skill_md = skills_root / sid / "SKILL.md"
        assert skill_md.is_file(), f"missing {skill_md}"
        body = skill_md.read_text(encoding="utf-8")
        assert body.strip().startswith("---"), f"{sid} missing frontmatter"
        assert "CARD-436" in body or sid == "socratic-tutoring"
        if sid in LEARNING_OS_SKILL_IDS:
            assert "/api/education/" in body or "education-" in body


def test_tutor_pack_json_skills_match_folders():
    raw = pack_dict("tutor")
    listed = [s["id"] for s in raw["skills"]]
    assert listed == list(ALL_TUTOR_SKILL_IDS)
    assert raw["allowed_skill"] == list(ALL_TUTOR_SKILL_IDS)
    for sid in ALL_TUTOR_SKILL_IDS:
        assert (SKILLS_ROOT / sid / "SKILL.md").is_file()


def test_inventory_catalogues_learning_os_skill_ids():
    assert INVENTORY_PATH.is_file()
    text = INVENTORY_PATH.read_text(encoding="utf-8")
    for sid in LEARNING_OS_SKILL_IDS:
        assert sid in text, f"inventory missing skill id {sid}"
    assert "Hard rails" in text or "hard rails" in text.lower()
    assert "#tab-education" in text
    assert "#view-education" in text
    assert "/api/education/quiz/grade" in text
    assert "/api/education/mastery" in text
    assert "/api/education/course" in text
    assert "/api/education/retention/run" in text

