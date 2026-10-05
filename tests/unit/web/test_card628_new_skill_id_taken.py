"""CARD-628: Skill Studio save refuses a taken id for a new skill; edits still overwrite."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.content.store import REPO_PLATFORM
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

MD = """---
name: Spot Check
description: A throwaway skill for CARD-628
tools: []
---
# Spot Check
Do nothing special.
"""


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    return app, data_dir


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_new_skill_refuses_shipped_id_with_suggested_free_id(app_env):
    app, data_dir = app_env
    shipped = REPO_PLATFORM / "skills" / "diagnostics" / "SKILL.md"
    assert shipped.is_file(), "platform diagnostics skill must exist for this proof"
    async with _client(app) as ac:
        resp = await ac.post(
            "/api/skill_studio/save",
            json={
                "skill_id": "diagnostics",
                "skill_content": MD,
                "name": "Diagnostics",
                "is_new": True,
            },
        )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "skill_id_taken"
    assert detail["skill_id"] == "diagnostics"
    assert "Diagnostics" in detail["existing_name"] or "diagnostics" in detail["existing_name"].lower()
    assert detail["suggested_id"] == "diagnostics_2"
    assert not (data_dir / "skills" / "diagnostics" / "SKILL.md").exists()
    assert shipped.read_text(encoding="utf-8").startswith("---")


@pytest.mark.asyncio
async def test_edit_of_same_id_still_saves(app_env):
    app, data_dir = app_env
    async with _client(app) as ac:
        first = await ac.post(
            "/api/skill_studio/save",
            json={"skill_id": "c628-edit", "skill_content": MD, "name": "C628 Edit", "is_new": True},
        )
        assert first.status_code == 200, first.text
        second = await ac.post(
            "/api/skill_studio/save",
            json={
                "skill_id": "c628-edit",
                "skill_content": MD.replace("Spot Check", "C628 Edit v2"),
                "name": "C628 Edit v2",
                "is_new": False,
            },
        )
    assert second.status_code == 200, second.text
    text = (data_dir / "skills" / "c628-edit" / "SKILL.md").read_text(encoding="utf-8")
    assert "C628 Edit v2" in text


@pytest.mark.asyncio
async def test_new_skill_can_use_suggested_free_id(app_env):
    app, data_dir = app_env
    async with _client(app) as ac:
        blocked = await ac.post(
            "/api/skill_studio/save",
            json={"skill_id": "diagnostics", "skill_content": MD, "is_new": True},
        )
        assert blocked.status_code == 409
        suggested = blocked.json()["detail"]["suggested_id"]
        ok = await ac.post(
            "/api/skill_studio/save",
            json={"skill_id": suggested, "skill_content": MD, "name": "Diagnostics 2", "is_new": True},
        )
    assert ok.status_code == 200, ok.text
    assert (data_dir / "skills" / suggested / "SKILL.md").is_file()
