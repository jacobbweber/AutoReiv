"""CARD-589: wiki_note_list category filter matches the scaffolded numbered folders (it returned [] for 'notes')."""

from __future__ import annotations

import tempfile

import pytest

from src.domain.wiki.store import WikiStore


@pytest.fixture
def wiki():
    with tempfile.TemporaryDirectory() as tmp:
        store = WikiStore(root_dir=tmp)
        store.scaffold()
        (store.root_dir / "01_Notes").mkdir(exist_ok=True)
        (store.root_dir / "01_Notes" / "k8s.md").write_text("---\ntitle: K8s\n---\n# K8s\n", encoding="utf-8")
        (store.root_dir / "00_Inbox" / "idea.md").write_text("---\ntitle: Idea\n---\n# Idea\n", encoding="utf-8")
        yield store


def _paths(notes):
    return sorted(n["path"] for n in notes)


def test_enum_categories_match_numbered_folders(wiki):
    assert _paths(wiki.list_notes(category="notes")) == ["01_Notes/k8s.md"]
    assert _paths(wiki.list_notes(category="inbox")) == ["00_Inbox/idea.md"]
    resources = _paths(wiki.list_notes(category="resources"))
    assert resources and all(p.startswith("02_Resources/") for p in resources)


def test_folder_names_and_legacy_folders_still_work(wiki):
    assert _paths(wiki.list_notes(category="01_Notes")) == ["01_Notes/k8s.md"]
    assert _paths(wiki.list_notes(category="Notes/")) == ["01_Notes/k8s.md"]
    (wiki.root_dir / "notes").mkdir()
    (wiki.root_dir / "notes" / "old.md").write_text("---\ntitle: Old\n---\n", encoding="utf-8")
    assert _paths(wiki.list_notes(category="notes")) == ["01_Notes/k8s.md", "notes/old.md"]
