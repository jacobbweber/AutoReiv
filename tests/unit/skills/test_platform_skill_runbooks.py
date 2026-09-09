from pathlib import Path

from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS


def test_bundled_pack_ids_include_all_platform_skills():
    """Verify all platform skill primitives have bundled seeds [CARD-200, REQ-SKILL-020]."""
    expected = {
        "wiki",
        "proposals",
        "build-agent-pack",
        "sandbox",
        "coordination",
        "worker",
        "planning",
        "verification",
    }
    assert expected.issubset(set(BUNDLED_PACK_IDS))


def test_user_catalog_resolves_platform_skill_seeds(tmp_path: Path):
    """Verify UserSkillCatalog resolves platform skill runbooks from bundled seeds [CARD-200]."""
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")

    for skill_id in ("sandbox", "coordination", "worker", "planning", "verification", "wiki", "proposals"):
        res = catalog.read_pack(skill_id)
        assert res.get("success") is True, f"Failed to read platform skill runbook for '{skill_id}': {res.get('error')}"
        assert res.get("manifest", {}).get("id") == skill_id
        assert len(res.get("instructions", "")) > 10


def test_user_catalog_resolves_fleet_shared_skills(tmp_path: Path):
    """Verify UserSkillCatalog resolves fleet shared skills like manage-opentofu-hyperv [CARD-200]."""
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")

    res = catalog.read_pack("manage-opentofu-hyperv")
    assert res.get("success") is True, f"Failed to read fleet shared skill: {res.get('error')}"
    assert "OpenTofu" in res.get("instructions", "") or "Hyper-V" in res.get("instructions", "")


def test_nonexistent_pack_returns_clean_not_found(tmp_path: Path):
    """Verify non-existent packs return 'Pack <id> not found' without mentioning archive [CARD-200]."""
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")
    res = catalog.read_pack("totally-nonexistent-skill-xyz")
    assert res.get("success") is False
    assert res.get("not_found") is True
    assert "Archived" not in res.get("error", "")
    assert "totally-nonexistent-skill-xyz" in res.get("error", "")
