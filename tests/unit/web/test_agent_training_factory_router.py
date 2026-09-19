"""Unit tests for Agent Training Factory Router enhancements [REQ-FACT-064]."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_target_directory_defaults_from_selected_project(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    # Seed selected_project setting
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    store.set_setting("selected_project", json.dumps({"slug": "my_project", "path": str(proj_dir)}))

    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agent_training_factory/jobs",
            json={
                "target_agent_id": "homelab-admin",
                "seed_intent": "Manage infrastructure",
                "objectives": ["Status", "Deploy"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        job_id = data["job_id"]

        # Inspect the initial work packet payload in SQLite
        packets = store.list_packets(job_id)
        assert len(packets) >= 1
        work_pkt = packets[0].payload
        assert work_pkt.get("target_directory") == str(proj_dir)


@pytest.mark.asyncio
async def test_target_directory_explicit_overrides_selected_project(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    proj_dir = tmp_path / "default_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    custom_dir = tmp_path / "custom_project"
    custom_dir.mkdir(parents=True, exist_ok=True)
    store.set_setting("selected_project", json.dumps({"slug": "default_project", "path": str(proj_dir)}))

    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agent_training_factory/jobs",
            json={
                "target_agent_id": "homelab-admin",
                "seed_intent": "Manage custom infra",
                "target_directory": str(custom_dir),
                "objectives": ["Status"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        job_id = data["job_id"]

        packets = store.list_packets(job_id)
        assert len(packets) >= 1
        work_pkt = packets[0].payload
        assert work_pkt.get("target_directory") == str(custom_dir)


@pytest.mark.asyncio
async def test_phase_instructions_update_and_reset(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET all phase instructions
        get_res = await ac.get("/api/agent_training_factory/phases/instructions")
        assert get_res.status_code == 200

        # PUT custom instructions for blueprint phase
        put_res = await ac.put(
            "/api/agent_training_factory/phases/blueprint/instructions",
            json={"prompt": "Customized test blueprint instructions."},
        )
        assert put_res.status_code == 200
        put_data = put_res.json()
        assert put_data["success"] is True
        assert put_data["phase"]["active_prompt"] == "Customized test blueprint instructions."
        assert put_data["phase"]["is_custom"] is True

        # DELETE to reset instructions for blueprint phase
        del_res = await ac.delete("/api/agent_training_factory/phases/blueprint/instructions")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["success"] is True
        assert del_data["phase"]["is_custom"] is False


@pytest.mark.asyncio
async def test_step_factory_job_returns_404_for_nonexistent_job(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        step_res = await ac.post("/api/agent_training_factory/jobs/fjob_nonexistent_999/step")
        assert step_res.status_code == 404
        assert "not found" in step_res.json()["detail"].lower()

