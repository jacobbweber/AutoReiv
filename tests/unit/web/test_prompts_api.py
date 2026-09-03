"""
Unit & Integration Tests for Prompt Catalog REST API [CARD-147, REQ-PROMPT-001 - REQ-PROMPT-004].
"""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def client(store):
    app = create_app(state_store=store)
    return TestClient(app)


def test_list_prompts_seeded(client):
    res = client.get("/api/prompts")
    assert res.status_code == 200
    prompts = res.json()
    assert len(prompts) >= 4
    titles = [p["title"] for p in prompts]
    assert any("Health" in t for t in titles)
    assert any("Review" in t or "Summary" in t for t in titles)


def test_create_and_get_prompt(client):
    payload = {
        "title": "Database Schema Audit",
        "description": "Inspect foreign keys and missing indexes",
        "category": "system",
        "template_text": "Audit the SQLite tables for missing indices and invalid foreign keys.",
        "tags": ["sqlite", "database", "perf"],
    }
    res = client.post("/api/prompts", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["id"].startswith("prompt_")
    assert created["title"] == "Database Schema Audit"
    assert created["is_builtin"] is False

    res_list = client.get("/api/prompts?category=system")
    assert res_list.status_code == 200
    items = res_list.json()
    assert any(p["id"] == created["id"] for p in items)


def test_update_and_delete_prompt(client):
    payload = {
        "title": "Temp Prompt",
        "category": "general",
        "template_text": "Original text",
    }
    res = client.post("/api/prompts", json=payload)
    assert res.status_code == 201
    p_id = res.json()["id"]

    up_res = client.put(f"/api/prompts/{p_id}", json={"title": "Updated Prompt", "template_text": "New text"})
    assert up_res.status_code == 200
    updated = up_res.json()
    assert updated["title"] == "Updated Prompt"
    assert updated["template_text"] == "New text"

    del_res = client.delete(f"/api/prompts/{p_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    get_del = client.get(f"/api/prompts/{p_id}")
    assert get_del.status_code == 404
