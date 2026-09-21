"""
Tests for Skill Capability Linter consolidation and new skills validation [CARD-366, REQ-CONSOL-001..006].
"""

from pathlib import Path

from src.application.skills.linter import CapabilityLinter, SkillContractCompiler


def test_linter_resolves_without_import_error(tmp_path: Path):
    """Linter must resolve user and platform data dirs without ImportError [REQ-CONSOL-006]."""
    fake_data = tmp_path / "user_data"
    fake_data.mkdir(parents=True)
    linter = CapabilityLinter()
    # Before fix, this fails with ImportError on resolve_data_dir
    report = linter.lint_platform_and_user_skills(data_dir=fake_data)
    assert report is not None
    assert isinstance(report.scanned_count, int)


def test_consolidated_skills_exist_and_pass_lint():
    """Consolidated skills pass lint across platform packs."""
    repo_root = Path(__file__).resolve().parents[3]
    platform_packs_dir = repo_root / "platform-packs"

    expected_skills = [
        ("developer", "sdlc-engineering"),
        ("autoreiv", "agent-authoring"),
        ("autoreiv", "socratic-tutoring"),
    ]

    compiler = SkillContractCompiler()
    for pack_id, skill_name in expected_skills:
        skill_path = platform_packs_dir / pack_id / "skills" / skill_name / "SKILL.md"
        assert skill_path.is_file(), f"Expected skill {skill_name} at {skill_path}"

        text = skill_path.read_text(encoding="utf-8")
        contract, violations = compiler.compile(text, path=str(skill_path))

        error_violations = [v for v in violations if v.severity.value == "error"]
        assert not error_violations, f"Violations found for {skill_name}: {error_violations}"
        assert contract is not None
        assert len(contract.requires_tools) <= 6
        assert contract.verification is not None
        assert contract.verification.rule.strip() != ""
