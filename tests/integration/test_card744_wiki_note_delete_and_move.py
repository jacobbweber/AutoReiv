"""CARD-744: Operator contract for HITL-gated wiki_note_delete and wiki_note_move with empty-folder pruning."""

from __future__ import annotations

from pathlib import Path

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.kernel.tool_access import WRITE, tool_access
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.application.skills.wiki_tools import WikiTools
from src.domain.gateway.models import ToolCall


def test_card744_wiki_note_delete_and_move_registered_and_hitl_gated(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    tools = WikiTools(wiki_root=wiki_root)
    registry = ScopedToolRegistry()
    tools.register_tools(registry)

    assert "wiki_note_delete" in registry.builtin_tool_names()
    assert "wiki_note_move" in registry.builtin_tool_names()
    assert registry.get_tool_risk("wiki_note_delete") == "destructive"
    assert registry.get_tool_risk("wiki_note_move") == "write"
    assert tool_access("wiki_note_delete") == WRITE
    assert tool_access("wiki_note_move") == WRITE

    allowed = resolve_allowed_tools({"allowed_skill": ["wiki-curation"]})
    assert "wiki_note_delete" in allowed
    assert "wiki_note_move" in allowed

    gate = ToolPolicyGate(store=None)
    agent = {"id": "autoreiv", "allowed_skill": ["wiki-curation"]}
    del_decision = gate.evaluate(
        ToolCall(id="tc_del", name="wiki_note_delete", arguments={"relative_path": "01_Notes/general/ai/stub.md"}),
        agent,
        registry_tool_names=set(registry._tools.keys()),
        tool_risk=registry.get_tool_risk("wiki_note_delete"),
    )
    assert del_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    assert "destructive" in del_decision.reason.lower()

    move_decision = gate.evaluate(
        ToolCall(
            id="tc_move",
            name="wiki_note_move",
            arguments={
                "source_path": "01_Notes/general/ai/stub.md",
                "destination_path": "01_Notes/devops/splunk/stub.md",
            },
        ),
        agent,
        registry_tool_names=set(registry._tools.keys()),
        tool_risk=registry.get_tool_risk("wiki_note_move"),
    )
    assert move_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM


def test_card744_wiki_note_delete_prunes_empty_topic_and_domain_folders(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    tools = WikiTools(wiki_root=wiki_root)

    tools.store.write_note(
        relative_path="01_Notes/general/artificial_intelligence/splunk_learning_topic.md",
        content="Temporary stub note created in wrong folder.",
        update_frontmatter={
            "title": "Splunk Learning Topic",
            "domain": "general",
            "topic": "artificial_intelligence",
        },
    )
    note_file = wiki_root / "01_Notes" / "general" / "artificial_intelligence" / "splunk_learning_topic.md"
    assert note_file.is_file()

    res = tools.delete_wiki_note(
        relative_path="01_Notes/general/artificial_intelligence/splunk_learning_topic.md",
        reason="Duplicate stub cleanup",
    )
    assert res["success"] is True
    assert res["deleted_path"] == "01_Notes/general/artificial_intelligence/splunk_learning_topic.md"
    assert not note_file.exists()
    # Both empty topic and empty domain folders are pruned, while 01_Notes root stays intact.
    assert not (wiki_root / "01_Notes" / "general" / "artificial_intelligence").exists()
    assert not (wiki_root / "01_Notes" / "general").exists()
    assert (wiki_root / "01_Notes").is_dir()
    assert "01_Notes/general/artificial_intelligence" in res["pruned_dirs"]
    assert "01_Notes/general" in res["pruned_dirs"]

    tree = tools.store.get_tree()
    assert "general" not in tree["01_Notes"]

    # Negative assertions: refuses path traversal and refuses deleting templates.
    bad_traversal = tools.delete_wiki_note(relative_path="../../outside.md")
    assert bad_traversal["success"] is False
    assert "outside" in bad_traversal["error"].lower() or "traversal" in bad_traversal["error"].lower()

    bad_template = tools.delete_wiki_note(relative_path="02_Resources/_Templates/note_template.md")
    assert bad_template["success"] is False
    assert "template" in bad_template["error"].lower()
    assert (wiki_root / "02_Resources" / "_Templates" / "note_template.md").is_file()


def test_card744_wiki_note_move_updates_frontmatter_and_prunes_empty_source_folders(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    tools = WikiTools(wiki_root=wiki_root)

    tools.store.write_note(
        relative_path="01_Notes/general/temp_topic/splunk_guide.md",
        content="# Splunk Architecture\n\nIndexer, Forwarder, and Search Head.",
        update_frontmatter={
            "title": "Splunk Architecture Guide",
            "domain": "general",
            "topic": "temp_topic",
            "tags": ["splunk"],
        },
    )

    res = tools.move_wiki_note(
        source_path="01_Notes/general/temp_topic/splunk_guide.md",
        destination_path="01_Notes/devops/splunk/splunk_guide.md",
    )
    assert res["success"] is True
    assert res["destination_path"] == "01_Notes/devops/splunk/splunk_guide.md"
    assert res["domain"] == "devops"
    assert res["topic"] == "splunk"

    assert not (wiki_root / "01_Notes" / "general" / "temp_topic" / "splunk_guide.md").exists()
    assert not (wiki_root / "01_Notes" / "general" / "temp_topic").exists()
    assert not (wiki_root / "01_Notes" / "general").exists()
    assert (wiki_root / "01_Notes" / "devops" / "splunk" / "splunk_guide.md").is_file()

    moved = tools.read_wiki_note(relative_path="01_Notes/devops/splunk/splunk_guide.md")
    assert moved["success"] is True
    assert moved["frontmatter"]["domain"] == "devops"
    assert moved["frontmatter"]["topic"] == "splunk"
    assert "Indexer, Forwarder" in moved["content"]

    # Negative assertion: refuses moving templates.
    bad_move = tools.move_wiki_note(
        source_path="02_Resources/_Templates/note_template.md",
        destination_path="01_Notes/devops/splunk/note_template.md",
    )
    assert bad_move["success"] is False
    assert "template" in bad_move["error"].lower()


def test_card744_parked_tool_records_deferred_sibling_tool_calls():
    from src.application.kernel.reply_rules import record_deferred_sibling_tool_calls
    from src.domain.gateway.models import Role

    saved = []

    class DummyStore:
        def save_message(self, session_id: str, agent_id: str, message):
            saved.append((session_id, agent_id, message))

    history = []
    remaining = [
        ToolCall(id="call_del_1", name="wiki_note_delete", arguments={"relative_path": "01_Notes/general/stub.md"})
    ]
    record_deferred_sibling_tool_calls(
        DummyStore(), "sess_1", "autoreiv", "wiki_note_move", remaining, history, save_to_history=True
    )
    assert len(history) == 1
    assert len(saved) == 1
    msg = history[0]
    assert msg.role == Role.TOOL
    assert msg.tool_call_id == "call_del_1"
    assert msg.name == "wiki_note_delete"
    assert "Not run yet" in msg.content
    assert "wiki_note_move" in msg.content
    assert "Call 'wiki_note_delete' again now" in msg.content

