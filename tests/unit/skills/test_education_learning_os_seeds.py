"""CARD-238 Learning OS Priming + Dual Coding skill seeds [REQ-LOS-012-001]."""

from __future__ import annotations

from pathlib import Path

from src.infrastructure.skills.seed import (
    BUNDLED_PACK_IDS,
    bundled_skill_md,
    seed_bundled_skill_packs,
)


def test_education_packs_are_bundled():
    assert "education-priming" in BUNDLED_PACK_IDS
    assert "education-dual-coding" in BUNDLED_PACK_IDS


def test_education_skill_md_files_exist_and_describe_modes():
    priming = bundled_skill_md("education-priming").read_text(encoding="utf-8")
    dual = bundled_skill_md("education-dual-coding").read_text(encoding="utf-8")
    assert "Education Priming" in priming
    assert "schema" in priming.lower() or "outline" in priming.lower()
    assert "prereq" in priming.lower() or "prerequisite" in priming.lower()
    assert "Education Dual Coding" in dual
    assert "mermaid" in dual.lower()
    assert "Lumina" not in dual


def test_seed_bundled_copies_education_packs_if_missing(tmp_path: Path):
    skills = tmp_path / "skills"
    seed_bundled_skill_packs(skills)
    assert (skills / "education-priming" / "SKILL.md").is_file()
    assert (skills / "education-dual-coding" / "SKILL.md").is_file()
    # copy-if-missing: do not clobber
    marker = "USER EDIT"
    dest = skills / "education-priming" / "SKILL.md"
    dest.write_text(marker, encoding="utf-8")
    seed_bundled_skill_packs(skills)
    assert dest.read_text(encoding="utf-8") == marker
