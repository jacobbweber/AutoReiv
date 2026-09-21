"""
Negative assertion tests for CARD-395 dead code scavenger and pruning pass.

Guarantees that retired frontend and backend dead paths remain excised:
- Retired standalone skills.js studio
- Retired workflows router, service, repository, and domain models
- Retired /api/chat/goal endpoint
"""

import importlib
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.application.agent_packs.service import AgentPackService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def test_skills_studio_file_excised():
    """Verify that standalone skills.js studio is deleted from disk."""
    p = Path("src/web/static/modules/studios/skills.js")
    assert not p.exists(), f"Retired studio file {p} still exists on disk"


def test_workflows_router_file_excised():
    """Verify that workflows router is deleted from disk and cannot be imported."""
    p = Path("src/web/routers/workflows.py")
    assert not p.exists(), f"Orphaned router file {p} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.web.routers.workflows")


def test_workflow_service_file_excised():
    """Verify that workflow service is deleted from disk and cannot be imported."""
    p = Path("src/application/orchestration/workflow_service.py")
    assert not p.exists(), f"Orphaned service file {p} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.application.orchestration.workflow_service")


def test_workflow_repository_file_excised():
    """Verify that workflow repository is deleted from disk and cannot be imported."""
    p = Path("src/infrastructure/memory/repositories/workflows.py")
    assert not p.exists(), f"Orphaned repository file {p} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.infrastructure.memory.repositories.workflows")


def test_workflow_domain_file_excised():
    """Verify that workflow domain model is deleted from disk and cannot be imported."""
    p = Path("src/domain/orchestration/workflow.py")
    assert not p.exists(), f"Orphaned domain model file {p} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.domain.orchestration.workflow")


def test_agent_pack_service_no_workflow_helpers():
    """Verify that AgentPackService does not expose legacy workflow copy methods."""
    assert not hasattr(AgentPackService, "_copy_workflows_out"), "AgentPackService still exposes _copy_workflows_out"
    assert not hasattr(AgentPackService, "_copy_workflows_in"), "AgentPackService still exposes _copy_workflows_in"


def test_app_unmounts_workflow_endpoints_and_goal_endpoint():
    """Verify that FastAPI app returns 404 for all excised workflow and goal endpoints."""
    app = create_app(state_store=SQLiteStateStore(db_path=":memory:"))
    client = TestClient(app)

    resp_wf = client.get("/api/agents/general-assistant/workflows")
    assert resp_wf.status_code == 404

    resp_goal = client.post(
        "/api/chat/goal",
        json={"agent_id": "general-assistant", "session_id": "s1", "goal": "test"},
    )
    assert resp_goal.status_code == 404
