"""CARD-121: tools are one atomic callable; untick omits schema; SKILL.md stubs are not callables."""

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.kernel.models import AgentProfile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _bootstrap(tmp_path, skills_dir=None):
    store = SQLiteStateStore(db_path=str(tmp_path / "autoreiv.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    return BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(skills_dir) if skills_dir is not None else None,
    )


def test_untick_omits_tool_schema_from_agent_list():
    registry = ScopedToolRegistry()
    registry.register_tool(
        name="wiki_note_read",
        description="Read a wiki note",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=lambda path="": {"path": path},
    )
    registry.register_tool(
        name="wiki_note_create",
        description="Create a wiki note",
        parameters={"type": "object", "properties": {"title": {"type": "string"}}},
        handler=lambda title="": {"title": title},
    )
    ticked = AgentProfile(
        id="assistant-like",
        name="Assistant like",
        description="Has wiki read",
        system_prompt="You help.",
        allowed_tool_names=["wiki_note_read"],
    )
    tools = registry.get_tools_for_agent(ticked)
    names = [t.name for t in tools]
    assert names == ["wiki_note_read"]
    schemas = [t.parameters for t in tools]
    assert schemas[0]["properties"]["path"]["type"] == "string"
    assert "wiki_note_create" not in names


def test_wiki_read_and_write_are_separate_registered_tools(tmp_path):
    _registry, tool_reg = _bootstrap(tmp_path)
    names = {t.name for t in tool_reg.list_tools()}
    assert "wiki_note_read" in names
    assert "wiki_note_create" in names
    assert "wiki_note_update" in names
    assert "wiki" not in names
    assert "wiki_read" not in names
    assert "wiki_write" not in names
    read_def = tool_reg.get_tool_definition("wiki_note_read")
    write_def = tool_reg.get_tool_definition("wiki_note_create")
    assert read_def is not None and write_def is not None
    assert read_def.name != write_def.name
    assert read_def.description != write_def.description


def test_skill_md_stub_json_tools_are_not_model_callables(tmp_path):
    skills = tmp_path / "skills"
    pack = skills / "user-runbook"
    pack.mkdir(parents=True)
    (pack / "SKILL.md").write_text(
        """---
name: user-runbook
description: Generic user skill fixture.
---

Playbook body.

```json
{
  "name": "list_lab_users",
  "description": "Stub. Not wired.",
  "parameters": {"type": "object", "properties": {}}
}
```
""",
        encoding="utf-8",
    )
    _registry, tool_reg = _bootstrap(tmp_path, skills)
    catalog = _registry.user_skill_catalog
    opened = catalog.skill_view("user-runbook")
    assert opened["success"] is True
    stub_names = {t["name"] for t in opened["tools"]}
    assert "list_lab_users" in stub_names
    registered = {t.name for t in tool_reg.list_tools()}
    assert "list_lab_users" not in registered
    assistant = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Has catalog openers",
        system_prompt="You help.",
        allowed_tool_names=["list_user_skill_packs", "skill_view", "wiki_note_read"],
        allowed_skill=["user-runbook"],
    )
    model_tools = {t.name for t in tool_reg.get_tools_for_agent(assistant)}
    assert "skill_view" in model_tools
    assert "list_user_skill_packs" in model_tools
    assert "list_lab_users" not in model_tools


def test_builtin_allowlists_unchanged_for_specialists():
    from src.domain.agents.profiles import (
        AGENT_BUILDER_PROFILE,
        ASSISTANT_PROFILE,
        AUTOREIV_PROFILE,
        CODING_PROFILE,
        CONDUCTOR_PROFILE,
        REVIEW_PROFILE,
    )

    assert "wiki_note_read" in ASSISTANT_PROFILE.allowed_tool_names
    assert "wiki_note_create" in ASSISTANT_PROFILE.allowed_tool_names
    assert "wiki_note_read" in AUTOREIV_PROFILE.allowed_tool_names
    assert "execute_code" in CODING_PROFILE.allowed_tool_names
    assert "wiki_note_read" not in CODING_PROFILE.allowed_tool_names
    assert "execute_code" not in CONDUCTOR_PROFILE.allowed_tool_names
    assert "execute_code" not in REVIEW_PROFILE.allowed_tool_names
    assert "skill_view" in AGENT_BUILDER_PROFILE.allowed_tool_names
    assert "skill_view" not in CODING_PROFILE.allowed_tool_names
