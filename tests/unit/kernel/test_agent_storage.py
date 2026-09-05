"""
Unit tests for CARD-148: Per-Agent Persistent Storage in Agent Studio and Pack SDK.
"""

import sqlite3

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agent_storage_tools import AgentStorageTools
from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.infrastructure.data.resolver import (
    get_agent_storage_connection,
    resolve_agent_storage_path,
)


def test_agent_profile_storage_fields_default():
    profile = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        system_prompt="You are a helpful assistant.",
    )
    assert hasattr(profile, "storage_enabled")
    assert profile.storage_enabled is False
    assert hasattr(profile, "storage_type")
    assert profile.storage_type == "sqlite"


def test_agent_profile_guardrail_validates_storage():
    data = {
        "id": "finance-bot",
        "name": "Finance Bot",
        "system_prompt": "You track personal expenses.",
        "storage_enabled": True,
        "storage_type": "sqlite",
    }
    profile = AgentProfileGuardrail.validate(data)
    assert profile.storage_enabled is True
    assert profile.storage_type == "sqlite"


def test_resolve_agent_storage_path(tmp_path):
    storage_path = resolve_agent_storage_path("finance-bot", data_dir=tmp_path)
    assert storage_path == tmp_path / "packs" / "finance-bot" / "finance_bot_storage.db"


def test_resolve_agent_memory_path(tmp_path):
    from src.infrastructure.data.resolver import resolve_agent_memory_path

    memory_path = resolve_agent_memory_path("finance-bot", data_dir=tmp_path)
    assert memory_path == tmp_path / "packs" / "finance-bot" / "finance_bot_memory.db"
    assert memory_path != resolve_agent_storage_path("finance-bot", data_dir=tmp_path)


def test_resolve_agent_storage_path_migrates_legacy(tmp_path):
    legacy = tmp_path / "agents" / "finance-bot" / "storage.db"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"LEGACY-STORAGE-DB")

    storage_path = resolve_agent_storage_path("finance-bot", data_dir=tmp_path)
    assert storage_path == tmp_path / "packs" / "finance-bot" / "finance_bot_storage.db"
    assert storage_path.is_file()
    assert storage_path.read_bytes() == b"LEGACY-STORAGE-DB"


def test_get_agent_storage_connection_creates_db(tmp_path):
    conn = get_agent_storage_connection("finance-bot", data_dir=tmp_path)
    try:
        assert isinstance(conn, sqlite3.Connection)
        conn.execute("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test_items (name) VALUES ('item1')")
        conn.commit()
        cur = conn.execute("SELECT name FROM test_items")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "item1"
    finally:
        conn.close()

    db_path = tmp_path / "packs" / "finance-bot" / "finance_bot_storage.db"
    assert db_path.is_file()


def test_agent_storage_tools_execute_and_query(tmp_path):
    tools = AgentStorageTools(data_dir=tmp_path)

    # 1. Execute DDL
    ddl_res = tools.execute_agent_database(
        query="CREATE TABLE expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, cost REAL)",
        agent_id="finance-bot",
    )
    assert ddl_res["status"] == "success"

    # 2. Execute Insert
    insert_res = tools.execute_agent_database(
        query="INSERT INTO expenses (item, cost) VALUES (?, ?)",
        parameters=["groceries", 45.50],
        agent_id="finance-bot",
    )
    assert insert_res["status"] == "success"
    assert insert_res["rows_affected"] == 1

    # 3. Query
    query_res = tools.query_agent_database(
        query="SELECT item, cost FROM expenses WHERE cost > ?",
        parameters=[20.0],
        agent_id="finance-bot",
    )
    assert query_res["status"] == "success"
    assert query_res["count"] == 1
    assert query_res["rows"][0]["item"] == "groceries"
    assert query_res["rows"][0]["cost"] == 45.50


def test_agent_storage_isolation_between_agents(tmp_path):
    tools = AgentStorageTools(data_dir=tmp_path)

    # Create table for Agent A
    tools.execute_agent_database(
        query="CREATE TABLE secrets (data TEXT)",
        agent_id="agent-a",
    )
    tools.execute_agent_database(
        query="INSERT INTO secrets (data) VALUES ('agent-a-secret')",
        agent_id="agent-a",
    )

    # Agent B should NOT have the table
    b_res = tools.query_agent_database(
        query="SELECT * FROM secrets",
        agent_id="agent-b",
    )
    assert b_res["status"] == "error"
    assert "no such table: secrets" in b_res["error"]


def test_tool_registry_auto_authorizes_storage_tools_when_enabled():
    registry = ScopedToolRegistry()
    tools = AgentStorageTools()
    tools.register_tools(registry)

    profile_no_storage = AgentProfile(
        id="basic-agent",
        name="Basic Agent",
        description="Basic agent description",
        system_prompt="You are basic.",
        storage_enabled=False,
    )
    tool_defs_no_storage = registry.get_tools_for_agent(profile_no_storage)
    tool_names_no = [t.name for t in tool_defs_no_storage]
    assert "query_agent_database" not in tool_names_no
    assert "execute_agent_database" not in tool_names_no

    profile_with_storage = AgentProfile(
        id="storage-agent",
        name="Storage Agent",
        description="Storage agent description",
        system_prompt="You have storage.",
        storage_enabled=True,
    )
    tool_defs_with_storage = registry.get_tools_for_agent(profile_with_storage)
    tool_names_with = [t.name for t in tool_defs_with_storage]
    assert "query_agent_database" in tool_names_with
    assert "execute_agent_database" in tool_names_with
