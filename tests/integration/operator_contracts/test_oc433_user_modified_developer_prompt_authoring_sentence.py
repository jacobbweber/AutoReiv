"""CARD-433 operator contract: one authoring paragraph on a user_modified developer prompt.

REQ-433-001: a user_modified developer whose prompt does not mention scaffold_agent_pack
gains one authoring paragraph. The existing prompt text stays.
REQ-433-002: after that append is recorded, deleting the paragraph stays deleted.
REQ-433-003: a developer that is not user_modified keeps the seed prompt. This card
does not rewrite platform-packs/developer/pack.json.
REQ-433-004: save_agent_specification stays off the developer allowlist.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.settings.models import AgentCustomization
from src.infrastructure.skills.platform_packs import (
    USER_MODIFIED_ADDITIVE_SKILL_GRANTS,
    install_platform_agent_packs,
)

AUTHORING_PARAGRAPH = (
    "Developer can propose and commit skills, propose tools, and scaffold agent packs "
    "with the capability-authoring tools. `scaffold_agent_pack` writes the pack. "
    "Do not use `save_agent_specification`."
)
PROMPT_APPEND_SETTING = "platform_user_modified_prompt_appends"
PROMPT_GRANT_ID = "developer-authoring-sentence"

ROOT = Path(__file__).resolve().parents[3]
SEED_PACK = ROOT / "platform-packs" / "developer" / "pack.json"
PROMPT_MARK = "OPERATOR PROMPT CARD-433"
KEPT_TEXT = f"{PROMPT_MARK}\nKeep the garage-project notes in this prompt."


def _seed_prompt() -> str:
    return json.loads(SEED_PACK.read_text(encoding="utf-8"))["system_prompt"]


def _save_developer_prompt(store, developer, prompt: str) -> None:
    developer.system_prompt = prompt
    developer.user_modified = True
    store.save_custom_agent_profile(developer)
    store.mark_agent_user_modified("developer", modified=True)
    store.save_agent_override(
        AgentCustomization(
            agent_id="developer",
            system_prompt=prompt,
            allowed_tool_names=list(developer.allowed_tool_names or []),
            allowed_skill=list(developer.allowed_skill or []),
            pack_tool_names=list(developer.pack_tool_names or []),
            user_modified=True,
        )
    )


def _assert_save_agent_specification_absent(agent, tools) -> None:
    assert "save_agent_specification" not in (agent.allowed_tool_names or [])
    assert "save_agent_specification" not in (agent.pack_tool_names or [])
    assert "save_agent_specification" not in tools
    for names in USER_MODIFIED_ADDITIVE_SKILL_GRANTS["developer"].values():
        assert "save_agent_specification" not in names


def test_oc433_appends_authoring_paragraph_once_and_deletion_sticks(operator_client):
    """REQ-433-001 and REQ-433-002. Existing text stays. A deleted paragraph stays deleted."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    developer = registry.get_agent("developer")
    assert developer is not None
    assert "scaffold_agent_pack" not in KEPT_TEXT

    _save_developer_prompt(store, developer, KEPT_TEXT)
    install_platform_agent_packs(wiki.parent, registry, tools)

    after = registry.get_agent("developer")
    assert after is not None
    expected = f"{KEPT_TEXT}\n\n{AUTHORING_PARAGRAPH}"
    assert after.system_prompt == expected
    assert after.system_prompt.startswith(KEPT_TEXT)
    assert after.system_prompt.count(AUTHORING_PARAGRAPH) == 1
    assert "scaffold_agent_pack" in after.system_prompt
    assert "propose_skill" in (after.allowed_tool_names or [])
    assert "scaffold_agent_pack" in (after.allowed_tool_names or [])
    _assert_save_agent_specification_absent(after, tools)
    assert bool(after.user_modified) is True

    stored = store.get_agent_profile("developer")
    assert stored is not None
    assert stored.system_prompt == expected
    override = store.get_agent_override("developer")
    assert override is not None
    assert override.system_prompt == expected
    recorded = store.get_setting(PROMPT_APPEND_SETTING) or {}
    assert PROMPT_GRANT_ID in (recorded.get("developer") or [])

    install_platform_agent_packs(wiki.parent, registry, tools)
    again = registry.get_agent("developer")
    assert again is not None
    assert again.system_prompt == expected
    assert again.system_prompt.count(AUTHORING_PARAGRAPH) == 1

    _save_developer_prompt(store, again, KEPT_TEXT)
    install_platform_agent_packs(wiki.parent, registry, tools)
    final = registry.get_agent("developer")
    assert final is not None
    assert final.system_prompt == KEPT_TEXT, "REQ-433-002 FAIL: deleted authoring paragraph was appended again"
    assert AUTHORING_PARAGRAPH not in (final.system_prompt or "")
    assert "propose_skill" in (final.allowed_tool_names or [])
    assert "scaffold_agent_pack" in (final.allowed_tool_names or [])
    _assert_save_agent_specification_absent(final, tools)
    final_profile = store.get_agent_profile("developer")
    assert final_profile is not None
    assert final_profile.system_prompt == KEPT_TEXT


def test_oc433_existing_scaffold_mention_is_left_until_the_operator_removes_it(operator_client):
    """REQ-433-001 negative: an operator sentence that already names the tool is not duplicated."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    developer = registry.get_agent("developer")
    assert developer is not None
    own = f"{PROMPT_MARK}\nI already call scaffold_agent_pack for new packs."
    _save_developer_prompt(store, developer, own)

    install_platform_agent_packs(wiki.parent, registry, tools)
    after = registry.get_agent("developer")
    assert after is not None
    assert after.system_prompt == own
    assert after.system_prompt.count("scaffold_agent_pack") == 1
    recorded = store.get_setting(PROMPT_APPEND_SETTING) or {}
    assert PROMPT_GRANT_ID not in (recorded.get("developer") or [])

    removed = f"{PROMPT_MARK}\nI no longer name the pack writer."
    assert "scaffold_agent_pack" not in removed
    _save_developer_prompt(store, after, removed)
    install_platform_agent_packs(wiki.parent, registry, tools)
    final = registry.get_agent("developer")
    assert final is not None
    assert final.system_prompt == f"{removed}\n\n{AUTHORING_PARAGRAPH}"
    assert final.system_prompt.startswith(removed)


def test_oc433_non_user_modified_seed_prompt_and_pack_json_stay(operator_client):
    """REQ-433-003 and REQ-433-004. Seed path and repo pack.json are untouched."""
    client, store, wiki = operator_client
    seed_bytes = SEED_PACK.read_bytes()
    seed_prompt = _seed_prompt()
    assert "scaffold_agent_pack" in seed_prompt

    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    developer = registry.get_agent("developer")
    assert developer is not None
    assert bool(developer.user_modified) is False
    assert developer.system_prompt == seed_prompt
    _assert_save_agent_specification_absent(developer, tools)

    install_platform_agent_packs(wiki.parent, registry, tools)
    again = registry.get_agent("developer")
    assert again is not None
    assert bool(again.user_modified) is False
    assert again.system_prompt == seed_prompt
    recorded = store.get_setting(PROMPT_APPEND_SETTING) or {}
    assert "developer" not in recorded
    assert SEED_PACK.read_bytes() == seed_bytes
    _assert_save_agent_specification_absent(again, tools)
