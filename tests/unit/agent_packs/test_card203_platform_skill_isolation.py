"""
CARD-203: Pure Platform Skill Isolation and Pack Boundary Guardrails.
Verifies that agent pack skills remain jailed within packs/<agent_id>/skills/,
never bleed into $DATA_DIR/skills/, and that retired personas are purged.
"""

import sqlite3
from pathlib import Path

from src.application.agent_packs.service import AgentPackService
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.data.resolver import (
    BLED_AGENT_SKILL_IDS,
    prune_bled_platform_skills,
    prune_orphan_databases,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import platform_packs_root
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS


def test_prune_bled_platform_skills(tmp_path: Path):
    """Verify that known agent skills that bled into $DATA_DIR/skills are safely pruned."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True)

    # Create legitimate platform seeds
    for sid in BUNDLED_PACK_IDS:
        seed_dir = skills_dir / sid
        seed_dir.mkdir(parents=True)
        (seed_dir / "SKILL.md").write_text(f"# {sid}\nPlatform skill runbook.", encoding="utf-8")

    # Create bled agent skills
    for bled in BLED_AGENT_SKILL_IDS:
        bled_dir = skills_dir / bled
        bled_dir.mkdir(parents=True)
        (bled_dir / "SKILL.md").write_text(f"# {bled}\nBled agent skill.", encoding="utf-8")

    pruned = prune_bled_platform_skills(skills_dir)
    assert set(pruned) == BLED_AGENT_SKILL_IDS

    # Verify all legitimate platform seeds survived
    for sid in BUNDLED_PACK_IDS:
        assert (skills_dir / sid / "SKILL.md").is_file()

    # Verify all bled skills were completely deleted
    for bled in BLED_AGENT_SKILL_IDS:
        assert not (skills_dir / bled).exists()


def test_prune_orphan_databases(tmp_path: Path):
    """Verify that empty legacy storage.db and 0-byte state.db are pruned."""
    # 1. 0-byte autoreiv_state.db
    state_db = tmp_path / "autoreiv_state.db"
    state_db.touch()
    assert state_db.is_file()

    # 2. empty autoreiv storage.db
    storage_dir = tmp_path / "packs" / "autoreiv"
    storage_dir.mkdir(parents=True)
    empty_storage = storage_dir / "storage.db"
    conn = sqlite3.connect(str(empty_storage))
    conn.close()

    # 3. non-empty real database (must NOT be pruned)
    populated_storage = storage_dir / "autoreiv_memory.db"
    conn = sqlite3.connect(str(populated_storage))
    conn.execute("CREATE TABLE memories (id INT, text TEXT)")
    conn.commit()
    conn.close()

    pruned = prune_orphan_databases(tmp_path)
    assert str(state_db) in pruned
    assert str(empty_storage) in pruned
    assert not state_db.exists()
    assert not empty_storage.exists()
    assert populated_storage.exists()


def test_import_path_never_copies_skills_to_platform_skills_dir(tmp_path: Path):
    """Verify that importing an agent pack never copies its skills into $DATA_DIR/skills/."""
    data_dir = tmp_path / "data"
    skills_dir = data_dir / "skills"
    packs_dir = data_dir / "packs"
    skills_dir.mkdir(parents=True)
    packs_dir.mkdir(parents=True)

    store = SQLiteStateStore(db_path=str(data_dir / "database" / "autoreiv.db"))
    store.initialize_db()
    agent_reg = BuiltinAgentRegistry(state_store=store)

    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=agent_reg,
        store=store,
    )

    # Create a dummy agent pack with a dedicated skill
    sample_pack = tmp_path / "sample_pack"
    sample_pack.mkdir()
    (sample_pack / "skills" / "my_custom_skill").mkdir(parents=True)
    (sample_pack / "skills" / "my_custom_skill" / "SKILL.md").write_text(
        "---\nname: My Custom Skill\ndescription: Domain skill.\n---\n# SOP\n",
        encoding="utf-8",
    )
    (sample_pack / "pack.json").write_text(
        '{"schema_version": "1.1", "id": "custom-agent", "name": "Custom Agent", "allowed_skill": ["my_custom_skill"]}',
        encoding="utf-8",
    )

    # Import the pack
    service.import_path(sample_pack)

    # Verify that the skill is NOT in data_dir/skills
    assert not (skills_dir / "my_custom_skill").exists()

    # Verify that the skill IS in data_dir/packs/custom-agent/skills/
    installed_skill = packs_dir / "custom-agent" / "skills" / "my_custom_skill" / "SKILL.md"
    assert installed_skill.is_file()


def test_platform_packs_directory_purged_of_retired_personas():
    """Verify that retired factory personas are absent from platform-packs/."""
    root = platform_packs_root()
    retired = ["coder", "critic", "inspector", "sandbox_runner"]
    for r in retired:
        assert not (root / r).exists(), f"Retired persona folder '{r}' must not exist in platform-packs/"
