"""
Integration tests for Credential Vault REST API [CARD-168].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_credentials_api_lifecycle(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Initially empty
        res = await ac.get("/api/vault/credentials")
        assert res.status_code == 200
        assert res.json() == []

        # 2. Create Credential
        payload = {
            "name": "AWS Production Token",
            "type": "token",
            "secret": "AKIAIOSFODNN7EXAMPLE",
            "description": "Production deployment credentials",
        }
        create_res = await ac.post("/api/vault/credentials", json=payload)
        assert create_res.status_code == 200
        data = create_res.json()
        assert data["status"] == "created"
        assert "id" in data
        cred_id = data["id"]

        # 3. List credentials - ensure plaintext secret is NEVER exposed
        list_res = await ac.get("/api/vault/credentials")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 1
        assert items[0]["id"] == cred_id
        assert items[0]["name"] == "AWS Production Token"
        assert "secret" not in items[0] or items[0]["secret"] == ""
        assert items[0]["masked_preview"].startswith("****") or "***" in items[0]["masked_preview"]

        # 4. Delete Credential
        del_res = await ac.delete(f"/api/vault/credentials/{cred_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 5. List empty again
        list_res2 = await ac.get("/api/vault/credentials")
        assert list_res2.status_code == 200
        assert list_res2.json() == []
