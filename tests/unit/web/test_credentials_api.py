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


@pytest.mark.asyncio
async def test_credentials_reveal_and_update_retention(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create Credential
        payload = {
            "name": "GitHub Key",
            "type": "key",
            "secret": "ghp_supersecretkey123",
            "description": "My personal access token",
        }
        create_res = await ac.post("/api/vault/credentials", json=payload)
        assert create_res.status_code == 200
        cred_id = create_res.json()["id"]

        # 2. Reveal Secret [REQ-VAULT-006]
        reveal_res = await ac.get(f"/api/vault/credentials/{cred_id}/reveal")
        assert reveal_res.status_code == 200
        reveal_data = reveal_res.json()
        assert reveal_data["id"] == cred_id
        assert reveal_data["secret"] == "ghp_supersecretkey123"

        # 3. Update without secret (retain existing secret) [REQ-VAULT-007]
        update_payload = {
            "id": cred_id,
            "name": "GitHub Key Renamed",
            "type": "key",
            "secret": "",
            "description": "Updated description",
        }
        update_res = await ac.post("/api/vault/credentials", json=update_payload)
        assert update_res.status_code == 200

        # Verify retention
        reveal_res2 = await ac.get(f"/api/vault/credentials/{cred_id}/reveal")
        assert reveal_res2.status_code == 200
        assert reveal_res2.json()["secret"] == "ghp_supersecretkey123"

        # Verify metadata changed
        list_res = await ac.get("/api/vault/credentials")
        item = [x for x in list_res.json() if x["id"] == cred_id][0]
        assert item["name"] == "GitHub Key Renamed"
        assert item["description"] == "Updated description"

        # 4. Reveal non-existent credential returns 404
        bad_res = await ac.get("/api/vault/credentials/non-existent-id/reveal")
        assert bad_res.status_code == 404

