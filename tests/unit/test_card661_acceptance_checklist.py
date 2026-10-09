"""CARD-661: the written 1.0 acceptance checklist exists and covers the required steps."""

from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "acceptance-checklist-1.0.md"


def test_checklist_covers_required_steps():
    assert DOC.is_file(), "docs/acceptance-checklist-1.0.md is missing"
    text = DOC.read_text(encoding="utf-8").lower()
    for step in (
        "fresh install",
        "real chat",
        "wiki action",
        "course step",
        "skill toggle",
        "agent studio",
        "routine",
        "restart",
        "persistence",
    ):
        assert step in text, step
    assert "throwaway data folder" in text
    assert "card-661" in text
