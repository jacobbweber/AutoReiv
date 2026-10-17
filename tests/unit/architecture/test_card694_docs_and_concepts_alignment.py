"""CARD-694 guard: AUTOREIV_CONCEPTS, user-guide, steering docs, and findings match M26-M28."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.domain.agents.product_concepts import AUTOREIV_CONCEPTS

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def test_autoreiv_concepts_names_three_shipped_agents_and_capabilities_studio() -> None:
    """AUTOREIV_CONCEPTS must list only AutoReiv, Tutor, Direct and name the Capabilities studio."""
    assert "Shipped agents: AutoReiv, Tutor, Direct." in AUTOREIV_CONCEPTS
    assert "Capabilities studio" in AUTOREIV_CONCEPTS
    for retired in ("Architect", "Toolsmith", "Skill Studio", "Tools Studio"):
        assert retired not in AUTOREIV_CONCEPTS, f"Retired name still in AUTOREIV_CONCEPTS: {retired}"


def test_user_guide_and_product_steering_match_unified_capabilities_and_three_agents() -> None:
    """docs/user-guide.md and steering/product.md reflect Capabilities studio and the 3-agent roster."""
    user_guide = (ROOT / "docs" / "user-guide.md").read_text(encoding="utf-8")
    assert "| **Capabilities** |" in user_guide
    for retired_row in ("| **Skill Studio** |", "| **Tools Studio** |", "| **Architect** |", "| **Developer** |", "| **Toolsmith** |"):
        assert retired_row not in user_guide, f"Retired table row still in docs/user-guide.md: {retired_row}"

    product_md = (ROOT / "steering" / "product.md").read_text(encoding="utf-8")
    assert "Capabilities (`capabilities_studio.js`)" in product_md
    assert "authoring jobs go to Toolsmith" not in product_md
    assert "the active project for Architect and Developer" not in product_md


def test_findings_has_no_already_done_carded_entries() -> None:
    """docs/findings.md must not retain entries already carded into Done cards or pointing to platform-packs/developer."""
    findings = (ROOT / "docs" / "findings.md").read_text(encoding="utf-8")
    assert "platform-packs/developer" not in findings
    assert "platform/skills/native-tool-engineering" not in findings

    carded_matches = re.findall(r"carded as (CARD-\d+)", findings)
    assert carded_matches == [], f"Resolved carded findings still listed in docs/findings.md: {carded_matches}"
