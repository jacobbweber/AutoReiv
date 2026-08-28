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

    assert mock_store.save_message.call_count >= 2
    saved_roles = [call.kwargs.get('message').role for call in mock_store.save_message.call_args_list]
    assert Role.USER in saved_roles
    assert Role.ASSISTANT in saved_roles
