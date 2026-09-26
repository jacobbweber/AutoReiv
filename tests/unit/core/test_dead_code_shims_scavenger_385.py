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


def test_factory_orchestrator_package_does_not_exist():
    """CARD-497: the whole agent_training_factory package (and its FactoryRunner alias) is deleted."""
    assert not Path("src/application/agent_training_factory").exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.application.agent_training_factory.orchestrator")


def test_app_state_and_web_app_factory_orchestrator_cleanliness():
    """CARD-497: no Factory orchestrator, repo or runner on app.state, and the Factory jobs route is gone."""
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    app = create_app(state_store=SQLiteStateStore(db_path=":memory:"))
    for attr in ("factory_orchestrator", "factory_repo", "factory_runner"):
        assert not hasattr(app.state, attr), f"app.state still exposes {attr}"

    client = TestClient(app)
    resp = client.get("/api/agent_training_factory/jobs")
    assert resp.status_code == 404
