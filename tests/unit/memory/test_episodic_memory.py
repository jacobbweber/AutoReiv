"""
Unit and Integration Tests for Episodic Memory Fact Store & Auto-Recall [REQ-EPISODIC-001 - REQ-EPISODIC-005].
"""

import pytest
from starlette.testclient import TestClient

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.memory_skill import EpisodicMemorySkill, render_memory_context
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import Role
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def memory_store():
    store = SQLiteStateStore(db_path=":memory:")
    return store


def test_sqlite_store_fact_crud_and_search(memory_store):
    # 1. Upsert facts
    memory_store.save_fact(entity="user", key="name", value="Jacob", confidence=1.0)
    memory_store.save_fact(entity="user", key="preferred_model", value="llama3.3:70b", confidence=0.9)
    memory_store.save_fact(entity="environment", key="deploy_region", value="us-west-2", confidence=0.8)
    memory_store.save_fact(entity="project", key="codename", value="AutoReiv", confidence=0.95)

    # 2. List all facts
    all_facts = memory_store.get_facts()
    assert len(all_facts) == 4

    # 3. Filter by entity
    user_facts = memory_store.get_facts(entity="user")
    assert len(user_facts) == 2

    # 4. Search by keyword
    search_res = memory_store.search_facts(query="preferred llama3.3", limit=5)
    assert len(search_res) >= 1
    assert search_res[0]["key"] == "preferred_model"
    assert search_res[0]["value"] == "llama3.3:70b"

    # 5. Search with confidence filter
    high_conf = memory_store.search_facts(query="region", min_confidence=0.85)
    assert len(high_conf) == 0  # deploy_region confidence is 0.8

    # 6. Delete fact
    deleted = memory_store.delete_fact(entity="user", key="name")
    assert deleted is True
    assert len(memory_store.get_facts(entity="user")) == 1


def test_memory_skill_rendering_and_auto_recall(memory_store):
    skill = EpisodicMemorySkill(store=memory_store)
    skill.save_fact(entity="user", key="theme", value="dark", confidence=0.9)
    skill.save_fact(entity="user", key="timezone", value="America/New_York", confidence=1.0)

    facts = skill.get_facts(entity="user")
    block = render_memory_context(facts)
    assert "[Episodic Memory - Recalled Facts]" in block
    assert "user.theme: dark" in block
    assert "user.timezone: America/New_York" in block

    # Auto recall matching query
    recalled = skill.auto_recall(prompt="What timezone am I in?", min_confidence=0.5)
    assert "user.timezone: America/New_York" in recalled


def test_agent_kernel_episodic_auto_recall(memory_store):
    memory_store.save_fact(entity="user", key="favorite_framework", value="FastAPI", confidence=0.95)

    agent = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="Test Agent Description",
        system_prompt="You are a helpful software architect.",
    )

    kernel = AgentKernel(
        gateway=None,
        tool_registry=ScopedToolRegistry(),
        state_store=memory_store,
        telemetry=TelemetryCollector(store=memory_store),
    )

    # Prompt matching stored fact keyword
    system_msg = kernel._build_effective_system_message(
        agent, user_content="Please scaffold a project with my favorite framework"
    )

    assert system_msg.role == Role.SYSTEM
    assert "You are a helpful software architect." in system_msg.content
    assert "[Episodic Memory - Recalled Facts]" in system_msg.content
    assert "user.favorite_framework: FastAPI" in system_msg.content


def test_memory_rest_api_endpoints(memory_store):
    app = create_app(state_store=memory_store)
    client = TestClient(app)

    # 1. POST to create fact
    res = client.post(
        "/api/memory/facts",
        json={
            "entity": "user",
            "key": "editor",
            "value": "Antigravity",
            "confidence": 1.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "saved"
    assert data["fact"]["key"] == "editor"

    # 2. GET all facts
    res = client.get("/api/memory/facts")
    assert res.status_code == 200
    facts = res.json()
    assert len(facts) == 1
    assert facts[0]["value"] == "Antigravity"

    # 3. GET with search query
    res = client.get("/api/memory/facts?q=Antigravity")
    assert res.status_code == 200
    matched = res.json()
    assert len(matched) == 1

    # 4. DELETE fact
    res = client.delete("/api/memory/facts/user/editor")
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

    # 5. DELETE nonexistent fact returns 404
    res = client.delete("/api/memory/facts/user/editor")
    assert res.status_code == 404
