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
    pack_path = ASSISTANT_DIR / "pack.json"
    assert pack_path.is_file(), "Assistant pack.json missing"
    data = json.loads(pack_path.read_text(encoding="utf-8"))

    prompt = data.get("system_prompt", "")
    assert "search and write knowledge notes in the Wiki" not in prompt
    assert "Wiki notes," not in prompt
    assert "hunt for Wiki vault files" not in prompt

    allowed_skills = data.get("allowed_skill", [])
    assert "wiki" not in allowed_skills
    assert "weekly-tasks" in allowed_skills

    pack_tools = data.get("pack_tool_names", [])
    wiki_tools = {
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_note_organize",
        "wiki_overview",
        "wiki_graph",
        "promote_artifact_to_wiki",
    }
    present_wiki_tools = set(pack_tools) & wiki_tools
    assert not present_wiki_tools, f"Assistant pack still carries wiki tools: {present_wiki_tools}"


def test_assistant_pack_has_no_duplicate_wiki_skill():
    wiki_skill_dir = ASSISTANT_DIR / "skills" / "wiki"
    assert not wiki_skill_dir.exists(), "Duplicate wiki skill directory must be removed from Assistant pack"


def test_wiki_pack_retains_wiki_curation_ownership():
    pack_path = WIKI_DIR / "pack.json"
    assert pack_path.is_file(), "Wiki pack.json missing"
    data = json.loads(pack_path.read_text(encoding="utf-8"))

    prompt = data.get("system_prompt", "")
    assert "Wiki Librarian" in prompt
    assert "wiki_note_create" in prompt

    skill_ids = {s.get("id") for s in data.get("skills", [])}
    assert "wiki-curation" in skill_ids

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
