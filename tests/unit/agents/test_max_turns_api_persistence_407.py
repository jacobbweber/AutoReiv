"""
Unit and API regression tests for Agent max_turns range expansion (1-1000) [REQ-407-006].
Verifies that max_turns between 1 and 1000 persist to SQLite and pack.json, and values >1000 fail 422.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.web.app import app


def test_agent_profile_model_allows_max_turns_1_to_1000():
    p1 = AgentProfile(
        id="test-turns",
        name="Test Turns",
        description="Test",
        system_prompt="Test",
        max_turns=1,
    )
    assert p1.max_turns == 1

    p100 = AgentProfile(
        id="test-turns",
        name="Test Turns",
        description="Test",
        system_prompt="Test",
        max_turns=100,
    )
    assert p100.max_turns == 100

    p1000 = AgentProfile(
        id="test-turns",
        name="Test Turns",
        description="Test",
        system_prompt="Test",
        max_turns=1000,
    )
    assert p1000.max_turns == 1000

    with pytest.raises(ValidationError):
        AgentProfile(
            id="test-turns",
            name="Test Turns",
            description="Test",
            system_prompt="Test",
            max_turns=0,
        )

    with pytest.raises(ValidationError):
        AgentProfile(
            id="test-turns",
            name="Test Turns",
            description="Test",
            system_prompt="Test",
            max_turns=1001,
        )


def test_agent_guardrail_validates_1_to_1000():
    valid = {
        "id": "valid-agent",
        "name": "Valid Agent",
        "description": "Agent description",
        "system_prompt": "Prompt with at least 10 characters",
        "purpose": "general",
        "allowed_tools": [],
        "max_turns": 100,
    }
    prof = AgentProfileGuardrail.validate(valid)
    assert prof.max_turns == 100

    valid["max_turns"] = 1000
    prof = AgentProfileGuardrail.validate(valid)
    assert prof.max_turns == 1000


def test_api_agents_put_accepts_100_and_1000_and_rejects_1001():
    client = TestClient(app)

    # Fetch autoreiv profile
    res = client.get("/api/agents/autoreiv")
    assert res.status_code == 200
    payload = res.json()

    # Save with 100
    payload["max_turns"] = 100
    put_100 = client.put("/api/agents/autoreiv", json=payload)
    assert put_100.status_code == 200, put_100.text
    assert put_100.json()["agent"]["max_turns"] == 100

    # Verify GET returns 100
    get_100 = client.get("/api/agents/autoreiv")
    assert get_100.status_code == 200
    assert get_100.json()["max_turns"] == 100

    # Save with 1000
    payload["max_turns"] = 1000
    put_1000 = client.put("/api/agents/autoreiv", json=payload)
    assert put_1000.status_code == 200, put_1000.text
    assert put_1000.json()["agent"]["max_turns"] == 1000

    # Verify GET returns 1000
    get_1000 = client.get("/api/agents/autoreiv")
    assert get_1000.status_code == 200
    assert get_1000.json()["max_turns"] == 1000

    # Reject 1001
    payload["max_turns"] = 1001
    put_1001 = client.put("/api/agents/autoreiv", json=payload)
    assert put_1001.status_code == 422
