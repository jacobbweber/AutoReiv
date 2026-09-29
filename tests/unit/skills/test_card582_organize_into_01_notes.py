"""CARD-582: wiki_note_organize files into 01_Notes/, not the legacy notes/ tree, in a scaffolded vault."""

from __future__ import annotations

import shutil

from src.application.skills.librarian_tools import LibrarianTools


def test_organize_moves_inbox_note_into_01_notes(tmp_path):
    tools = LibrarianTools(wiki_root=str(tmp_path))
    assert (tmp_path / "01_Notes").is_dir()
    tools.create_wiki_note(title="W40", category="inbox", content="- [ ] renew passport", relative_path="00_Inbox/w40.md")
    res = tools.organize_wiki_note(source_path="00_Inbox/w40.md", target_domain="weekly", target_topic="worklog")
    assert res["success"] is True
    assert res["target_path"] == "01_Notes/weekly/worklog/w40.md"
    assert (tmp_path / "01_Notes/weekly/worklog/w40.md").is_file()
    assert not (tmp_path / "notes").exists()
    assert not (tmp_path / "00_Inbox/w40.md").exists()


def test_legacy_vault_without_01_notes_keeps_notes(tmp_path):
    tools = LibrarianTools(wiki_root=str(tmp_path))
    tools.create_wiki_note(title="Old", category="inbox", content="x", relative_path="00_Inbox/old.md")
    shutil.rmtree(tmp_path / "01_Notes")
    res = tools.organize_wiki_note(source_path="00_Inbox/old.md", target_domain="general", target_topic="misc")
    assert res["success"] is True
    assert res["target_path"] == "notes/general/misc/old.md"
