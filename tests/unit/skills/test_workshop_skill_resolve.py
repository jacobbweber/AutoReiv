"""CARD-411: picker skill ids resolve to a SKILL.md the workshop can open."""

from pathlib import Path

import pytest

from src.application.skills.workshop import (
    accept_skill_id,
    list_workshop_skills,
    load_workshop_skill,
    locate_skill_markdown,
    operator_store_skills,
)

_RUNBOOK = """---
name: Dotted Notes
description: Notes for a dotted skill id
tier: user
requires_tools:
  - inspect_widget
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
---

# Dotted Notes

Keep-the-body.
"""


def test_seed_skill_resolves_without_a_data_dir_copy(tmp_path: Path):
    """Catalog ids such as coordination live in bundled seeds, not only platform-packs."""
    listed = {row["id"]: row for row in list_workshop_skills(tmp_path)}
    assert "coordination" in listed
    assert listed["coordination"]["source"] == "seed"
    path = locate_skill_markdown(tmp_path, "coordination")
    assert path is not None
    assert path.name == "SKILL.md"
    assert "seeds" in path.parts

    loaded = load_workshop_skill(
        tmp_path,
        "coordination",
        db_path=str(tmp_path / "missing-dir" / "autoreiv.db"),
    )
    assert loaded is not None
    assert loaded["skill_id"] == "coordination"
    assert loaded["name"] == "Agent Coordination & Handoff"
    assert "markdown_content" in loaded
    assert "# Agent Coordination" in loaded["markdown_content"]
    assert loaded["binding_source"] == "frontmatter"
    assert loaded["deletable"] is False
    assert listed["coordination"]["deletable"] is False


def test_pack_home_and_skill_store_and_dotted_id(tmp_path: Path):
    pack_skill = tmp_path / "packs" / "autoreiv" / "skills" / "pack-only" / "SKILL.md"
    pack_skill.parent.mkdir(parents=True)
    pack_skill.write_text(_RUNBOOK.replace("Dotted Notes", "Pack Only"), encoding="utf-8")

    dotted = tmp_path / "skills" / "My.Skill" / "SKILL.md"
    dotted.parent.mkdir(parents=True)
    dotted.write_text(_RUNBOOK, encoding="utf-8")

    nested = tmp_path / "skills" / "group" / "notes" / "SKILL.md"
    nested.parent.mkdir(parents=True)
    nested.write_text(_RUNBOOK.replace("Dotted Notes", "Grouped Notes"), encoding="utf-8")

    assert locate_skill_markdown(tmp_path, "pack-only", agent_id="autoreiv") == pack_skill
    assert locate_skill_markdown(tmp_path, "My.Skill") == dotted
    assert locate_skill_markdown(tmp_path, "group/notes") == nested

    rows = {row["id"]: row for row in list_workshop_skills(tmp_path)}
    assert "pack-only" in rows
    assert "My.Skill" in rows
    assert "group/notes" in rows
    assert "not-a-skill" not in rows
    assert rows["My.Skill"]["deletable"] is True
    assert rows["group/notes"]["deletable"] is True
    assert rows["pack-only"]["deletable"] is False

    loaded = load_workshop_skill(tmp_path, "My.Skill", db_path=str(tmp_path / "no.db"))
    assert loaded is not None
    assert loaded["name"] == "Dotted Notes"
    assert loaded["requires_tools"] == ["inspect_widget"]
    assert "Keep-the-body." in loaded["markdown_content"]
    assert loaded["deletable"] is True

    operator = {row["id"]: row for row in operator_store_skills(tmp_path)}
    assert set(operator) == {"My.Skill", "group/notes"}
    assert operator["My.Skill"]["requires_tools"] == ["inspect_widget"]
    assert operator["My.Skill"]["tools"] == [{"name": "inspect_widget"}]
    assert "pack-only" not in operator
    assert "coordination" not in operator


def test_unknown_and_unsafe_ids_do_not_resolve(tmp_path: Path):
    assert locate_skill_markdown(tmp_path, "not-a-real-skill") is None
    assert load_workshop_skill(tmp_path, "not-a-real-skill") is None
    assert accept_skill_id("../etc") is None
    assert accept_skill_id("foo/../bar") is None
    assert accept_skill_id("") is None


@pytest.mark.asyncio
async def test_get_workshop_skill_opens_seed_pack_and_dotted_ids(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "card411-resolve.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    dotted = data_dir / "skills" / "My.Skill" / "SKILL.md"
    dotted.parent.mkdir(parents=True)
    dotted.write_text(_RUNBOOK, encoding="utf-8")
    nested = data_dir / "skills" / "group" / "notes" / "SKILL.md"
    nested.parent.mkdir(parents=True)
    nested.write_text(_RUNBOOK.replace("Dotted Notes", "Grouped Notes"), encoding="utf-8")

    from httpx import ASGITransport, AsyncClient

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    app = create_app(state_store=SQLiteStateStore(db_path=str(db_path)))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listed = await ac.get("/api/skill_studio/skills")
        assert listed.status_code == 200
        ids = {row["id"] for row in listed.json()["skills"]}
        assert "coordination" in ids
        assert "My.Skill" in ids
        assert "group/notes" in ids

        opened = await ac.get("/api/skill_studio/skills/coordination")
        assert opened.status_code == 200
        body = opened.json()
        assert body["skill_id"] == "coordination"
        assert body["name"] == "Agent Coordination & Handoff"
        assert body["markdown_content"]

        dotted_res = await ac.get("/api/skill_studio/skills/My.Skill")
        assert dotted_res.status_code == 200
        assert dotted_res.json()["requires_tools"] == ["inspect_widget"]
        assert "Keep-the-body." in dotted_res.json()["markdown_content"]

        nested_res = await ac.get("/api/skill_studio/skills/group/notes")
        assert nested_res.status_code == 200
        assert nested_res.json()["skill_id"] == "group/notes"

        catalog = await ac.get("/api/skills/catalog")
        assert catalog.status_code == 200
        payload = catalog.json()
        operator_ids = {row["id"] for row in payload["operator_skills"]}
        platform_ids = {row["id"] for row in payload["platform_skills"]}
        assert "My.Skill" in operator_ids
        assert "group/notes" in operator_ids
        assert "coordination" not in operator_ids
        assert "My.Skill" not in platform_ids
        assert "coordination" in platform_ids

        missing = await ac.get("/api/skill_studio/skills/not-a-real-skill")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Skill 'not-a-real-skill' not found"

        unsafe = await ac.get("/api/skill_studio/skills/../etc")
        assert unsafe.status_code in (400, 404)
