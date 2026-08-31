"""CARD-123 workflow API: empty picker list, save from job, instantiate."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.models import PhaseSpec
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    return tmp_path


@pytest.fixture
def app(data_dir):
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_empty_workflow_list_for_agent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/agents/assistant/workflows")
        assert res.status_code == 200
        assert res.json() == []


@pytest.mark.asyncio
async def test_save_from_job_and_instantiate(app):
    store = app.state.store
    orch = JobPhaseOrchestrator(store)
    sess = store.create_session(agent_id="assistant", title="Goal run")
    job = orch.create_job_with_phases(
        goal="Onboard Jane Doe jane@example.com",
        session_id=sess.id,
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Create account", success_rule="Account exists", assigned_agent_id="assistant"),
            PhaseSpec(name="Assign laptop", success_rule="Laptop assigned", assigned_agent_id="assistant"),
        ],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        save = await ac.post(
            "/api/agents/assistant/workflows/from-job",
            json={"name": "new-employee-onboarding", "job_id": job.id, "session_id": sess.id},
        )
        assert save.status_code == 200, save.text
        body = save.json()
        workflow = body["workflow"]
        assert workflow["name"] == "new-employee-onboarding"
        assert [c["name"] for c in workflow["chapters"]] == ["Create account", "Assign laptop"]
        blob = str(workflow).lower()
        assert "jane@example.com" not in blob
        assert "jane doe" not in blob

        listed = await ac.get("/api/agents/assistant/workflows")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["id"] == workflow["id"]

        inst = await ac.post(
            f"/api/agents/assistant/workflows/{workflow['id']}/instantiate",
            json={"goal": "Onboard Bob Smith", "session_id": sess.id},
        )
        assert inst.status_code == 200, inst.text
        created = inst.json()
        assert created["goal"] == "Onboard Bob Smith"
        assert created["template_id"] == workflow["id"]
        assert [p["name"] for p in created["phases"]] == ["Create account", "Assign laptop"]
