import sqlite3

from src.domain.kernel.models import AgentOrigin, AgentProfile
from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_agent_origin_enum_values():
    assert AgentOrigin.PACK.value == "pack"
    assert AgentOrigin.SYSTEM.value == "system"
    assert AgentOrigin.PLATFORM.value == "platform"
    assert AgentOrigin.CUSTOM.value == "custom"
    assert AgentOrigin("pack") == AgentOrigin.PACK
    assert AgentOrigin("system") == AgentOrigin.SYSTEM
    assert AgentOrigin("platform") == AgentOrigin.PLATFORM
    assert AgentOrigin("custom") == AgentOrigin.CUSTOM


def test_agent_profile_default_origin():
    profile = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        system_prompt="Test prompt",
    )
    assert profile.origin == AgentOrigin.PACK
    assert profile.origin.value == "pack"


def test_agent_profile_explicit_origin():
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Core platform agent",
        system_prompt="Platform prompt",
        origin=AgentOrigin.PACK,
    )
    assert profile.origin == AgentOrigin.PACK
    assert profile.origin.value == "pack"


def test_sqlite_schema_migration_adds_origin_column(tmp_path):
    db_path = tmp_path / "test.db"
    # Create legacy table without origin
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE custom_agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'default',
            purpose TEXT NOT NULL DEFAULT 'general',
            tone TEXT DEFAULT 'default',
            avatar_icon TEXT DEFAULT 'bot',
            model TEXT DEFAULT 'default',
            allowed_tools_json TEXT,
            allowed_skills_json TEXT,
            pack_tools_json TEXT,
            show_in_chat INTEGER DEFAULT 1,
            max_turns INTEGER DEFAULT 10,
            history_retention_days INTEGER DEFAULT 30,
            is_builtin BOOLEAN DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO custom_agents (id, name, description, system_prompt)
        VALUES ('legacy-agent', 'Legacy Agent', 'Legacy description', 'Legacy prompt')
        """
    )
    conn.commit()
    conn.close()

    # Now run SQLiteConnectionManager to trigger migrations
    mgr = SQLiteConnectionManager(str(db_path))
    conn = mgr._get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(custom_agents)")
    columns = {row[1]: row for row in cur.fetchall()}
    assert "origin" in columns
    # Verify legacy row got default 'custom'
    cur.execute("SELECT id, origin FROM custom_agents WHERE id = 'legacy-agent'")
    row = cur.fetchone()
    assert row[1] == "custom"
    conn.close()


def test_sqlite_state_store_persists_and_loads_origin(tmp_path):
    db_path = tmp_path / "test_store.db"
    store = SQLiteStateStore(db_path=db_path)

    # Save custom agent (default origin)
    custom_profile = AgentProfile(
        id="my-custom-agent",
        name="My Custom Agent",
        description="User custom agent",
        system_prompt="Custom prompt",
        origin=AgentOrigin.CUSTOM,
    )
    store.save_agent_profile(custom_profile)

    # Save platform agent
    platform_profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform orchestrator",
        system_prompt="Platform prompt",
        origin=AgentOrigin.PLATFORM,
    )
    store.save_agent_profile(platform_profile)

    # Load individual profiles
    loaded_custom = store.get_agent_profile("my-custom-agent")
    assert loaded_custom is not None
    assert loaded_custom.origin == AgentOrigin.PACK

    loaded_platform = store.get_agent_profile("autoreiv")
    assert loaded_platform is not None
    assert loaded_platform.origin == AgentOrigin.PACK

    # List custom agent profiles
    all_profiles = store.list_custom_agent_profiles()
    profile_map = {p.id: p for p in all_profiles}
    assert profile_map["my-custom-agent"].origin == AgentOrigin.PACK
    assert profile_map["autoreiv"].origin == AgentOrigin.PACK
