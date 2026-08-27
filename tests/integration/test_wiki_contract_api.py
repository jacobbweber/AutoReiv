"""
Wiki Studio Vault & Knowledge Graph API Contract Integration Tests [REQ-API-002].
"""

import os

import pytest
from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def wiki_client(tmp_path):
    db_path = str(tmp_path / "test_wiki.db")
    wiki_path = str(tmp_path / "wiki")
    os.makedirs(wiki_path, exist_ok=True)

    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    app = create_app(
        state_store=store,
        wiki_path=wiki_path,
    )
    with TestClient(app) as client:
        yield client


def test_wiki_tree_endpoint(wiki_client):
    """GET /api/wiki/tree returns vault tree structure."""
    response = wiki_client.get("/api/wiki/tree")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "inbox" in data or "notes" in data or "resources" in data


def test_wiki_note_crud_lifecycle(wiki_client):
    """Full lifecycle: POST create note, GET note, PUT update note, DELETE note."""
    # 1. Create Note
    create_payload = {
        "title": "Architecture Overview",
        "category": "notes",
        "domain": "Systems",
        "topic": "Architecture",
        "document_type": "concept",
        "tags": ["core", "arch"],
        "summary": "High level system architecture",
        "content": "This note links to [[Database Design]].",
    }
    create_res = wiki_client.post("/api/wiki/note", json=create_payload)
    assert create_res.status_code == 200
    create_data = create_res.json()
    assert create_data.get("success") is True
    rel_path = create_data["path"]

    # 2. Get Note
    get_res = wiki_client.get(f"/api/wiki/note?path={rel_path}")
    assert get_res.status_code == 200
    note_data = get_res.json()
    assert note_data.get("success") is True
    assert note_data["title"] == "Architecture Overview"
    assert note_data["meta"]["domain"] == "Systems"
    assert "Database Design" in note_data["content"]

    # 3. Update Note
    update_payload = {
        "path": rel_path,
        "content": "Updated content with link to [[Storage Layer]].",
        "update_frontmatter": {"summary": "Updated system architecture"},
    }
    update_res = wiki_client.put("/api/wiki/note", json=update_payload)
    assert update_res.status_code == 200
    update_data = update_res.json()
    assert update_data.get("success") is True

    # Verify update
    get_updated = wiki_client.get(f"/api/wiki/note?path={rel_path}")
    assert get_updated.status_code == 200
    assert "Storage Layer" in get_updated.json()["content"]

    # 4. Search Note
    search_res = wiki_client.get("/api/wiki/search?q=Storage")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data["hits"]) > 0

    # 5. Delete Note
    del_res = wiki_client.delete(f"/api/wiki/note?path={rel_path}")
    assert del_res.status_code == 200
    assert del_res.json().get("success") is True

    # 6. Verify 404 after deletion
    get_deleted = wiki_client.get(f"/api/wiki/note?path={rel_path}")
    assert get_deleted.status_code == 404


def test_wiki_graph_and_mindmap_endpoints(wiki_client):
    """GET /api/wiki/graph and GET /api/wiki/mindmap return structured node/edge graph data."""
    # Seed a note first
    wiki_client.post(
        "/api/wiki/note",
        json={
            "title": "Kernel Core",
            "category": "notes",
            "domain": "AI",
            "topic": "Kernel",
            "tags": ["kernel"],
            "summary": "Core kernel note",
            "content": "Links to [[Memory Store]].",
        },
    )

    graph_res = wiki_client.get("/api/wiki/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data

    mindmap_res = wiki_client.get("/api/wiki/mindmap")
    assert mindmap_res.status_code == 200
    mindmap_data = mindmap_res.json()
    assert "nodes" in mindmap_data
    assert "edges" in mindmap_data


def test_export_chat_to_wiki_inbox(wiki_client):
    """POST /api/export/wiki saves session messages to inbox notes."""
    export_payload = {
        "title": "Session Summary Export",
        "category": "inbox",
        "agent_id": "assistant",
        "session_id": "sess-12345",
        "messages": [
            {"role": "user", "content": "Explain Redis caching."},
            {"role": "assistant", "content": "Redis is an in-memory data store..."},
        ],
        "tags": ["session", "export"],
    }

    res = wiki_client.post("/api/export/wiki", json=export_payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "success"
    assert "filepath" in data
    assert "inbox" in data["filepath"]
