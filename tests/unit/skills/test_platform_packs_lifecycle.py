"""
Tests for Platform Packs consolidation and lifecycle cleanup [CARD-366, REQ-CONSOL-004].
"""

from pathlib import Path

from src.domain.agents.profiles import canonical_agent_id
from src.infrastructure.skills.platform_packs import (
    PLATFORM_PACK_IDS,
    RETIRED_PLATFORM_PACK_IDS,
    cleanup_orphaned_platform_packs,
)


def test_platform_pack_ids_restricted_to_autoreiv_and_direct():
    """Active platform pack IDs must be strictly autoreiv and direct [REQ-CONSOL-004]."""
    assert PLATFORM_PACK_IDS == ("autoreiv", "direct")


def test_retired_platform_packs_include_developer_tutor_forge():
    """Retired platform packs must include developer, tutor, forge, homelab, and finance [REQ-CONSOL-004, REQ-CONSOL-005]."""
    for retired_id in ("developer", "tutor", "forge", "assistant", "wiki", "homelab", "finance"):
        assert retired_id in RETIRED_PLATFORM_PACK_IDS


def test_cleanup_orphaned_platform_packs_removes_retired(tmp_path: Path):
    """Cleanup routine must purge retired packs from user data packs directory [REQ-CONSOL-004]."""
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(parents=True)

    # Create dummy directories for retired and active packs
    (packs_dir / "autoreiv").mkdir()
    (packs_dir / "direct").mkdir()
    (packs_dir / "developer").mkdir()
    (packs_dir / "tutor").mkdir()
    (packs_dir / "forge").mkdir()

    cleaned = cleanup_orphaned_platform_packs(packs_dir)

    assert "developer" in cleaned
    assert "tutor" in cleaned
    assert "forge" in cleaned

    assert not (packs_dir / "developer").exists()
    assert not (packs_dir / "tutor").exists()
    assert not (packs_dir / "forge").exists()
    assert (packs_dir / "autoreiv").exists()
    assert (packs_dir / "direct").exists()


def test_canonical_agent_id_aliases_retired_personas_to_autoreiv():
    """Legacy queries for developer, tutor, or forge resolve to autoreiv [REQ-CONSOL-004]."""
    assert canonical_agent_id("developer") == "autoreiv"
    assert canonical_agent_id("tutor") == "autoreiv"
    assert canonical_agent_id("forge") == "autoreiv"
    assert canonical_agent_id("autoreiv") == "autoreiv"
    assert canonical_agent_id("direct") == "direct"
