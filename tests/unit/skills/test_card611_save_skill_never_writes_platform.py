"""CARD-611: saving a skill never writes the shipped platform/skills/<id>/SKILL.md.

save_skill writes only the data copy (skills_dir/<id>/SKILL.md), keeps the live copy's other frontmatter
(tools, tier, ...), and the data copy is what loads next. The self-learning save (commit_skill of an
online-ACE proposal) and its undo (rollback_skill) leave the platform file byte-identical; undo removes the
data copy so the shipped skill is live again.
"""

from __future__ import annotations

import pytest

import src.infrastructure.content.store as store_mod
from src.application.orchestration.ace_online import record_failed_turn_delta
from src.application.orchestration.skill_proposals import apply_skill_proposal_decision, commit_skill
from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.content.store import REPO_PLATFORM, ContentStore, split_frontmatter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

PLATFORM_ID = "wiki"
PLATFORM_FILE = REPO_PLATFORM / "skills" / PLATFORM_ID / "SKILL.md"


@pytest.fixture
def shipped():
    before = (PLATFORM_FILE.read_bytes(), PLATFORM_FILE.stat().st_mtime_ns)
    yield split_frontmatter(before[0].decode("utf-8"))[0]
    assert (PLATFORM_FILE.read_bytes(), PLATFORM_FILE.stat().st_mtime_ns) == before, "platform SKILL.md was written"


def _meta(path):
    return split_frontmatter(path.read_text(encoding="utf-8"))[0]


def test_temp_folder_save_writes_only_the_data_copy(tmp_path, shipped):
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")
    saved = catalog.save_skill(PLATFORM_ID, "Wiki (mine)", "My wiki notes.", "Search first.")
    data_copy = tmp_path / "skills" / PLATFORM_ID / "SKILL.md"
    assert saved["success"] and saved["manifest"]["path"] == str(data_copy.resolve())
    meta = _meta(data_copy)
    assert meta["name"] == "Wiki (mine)" and meta["description"] == "My wiki notes."
    assert meta["tools"] == shipped["tools"]  # the shipped grants are kept, not dropped
    assert "Search first." in data_copy.read_text(encoding="utf-8")


def test_data_folder_save_goes_through_the_store_and_is_what_loads(tmp_path, monkeypatch, shipped):
    monkeypatch.setattr(store_mod, "_STORE", ContentStore(data_root=tmp_path))
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")
    catalog.save_skill(PLATFORM_ID, "Wiki (mine)", "My wiki notes.", "Search first.")
    loaded = store_mod.get_store().skills.load(PLATFORM_ID)
    assert loaded.source == "user" and loaded.path == tmp_path / "skills" / PLATFORM_ID / "SKILL.md"
    assert loaded.based_on == store_mod.get_store().skills.shipped_hash(PLATFORM_ID)
    assert loaded.tools == shipped["tools"] and "Search first." in loaded.body
    assert catalog.read_skill(PLATFORM_ID)["manifest"]["origin"] == "user"


def test_a_second_save_keeps_the_data_copy_tools(tmp_path, shipped):
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")
    data_copy = tmp_path / "skills" / PLATFORM_ID / "SKILL.md"
    data_copy.parent.mkdir(parents=True)
    data_copy.write_text("---\nname: w\ndescription: d\ntools:\n- wiki_note_read\ntier: user\n---\nold\n", encoding="utf-8")
    catalog.save_skill(PLATFORM_ID, "w2", "d2", "new")
    meta = _meta(data_copy)
    assert meta == {"name": "w2", "description": "d2", "tools": ["wiki_note_read"], "tier": "user"}


def test_a_new_id_is_created_in_the_data_folder(tmp_path):
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills")
    assert catalog.save_skill("c611-new", "New", "A new skill.", "Body.")["success"]
    assert _meta(tmp_path / "skills" / "c611-new" / "SKILL.md") == {"name": "New", "description": "A new skill."}
    assert not (REPO_PLATFORM / "skills" / "c611-new").exists()


def test_self_learning_save_and_undo_never_touch_the_platform_file(tmp_path, shipped):
    db = SQLiteStateStore(db_path=tmp_path / "state.db")
    db.initialize_db()
    data_dir = tmp_path / "data"
    catalog = UserSkillCatalog(skills_dir=data_dir / "skills")
    drafted = record_failed_turn_delta(
        db, skill_id=PLATFORM_ID, data_dir=data_dir, session_id="s611", agent_id="autoreiv",
        tool_errors=[{"tool_name": "wiki_note_read", "error": "Timed out after 30s"}], catalog=catalog,
    )
    assert drafted.get("proposal_id"), drafted
    apply_skill_proposal_decision(db, proposal_id=drafted["proposal_id"], decision="approved")
    committed = commit_skill(db, proposal_id=drafted["proposal_id"], data_dir=data_dir, catalog=catalog, overwrite=True)
    data_copy = data_dir / "skills" / PLATFORM_ID / "SKILL.md"
    assert committed["disk_written"] is True and data_copy.is_file()
    assert _meta(data_copy)["tools"] == shipped["tools"]
    rolled = catalog.rollback_skill(PLATFORM_ID, committed["snapshot_id"])
    assert rolled["success"] and "SKILL.md" in rolled["removed"]
    assert not data_copy.exists()  # undo: the shipped skill is live again
