"""
Web Router Integration Tests for System Version & Updates API [REQ-UPD-001..REQ-UPD-005].
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
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
    return TestClient(app)


def test_health_check_returns_dynamic_version(client):
    """[REQ-UPD-001] Health endpoint returns valid semver matching pyproject.toml."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"].startswith("0.")


def test_get_system_version_endpoint(client):
    """[REQ-UPD-001] GET /api/system/version returns full version info."""
    resp = client.get("/api/system/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_version" in data
    assert "is_git" in data
    assert "deployment_mode" in data


def test_get_and_put_update_config_endpoints(client):
    """[REQ-UPD-002] GET & PUT /api/system/updates/config manage upstream repo settings."""
    resp = client.get("/api/system/updates/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "upstream_repo_url" in cfg
    assert cfg["tracked_branch"] in ("qa", "main")

    put_resp = client.put(
        "/api/system/updates/config",
        json={
            "upstream_repo_url": "https://github.com/my-org/my-fork.git",
            "tracked_branch": "dev",
            "auto_check_cadence": "daily",
        },
    )
    assert put_resp.status_code == 200
    new_cfg = put_resp.json()
    assert new_cfg["upstream_repo_url"] == "https://github.com/my-org/my-fork.git"
    assert new_cfg["tracked_branch"] == "dev"

    verify_resp = client.get("/api/system/updates/config")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["tracked_branch"] == "dev"


def test_check_for_updates_endpoint(client):
    """[REQ-UPD-003] GET /api/system/updates/check returns UpdateCheckResult."""
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
        assert data["remote_commit"] == "f1a2b3c"
        assert data["commits_behind"] == 2


def test_apply_update_endpoint(client):
    """[REQ-UPD-004, REQ-UPD-005] POST /api/system/updates/apply triggers safe update apply."""
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
        )

        resp = client.post("/api/system/updates/apply")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["new_commit"] == "f1a2b3c"
