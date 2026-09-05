"""
Integration tests for CARD-116: Agent Cognitive Memory REST Endpoints.
"""

from fastapi.testclient import TestClient

from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.web.app import create_app


def test_agent_memory_api_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    app = create_app()
    client = TestClient(app)

    # 1. Create a custom agent
    agent_payload = {
        "id": "mem-bot",
        "name": "Memory Bot",
        "system_prompt": "You are an agent with cognitive memory.",
        "memory_enabled": True,
        "memory_retention_days": 45,
        "pinned_memory": "Rule: Always answer with precision.",
    }
    resp = client.post("/api/agents", json=agent_payload)
    assert resp.status_code == 200, resp.text

    # Seed some facts directly via repository
    repo = AgentMemoryRepository(agent_id="mem-bot", data_dir=tmp_path)
    repo.initialize_schema()
    fact_id = repo.add_semantic_fact(
        entity="user",
        attribute="favorite_os",
        value="Windows 11",
        category="environment",
    )
    repo.record_session_summary("s-10", "Tested memory endpoints.")

    # 2. GET /api/agents/{agent_id}/memory
    get_resp = client.get("/api/agents/mem-bot/memory")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["memory_enabled"] is True
    assert data["retention_days"] == 45
    assert len(data["facts"]) >= 1
    assert data["facts"][0]["attribute"] == "favorite_os"
    assert len(data["summaries"]) >= 1

    # 3. GET with search query filter
    search_resp = client.get("/api/agents/mem-bot/memory?query=Windows")
    assert search_resp.status_code == 200
    sdata = search_resp.json()
    assert len(sdata["facts"]) >= 1
    assert sdata["facts"][0]["value"] == "Windows 11"

    # 4. DELETE /api/agents/{agent_id}/memory/facts/{fact_id}
    del_fact_resp = client.delete(f"/api/agents/mem-bot/memory/facts/{fact_id}")
    assert del_fact_resp.status_code == 200
    assert del_fact_resp.json()["status"] == "ok"

    # Verify fact is gone
    get_after_del = client.get("/api/agents/mem-bot/memory")
    assert len(get_after_del.json()["facts"]) == 0

    # 5. DELETE /api/agents/{agent_id}/memory (purge all)
    purge_resp = client.delete("/api/agents/mem-bot/memory")
    assert purge_resp.status_code == 200
    assert purge_resp.json()["status"] == "ok"

    # Verify everything purged
    get_after_purge = client.get("/api/agents/mem-bot/memory")
    assert len(get_after_purge.json()["summaries"]) == 0
