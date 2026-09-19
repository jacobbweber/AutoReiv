import json

import pytest

from src.domain.kernel.models import AgentOrigin, AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.reconciler import DeclarativePackReconciler


@pytest.fixture
def test_env(tmp_path):
    data_dir = tmp_path / "user_data"
    data_dir.mkdir(parents=True)
    packs_dir = data_dir / "packs"
    packs_dir.mkdir(parents=True)
    db_path = data_dir / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True)
    store = SQLiteStateStore(db_path=db_path)
    return {
        "data_dir": data_dir,
        "packs_dir": packs_dir,
        "store": store,
    }


def test_reconciler_purges_stale_platform_agent_from_db_and_disk(test_env):
    store = test_env["store"]
    packs_dir = test_env["packs_dir"]
    data_dir = test_env["data_dir"]

    # 1. Seed an active platform agent
    active_profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Active platform prompt",
        origin=AgentOrigin.PLATFORM,
    )
    store.save_agent_profile(active_profile)
    (packs_dir / "autoreiv").mkdir()
    (packs_dir / "autoreiv" / "pack.json").write_text(
        json.dumps({"id": "autoreiv", "name": "AutoReiv", "origin": "platform"}),
        encoding="utf-8",
    )

    # 2. Seed an obsolete platform agent (origin=platform, not in PLATFORM_PACK_IDS)
    stale_profile = AgentProfile(
        id="old-platform-helper",
        name="Old Platform Helper",
        description="Deprecated platform agent",
        system_prompt="Stale prompt",
        origin=AgentOrigin.PLATFORM,
    )
    store.save_agent_profile(stale_profile)
    (packs_dir / "old-platform-helper").mkdir()
    (packs_dir / "old-platform-helper" / "pack.json").write_text(
        json.dumps({"id": "old-platform-helper", "name": "Old Helper", "origin": "platform"}),
        encoding="utf-8",
    )

    # 3. Seed a retired platform agent (in RETIRED_PLATFORM_PACK_IDS)
    retired_profile = AgentProfile(
        id="developer",
        name="Developer",
        description="Absorbed developer",
        system_prompt="Developer prompt",
        origin=AgentOrigin.CUSTOM,  # Legacy row default
    )
    store.save_agent_profile(retired_profile)
    (packs_dir / "developer").mkdir()
    (packs_dir / "developer" / "pack.json").write_text(
        json.dumps({"id": "developer", "name": "Developer"}),
        encoding="utf-8",
    )

    # 4. Seed a genuine custom agent
    custom_profile = AgentProfile(
        id="my-custom-researcher",
        name="My Custom Researcher",
        description="User custom agent",
        system_prompt="Custom prompt",
        origin=AgentOrigin.CUSTOM,
    )
    store.save_agent_profile(custom_profile)
    custom_pack = packs_dir / "my-custom-researcher"
    custom_pack.mkdir()
    (custom_pack / "pack.json").write_text(
        json.dumps({"id": "my-custom-researcher", "name": "Custom", "origin": "custom"}),
        encoding="utf-8",
    )
    (custom_pack / "my-custom-researcher_storage.db").write_text("dummy-data", encoding="utf-8")

    # Run reconciler
    reconciler = DeclarativePackReconciler(
        data_dir=data_dir,
        state_store=store,
    )
    report = reconciler.reconcile(desired_platform_ids=["autoreiv", "direct"])

    # Verify report
    assert "old-platform-helper" in report.purged_database_agents
    assert "developer" in report.purged_database_agents
    assert "old-platform-helper" in report.purged_pack_directories
    assert "developer" in report.purged_pack_directories
    assert "my-custom-researcher" in report.preserved_custom_agents
    assert "autoreiv" in report.active_platform_agents

    # Verify DB state
    assert store.get_agent_profile("autoreiv") is not None
    assert store.get_agent_profile("my-custom-researcher") is not None
    assert store.get_agent_profile("old-platform-helper") is None
    assert store.get_agent_profile("developer") is None

    # Verify Filesystem state
    assert (packs_dir / "autoreiv").exists()
    assert (packs_dir / "my-custom-researcher").exists()
    assert (custom_pack / "my-custom-researcher_storage.db").exists()
    assert not (packs_dir / "old-platform-helper").exists()
    assert not (packs_dir / "developer").exists()


def test_reconciler_strictly_preserves_custom_agents(test_env):
    store = test_env["store"]
    packs_dir = test_env["packs_dir"]
    data_dir = test_env["data_dir"]

    # User created agent named 'finance-tracker' (not in RETIRED_PLATFORM_PACK_IDS)
    custom_profile = AgentProfile(
        id="finance-tracker",
        name="Finance Tracker",
        description="User custom finance tracker",
        system_prompt="Custom finance tracker prompt",
        origin=AgentOrigin.CUSTOM,
    )
    store.save_agent_profile(custom_profile)
    pack_dir = packs_dir / "finance-tracker"
    pack_dir.mkdir()
    (pack_dir / "pack.json").write_text(
        json.dumps({"id": "finance-tracker", "name": "Finance Tracker", "user_managed": True}),
        encoding="utf-8",
    )

    reconciler = DeclarativePackReconciler(data_dir=data_dir, state_store=store)
    report = reconciler.reconcile()

    assert "finance-tracker" in report.preserved_custom_agents
    assert "finance-tracker" not in report.purged_database_agents
    assert store.get_agent_profile("finance-tracker") is not None
    assert pack_dir.exists()


def test_reconciler_is_idempotent(test_env):
    store = test_env["store"]
    data_dir = test_env["data_dir"]

    reconciler = DeclarativePackReconciler(data_dir=data_dir, state_store=store)
    report1 = reconciler.reconcile()
    assert report1 is not None
    report2 = reconciler.reconcile()

    assert report2.purged_database_agents == []
    assert report2.purged_pack_directories == []
