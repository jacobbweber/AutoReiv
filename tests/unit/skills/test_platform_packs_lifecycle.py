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


def test_platform_pack_ids_include_developer_and_tutor():
    """Active platform pack IDs must include autoreiv, direct, developer, and tutor [CARD-388, REQ-388-001]."""
    assert PLATFORM_PACK_IDS == ("autoreiv", "direct", "developer", "tutor")


def test_retired_platform_packs_exclude_developer_and_tutor():
    """Retired platform packs must NOT include developer or tutor [CARD-388, REQ-388-006]."""
    assert "developer" not in RETIRED_PLATFORM_PACK_IDS
    assert "tutor" not in RETIRED_PLATFORM_PACK_IDS
    for retired_id in ("forge", "assistant", "wiki", "homelab", "homelab-admin", "finance"):
        assert retired_id in RETIRED_PLATFORM_PACK_IDS


def test_cleanup_orphaned_platform_packs_preserves_developer_and_tutor(tmp_path: Path):
    """Cleanup routine must NOT purge developer or tutor from user data [CARD-388, REQ-388-006]."""
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(parents=True)

    # Create dummy directories for retired and active packs
    (packs_dir / "autoreiv").mkdir()
    (packs_dir / "direct").mkdir()
    (packs_dir / "developer").mkdir()
    (packs_dir / "tutor").mkdir()
    (packs_dir / "forge").mkdir()

    cleaned = cleanup_orphaned_platform_packs(packs_dir)

    assert "developer" not in cleaned
    assert "tutor" not in cleaned
    assert "forge" in cleaned

    assert (packs_dir / "developer").exists()
    assert (packs_dir / "tutor").exists()
    assert not (packs_dir / "forge").exists()
    assert (packs_dir / "autoreiv").exists()
    assert (packs_dir / "direct").exists()


def test_canonical_agent_id_preserves_developer_and_tutor():
    """Queries for developer and tutor resolve to themselves, not aliased to autoreiv [CARD-388, REQ-388-006]."""
    assert canonical_agent_id("developer") == "developer"
    assert canonical_agent_id("tutor") == "tutor"
    assert canonical_agent_id("forge") == "autoreiv"
    assert canonical_agent_id("autoreiv") == "autoreiv"
    assert canonical_agent_id("direct") == "direct"
