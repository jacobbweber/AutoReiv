"""
Unit tests for CARD-406: Vanilla Wiki Seeding Invariants.

Ensures that when a fresh Wiki is seeded, it contains only the canonical numbered
folder structure (00_Inbox, 01_Notes, 02_Resources/_Templates, 03_Archive),
with clean templates and zero rogue folders or fake pre-filled notes.
"""

from pathlib import Path

from src.domain.wiki.store import WikiStore


def test_vanilla_wiki_scaffold_seeding(tmp_path: Path):
    """
    On a fresh scaffold(auto_seed=True), only canonical directories and templates
    should exist, with no rogue 'notes' folder or pre-filled fake weekly notes.
    """
    wiki_root = tmp_path / "wiki"
    store = WikiStore(root_dir=str(wiki_root))
    store.scaffold(seed_starter=True)

    # 1. Canonical numbered directories exist
    assert (wiki_root / "00_Inbox").is_dir()
    assert (wiki_root / "01_Notes").is_dir()
    assert (wiki_root / "02_Resources").is_dir()
    assert (wiki_root / "02_Resources" / "_Templates").is_dir()
    assert (wiki_root / "03_Archive").is_dir()

    # 2. Rogue unnumbered 'notes' directory does NOT exist
    assert not (wiki_root / "notes").exists(), "Rogue 'notes' directory was created during seeding!"

    # 3. No pre-filled notes exist in 00_Inbox or 01_Notes
    inbox_md_files = list((wiki_root / "00_Inbox").glob("*.md"))
    notes_md_files = list((wiki_root / "01_Notes").rglob("*.md"))
    assert inbox_md_files == [], f"00_Inbox should be empty on fresh seed, found: {inbox_md_files}"
    assert notes_md_files == [], f"01_Notes should be empty on fresh seed, found: {notes_md_files}"

    # 4. Canonical templates exist
    weekly_template_path = wiki_root / "02_Resources" / "_Templates" / "weekly_notes.md"
    assert weekly_template_path.exists(), "weekly_notes.md template missing from _Templates!"

    # 5. Templates are clean and do NOT contain mock company projects
    weekly_template_content = weekly_template_path.read_text(encoding="utf-8")
    for mock_term in ["Server Currency", "AQS Migration", "Leaders Life"]:
        assert mock_term not in weekly_template_content, (
            f"Mock project '{mock_term}' found in canonical weekly_notes.md template!"
        )

    # 6. Basic templates present
    note_template_path = wiki_root / "02_Resources" / "_Templates" / "note_template.md"
    assert note_template_path.exists(), "note_template.md missing from _Templates!"
