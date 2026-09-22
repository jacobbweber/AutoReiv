"""
Unit tests for CARD-406 / CARD-416: Vanilla Wiki Seeding Invariants.

Ensures that when a fresh Wiki is seeded, it contains only the canonical numbered
folder structure (00_Inbox, 01_Notes, 02_Resources/_Templates, 03_Archive),
with clean templates and zero rogue folders, fake pre-filled notes, or leftover
empty seed taxonomy under 01_Notes.
"""

from pathlib import Path

from src.domain.wiki.store import WikiStore, _EMPTY_SEED_TAXONOMY_REL_PATHS


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

    # 3b. CARD-416: 01_Notes must have zero children (no empty taxonomy dirs)
    notes_children = list((wiki_root / "01_Notes").iterdir())
    assert notes_children == [], f"01_Notes must have zero children, found: {notes_children}"

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


def test_card416_scrub_removes_empty_seed_taxonomy_keeps_real_notes(tmp_path: Path):
    """
    Plant the five empty seed taxonomy dirs, re-scaffold/scrub → gone.
    A real operator note under 01_Notes is kept; a non-empty seed leaf is kept.
    """
    wiki_root = tmp_path / "wiki"
    store = WikiStore(root_dir=str(wiki_root))
    store.scaffold(seed_starter=False)

    notes = wiki_root / "01_Notes"
    for rel in _EMPTY_SEED_TAXONOMY_REL_PATHS:
        (notes / rel).mkdir(parents=True, exist_ok=True)

    # Real operator note outside the seed five-pack
    real_dir = notes / "operator" / "journal"
    real_dir.mkdir(parents=True, exist_ok=True)
    real_note = real_dir / "keeper.md"
    real_note.write_text("# Keeper\n\nOperator content.\n", encoding="utf-8")

    # Non-empty seed leaf must not be deleted
    kept_leaf = notes / "operations" / "worklog"
    kept_leaf.mkdir(parents=True, exist_ok=True)
    kept_note = kept_leaf / "real_worklog.md"
    kept_note.write_text("# Real worklog\n", encoding="utf-8")

    actions = store.scrub_empty_seed_taxonomy()
    # Also ensure scaffold path invokes scrub (idempotent second pass)
    store.scaffold(seed_starter=False, auto_migrate=False)

    assert real_note.is_file(), "Real operator note must be preserved"
    assert kept_note.is_file(), "Non-empty seed leaf note must be preserved"
    assert kept_leaf.is_dir(), "Non-empty operations/worklog must remain"

    # Empty seed leaves must be gone
    assert not (notes / "computer_science" / "artificial_intelligence").exists()
    assert not (notes / "computer_science").exists()
    assert not (notes / "general" / "notes").exists()
    assert not (notes / "general").exists()
    assert not (notes / "operations" / "diagnostics").exists()
    assert not (notes / "systems_engineering" / "observability").exists()
    assert not (notes / "systems_engineering").exists()
    # operations parent remains because worklog still has content
    assert (notes / "operations").is_dir()

    assert any(
        "computer_science" in a
        or "general" in a
        or "systems_engineering" in a
        or "diagnostics" in a
        for a in actions
    )
