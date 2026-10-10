"""CARD-686: retired names must not appear in strings the server sends.

Scans every string literal (including docstrings, which FastAPI shows in the
API docs, and tool descriptions and prompt text the agents repeat to the user).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RETIRED = re.compile(
    r"Purpose Matrix|Observe Studio|Agent Forge|Forge Studio|Forge Approve|\bLumina\b|platform[- ]packs|Docs Studio",
    re.IGNORECASE,
)


def test_card686_no_retired_names_in_server_strings() -> None:
    hits: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and RETIRED.search(node.value):
                hits.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert hits == []


def test_card686_agent_concepts_name_the_agents_studio() -> None:
    from src.domain.agents.product_concepts import AUTOREIV_CONCEPTS

    assert "Agents studio" in AUTOREIV_CONCEPTS
    assert "Toolsmith" in AUTOREIV_CONCEPTS
