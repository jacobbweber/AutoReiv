"""
Session Artifacts REST API Contract Integration Tests [REQ-ART-004].
"""

import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.domain.memory.models import SessionArtifact
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def artifact_client(tmp_path):
    db_path = str(tmp_path / "test_artifacts.db")
    wiki_path = str(tmp_path / "wiki")
    os.makedirs(wiki_path, exist_ok=True)

    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    app = create_app(
        state_store=store,
        wiki_path=wiki_path,
    )
    with TestClient(app) as client:
        yield client, store, wiki_path


def test_session_artifacts_api_lifecycle(artifact_client):
    client, store, wiki_path = artifact_client
    session = store.create_session(agent_id="assistant", title="Scan Session")

    # 1. Populate artifact in store
    art = SessionArtifact(
        id="art_api_test",
        session_id=session.id,
        title="Security Audit API",
        content_type="text/markdown",
        content="# API Audit\n- Finding A\n- Finding B",
        summary="Found 2 findings across 5 files.",
        item_count=5,
        is_pinned=False,
    )
    store.save_artifact(art)

    # 2. GET /api/sessions/{session_id}/artifacts
    list_res = client.get(f"/api/sessions/{session.id}/artifacts")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["success"] is True
    assert len(list_data["artifacts"]) == 1
    assert list_data["artifacts"][0]["id"] == "art_api_test"
    assert list_data["artifacts"][0]["title"] == "Security Audit API"

    # 3. GET /api/artifacts/{artifact_id}
    get_res = client.get("/api/artifacts/art_api_test")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["success"] is True
    assert get_data["artifact"]["id"] == "art_api_test"
    assert "Finding A" in get_data["artifact"]["content"]

    # 4. POST /api/artifacts/{artifact_id}/pin
    pin_res = client.post("/api/artifacts/art_api_test/pin", json={"is_pinned": True})
    assert pin_res.status_code == 200
    pin_data = pin_res.json()
    assert pin_data["success"] is True
    assert pin_data["is_pinned"] is True

    # 5. POST /api/artifacts/{artifact_id}/promote
    promote_res = client.post(
        "/api/artifacts/art_api_test/promote",
        json={
            "wiki_slug": "audits/security-api-audit",
            "title": "Permanent Security Audit",
            "category": "audits",
        },
    )
    assert promote_res.status_code == 200
    promo_data = promote_res.json()
    assert promo_data["success"] is True
    assert "path" in promo_data

    # Verify promoted file exists on disk
    target_file = Path(wiki_path) / promo_data["path"]
    assert target_file.is_file()
    assert "Finding A" in target_file.read_text(encoding="utf-8")

    # 6. DELETE /api/artifacts/{artifact_id}
    del_res = client.delete("/api/artifacts/art_api_test")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 7. Verify deletion
    get_after_del = client.get("/api/artifacts/art_api_test")
    assert get_after_del.status_code == 404
