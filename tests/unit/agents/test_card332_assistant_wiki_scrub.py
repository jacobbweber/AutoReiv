"""CARD-332: Assistant constitution Wiki scrub tests.

Verifies that Assistant no longer carries Wiki operating instructions,
redundant Wiki skill runbooks, or Wiki tools, leaving them exclusively
with the Wiki Librarian platform pack.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.domain.agents.good_agent_instructions import (
    render_good_agent_instructions,
)

ROOT = Path(__file__).resolve().parents[3]
ASSISTANT_DIR = ROOT / "platform-packs" / "assistant"
WIKI_DIR = ROOT / "platform-packs" / "wiki"


def test_assistant_pack_manifest_scrubbed_of_wiki():
    """Verify assistant pack is retired and does not exist in platform-packs [CARD-341]."""
    pack_path = ASSISTANT_DIR / "pack.json"
    assert not pack_path.exists(), "Assistant pack must be deleted from platform-packs"


def test_assistant_pack_has_no_duplicate_wiki_skill():
    wiki_skill_dir = ASSISTANT_DIR / "skills" / "wiki"
    assert not wiki_skill_dir.exists(), "Duplicate wiki skill directory must be removed from Assistant pack"


def test_wiki_pack_retains_wiki_curation_ownership():
    """Verify wiki pack is retired from platform-packs and autoreiv owns wiki curation [CARD-341]."""
    pack_path = WIKI_DIR / "pack.json"
    assert not pack_path.exists(), "Wiki pack must be deleted from platform-packs"

    autoreiv_pack_path = ROOT / "platform-packs" / "autoreiv" / "pack.json"
    assert autoreiv_pack_path.is_file(), "AutoReiv pack.json missing"
    data = json.loads(autoreiv_pack_path.read_text(encoding="utf-8"))

    skill_ids = {s.get("id") for s in data.get("skills", [])}
    assert "wiki" in skill_ids

    pack_tools = set(data.get("pack_tool_names", []))
    assert "wiki_note_create" in pack_tools
    assert "wiki_note_organize" in pack_tools


def test_good_agent_template_does_not_inject_wiki_rules_by_default():
    prompt = render_good_agent_instructions(
        name="GeneralAgent",
        role="task helper",
        domain_focus="general tasks",
    )
    assert "hunt for Wiki vault files" not in prompt
    assert "Always use canonical wiki_* tools" not in prompt
