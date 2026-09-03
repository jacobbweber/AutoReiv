import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus
from src.web.routers.chat import format_json_deliverable_to_markdown, router


def test_format_json_deliverable_to_markdown():
    raw_json = json.dumps({
        'goal': 'Organize weekly notes',
        'status': 'completed',
        'wiki_inventory_summary': {
            'active_weekly_notes': 1,
            'template': 'templates/weekly.md',
            'key_gaps': ['Missing tags', 'No template prompts']
        },
        'action_plan': {
            'title': 'Weekly Notes 3-Step Action Plan',
            'steps': [
                {'step_number': 1, 'title': 'Standardize template', 'objective': 'Create template file'},
                {'step_number': 2, 'title': 'Daily review ritual', 'objective': 'Log daily tasks'}
            ]
        }
    })

    markdown = format_json_deliverable_to_markdown(raw_json)
    assert '## 🎯 Goal: Organize weekly notes' in markdown
    assert '### 📊 Inventory Summary' in markdown
    assert 'templates/weekly.md' in markdown
    assert '### 📋 Action Plan: Weekly Notes 3-Step Action Plan' in markdown
    assert '**Step 1: Standardize template**' in markdown
    assert '**Step 2: Daily review ritual**' in markdown


@pytest.mark.asyncio
async def test_background_shielded_goal_mode_execution():
    app = FastAPI()
    app.include_router(router)

    mock_registry = MagicMock()
    mock_agent = AgentProfile(id='assistant', name='Assistant', description='General assistant', system_prompt='', tools=[], max_turns=5)
    mock_registry.get_profile.return_value = mock_agent

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(return_value=ChatMessage(role=Role.ASSISTANT, content='## Synthesized Plan Result'))

    mock_plan_engine = MagicMock()
    mock_plan = ExecutionPlan(
        id='plan_1',
        goal='Test Goal',
        agent_id='assistant',
        session_id='test_sess_1',
        steps=[PlanStep(id='s1', title='Step 1', description='Do step 1', status=StepStatus.PENDING)],
    )
    mock_plan_engine.formulate_plan = AsyncMock(return_value=mock_plan)

    mock_store = MagicMock()
    mock_store.create_approval.return_value = "appr_plan_1"
    mock_store.get_messages.return_value = []
    app.state.registry = mock_registry
    app.state.kernel = mock_kernel
    app.state.plan_engine = mock_plan_engine
    app.state.reflexion_engine = None
    app.state.store = mock_store

    client = TestClient(app)

    payload = {
        'agent_id': 'assistant',
        'session_id': 'test_sess_1',
        'content': 'Test Goal',
        'goal_mode': True,
        'self_verify': False,
    }

    with client.stream('POST', '/api/chat/stream', json=payload) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if 'plan_formulated' in line:
                break

    await asyncio.sleep(0.1)

    assert mock_store.save_message.call_count >= 1
    saved_roles = [call.kwargs.get('message').role for call in mock_store.save_message.call_args_list]
    assert Role.USER in saved_roles
    mock_store.create_approval.assert_called()


@pytest.mark.asyncio
async def test_chat_stream_resume_does_not_append_user():
    from src.domain.kernel.models import KernelEvent, KernelEventType

    app = FastAPI()
    app.include_router(router)

    mock_registry = MagicMock()
    mock_agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="General assistant",
        system_prompt="",
        tools=[],
        max_turns=5,
    )
    mock_registry.get_profile.return_value = mock_agent

    captured = {}

    async def fake_stream_turn(profile, session_id, user_content=None, approval_mode="ask", resume=False, **kwargs):
        captured["user_content"] = user_content
        captured["resume"] = resume
        captured["session_id"] = session_id
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Continued after approve.")
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Continued after approve.", is_finished=True)

    mock_kernel = MagicMock()
    mock_kernel.stream_turn = fake_stream_turn
    mock_store = MagicMock()
    app.state.registry = mock_registry
    app.state.kernel = mock_kernel
    app.state.plan_engine = None
    app.state.reflexion_engine = None
    app.state.store = mock_store

    client = TestClient(app)
    payload = {
        "agent_id": "assistant",
        "session_id": "sess_resume",
        "content": "",
        "resume": True,
        "goal_mode": False,
        "self_verify": False,
    }
    events = []
    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            events.append(line)

    assert captured.get("resume") is True
    assert captured.get("user_content") in (None, "")
    assert captured.get("session_id") == "sess_resume"
    joined = "\n".join(str(e) for e in events)
    assert "Continued after approve." in joined
    user_saves = [
        c for c in mock_store.save_message.call_args_list
        if c.kwargs.get("message") and getattr(c.kwargs.get("message"), "role", None) == Role.USER
    ]
    assert user_saves == []


@pytest.mark.asyncio
async def test_abort_stream_endpoint_cancels_active_task():
    from src.web.routers.chat import _active_stream_tasks

    app = FastAPI()
    app.include_router(router)

    mock_telemetry = MagicMock()
    mock_store = MagicMock()
    fake_job = MagicMock()
    fake_job.id = "job_1"
    fake_job.status = "in_progress"
    fake_phase = MagicMock()
    fake_phase.id = "phase_1"
    fake_phase.status = "running"
    mock_store.list_jobs_for_session.return_value = [fake_job]
    mock_store.list_phases_for_job.return_value = [fake_phase]

    app.state.telemetry = mock_telemetry
    app.state.store = mock_store

    async def long_running():
        await asyncio.sleep(10)

    dummy_task = asyncio.create_task(long_running())
    _active_stream_tasks["sess_abort_test"] = dummy_task

    client = TestClient(app)
    resp = client.post("/api/chat/stream/sess_abort_test/abort")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "aborted"
    assert data["session_id"] == "sess_abort_test"
    assert data["task_cancelled"] is True
    assert (hasattr(dummy_task, "cancelling") and dummy_task.cancelling() > 0) or dummy_task.cancelled()
    try:
        await dummy_task
    except asyncio.CancelledError:
        pass
    assert dummy_task.cancelled()
    mock_store.update_job_status.assert_called_with("job_1", "cancelled")
    mock_store.update_phase_status.assert_called_with("phase_1", "cancelled")
    mock_telemetry.record_turn_span.assert_called_once()

