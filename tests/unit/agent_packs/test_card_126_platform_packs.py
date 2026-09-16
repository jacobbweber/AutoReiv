"""CARD-126: Platform Agent Packs, wiki skill stub, seed-if-missing."""

from src.application.agent_packs.schema import (
    PLATFORM_PACK_IDS,
    WIKI_TOOL_NAMES,
    is_platform_pack,
)
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES, get_builtin_profile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import (
    seed_platform_pack_folders,
)
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS, bundled_skill_md
from tests.unit.agent_packs.catalog import (
    load_platform_manifest,
    platform_dir,
    platform_pack_profile,
)


def _bootstrap(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=TelemetryCollector(store=store),
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    return tmp_path, registry, tool_reg


def test_platform_packs_parse_as_schema_1_1():
    for pack_id in ("autoreiv", "developer", "tutor", "direct"):
        manifest = load_platform_manifest(pack_id)
        assert manifest.schema_version == "1.1"
        assert manifest.id == pack_id
        assert manifest.show_in_chat is True
        assert (platform_dir() / pack_id / "pack.json").is_file()
        assert not list((platform_dir() / pack_id).rglob("*.py"))
        if pack_id in ("autoreiv", "tutor"):
            assert "wiki" in manifest.allowed_skill


def test_autoreiv_pack_weekly_tasks_and_skills():
    manifest = load_platform_manifest("autoreiv")
    assert {s.id for s in manifest.skills} == {
        "build-agent-pack",
        "platform-health",
        "session-inspect",
        "tasks",
        "wiki",
    }
    weekly = next(s for s in manifest.skills if s.id == "tasks")
    assert weekly.tools == [
        "get_or_create_weekly_note",
        "log_daily_work_item",
        "complete_weekly_task",
        "rollover_weekly_tasks",
        "get_weekly_summary",
    ]
    task_tools = {
        "get_or_create_weekly_note",
        "log_daily_work_item",
        "complete_weekly_task",
        "rollover_weekly_tasks",
        "get_weekly_summary",
    }
    assert task_tools <= set(manifest.pack_tool_names)
    assert "save_agent_specification" not in manifest.pack_tool_names
    profile = platform_pack_profile("autoreiv")
    assert "wiki_note_read" in profile.allowed_tool_names
    assert "wiki" in profile.allowed_skill
    assert "tasks" in profile.allowed_skill
    assert "proposals" in profile.allowed_skill


def test_builtins_are_only_hidden_agent_builder():
    ids = {p.id for p in BUILTIN_PROFILES}
    assert ids == {"agent-builder"}
    assert get_builtin_profile("assistant") is None
    assert get_builtin_profile("autoreiv") is None
    assert get_builtin_profile("developer") is None
    assert get_builtin_profile("agent-builder") is not None
    assert get_builtin_profile("agent-builder").show_in_chat is False
    assert not is_platform_pack("assistant")
    assert is_platform_pack("autoreiv")
    assert is_platform_pack("developer")
    assert not is_platform_pack("wiki")
    assert is_platform_pack("tutor")
    assert is_platform_pack("direct")
    assert not is_platform_pack("conductor")
    assert PLATFORM_PACK_IDS == {"autoreiv", "developer", "tutor", "direct"}


def test_launch_seeds_platform_packs_not_agent_packs(tmp_path):
    data_dir, registry, _tool_reg = _bootstrap(tmp_path)
    ids = {a.id for a in registry.list_agents()}
    assert {"autoreiv", "developer", "tutor", "direct", "agent-builder"} <= ids
    assert "assistant" not in ids
    assert "wiki" not in ids
    assert "conductor" not in ids
    assert "coding" not in ids
    assert "review" not in ids
    autoreiv = registry.get_agent("autoreiv")
    developer = registry.get_agent("developer")
    tutor = registry.get_agent("tutor")
    assert autoreiv is not None and autoreiv.is_builtin is False
    assert developer is not None and developer.is_builtin is False
    assert tutor is not None and tutor.is_builtin is False
    assert (data_dir / "packs" / "autoreiv" / "pack.json").is_file()
    assert (data_dir / "packs" / "developer" / "pack.json").is_file()
    assert (data_dir / "packs" / "tutor" / "pack.json").is_file()
    assert (data_dir / "packs" / "direct" / "pack.json").is_file()
    assert not (data_dir / "packs" / "assistant" / "pack.json").is_file()
    assert not (data_dir / "packs" / "wiki" / "pack.json").is_file()
    assert not (data_dir / "packs" / "conductor" / "pack.json").is_file()
    assert "wiki" in autoreiv.allowed_skill
    assert "tasks" in autoreiv.allowed_skill
    assert "wiki_note_read" in autoreiv.allowed_tool_names
    assert "save_agent_specification" not in autoreiv.allowed_tool_names


def test_seed_if_missing_does_not_clobber(tmp_path):
    packs = tmp_path / "packs"
    dest = packs / "assistant"
    dest.mkdir(parents=True)
    marker = dest / "pack.json"
    marker.write_text('{"id": "user-copy"}', encoding="utf-8")
    copied = seed_platform_pack_folders(packs)
    assert "assistant" not in copied
    assert marker.read_text(encoding="utf-8") == '{"id": "user-copy"}'


def test_wiki_skill_stub_is_bundled():
    assert "wiki" in BUNDLED_PACK_IDS
    path = bundled_skill_md("wiki")
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    assert "name: Wiki" in body
    assert "Knowledge Vault" in body or "Wiki" in body
    for tool in WIKI_TOOL_NAMES:
        assert tool  # catalog names stay non-empty


def test_seed_platform_ids():
    """Platform seed ids are autoreiv, developer, tutor, direct."""
    from src.infrastructure.skills import platform_packs as pp

    assert pp.PLATFORM_PACK_IDS == ("autoreiv", "developer", "tutor", "direct")
    assert pp.ALL_PLATFORM_PACK_IDS == ("autoreiv", "developer", "tutor", "direct")
    assert not hasattr(pp, "HOMELAB_PACK_IDS") or getattr(pp, "HOMELAB_PACK_IDS", ()) == ()
    # Repo platform-packs/ must not ship user-class homelab seeds
    root = platform_dir()
    for hid in (
        "homelab",
        "homelab-architect",
        "homelab-engineer",
        "homelab-admin",
        "homelab-janitor",
    ):
        assert not (root / hid).exists(), f"{hid} must not ship under platform-packs/"
    for pid in pp.PLATFORM_PACK_IDS:
        assert (root / pid / "pack.json").is_file()
    # developer keeps id + display name Developer (coding/coder obsolete)
    manifest = load_platform_manifest("developer")
    assert manifest.id == "developer"
    assert manifest.name == "Developer"
