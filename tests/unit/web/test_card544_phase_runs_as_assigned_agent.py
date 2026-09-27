"""CARD-544 (found in live QA): a job phase assigned to another agent runs as that agent.

The Execute phase of a code job is assigned to Developer (AutoReiv no longer ticks coding), but the chat runner
ran every phase with the chat's profile, so AutoReiv hit tool_policy_blocked on execute_code and failed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.orchestration.models import Job, Phase
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.chat import execute_goal_job_phases, profile_for_phase


class _Registry:
    def __init__(self, profiles):
        self._p = {p.id: p for p in profiles}

    def get_profile(self, agent_id):
        return self._p.get(agent_id)


def _phase(agent_id, name="Execute"):
    return Phase(id=f"phase_{name.lower()}", job_id="job_544", index=1, name=name, assigned_agent_id=agent_id)


def test_profile_for_phase_uses_the_assigned_agent():
    autoreiv, developer = MagicMock(id="autoreiv"), MagicMock(id="developer")
    reg = _Registry([autoreiv, developer])
    assert profile_for_phase(autoreiv, _phase("developer"), reg) is developer
    assert profile_for_phase(autoreiv, _phase("autoreiv"), reg) is autoreiv
    # Unknown or missing assignment, or no registry: stay on the chat agent (fail safe, never crash).
    assert profile_for_phase(autoreiv, _phase("nobody"), reg) is autoreiv
    assert profile_for_phase(autoreiv, _phase(""), reg) is autoreiv
    assert profile_for_phase(autoreiv, _phase("developer"), None) is autoreiv


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_execute_phase_assigned_to_developer_streams_as_developer(store, tmp_path):
    sid = "sess_544"
    store.create_session(agent_id="autoreiv", title="Code ask", session_id=sid)
    job = Job(id="job_544", agent_id="autoreiv", goal="Reverse a string in Python", session_id=sid)
    store.create_job(job)
    phase = _phase("developer")
    store.create_phase(phase)
    orch = MagicMock()
    orch.get_next_phase.side_effect = [phase, None]
    orch.start_phase.return_value = phase
    autoreiv, developer = MagicMock(id="autoreiv"), MagicMock(id="developer")

    with patch("src.web.routers.chat._stream_turn_bound", new_callable=AsyncMock) as bound:
        bound.return_value = "parked"
        await execute_goal_job_phases(
            queue=asyncio.Queue(), kernel=MagicMock(), orch=orch, store=store, reflexion_engine=MagicMock(),
            profile=autoreiv, job=job, session_id=sid, self_verify=False, approval_mode="ask",
            data_dir=str(tmp_path / "data"), registry=_Registry([autoreiv, developer]),
        )

    assert bound.await_args.kwargs["profile"] is developer
    phase_sid = bound.await_args.kwargs["session_id"]
    assert store.get_session(phase_sid).agent_id == "developer"
