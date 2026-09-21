"""
Unit tests for Wiki Thin Grounding Creation Intent & Provenanced Tools Parity [CARD-409].
"""

from src.application.orchestration.wiki_thin_grounding import (
    assess_wiki_thin_grounding,
    collect_provenanced_paths_from_tool_result,
    format_grounding_constraint_block,
    is_wiki_create_ask,
    ungrounded_claimed_paths,
)


def test_is_wiki_create_ask_detects_creation_intent():
    assert is_wiki_create_ask("hi, can you do a system health check, and then save that note to the wiki") is True
    assert is_wiki_create_ask("create a note about quantum computing in the wiki") is True
    assert is_wiki_create_ask("write a runbook for redis restart to the wiki") is True
    assert is_wiki_create_ask("stage a note in 00_inbox") is True

    # Pure query/summarize is NOT create ask
    assert is_wiki_create_ask("what does the wiki say about docker?") is False
    assert is_wiki_create_ask("summarize the existing notes on python") is False


def test_creation_intent_not_poisoned_by_irrelevant_hits():
    # User asks to save health check note; search returns irrelevant hits like weekly note W35
    intent = "hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"
    hits = [
        {"path": "01_Notes/weekly/2026-W35.md", "title": "WEEK 35", "summary": "System health check tasks"},
        {"path": "02_Resources/_Templates/sop-runbook.md", "title": "SOP Runbook", "summary": "System runbook"},
    ]
    decision = assess_wiki_thin_grounding(intent, hits)

    # For creation-shaped asks, action should reflect that novel staging is expected
    assert decision.create_shaped is True

    block = format_grounding_constraint_block(decision)
    # The prompt constraint must NOT tell the model it cannot create new notes in 00_Inbox
    assert "Allowed to stage new notes in `00_Inbox/`" in block or "creation-shaped" in block or "00_Inbox" in block


def test_provenance_collector_recognizes_all_note_tools():
    # 1. wiki_note_create
    p1 = collect_provenanced_paths_from_tool_result("wiki_note_create", {"success": True, "path": "00_Inbox/health_check.md"})
    assert "00_Inbox/health_check.md" in p1

    # 2. wiki_note_update
    p2 = collect_provenanced_paths_from_tool_result("wiki_note_update", {"success": True, "path": "01_Notes/general/tech/doc.md"})
    assert "01_Notes/general/tech/doc.md" in p2

    # 3. wiki_note_organize
    p3 = collect_provenanced_paths_from_tool_result("wiki_note_organize", {"success": True, "target_path": "01_Notes/engineering/architecture/api.md"})
    assert "01_Notes/engineering/architecture/api.md" in p3

    # 4. wiki_note_archive
    p4 = collect_provenanced_paths_from_tool_result("wiki_note_archive", {"success": True, "archive_path": "03_Archive/old_note.md"})
    assert "03_Archive/old_note.md" in p4

    # 5. wiki_template_create
    p5 = collect_provenanced_paths_from_tool_result("wiki_template_create", {"success": True, "path": "02_Resources/_Templates/custom-spec.md"})
    assert "02_Resources/_Templates/custom-spec.md" in p5


def test_honesty_gate_accepts_provenanced_weekly_note_paths():
    provenanced = ["01_Notes/weekly/2026-W39.md"]
    text = "Logged the task into `01_Notes/weekly/2026-W39.md` successfully."
    bad = ungrounded_claimed_paths(text, provenanced)
    assert bad == []
