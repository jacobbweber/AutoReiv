"""
Unit tests for Wiki Web REST API Endpoints [REQ-WIKI-006].
"""

import tempfile

import pytest
from fastapi.testclient import TestClient

from src.application.wiki.service import WikiService
from src.web.app import create_app


@pytest.fixture
def wiki_client():
    with tempfile.TemporaryDirectory() as tmp:
        wiki_service = WikiService(wiki_root=tmp)
        app = create_app()
        # Inject test wiki service
        app.state.wiki_service = wiki_service
        client = TestClient(app)
        yield client, wiki_service


def test_wiki_api_tree_and_create(wiki_client):
    client, wiki_service = wiki_client

    # 1. Fetch initial tree
    res = client.get("/api/wiki/tree")
    assert res.status_code == 200
    data = res.json()
    assert "inbox" in data
    assert "notes" in data
    assert "resources" in data

    # 2. Create note
    payload = {
        "title": "FastAPI Web Integration",
        "content": "# FastAPI\nHigh performance web framework.",
        "domain": "information_technology",
        "topic": "web_dev",
        "tags": ["fastapi", "python"],
        "summary": "FastAPI integration notes.",
    }
    create_res = client.post("/api/wiki/note", json=payload)
    assert create_res.status_code == 200
    create_data = create_res.json()
    assert create_data["success"] is True
    rel_path = create_data["path"]

    # 3. Read note
    read_res = client.get(f"/api/wiki/note?path={rel_path}")
    assert read_res.status_code == 200
    read_data = read_res.json()
    assert read_data["title"] == "FastAPI Web Integration"
    assert "High performance" in read_data["content"]
    assert read_data["meta"]["domain"] == "information_technology"

    # 4. Search note
    search_res = client.get("/api/wiki/search?q=fastapi")
    assert search_res.status_code == 200
    hits = search_res.json().get("hits", [])
    assert len(hits) >= 1

    # 5. Graph
    graph_res = client.get("/api/wiki/graph")
    assert graph_res.status_code == 200
    assert "nodes" in graph_res.json()

    # 6. Overview
    overview_res = client.get("/api/wiki/overview")
    assert overview_res.status_code == 200
    assert "FastAPI Web Integration" in overview_res.json().get("overview", "")
