"""CARD-426 operator contract: legacy-loader warning on a user-modified developer.

REQ-426-001: an older live native-tool-engineering skill gains the seed warning.
The developer prompt and unrelated skill bodies stay.
REQ-426-002: an edited skill file is not replaced with the seed copy.

Temp user-data only [ADR-0055]. Catalog labels do not read this skill file.
"""

from __future__ import annotations

from pathlib import Path

from src.application.capabilities.progressive_skills import load_one_skill_body
from src.application.tools.native_packaging import catalog_origin_label
from src.domain.settings.models import AgentCustomization
from src.infrastructure.skills.platform_packs import (
    LEGACY_LOADER_WARNING_HEADING,
    LEGACY_LOADER_WARNING_MARKER,
    install_platform_agent_packs,
)

NATIVE_SKILL = "native-tool-engineering"
PROMPT_MARK = "OPERATOR PROMPT CARD-426"
OPERATOR_KEPT = "OPERATOR KEPT THIS SENTENCE CARD-426"
OPERATOR_EDIT = "OPERATOR EDITED THIS RUNBOOK CARD-426"
SEED_ONLY = "A folder of scripts is chat context"
ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "platform-packs" / "developer" / "skills" / NATIVE_SKILL / "SKILL.md"

OLDER_SKILL = f"""---
name: Native AutoReiv Tool Engineering
description: Older runbook. No legacy-loader warning.
version: 0.9.0
---

# Native AutoReiv Tool Engineering

{OPERATOR_KEPT}

Use register_native_tool for a native custom tool. Do not replace this file.
"""

EDITED_WITH_MARKER = f"""---
name: Native AutoReiv Tool Engineering
description: Operator edited the runbook.
---

# Native AutoReiv Tool Engineering

{OPERATOR_EDIT}

{LEGACY_LOADER_WARNING_MARKER}

Keep this operator note. Do not replace the file with the seed.
"""

HEADING_WITHOUT_MARKER = f"""---
name: Native AutoReiv Tool Engineering
description: Operator already has the warning heading.
---

# Native AutoReiv Tool Engineering

{OPERATOR_EDIT}

{LEGACY_LOADER_WARNING_HEADING}

`packs/<id>/tools/*.py` is a legacy in-process loader. Tools Studio labels them **Legacy pack tool**.
"""

UNRELATED_SKILL = """---
name: Operator Notes
description: Unrelated skill body that must stay.
---

# Operator Notes

UNRELATED SKILL BODY CARD-426
"""


def _skill_bodies(skills_root: Path) -> dict[str, str]:
    bodies: dict[str, str] = {}
    if not skills_root.is_dir():
        return bodies
    for path in sorted(skills_root.glob("*/SKILL.md")):
        bodies[path.parent.name] = path.read_text(encoding="utf-8")
    return bodies


def _mark_developer(registry, store, prompt: str) -> None:
    developer = registry.get_agent("developer")
    assert developer is not None
    developer.system_prompt = prompt
    developer.user_modified = True
    store.save_custom_agent_profile(developer)
    store.mark_agent_user_modified("developer", modified=True)
    existing = store.get_agent_override("developer")
    store.save_agent_override(
        AgentCustomization(
            agent_id="developer",
            system_prompt=prompt,
            allowed_tool_names=list(developer.allowed_tool_names or []),
            allowed_skill=list(developer.allowed_skill or []),
            pack_tool_names=list(developer.pack_tool_names or []),
            mcp_servers=list(getattr(existing, "mcp_servers", None) or getattr(developer, "mcp_servers", None) or []),
            user_modified=True,
        )
    )


def _assert_prompt(registry, store, prompt: str) -> None:
    after = registry.get_agent("developer")
    assert after is not None
    assert after.system_prompt == prompt
    assert PROMPT_MARK in after.system_prompt
    assert LEGACY_LOADER_WARNING_MARKER not in after.system_prompt
    stored = store.get_agent_profile("developer")
    assert stored is not None
    assert stored.system_prompt == prompt
    override = store.get_agent_override("developer")
    assert override is not None
    assert override.system_prompt == prompt
    assert bool(after.user_modified) is True


def test_oc426_older_skill_gains_warning_without_replacing_file_or_prompt(operator_client):
    """REQ-426-001 and REQ-426-002. Append the warning. Keep operator text and the prompt."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    user_data = wiki.parent
    live = user_data / "packs" / "developer" / "skills" / NATIVE_SKILL / "SKILL.md"
    unrelated = user_data / "packs" / "developer" / "skills" / "operator-notes" / "SKILL.md"
    tutor_notes = user_data / "packs" / "tutor" / "skills" / "tutor-notes" / "SKILL.md"
    assert live.is_file()
    seed_text = SEED.read_text(encoding="utf-8")
    assert LEGACY_LOADER_WARNING_MARKER in seed_text
    assert LEGACY_LOADER_WARNING_HEADING in seed_text
    assert SEED_ONLY in seed_text

    prompt = f"{PROMPT_MARK}\n{registry.get_agent('developer').system_prompt}"
    _mark_developer(registry, store, prompt)

    live.write_text(OLDER_SKILL, encoding="utf-8")
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text(UNRELATED_SKILL, encoding="utf-8")
    tutor_notes.parent.mkdir(parents=True, exist_ok=True)
    tutor_notes.write_text(UNRELATED_SKILL, encoding="utf-8")
    before = _skill_bodies(live.parent.parent)
    assert OPERATOR_KEPT in before[NATIVE_SKILL]
    assert LEGACY_LOADER_WARNING_MARKER not in before[NATIVE_SKILL]
    assert LEGACY_LOADER_WARNING_HEADING not in before[NATIVE_SKILL]
    assert "Legacy pack tool" not in before[NATIVE_SKILL]
    assert catalog_origin_label("legacy_pack_tool") == "Legacy pack tool"
    assert catalog_origin_label("native_custom") == "Native custom"

    install_platform_agent_packs(user_data, registry, tools)

    updated = live.read_text(encoding="utf-8")
    assert updated.startswith(OLDER_SKILL)
    assert updated != seed_text
    assert SEED_ONLY not in updated, "REQ-426-002 FAIL: live skill was replaced with the seed copy"
    assert OPERATOR_KEPT in updated
    assert LEGACY_LOADER_WARNING_MARKER in updated
    assert updated.count(LEGACY_LOADER_WARNING_MARKER) == 1
    assert updated.count(LEGACY_LOADER_WARNING_HEADING) == 1
    assert "legacy in-process loader" in updated
    assert "Legacy pack tool" in updated
    assert "**Native custom**" in updated
    _assert_prompt(registry, store, prompt)

    after = _skill_bodies(live.parent.parent)
    assert set(after) == set(before)
    for skill_id, body in before.items():
        if skill_id == NATIVE_SKILL:
            continue
        assert after[skill_id] == body, f"REQ-426-001 FAIL: unrelated skill {skill_id} was rewritten"
    assert tutor_notes.read_text(encoding="utf-8") == UNRELATED_SKILL
    assert catalog_origin_label("legacy_pack_tool") == "Legacy pack tool"

    pack_read = client.get(f"/api/skills/user-packs/{NATIVE_SKILL}")
    assert pack_read.status_code == 200, pack_read.text
    pack_body = pack_read.json()
    assert Path(pack_body["manifest"]["path"]).resolve() == live.resolve()
    assert OPERATOR_KEPT in pack_body["instructions"]
    assert LEGACY_LOADER_WARNING_MARKER in pack_body["instructions"]
    assert "Legacy pack tool" in pack_body["instructions"]
    assert SEED_ONLY not in pack_body["markdown"]

    workshop = client.get(
        f"/api/skill_studio/skills/{NATIVE_SKILL}",
        params={"agent_id": "developer"},
    )
    assert workshop.status_code == 200, workshop.text
    workshop_body = workshop.json()
    assert Path(workshop_body["path"]).resolve() == live.resolve()
    assert OPERATOR_KEPT in workshop_body["markdown_content"]
    assert "legacy in-process loader" in workshop_body["markdown_content"]

    loaded = load_one_skill_body(registry.user_skill_catalog, NATIVE_SKILL)
    assert loaded.get("success") is True
    assert loaded.get("body_loaded") is True
    assert Path(loaded["path"]).resolve() == live.resolve()
    assert OPERATOR_KEPT in loaded["body"]
    assert "Legacy pack tool" in loaded["body"]
    assert SEED_ONLY not in loaded["body"]

    install_platform_agent_packs(user_data, registry, tools)
    again = live.read_text(encoding="utf-8")
    assert again == updated
    assert again.count(LEGACY_LOADER_WARNING_MARKER) == 1
    _assert_prompt(registry, store, prompt)
    assert unrelated.read_text(encoding="utf-8") == UNRELATED_SKILL


def test_oc426_operator_edit_with_marker_or_heading_is_left_alone(operator_client):
    """REQ-426-002. Marker or warning heading means the file is not rewritten."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    user_data = wiki.parent
    live = user_data / "packs" / "developer" / "skills" / NATIVE_SKILL / "SKILL.md"
    unrelated = user_data / "packs" / "developer" / "skills" / "operator-notes" / "SKILL.md"
    seed_text = SEED.read_text(encoding="utf-8")
    prompt = f"{PROMPT_MARK}\n{registry.get_agent('developer').system_prompt}"
    _mark_developer(registry, store, prompt)

    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text(UNRELATED_SKILL, encoding="utf-8")
    live.write_text(EDITED_WITH_MARKER, encoding="utf-8")
    others = _skill_bodies(live.parent.parent)

    install_platform_agent_packs(user_data, registry, tools)

    assert live.read_text(encoding="utf-8") == EDITED_WITH_MARKER
    assert live.read_text(encoding="utf-8") != seed_text
    assert SEED_ONLY not in live.read_text(encoding="utf-8")
    assert OPERATOR_EDIT in live.read_text(encoding="utf-8")
    assert LEGACY_LOADER_WARNING_HEADING not in live.read_text(encoding="utf-8")
    _assert_prompt(registry, store, prompt)
    after = _skill_bodies(live.parent.parent)
    for skill_id, body in others.items():
        assert after[skill_id] == body

    pack_read = client.get(f"/api/skills/user-packs/{NATIVE_SKILL}")
    assert pack_read.status_code == 200, pack_read.text
    assert OPERATOR_EDIT in pack_read.json()["markdown"]
    assert SEED_ONLY not in pack_read.json()["markdown"]

    live.write_text(HEADING_WITHOUT_MARKER, encoding="utf-8")
    install_platform_agent_packs(user_data, registry, tools)
    heading_text = live.read_text(encoding="utf-8")
    assert heading_text == HEADING_WITHOUT_MARKER
    assert heading_text != seed_text
    assert OPERATOR_EDIT in heading_text
    assert heading_text.count(LEGACY_LOADER_WARNING_HEADING) == 1
    assert LEGACY_LOADER_WARNING_MARKER not in heading_text
    assert SEED_ONLY not in heading_text
    _assert_prompt(registry, store, prompt)
    assert unrelated.read_text(encoding="utf-8") == UNRELATED_SKILL
