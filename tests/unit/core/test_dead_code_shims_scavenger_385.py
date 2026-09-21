"""Negative assertion tests asserting that retired shims and dead code paths remain excised [CARD-385]."""

import importlib
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def test_card313_shim_file_does_not_exist():
    """Verify that _card313_import_data_dir_migrate.py is excised and cannot be imported."""
    shim_path = Path("src/web/routers/_card313_import_data_dir_migrate.py")
    assert not shim_path.exists(), f"Orphaned shim {shim_path} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.web.routers._card313_import_data_dir_migrate")


def test_factory_router_shim_file_does_not_exist():
    """Verify that src/web/routers/factory.py is excised and cannot be imported."""
    shim_path = Path("src/web/routers/factory.py")
    assert not shim_path.exists(), f"Orphaned shim {shim_path} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.web.routers.factory")


def test_factory_runner_shim_file_does_not_exist():
    """Verify that src/application/orchestration/factory_runner.py is excised and cannot be imported."""
    shim_path = Path("src/application/orchestration/factory_runner.py")
    assert not shim_path.exists(), f"Orphaned shim {shim_path} still exists on disk"

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.application.orchestration.factory_runner")


def test_orchestrator_does_not_export_factory_runner_alias():
    """Verify that src.application.agent_training_factory.orchestrator does not export FactoryRunner."""
    from src.application.agent_training_factory import orchestrator

    assert not hasattr(orchestrator, "FactoryRunner"), (
        "orchestrator still exposes obsolete FactoryRunner alias"
    )


def test_app_state_and_web_app_factory_orchestrator_cleanliness():
    """Verify that the FastAPI application mounts the agent_training_factory router cleanly and has no factory_runner alias."""
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    app = create_app(state_store=SQLiteStateStore(db_path=":memory:"))
    assert hasattr(app.state, "factory_orchestrator"), "app.state missing canonical factory_orchestrator"
    assert not hasattr(app.state, "factory_runner"), "app.state still exposes obsolete factory_runner alias"

    client = TestClient(app)
    resp = client.get("/api/agent_training_factory/jobs")
    assert resp.status_code == 200
    assert "jobs" in resp.json()
