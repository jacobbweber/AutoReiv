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
    assert "inbox" in data["filepath"].lower()


def test_curate_inbox_api_endpoint(wiki_client):
    """POST /api/wiki/curate triggers autonomous curation across 00_Inbox."""
    # 1. Create note in inbox
    create_res = wiki_client.post(
        "/api/wiki/note",
        json={
            "title": "Staged Network Notes",
            "category": "inbox",
            "domain": "systems_engineering",
            "topic": "networking",
            "content": "Here is what you requested! VLAN and subnet architecture.",
        },
    )
    assert create_res.status_code == 200

    # 2. Trigger curation
    curate_res = wiki_client.post("/api/wiki/curate")
    assert curate_res.status_code == 200
    curate_data = curate_res.json()
    assert curate_data["success"] is True
    assert curate_data["curated_count"] >= 1

    # 3. Verify note has graduated
    tree_res = wiki_client.get("/api/wiki/tree")
    assert tree_res.status_code == 200
    tree = tree_res.json()
    assert len(tree["inbox"]) == 0
    assert "systems_engineering" in tree["notes"]


def test_wiki_folder_deletion_api(wiki_client):
    """Verify DELETE /api/wiki/folder endpoint for subfolder deletion and root protection [REQ-WIKI-024, REQ-WIKI-025]."""
    # 1. Create a note in a subfolder
    create_res = wiki_client.post(
        "/api/wiki/note",
        json={
            "title": "Topic For Deletion",
            "category": "notes",
            "domain": "delete_domain",
            "topic": "delete_topic",
            "content": "Temporary note.",
        },
    )
    assert create_res.status_code == 200

    # 2. Attempt to delete protected root folder -> 400 Bad Request
    root_del = wiki_client.delete("/api/wiki/folder?path=01_Notes")
    assert root_del.status_code == 400
    assert "protected" in root_del.json()["detail"].lower()

    # 3. Delete valid subfolder -> 200 OK
    sub_del = wiki_client.delete("/api/wiki/folder?path=01_Notes/delete_domain/delete_topic")
    assert sub_del.status_code == 200
    assert sub_del.json()["success"] is True


def test_wiki_templates_api(wiki_client):
    """Verify GET /api/wiki/templates and GET /api/wiki/template endpoints [REQ-WIKI-032]."""
    res = wiki_client.get("/api/wiki/templates")
    assert res.status_code == 200
    templates = res.json()
    assert isinstance(templates, list)
    assert len(templates) >= 6

    slugs = [t["slug"] for t in templates]
    assert "feynman-technique" in slugs
    assert "concept-map-system-hub" in slugs

    # Single template retrieval
    single_res = wiki_client.get("/api/wiki/template?slug=feynman-technique")
    assert single_res.status_code == 200
    tmpl = single_res.json()
    assert tmpl["slug"] == "feynman-technique"
    assert "Feynman" in tmpl["title"]
    assert "content" in tmpl

    # Non-existent template -> 404
    missing_res = wiki_client.get("/api/wiki/template?slug=non-existent-template")
    assert missing_res.status_code == 404

