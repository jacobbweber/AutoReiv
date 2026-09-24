"""
Web Router Integration Tests for System Version & Updates API [CARD-451].
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.system.serve_restarter import NoOpRestarter
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, StreamChunk
from src.domain.system.models import (
    UpdateApplyResult,
    UpdateCheckResult,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockProvider:
    provider_id = "mock-system"

    async def generate(self, *args, **kwargs):
        return CompletionResponse(
            model="mock",
            message=ChatMessage(role=Role.ASSISTANT, content="mock"),
        )

    async def stream(self, *args, **kwargs):
        yield StreamChunk(content="mock")


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "system_test.db"))
    store.initialize_db()

    mock_provider = MockProvider()
    gateway = MultiProviderGateway(default_provider_id="mock-system")
    gateway.register_provider(mock_provider)

    app = create_app(
        state_store=store,
        gateway_instance=gateway,
        wiki_path=str(tmp_path / "wiki"),
    )
    # Ensure tests never restart serve
    app.state.serve_restarter = NoOpRestarter()
    if getattr(app.state, "update_service", None):
        app.state.update_service.restarter = app.state.serve_restarter
    return TestClient(app)


def test_health_check_returns_dynamic_version(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"].startswith("0.")


def test_get_system_version_endpoint(client):
    resp = client.get("/api/system/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_version" in data
    assert "is_git" in data
    assert "deployment_mode" in data
    assert "ahead" in data
    assert "behind" in data
    assert data.get("remote_name") == "origin"


def test_get_and_put_update_config_endpoints(client):
    resp = client.get("/api/system/updates/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "auto_update_enabled" in cfg
    assert cfg["auto_update_enabled"] is False

    put_resp = client.put(
        "/api/system/updates/config",
        json={"auto_update_enabled": True, "auto_update_time": "02:30"},
    )
    assert put_resp.status_code == 200
    new_cfg = put_resp.json()
    assert new_cfg["auto_update_enabled"] is True
    assert new_cfg["auto_update_time"] == "02:30"

    verify_resp = client.get("/api/system/updates/config")
    assert verify_resp.json()["auto_update_time"] == "02:30"


def test_check_for_updates_endpoint(client):
    with patch(
        "src.application.system.update_service.UpdateService.check_for_updates"
    ) as mock_check:
        mock_check.return_value = UpdateCheckResult(
            update_available=True,
            current_version="0.23.0",
            current_commit="cd85cbd",
            remote_commit="f1a2b3c",
            commits_behind=2,
            channel="qa",
            upstream_url="https://github.com/jacobbweber/AutoReiv.git",
            release_notes="Fix: Minor updates",
            checked_at="2026-09-09T00:00:00Z",
        )
        resp = client.get("/api/system/updates/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["update_available"] is True
        assert data["commits_behind"] == 2


def test_apply_update_endpoint_uses_injected_restarter(client):
    with patch(
        "src.application.system.update_service.UpdateService.apply_update"
    ) as mock_apply:
        mock_apply.return_value = UpdateApplyResult(
            success=True,
            backup_path="/data/autoreiv.db.bak-123",
            previous_commit="cd85cbd",
            new_commit="f1a2b3c",
            message="Update applied cleanly.",
            restart_required=True,
            restart_scheduled=True,
        )
        resp = client.post("/api/system/updates/apply")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["new_commit"] == "f1a2b3c"


def test_branches_and_history_endpoints(client):
    with patch(
        "src.application.system.update_service.UpdateService.list_branches"
    ) as mock_list:
        from src.domain.system.models import BranchListItem, BranchListResult

        mock_list.return_value = BranchListResult(
            branches=[BranchListItem(name="qa", is_local=True, is_current=True)],
            current="qa",
        )
        resp = client.get("/api/system/updates/branches")
        assert resp.status_code == 200
        assert resp.json()["current"] == "qa"

    hist = client.get("/api/system/updates/history")
    assert hist.status_code == 200
    assert "entries" in hist.json()

    auto = client.get("/api/system/updates/auto-status")
    assert auto.status_code == 200
    assert auto.json()["enabled"] is False
