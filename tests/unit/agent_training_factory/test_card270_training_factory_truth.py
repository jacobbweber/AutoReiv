"""CARD-270: Training Factory truth — gap status honesty + no invent at promote."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.agent_training_factory.gap_link import (
    GAP_CANT,
    GAP_FAILED,
    GAP_TRAINING,
    GAP_TRAINED,
    encode_gap_id_objective,
    gap_id_from_job,
    gap_id_from_objectives,
)
from src.domain.orchestration.factory_packets import FactoryJob
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.schema import INIT_SCHEMA_SQL
from src.web.routers import agent_training_factory as atf_mod
from src.web.routers import gaps as gaps_mod


def _mem_gap_repo():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(INIT_SCHEMA_SQL)
    return CapabilityGapRepository(connection_factory=lambda: conn), conn


def test_gap_id_roundtrip_in_objectives():
    oid = encode_gap_id_objective("gap_abc")
    assert gap_id_from_objectives([oid, "other"]) == "gap_abc"
    job = FactoryJob(
        id="fjob_1",
        target_agent_id="assistant",
        session_id="sess_1",
        seed_intent="need tool",
        objectives=[oid],
    )
    assert gap_id_from_job(job) == "gap_abc"


def test_train_sets_training_not_trained():
    gap_repo, _conn = _mem_gap_repo()

    class FakeFactoryRepo:
        def __init__(self):
            self.jobs = {}

        def save_job(self, job):
            self.jobs[job.id] = job

        def get_job(self, job_id):
            return self.jobs.get(job_id)

    factory_repo = FakeFactoryRepo()
    gap = gap_repo.create_gap(
        agent_id="assistant",
        turn_text="need a widget counter tool",
        identified_capability="Count widgets",
        suggested_tool_name="count_widgets",
    )

    app = FastAPI()
    app.include_router(gaps_mod.router)
    app.state.capability_gap_repo = gap_repo
    app.state.factory_repo = factory_repo
    app.state.state_store = None
    app.state.factory_orchestrator = None
    app.state.registry = None

    client = TestClient(app)
    r = client.post(f"/api/agents/assistant/gaps/{gap.id}/train")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["status"] == GAP_TRAINING
    refreshed = gap_repo.get_gap(gap.id)
    assert refreshed is not None
    assert refreshed.status == GAP_TRAINING
    assert refreshed.status != GAP_TRAINED
    job = factory_repo.jobs[body["job_id"]]
    assert gap_id_from_job(job) == gap.id


def test_promote_without_files_refuses_no_invent(monkeypatch):
    called = {"synthesize": False}

    class TS:
        @staticmethod
        def synthesize_tool(**kwargs):
            called["synthesize"] = True
            return {"tools/x.py": "pass"}

    monkeypatch.setattr(atf_mod, "ToolSynthesizer", TS)

    gap_repo, _conn = _mem_gap_repo()
    gap = gap_repo.create_gap(
        agent_id="assistant",
        turn_text="need tool",
        identified_capability="X",
        suggested_tool_name="x_tool",
    )
    gap_repo.update_gap_status(gap.id, GAP_TRAINING)

    job = FactoryJob(
        id="fjob_empty",
        target_agent_id="assistant",
        session_id="sess",
        seed_intent="X",
        objectives=[encode_gap_id_objective(gap.id)],
        status="waiting_approval",
        current_node_id="promote",
    )

    class FakeRepo:
        def get_job(self, jid):
            return job if jid == job.id else None

        def list_packets(self, jid):
            return []

        def update_job_status(self, *a, **k):
            return True

        def save_job(self, j):
            pass

    app = FastAPI()
    app.include_router(atf_mod.router)
    app.state.factory_repo = FakeRepo()
    app.state.capability_gap_repo = gap_repo
    app.state.data_dir_paths = MagicMock(root=Path("."))
    app.state.registry = None

    client = TestClient(app)
    r = client.post(
        f"/api/agent_training_factory/jobs/{job.id}/promote",
        json={"decision": "approved"},
    )
    assert r.status_code == 422, r.text
    assert called["synthesize"] is False
    refreshed = gap_repo.get_gap(gap.id)
    assert refreshed is not None
    assert refreshed.status == GAP_CANT


def test_promote_reject_sets_gap_failed():
    gap_repo, _conn = _mem_gap_repo()
    gap = gap_repo.create_gap(
        agent_id="assistant",
        turn_text="need tool",
        identified_capability="X",
        suggested_tool_name="x_tool",
    )
    gap_repo.update_gap_status(gap.id, GAP_TRAINING)
    job = FactoryJob(
        id="fjob_rej",
        target_agent_id="assistant",
        session_id="sess",
        seed_intent="X",
        objectives=[encode_gap_id_objective(gap.id)],
        status="waiting_approval",
    )

    class FakeRepo:
        def get_job(self, jid):
            return job if jid == job.id else None

        def list_packets(self, jid):
            return []

        def update_job_status(self, *a, **k):
            return True

    app = FastAPI()
    app.include_router(atf_mod.router)
    app.state.factory_repo = FakeRepo()
    app.state.capability_gap_repo = gap_repo
    app.state.data_dir_paths = MagicMock(root=Path("."))
    client = TestClient(app)
    r = client.post(
        f"/api/agent_training_factory/jobs/{job.id}/promote",
        json={"decision": "rejected"},
    )
    assert r.status_code == 200, r.text
    assert gap_repo.get_gap(gap.id).status == GAP_FAILED
