"""CARD-570: agents and skills load from platform/ with user copies in the data dir (ADR-0062)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.content.store import (
    ContentStore,
    ReservedIdError,
    configure,
    is_known_tool,
    reset_store,
    set_tool_registry,
)


@pytest.fixture
def platform(tmp_path: Path) -> Path:
    root = tmp_path / "platform"
    (root / "agents").mkdir(parents=True)
    (root / "agents" / "helper.md").write_text(
        "---\nname: Helper\ndescription: d\nskills:\n  - notes\n---\nShipped prompt.\n", encoding="utf-8"
    )
    (root / "skills" / "notes").mkdir(parents=True)
    (root / "skills" / "notes" / "SKILL.md").write_text(
        "---\nname: Notes\ndescription: d\ntools:\n  - wiki_note_read\n---\nShipped body.\n", encoding="utf-8"
    )
    return root


@pytest.fixture
def store(tmp_path: Path, platform: Path) -> ContentStore:
    return ContentStore(data_root=tmp_path / "data", platform_root=platform)


def test_shipped_only_loads_from_platform(store):
    item = store.agents.load("helper")
    assert item.source == "shipped" and item.body.strip() == "Shipped prompt."
    assert not item.edited and store.skills.load("notes").tools == ["wiki_note_read"]


def test_user_copy_wins_and_use_shipped_removes_it(store, tmp_path):
    store.agents.save("helper", {"name": "Mine", "skills": ["notes"]}, "My prompt.\n")
    item = store.agents.load("helper")
    assert item.source == "user" and item.edited and item.meta["name"] == "Mine"
    assert (tmp_path / "data" / "agents" / "helper.md").is_file()
    assert store.agents.use_shipped("helper") is True
    assert store.agents.load("helper").source == "shipped"
    assert store.agents.use_shipped("helper") is False  # nothing left to remove


def test_shipped_changed_note(store, platform):
    store.agents.save("helper", {"name": "Mine"}, "My prompt.\n")
    assert store.agents.load("helper").shipped_changed is False
    (platform / "agents" / "helper.md").write_text("---\nname: Helper v2\n---\nNew shipped.\n", encoding="utf-8")
    item = store.agents.load("helper")
    assert item.source == "user" and item.shipped_changed is True


def test_delete_hides_shipped_and_persists(store, tmp_path, platform):
    assert store.agents.delete("helper") == "hidden"
    assert store.agents.load("helper") is None
    fresh = ContentStore(data_root=tmp_path / "data", platform_root=platform)  # like a restart
    assert fresh.agents.load("helper") is None and "helper" in fresh.agents.hidden()
    assert fresh.agents.unhide("helper") and fresh.agents.load("helper") is not None


def test_delete_removes_user_created(store):
    store.skills.save("mine", {"name": "Mine", "tools": []}, "b\n", create=True)
    assert store.skills.delete("mine") == "deleted"
    assert store.skills.load("mine") is None


def test_shipped_ids_are_reserved(store):
    with pytest.raises(ReservedIdError):
        store.agents.save("helper", {"name": "X"}, "p\n", create=True)
    with pytest.raises(ReservedIdError):
        store.skills.save("notes", {"name": "X"}, "p\n", create=True)


def test_unknown_tool_warns_and_grants_nothing(store):
    store.skills.save("odd", {"name": "Odd", "tools": ["wiki_note_read", "no_such_tool"]}, "b\n", create=True)

    class _Reg:
        def get_tool_definition(self, name):
            return object() if name == "wiki_note_read" else None

    assert store.validate_tools(["wiki_note_read"]) == {"odd": ["no_such_tool"]}
    set_tool_registry(_Reg())
    try:
        assert is_known_tool("wiki_note_read") and not is_known_tool("no_such_tool")
    finally:
        reset_store()


def test_every_shipped_skill_names_only_known_tools():
    from src.web.app import create_app

    with TestClient(create_app()) as client:
        warnings = client.app.state.registry.skill_tool_warnings
    assert warnings == {}, f"shipped skills name unknown tools: {warnings}"


def test_api_studio_edit_use_shipped_hide_and_reserved(tmp_path, monkeypatch):
    from src.web.app import create_app

    data = tmp_path / "data"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(data / "database" / "autoreiv.db"))
    reset_store()
    with TestClient(create_app()) as client:
        agent = client.get("/api/agents/tutor").json()
        assert agent["file_status"]["source"] == "shipped"
        agent["system_prompt"] = agent["system_prompt"] + "\nCARD-570 edit."
        assert client.put("/api/agents/tutor", json=agent).status_code == 200
        edited = client.get("/api/agents/tutor").json()
        assert edited["file_status"]["edited"] is True and "CARD-570 edit." in edited["system_prompt"]
        assert (data / "agents" / "tutor.md").is_file()

        assert client.post("/api/agents/tutor/use-shipped").status_code == 200
        back = client.get("/api/agents/tutor").json()
        assert back["file_status"]["source"] == "shipped" and "CARD-570 edit." not in back["system_prompt"]

        refused = client.post("/api/agents", json={"id": "developer", "name": "Dev", "description": "d", "system_prompt": "You are a developer copy."})
        assert refused.status_code == 409

        assert client.delete("/api/agents/architect").status_code == 200
        assert "architect" not in {a["id"] for a in client.get("/api/agents").json()}
    reset_store()
    with TestClient(create_app()) as client:  # restart: still hidden, then unhide
        assert "architect" not in {a["id"] for a in client.get("/api/agents").json()}
        assert client.post("/api/agents/architect/unhide").status_code == 200
        assert "architect" in {a["id"] for a in client.get("/api/agents").json()}
    configure(None)
