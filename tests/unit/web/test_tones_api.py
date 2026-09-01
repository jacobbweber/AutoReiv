"""
Unit & Integration Tests for Custom Tone Registry & REST API [CARD-131, REQ-TONE-001 - REQ-TONE-005].
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


def test_list_tones_seeded_with_builtins(client):
    """Verify GET /api/tones returns built-in presets by default."""
    res = client.get("/api/tones")
    assert res.status_code == 200
    tones = res.json()
    assert len(tones) >= 6
    ids = [t["id"] for t in tones]
    assert "default" in ids
    assert "technical" in ids
    assert "concise" in ids
    assert "friendly" in ids
    assert "academic" in ids
    assert "socratic" in ids
    # All seeded should have is_builtin=True
    assert all(t["is_builtin"] for t in tones if t["id"] in ["default", "technical", "concise", "friendly", "academic", "socratic"])


def test_create_and_fetch_custom_tone(client):
    """Verify POST /api/tones creates a new custom tone."""
    payload = {
        "id": "executive_briefing",
        "name": "Executive Briefing",
        "description": "High-level summary with key metrics",
        "directive": "Tone directive: High-level brevity. Lead with the bottom line.",
    }
    res = client.post("/api/tones", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "executive_briefing"
    assert data["name"] == "Executive Briefing"
    assert data["is_builtin"] is False

    # Fetch all and ensure it is listed
    res2 = client.get("/api/tones")
    all_tones = res2.json()
    created = next((t for t in all_tones if t["id"] == "executive_briefing"), None)
    assert created is not None
    assert created["directive"] == payload["directive"]


def test_update_custom_tone(client):
    """Verify PUT /api/tones/{id} updates a custom tone."""
    # Create custom tone first
    client.post("/api/tones", json={
        "id": "pirate",
        "name": "Pirate Mode",
        "directive": "Tone directive: Speak like a pirate.",
    })

    # Update it
    update_res = client.put("/api/tones/pirate", json={
        "name": "Captain Pirate",
        "description": "Nautical tone",
        "directive": "Tone directive: Ahoy matey, speak like a swashbuckling pirate captain!",
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["name"] == "Captain Pirate"
    assert updated["directive"] == "Tone directive: Ahoy matey, speak like a swashbuckling pirate captain!"


def test_delete_custom_tone(client):
    """Verify DELETE /api/tones/{id} deletes custom tone."""
    client.post("/api/tones", json={
        "id": "temp_tone",
        "name": "Temporary Tone",
        "directive": "Tone directive: Temp",
    })

    del_res = client.delete("/api/tones/temp_tone")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Verify not in list
    res = client.get("/api/tones")
    assert not any(t["id"] == "temp_tone" for t in res.json())


def test_builtin_tones_are_protected(client):
    """Verify built-in tones cannot be deleted or overwritten."""
    # Attempt to delete built-in
    del_res = client.delete("/api/tones/technical")
    assert del_res.status_code == 400
    assert "built-in" in del_res.json()["detail"].lower()

    # Attempt to update built-in
    put_res = client.put("/api/tones/technical", json={
        "name": "Hacked Technical",
        "directive": "Hacked",
    })
    assert put_res.status_code == 400
    assert "built-in" in put_res.json()["detail"].lower()


def test_save_agent_with_custom_tone(client):
    """Verify selecting and saving a custom tone on an agent profile persists."""
    # 1. Create custom tone
    client.post("/api/tones", json={
        "id": "executive_briefing",
        "name": "Executive Briefing",
        "directive": "Tone directive: Executive brevity.",
    })

    # 2. Update built-in assistant with custom tone
    update_res = client.put("/api/agents/assistant", json={
        "name": "Assistant",
        "system_prompt": "Helpful AI assistant",
        "tone": "executive_briefing",
    })
    assert update_res.status_code == 200
    assert update_res.json()["agent"]["tone"] == "executive_briefing"

    # 3. Fetch agents list and single agent to verify tone is preserved
    get_res = client.get("/api/agents/assistant")
    assert get_res.status_code == 200
    assert get_res.json()["tone"] == "executive_briefing"

    # 4. Create new custom agent with custom tone
    create_custom_res = client.post("/api/agents", json={
        "id": "exec-agent",
        "name": "Exec Agent",
        "system_prompt": "Executive persona",
        "tone": "executive_briefing",
    })
    assert create_custom_res.status_code == 200
    assert create_custom_res.json()["agent"]["tone"] == "executive_briefing"

    # 5. Fetch custom agent and verify persistence
    get_custom_res = client.get("/api/agents/exec-agent")
    assert get_custom_res.status_code == 200
    assert get_custom_res.json()["tone"] == "executive_briefing"


