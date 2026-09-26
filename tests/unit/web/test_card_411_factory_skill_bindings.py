"""CARD-411: Factory save is the skill/tool writer; bindings live in SQLite."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.repositories.skill_bindings import SkillToolBindingRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

SKILL_MD = """---
name: Widget Notes
description: Read a widget
tier: pack
requires_tools:
  - inspect_widget
  - not_a_real_tool
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Widget was read.
---

# Widget Notes

Keep-this-sentence.
"""


@pytest.mark.asyncio
async def test_factory_save_persists_sqlite_bindings_not_pack_json(tmp_path, monkeypatch):
    """REQ-411-002/003: valid catalog tools bind in SQLite; pack.json is not the binding writer."""
    data_dir = tmp_path / "data"
    db_path = tmp_path / "card411.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    tool_reg = app.state.tool_registry
    tool_reg.register_tool(
        "inspect_widget",
        "Inspect a widget",
        {"type": "object", "properties": {}},
        lambda **_kwargs: "ok",
    )

    agent_dir = data_dir / "packs" / "autoreiv"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "pack.json").write_text(
        json.dumps({
            "id": "autoreiv",
            "allowed_skill": ["wiki"],
            "skills": [{"id": "wiki", "name": "Wiki", "tools": ["wiki_note_read"]}],
        }),
        encoding="utf-8",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        rejected = await ac.post(
            "/api/skill_studio/save",
            json={
                "agent_id": "autoreiv",
                "skill_id": "widget-notes",
                "skill_content": SKILL_MD,
                "requires_tools": ["inspect_widget", "not_a_real_tool"],
                "auto_pin": True,
            },
        )
        assert rejected.status_code == 400
        assert "not_a_real_tool" in rejected.json()["detail"]
        assert not (data_dir / "skills" / "widget-notes" / "SKILL.md").exists()
        assert SkillToolBindingRepository(db_path=str(db_path)).get("widget-notes") is None

        saved = await ac.post(
            "/api/skill_studio/save",
            json={
                "agent_id": "autoreiv",
                "skill_id": "widget-notes",
                "skill_name": "Widget Notes",
                "name": "Widget Notes",
                "description": "Read a widget",
                "tier": "user",
                "safety": {"read_only": True, "requires_hitl": False, "untrusted_input_allowed": False},
                "skill_content": SKILL_MD,
                "requires_tools": ["inspect_widget"],
                "auto_pin": True,
            },
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["binding_store"] == "sqlite"
        assert body["requires_tools"] == ["inspect_widget"]

        store_md = (data_dir / "skills" / "widget-notes" / "SKILL.md").read_text(encoding="utf-8")
        pack_md = (data_dir / "packs" / "autoreiv" / "skills" / "widget-notes" / "SKILL.md").read_text(encoding="utf-8")
        assert "inspect_widget" in store_md
        assert "not_a_real_tool" not in store_md
        assert "Keep-this-sentence." in store_md
        assert store_md == pack_md

        pack = json.loads((agent_dir / "pack.json").read_text(encoding="utf-8"))
        skill_row = next(item for item in pack["skills"] if item["id"] == "widget-notes")
        assert "tools" not in skill_row
        wiki_row = next(item for item in pack["skills"] if item["id"] == "wiki")
        assert wiki_row["tools"] == ["wiki_note_read"]

        record = SkillToolBindingRepository(db_path=str(db_path)).get("widget-notes")
        assert record is not None
        assert record["requires_tools"] == ["inspect_widget"]
        assert record["tier"] == "user"

        # Stale pack.json tools must not override the SQLite binding.
        skill_row["tools"] = ["stale_pack_tool"]
        pack["skills"] = [wiki_row, skill_row]
        (agent_dir / "pack.json").write_text(json.dumps(pack), encoding="utf-8")

        agent = app.state.registry.get_agent("autoreiv")
        assert agent is not None
        assert "widget-notes" in (agent.allowed_skill or [])
        names = [tool.name for tool in tool_reg.get_tools_for_agent(agent, active_skills=["widget-notes"])]
        assert "inspect_widget" in names
        assert "stale_pack_tool" not in names

        opened = await ac.get("/api/skill_studio/skills/widget-notes", params={"agent_id": "autoreiv"})
        assert opened.status_code == 200
        assert opened.json()["requires_tools"] == ["inspect_widget"]
        assert opened.json()["binding_source"] == "sqlite"

        cleared = await ac.post(
            "/api/skill_studio/save",
            json={
                "agent_id": "autoreiv",
                "skill_id": "widget-notes",
                "skill_content": store_md,
                "requires_tools": [],
                "auto_pin": True,
            },
        )
        assert cleared.status_code == 200
        assert cleared.json()["requires_tools"] == []
        cleared_md = (data_dir / "skills" / "widget-notes" / "SKILL.md").read_text(encoding="utf-8")
        assert "inspect_widget" not in cleared_md
        assert "Keep-this-sentence." in cleared_md
        assert SkillToolBindingRepository(db_path=str(db_path)).get("widget-notes")["requires_tools"] == []
        names_after = [tool.name for tool in tool_reg.get_tools_for_agent(agent, active_skills=["widget-notes"])]
        assert "inspect_widget" not in names_after
