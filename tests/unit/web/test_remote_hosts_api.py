"""
Integration tests for Remote Hosts REST API [CARD-160].
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_remote_hosts_api_lifecycle(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Initially empty
        res = await ac.get("/api/remote_hosts")
        assert res.status_code == 200
        assert res.json() == []

        # 2. Create Remote Host
        payload = {
            "label": "My Linux VPS",
            "host": "192.168.1.50",
            "port": 22,
            "username": "ubuntu",
            "auth_type": "password",
            "credential_id": "vps_pw",
        }
        create_res = await ac.post("/api/remote_hosts", json=payload)
        assert create_res.status_code == 200
        data = create_res.json()
        assert data["status"] == "created"
        assert "id" in data
        host_id = data["id"]
        assert host_id == "my-linux-vps"

        # 3. List remote hosts
        list_res = await ac.get("/api/remote_hosts")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 1
        assert items[0]["id"] == host_id
        assert items[0]["label"] == "My Linux VPS"
        assert items[0]["host"] == "192.168.1.50"
        assert items[0]["username"] == "ubuntu"
        assert items[0]["credential_id"] == "vps_pw"

        # 4. Probe test endpoint (mocked Paramiko success)
        with patch("paramiko.SSHClient") as mock_ssh:
            mock_client = MagicMock()
            mock_ssh.return_value = mock_client
            test_res = await ac.post(f"/api/remote_hosts/{host_id}/test")
            assert test_res.status_code == 200
            test_data = test_res.json()
            assert test_data["status"] == "ok"
            assert "latency_ms" in test_data

        # 5. Delete Remote Host
        del_res = await ac.delete(f"/api/remote_hosts/{host_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 6. List empty again
        list_res2 = await ac.get("/api/remote_hosts")
        assert list_res2.status_code == 200
        assert list_res2.json() == []
