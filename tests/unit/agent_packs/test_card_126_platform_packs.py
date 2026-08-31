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
    catalog_dir,
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
    for pack_id in ("assistant", "autoreiv"):
        manifest = load_platform_manifest(pack_id)
        assert manifest.schema_version == "1.1"
        assert manifest.id == pack_id
        assert manifest.show_in_chat is True
        assert (platform_dir() / pack_id / "pack.json").is_file()
        assert not list((platform_dir() / pack_id).rglob("*.py"))
        assert "wiki" in manifest.allowed_skill
        assert "wiki" not in {s.id for s in manifest.skills}


def test_assistant_pack_weekly_tasks_and_leftovers():
    manifest = load_platform_manifest("assistant")
    assert {s.id for s in manifest.skills} == {"weekly-tasks"}
    weekly = next(s for s in manifest.skills if s.id == "weekly-tasks")
    assert weekly.tools == [
        "get_or_create_weekly_note",
        "log_daily_work_item",
        "complete_weekly_task",
        "rollover_weekly_tasks",
        "get_weekly_summary",
    ]
    leftovers = {
        "handoff_to_agent",
        "lookup_agents",
        "propose_followup",
        "batch_worker_scan",
        "get_session_artifact",
        "list_user_skill_packs",
        "skill_view",
        "propose_skill",
        "propose_tool",
        "propose_workflow",
    }
    assert leftovers <= set(manifest.pack_tool_names)
    assert "cli_exec" not in manifest.pack_tool_names
    assert "execute_code" not in manifest.pack_tool_names
    profile = platform_pack_profile("assistant")
    for tool in WIKI_TOOL_NAMES:
        assert tool in profile.allowed_tool_names
    assert "wiki" in profile.allowed_skill


def test_autoreiv_pack_four_skills_no_save_spec():
    manifest = load_platform_manifest("autoreiv")
    assert {s.id for s in manifest.skills} == {
        "build-agent-pack",
        "recommend-capability",
        "platform-health",
        "session-inspect",
    }
    by_id = {s.id: s.tools for s in manifest.skills}
    assert "export_agent_pack" in by_id["build-agent-pack"]
    assert "import_agent_pack" in by_id["build-agent-pack"]
    assert "scaffold_agent_pack" in by_id["build-agent-pack"]
    assert "propose_skill" in by_id["recommend-capability"]
    assert "system_info" in by_id["platform-health"]
    assert "cli_exec" in by_id["platform-health"]
    assert "get_session_transcript" in by_id["session-inspect"]
    assert "save_agent_specification" not in manifest.pack_tool_names
    profile = platform_pack_profile("autoreiv")
    assert "save_agent_specification" not in profile.allowed_tool_names
    assert "wiki_note_read" in profile.allowed_tool_names
    assert "wiki" in profile.allowed_skill


def test_builtins_are_only_hidden_agent_builder():
    ids = {p.id for p in BUILTIN_PROFILES}
    assert ids == {"agent-builder"}
    assert get_builtin_profile("assistant") is None
    assert get_builtin_profile("autoreiv") is None
    assert get_builtin_profile("agent-builder") is not None
    assert get_builtin_profile("agent-builder").show_in_chat is False
    assert is_platform_pack("assistant")
    assert is_platform_pack("autoreiv")
    assert not is_platform_pack("conductor")
    assert PLATFORM_PACK_IDS == {"assistant", "autoreiv"}


def test_launch_seeds_platform_packs_not_agent_packs(tmp_path):
    assert (catalog_dir() / "conductor" / "pack.json").is_file()
    data_dir, registry, _tool_reg = _bootstrap(tmp_path)
    ids = {a.id for a in registry.list_agents()}
    assert {"assistant", "autoreiv", "agent-builder"} <= ids
    assert "conductor" not in ids
    assert "coding" not in ids
    assert "review" not in ids
    assistant = registry.get_agent("assistant")
    autoreiv = registry.get_agent("autoreiv")
    assert assistant is not None and assistant.is_builtin is False
    assert autoreiv is not None and autoreiv.is_builtin is False
    assert (data_dir / "packs" / "assistant" / "pack.json").is_file()
    assert (data_dir / "packs" / "autoreiv" / "pack.json").is_file()
    assert not (data_dir / "packs" / "conductor" / "pack.json").is_file()
    assert "wiki" in assistant.allowed_skill
    assert "wiki_note_read" in assistant.allowed_tool_names
    assert "weekly-tasks" in assistant.allowed_skill
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
    assert "Placeholder" in body
    for tool in WIKI_TOOL_NAMES:
        assert tool  # catalog names stay non-empty
