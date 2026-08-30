"""Chat SSE forwards named ReAct overlay events [REQ-KERNEL-002]."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.kernel.models import AgentProfile, KernelEvent, KernelEventType
from src.web.routers.chat import router


def test_chat_stream_forwards_react_state_event():
    app = FastAPI()
    app.include_router(router)

    class _Registry:
        def get_profile(self, agent_id):
            return AgentProfile(
                id="assistant",
                name="Assistant",
                description="General assistant",
                system_prompt="",
                max_turns=5,
            )

    async def fake_stream_turn(profile, session_id, user_content=None, approval_mode="ask", resume=False, **kwargs):
        yield KernelEvent(
            event_type=KernelEventType.REACT_STATE,
            react={
                "react_state": "THINKING",
                "turn_idx": 0,
                "job_id": "job_1",
                "phase_id": "phase_1",
                "assigned_agent_id": profile.id,
                "job_status": "running",
                "phase_name": "Chat",
            },
        )
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Hello")
        yield KernelEvent(
            event_type=KernelEventType.REACT_STATE,
            react={
                "react_state": "DONE",
                "turn_idx": 0,
                "job_id": "job_1",
                "phase_id": "phase_1",
                "assigned_agent_id": profile.id,
                "job_status": "running",
                "phase_name": "Chat",
            },
        )
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Hello", is_finished=True)

    class _Kernel:
        stream_turn = staticmethod(fake_stream_turn)

    class _Store:
        def save_message(self, **kwargs):
            return None

        def get_messages(self, session_id):
            return []

    app.state.registry = _Registry()
    app.state.kernel = _Kernel()
    app.state.plan_engine = None
    app.state.reflexion_engine = None
    app.state.store = _Store()

    client = TestClient(app)
    payload = {
        "agent_id": "assistant",
        "session_id": "sess_react",
        "content": "hello",
        "goal_mode": False,
        "self_verify": False,
    }
    events = []
    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        current = None
        for line in response.iter_lines():
            if line.startswith("event:"):
                current = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current:
                events.append((current, json.loads(line.split(":", 1)[1].strip())))
                current = None

    named = [e for e in events if e[0] == "react_state"]
    assert [e[1]["react_state"] for e in named] == ["THINKING", "DONE"]
    assert named[0][1]["job_id"] == "job_1"
    assert named[0][1]["phase_id"] == "phase_1"
    assert named[0][1]["assigned_agent_id"] == "assistant"
    assert named[0][1]["turn_idx"] == 0
