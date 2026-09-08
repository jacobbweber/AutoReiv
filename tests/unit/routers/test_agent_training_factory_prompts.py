"""
Unit tests for Agent Training Factory Phase Prompt REST API [CARD-175].
Validates GET, PUT, and DELETE endpoints for phase instructions.
"""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.data.resolver import DataDirPaths
from src.web.app import app


@pytest.fixture
def client(tmp_path):
    # Set test data dir
    paths = DataDirPaths(
        root=tmp_path,
        db_path=tmp_path / "database" / "autoreiv.db",
        wiki_path=tmp_path / "wiki",
        skills_path=tmp_path / "skills",
        agents_path=tmp_path / "agents",
        job_templates_path=tmp_path / "templates" / "jobs",
        packs_path=tmp_path / "packs",
    )
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    app.state.data_paths = paths

    with TestClient(app) as test_client:
        yield test_client


def test_get_phase_instructions_endpoint(client):
    """GET /api/agent_training_factory/phases/instructions returns 8 phases with context variables."""
    resp = client.get("/api/agent_training_factory/phases/instructions")
    assert resp.status_code == 200
    data = resp.json()
    assert "phases" in data
    assert len(data["phases"]) == 8

    author = next((p for p in data["phases"] if p["id"] == "author"), None)
    assert author is not None
    assert "context_variables" in author
    assert len(author["context_variables"]) > 0
    assert author["is_custom"] is False


def test_put_and_delete_phase_instruction_endpoint(client):
    """PUT custom instructions and DELETE to reset to default."""
    custom_text = "Custom verify instructions with extra strictness."
    put_resp = client.put(
        "/api/agent_training_factory/phases/verify/instructions",
        json={"prompt": custom_text},
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["success"] is True
    assert data["phase"]["is_custom"] is True
    assert data["phase"]["active_prompt"] == custom_text

    # Verify GET reflects the update
    get_resp = client.get("/api/agent_training_factory/phases/instructions")
    verify_phase = next(p for p in get_resp.json()["phases"] if p["id"] == "verify")
    assert verify_phase["is_custom"] is True
    assert verify_phase["active_prompt"] == custom_text

    # Reset back to default
    del_resp = client.delete("/api/agent_training_factory/phases/verify/instructions")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["success"] is True
    assert del_data["phase"]["is_custom"] is False
    assert del_data["phase"]["active_prompt"] == del_data["phase"]["default_prompt"]
