"""CARD-418: Skill Studio save writes the skill store and SQLite without an agent brief."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.repositories.skill_bindings import SkillToolBindingRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

SKILL_MD = """---
name: Dock Notes
description: Read a dock note
tier: user
requires_tools:
  - inspect_widget
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
---

# Dock Notes

Keep-this-sentence.
"""


@pytest.mark.asyncio
async def test_skill_studio_save_without_agent_writes_store_and_sqlite(tmp_path, monkeypatch):
    """REQ-418-003: dock save persists body + SQLite bindings and does not invent pack.json tools."""
    data_dir = tmp_path / "data"
    db_path = tmp_path / "card418.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    app.state.tool_registry.register_tool(
        "inspect_widget",
        "Inspect a widget",
        {"type": "object", "properties": {}},
        lambda **_kwargs: "ok",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        saved = await ac.post(
            "/api/agent_training_factory/scaffold/save",
            json={
                "skill_id": "dock-notes",
                "name": "Dock Notes",
                "description": "Read a dock note",
                "tier": "user",
                "safety": {"read_only": True, "requires_hitl": False, "untrusted_input_allowed": False},
                "skill_content": SKILL_MD,
                "requires_tools": ["inspect_widget"],
                "auto_pin": False,
            },
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["binding_store"] == "sqlite"
        assert body["requires_tools"] == ["inspect_widget"]
        assert body["pinned"] is False
        assert body["agent_id"] is None

        store_md = (data_dir / "skills" / "dock-notes" / "SKILL.md").read_text(encoding="utf-8")
        assert "inspect_widget" in store_md
        assert "Keep-this-sentence." in store_md
        assert list((data_dir / "packs").rglob("skills/dock-notes/SKILL.md")) == []
        for pack_json in (data_dir / "packs").rglob("pack.json"):
            pack = json.loads(pack_json.read_text(encoding="utf-8"))
            assert "dock-notes" not in (pack.get("allowed_skill") or [])
            for skill in pack.get("skills") or []:
                if isinstance(skill, dict) and skill.get("id") == "dock-notes":
                    raise AssertionError(f"skill row leaked into {pack_json}")

        record = SkillToolBindingRepository(db_path=str(db_path)).get("dock-notes")
        assert record is not None
        assert record["requires_tools"] == ["inspect_widget"]

        opened = await ac.get("/api/agent_training_factory/skills/dock-notes")
        assert opened.status_code == 200
        opened_body = opened.json()
        assert opened_body["requires_tools"] == ["inspect_widget"]
        assert opened_body["binding_source"] == "sqlite"
        assert "not found" not in json.dumps(opened_body).lower()
