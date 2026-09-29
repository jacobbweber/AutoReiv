"""
Unit tests for CARD-148: Agent Pack storage manifest, pack export/import, and SQLite persistence.
"""








def test_agent_api_eagerly_creates_storage_db(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    app = create_app()
    client = TestClient(app)

    payload = {
        "name": "Eager Finance Tracker",
        "description": "Tracks money",
        "system_prompt": "You track money in SQLite.",
        "storage_enabled": True,
        "storage_type": "sqlite",
    }
    res = client.post("/api/agents", json=payload)
    assert res.status_code == 200
    agent_id = res.json()["agent"]["id"]
    db_file = tmp_path / "data" / "agents" / agent_id / "storage.db"  # CARD-570 layout
    assert db_file.is_file()
