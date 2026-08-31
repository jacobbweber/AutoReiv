"""CARD-124: SDLC specialists are optional Agent Packs, not shipped builtins."""

from src.application.agent_packs.schema import is_visible_in_chat
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES, get_builtin_profile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import catalog_dir, import_sdlc_packs, load_catalog_manifest


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


def test_catalog_packs_parse_as_schema_1_1():
    for pack_id in ("conductor", "coding", "review"):
        manifest = load_catalog_manifest(pack_id)
        assert manifest.schema_version == "1.1"
        assert manifest.id == pack_id
        assert (catalog_dir() / pack_id / "pack.json").is_file()
        assert not list((catalog_dir() / pack_id).rglob("*.py"))


def test_conductor_pack_walk_language_and_tools():
    manifest = load_catalog_manifest("conductor")
    prompt = manifest.system_prompt
    assert "three beats" in prompt.lower() or "Three beats" in prompt
    assert "what he means" in prompt
    assert "what AutoReiv does now" in prompt
    assert "what will change" in prompt
    assert "Stop if a word disagrees" in prompt
    assert "Ready until he says build" in prompt
    assert "Extract intent" in prompt
    assert manifest.show_in_chat is True
    tools = set(manifest.pack_tool_names)
    assert tools == {
        "list_cards",
        "read_card",
        "write_card",
        "set_card_status",
        "read_spec",
        "write_spec",
        "read_steering",
        "list_project_dir",
        "read_project_file",
        "handoff_to_agent",
        "lookup_agents",
        "propose_followup",
    }
    assert "write_project_file" not in tools
    assert "execute_code" not in tools
    assert "cli_exec" not in tools
    assert manifest.allowed_skill == ["covision-card", "handoff-coding"]


def test_coding_pack_one_card_rules():
    manifest = load_catalog_manifest("coding")
    assert manifest.show_in_chat is False
    assert "First tool call is read_card or read_spec" in manifest.system_prompt
    assert "skip git_commit" in manifest.system_prompt
    assert "In Review" in manifest.system_prompt
    assert "Do not mark Done or Returned" in manifest.system_prompt
    tools = set(manifest.pack_tool_names)
    assert "execute_code" in tools
    assert "write_project_file" in tools
    assert "git_commit" in tools
    assert "cli_exec" not in tools
    assert manifest.allowed_skill == ["implement-one-card"]


def test_review_pack_git_tools_not_writes():
    manifest = load_catalog_manifest("review")
    assert manifest.show_in_chat is False
    tools = set(manifest.pack_tool_names)
    assert "git_diff" in tools
    assert "git_status" in tools
    assert "write_project_file" not in tools
    assert "git_commit" not in tools
    assert "execute_code" not in tools
    assert "cli_exec" not in tools
    assert set(manifest.allowed_skill) == {"spec-review", "code-review", "alignment"}


def test_builtins_map_has_no_sdlc_specialists():
    ids = {p.id for p in BUILTIN_PROFILES}
    assert ids == {"assistant", "autoreiv", "agent-builder"}
    assert get_builtin_profile("coding") is None
    assert get_builtin_profile("conductor") is None
    assert get_builtin_profile("review") is None
    assert get_builtin_profile("product") is None
    assert get_builtin_profile("qa") is None
    assert get_builtin_profile("agent-builder") is not None


def test_startup_does_not_autoload_repo_agent_packs(tmp_path):
    assert (catalog_dir() / "conductor" / "pack.json").is_file()
    _data_dir, registry, _tool_reg = _bootstrap(tmp_path)
    ids = {a.id for a in registry.list_agents()}
    assert "conductor" not in ids
    assert "coding" not in ids
    assert "review" not in ids
    assert {"assistant", "autoreiv", "agent-builder"} <= ids


def test_import_makes_handoff_ids_resolvable(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    import_sdlc_packs(data_dir, registry, tool_reg)
    for pack_id in ("conductor", "coding", "review"):
        agent = registry.get_agent(pack_id)
        assert agent is not None
        assert agent.id == pack_id
        assert agent.is_builtin is False
    assert (data_dir / "packs" / "conductor" / "pack.json").is_file()
    assert (data_dir / "packs" / "coding" / "pack.json").is_file()
    assert (data_dir / "packs" / "review" / "pack.json").is_file()


def test_chat_visibility_conductor_shown_coding_review_hidden(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    import_sdlc_packs(data_dir, registry, tool_reg)
    conductor = registry.get_agent("conductor")
    coding = registry.get_agent("coding")
    review = registry.get_agent("review")
    assert conductor.show_in_chat is True
    assert coding.show_in_chat is False
    assert review.show_in_chat is False
    assert is_visible_in_chat(conductor) is True
    assert is_visible_in_chat(coding) is False
    assert is_visible_in_chat(review) is False
    assert is_visible_in_chat({"id": "coding", "show_in_chat": True}) is False
    assert is_visible_in_chat({"id": "review", "show_in_chat": True}) is False
    assert is_visible_in_chat({"id": "conductor", "show_in_chat": False}) is True


def test_stale_override_cannot_show_coding_or_hide_conductor(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    store = registry.state_store
    store.save_agent_override(AgentCustomization(agent_id="coding", show_in_chat=True))
    store.save_agent_override(AgentCustomization(agent_id="review", show_in_chat=True))
    store.save_agent_override(AgentCustomization(agent_id="conductor", show_in_chat=False))
    import_sdlc_packs(data_dir, registry, tool_reg)
    from src.web.routers.agents import _public_agent

    assert _public_agent(registry.get_agent("coding"))["show_in_chat"] is False
    assert _public_agent(registry.get_agent("review"))["show_in_chat"] is False
    assert _public_agent(registry.get_agent("conductor"))["show_in_chat"] is True
    assert is_visible_in_chat(registry.get_agent("coding")) is False
    assert is_visible_in_chat(registry.get_agent("review")) is False
    assert is_visible_in_chat(registry.get_agent("conductor")) is True
