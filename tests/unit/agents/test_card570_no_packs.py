"""CARD-570 guard: no pack concept remains in src/ (agents and skills are files; ADR-0062)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]
BANNED = ("pack.json", "platform-packs", "agent_pack", "keep_customizations", "skill_bindings")


def test_no_pack_terms_in_src():
    hits = []
    for path in (ROOT / "src").rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".js", ".html", ".css", ".md", ".json", ".toml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in BANNED:
            if term in text:
                hits.append(f"{path.relative_to(ROOT)}: {term}")
    assert not hits, "pack terms left in src/:\n" + "\n".join(hits)


def test_no_pack_wording_in_src_or_shipped_content():
    """CARD-570: the word "pack" is gone from src/ and platform/ (package/packet/unpack are other words)."""
    hits = []
    for base in (ROOT / "src", ROOT / "platform"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".js", ".html", ".css", ".md", ".json", ".toml", ".yaml"}:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                cleaned = re.sub(r"(?i)packag\w*|packet\w*|unpack\w*|backpack\w*", "", line)
                if re.search(r"(?i)pack", cleaned):
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:120]}")
    assert not hits, "pack wording left:\n" + "\n".join(hits[:40])


def test_no_pack_folders_ship():
    assert not (ROOT / "platform-packs").exists()
    assert not (ROOT / "src" / "infrastructure" / "skills" / "seeds").exists()
    assert (ROOT / "platform" / "agents").is_dir() and (ROOT / "platform" / "skills").is_dir()


def test_shipped_agents_are_markdown_with_frontmatter():
    ids = sorted(p.stem for p in (ROOT / "platform" / "agents").glob("*.md"))
    assert ids == ["architect", "autoreiv", "developer", "direct", "toolsmith", "tutor"]
    for agent_id in ids:
        text = (ROOT / "platform" / "agents" / f"{agent_id}.md").read_text(encoding="utf-8")
        assert text.startswith("---"), agent_id
        front = text.split("---", 2)[1]
        assert not re.search(r"^(model|provider|api_key|api_base_url):", front, re.M), (
            f"{agent_id}: model/provider are per-agent settings, not agent-file fields"
        )


def test_db_schema_has_no_agent_or_skill_definition_tables():
    schema = (ROOT / "src" / "infrastructure" / "memory" / "schema.py").read_text(encoding="utf-8")
    for table in ("agent_overrides", "custom_agents", "skill_tool_bindings"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" not in schema, table
