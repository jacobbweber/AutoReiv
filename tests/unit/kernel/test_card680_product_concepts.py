"""CARD-680: every agent's system message carries a short, fixed description of AutoReiv's own concepts,
so "what is a standing Job?" is answered from it instead of a dozen wiki and log lookups."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.agents.product_concepts import AUTOREIV_CONCEPTS
from src.domain.kernel.models import AgentProfile


@pytest.fixture
def kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    store = MagicMock()
    store.get_setting.return_value = None
    store.search_facts.return_value = []
    store.list_tones.return_value = []
    return AgentKernel(gateway=MagicMock(), tool_registry=ScopedToolRegistry(), state_store=store,
                       telemetry=MagicMock())


def test_concepts_define_a_standing_job_as_a_goal_run_in_phases():
    text = AUTOREIV_CONCEPTS
    assert "standing Job" in text
    for word in ("goal", "phases", "Formulate", "Execute", "done", "Run as a job"):
        assert word in text, word
    # The wrong live answer: a standing Job is not just a recurring scheduled task.
    assert "Routine" in text and "schedule" in text


def test_concepts_say_to_answer_without_tools():
    assert "without tools" in AUTOREIV_CONCEPTS


def test_concepts_stay_short():
    assert len(AUTOREIV_CONCEPTS) < 2500


@pytest.mark.parametrize("agent_id", ["autoreiv", "tutor", "direct", "my-own-agent"])
def test_every_agent_system_message_has_the_concepts(kernel, agent_id):
    agent = AgentProfile(id=agent_id, name="A", description="d", system_prompt="You are helpful.")
    msg = kernel._build_effective_system_message(agent, "In two short sentences, what is a standing Job?")
    assert AUTOREIV_CONCEPTS in msg.content
    assert msg.content.startswith("You are helpful.")
