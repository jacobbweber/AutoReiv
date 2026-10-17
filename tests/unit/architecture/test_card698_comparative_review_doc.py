"""CARD-698 guard: comparative architecture review of Crucible and Agent-OS against AutoReiv."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]
DOC_PATH = ROOT / "docs" / "architecture-comparison-crucible-agent-os.md"
DOCS_README = ROOT / "docs" / "README.md"


def test_comparative_review_doc_exists_and_is_indexed() -> None:
    """docs/architecture-comparison-crucible-agent-os.md exists, stays <= 800 lines, and is linked in docs/README.md."""
    assert DOC_PATH.is_file(), f"Missing {DOC_PATH}"
    text = DOC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert 120 <= len(lines) <= 800, f"Expected 120..800 lines, got {len(lines)}"

    readme_text = DOCS_README.read_text(encoding="utf-8")
    assert "(architecture-comparison-crucible-agent-os.md)" in readme_text


def test_comparative_review_covers_three_systems_six_layers_and_ranked_recommendations() -> None:
    """The comparative review covers AutoReiv, Crucible, and Agent-OS across all 6 layers and ranks Adopt/Adapt/Skip proposals."""
    text = DOC_PATH.read_text(encoding="utf-8")

    for system in ("AutoReiv", "Crucible", "Agent-OS"):
        assert system in text, f"Missing system in comparison: {system}"

    required_sections = (
        "## 1. Executive Summary & Side-by-Side Matrix",
        "## 2. Kernel Execution, Control Flow & Turn Tracing",
        "## 3. Capabilities: Skills, Recipes, Ingredients & Tools",
        "## 4. State, Memory, Compaction & Hot/Cold Session Archiving",
        "## 5. Autonomy, Governance, Self-Authoring & Graduation",
        "## 6. Operator Surface, Zero-Friction Setup & Verification Loops",
        "## 7. Prioritized Recommendations for AutoReiv (Adopt / Adapt / Skip)",
        "## 8. Decision Options for Next Milestone",
    )
    for section in required_sections:
        assert section in text, f"Missing required section heading: {section}"

    for disposition in ("Adopt", "Adapt", "Skip"):
        assert disposition in text, f"Missing disposition category: {disposition}"

    # Verify concrete references to key Crucible and Agent-OS mechanisms inspected
    for mechanism in (
        "compaction.py",
        "retention.py",
        "trace.py",
        "local_setup.py",
        "ADR-0008",
        "ADR-0009",
        "ADR-0014",
        "ADR-0015",
        "AUTOREIV_APPROVAL_MODE",
        "resolve_allowed_tools",
    ):
        assert mechanism in text, f"Missing concrete mechanism reference: {mechanism}"


def test_docs_readme_links_resolve() -> None:
    """Every relative markdown link in docs/README.md resolves to an existing path."""
    readme_text = DOCS_README.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+)\)", readme_text)
    assert links, "Expected markdown links in docs/README.md"
    for link in links:
        if link.startswith(("http://", "https://", "file://")):
            continue
        resolved = (DOCS_README.parent / link).resolve()
        assert resolved.exists(), f"Broken link in docs/README.md: {link} -> {resolved}"
