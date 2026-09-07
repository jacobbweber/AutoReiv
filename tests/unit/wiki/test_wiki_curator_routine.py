"""
Unit tests for WikiCuratorRoutine [CARD-173].
Tests autonomous inbox curation, tag authority self-registration, deduplication, and fluff scrubbing.
"""

import tempfile

import pytest

from src.application.routines.wiki_curator import WikiCuratorRoutine
from src.domain.wiki.store import WikiStore


@pytest.fixture
def temp_wiki():
    with tempfile.TemporaryDirectory() as tmp:
        store = WikiStore(root_dir=tmp)
        store.scaffold()
        yield store


def test_curate_empty_inbox(temp_wiki):
    """Verify curation succeeds gracefully when 00_Inbox is empty."""
    curator = WikiCuratorRoutine(store=temp_wiki)
    res = curator.curate_inbox()
    assert res["success"] is True
    assert res["curated_count"] == 0


def test_curate_graduates_inbox_note_to_notes(temp_wiki):
    """Verify curation cleans fluff, validates frontmatter, and graduates note to 01_Notes/."""
    raw_content = (
        "Here is what you requested! 🚀\n\n"
        "# Storage Spaces Direct Architecture\n\n"
        "Storage Spaces Direct (S2D) uses industry-standard servers with local storage.\n\n"
        "Hope this helps! Let me know if you need anything else! 😊"
    )
    file_res = temp_wiki.file_note(
        title="Storage Spaces Direct Architecture",
        content=raw_content,
        domain="systems_engineering",
        topic="storage",
        category="inbox",
    )
    assert file_res["success"] is True
    inbox_path = temp_wiki.root_dir / file_res["path"]
    assert inbox_path.exists()

    curator = WikiCuratorRoutine(store=temp_wiki)
    res = curator.curate_inbox()
    assert res["success"] is True
    assert res["curated_count"] == 1

    # Source in 00_Inbox must be removed
    assert not inbox_path.exists()

    # Destination in 01_Notes must exist
    dest_path = temp_wiki.root_dir / "01_Notes" / "systems_engineering" / "storage" / "storage_spaces_direct_architecture.md"
    assert dest_path.exists()

    # Content must be scrubbed of fluff
    read_res = temp_wiki.read_note("01_Notes/systems_engineering/storage/storage_spaces_direct_architecture.md")
    assert read_res["success"] is True
    assert "Here is what you requested" not in read_res["content"]
    assert "Hope this helps" not in read_res["content"]
    assert "Storage Spaces Direct" in read_res["content"]
    assert read_res["meta"]["status"] == "final"


def test_curate_tag_authority_check_and_register(temp_wiki):
    """Verify novel tags are checked and self-registered into tag-authority.md."""
    tag_auth_file = temp_wiki.root_dir / "02_Resources" / "_Templates" / "tag-authority.md"
    assert tag_auth_file.exists()
    assert "quantum_computing" not in tag_auth_file.read_text(encoding="utf-8")

    temp_wiki.file_note(
        title="Qubit Superposition",
        content="Overview of quantum superposition principles.",
        domain="computer_science",
        topic="quantum",
        tags=["quantum_computing", "qubits"],
        category="inbox",
    )

    curator = WikiCuratorRoutine(store=temp_wiki)
    res = curator.curate_inbox()
    assert res["success"] is True

    # Check that tag authority was updated with the novel tag
    updated_auth = tag_auth_file.read_text(encoding="utf-8")
    assert "quantum_computing" in updated_auth


def test_curate_deduplicates_and_appends(temp_wiki):
    """Verify high-similarity notes are appended to existing notes rather than creating duplicates."""
    # 1. Existing permanent note in 01_Notes/
    existing_res = temp_wiki.file_note(
        title="Hyper-V Virtual Switch Guide",
        content="Base configuration for external vSwitches.",
        domain="systems_engineering",
        topic="hyperv",
        category="notes",
    )
    assert existing_res["success"] is True

    # 2. Duplicate note staged in 00_Inbox/
    temp_wiki.file_note(
        title="Hyper-V Virtual Switch Guide",
        content="Additional details on teaming and SR-IOV performance settings.",
        domain="systems_engineering",
        topic="hyperv",
        category="inbox",
    )

    curator = WikiCuratorRoutine(store=temp_wiki)
    res = curator.curate_inbox()
    assert res["success"] is True

    # Check that existing note received append
    read_res = temp_wiki.read_note(existing_res["path"])
    assert "SR-IOV" in read_res["content"]
    assert "Base configuration" in read_res["content"]

    # Check that inbox note was removed
    inbox_files = list((temp_wiki.root_dir / "00_Inbox").glob("*.md"))
    assert len(inbox_files) == 0
