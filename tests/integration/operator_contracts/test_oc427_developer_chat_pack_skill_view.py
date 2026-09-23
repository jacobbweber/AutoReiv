"""CARD-427 operator contract: developer chat opens a pack skill runbook.

REQ-427-001: an allowlisted native-tool-engineering whose live body is
packs/developer/skills/native-tool-engineering/SKILL.md is returned by the
developer chat skill open path, including the CARD-426 legacy-loader warning.
REQ-427-002: that open does not copy the runbook into $DATA_DIR/skills/ and
does not replace the developer prompt or unrelated skill bodies.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.application.kernel.agent_kernel import AgentKernel
from src.application.skills.user_catalog import SKILL_VIEW, render_skill_index
from src.domain.gateway.models import ToolCall
from src.domain.settings.models import AgentCustomization
from src.infrastructure.skills.platform_packs import (
    LEGACY_LOADER_WARNING_HEADING,
    LEGACY_LOADER_WARNING_MARKER,
    install_platform_agent_packs,
)

NATIVE_SKILL = "native-tool-engineering"
PROMPT_MARK = "OPERATOR PROMPT CARD-427"
OPERATOR_KEPT = "OPERATOR KEPT THIS SENTENCE CARD-427"
UNRELATED_MARK = "UNRELATED SKILL BODY CARD-427"

OLDER_SKILL = f"""---
name: Native AutoReiv Tool Engineering
description: Older runbook. No legacy-loader warning.
version: 0.9.0
---

# Native AutoReiv Tool Engineering

{OPERATOR_KEPT}

Use register_native_tool for a native custom tool. Do not replace this file.
"""

UNRELATED_SKILL = f"""---
name: Operator Notes
description: Unrelated skill body that must stay.
---

# Operator Notes

{UNRELATED_MARK}
"""


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


def _skill_bodies(skills_root: Path) -> dict[str, str]:
    bodies: dict[str, str] = {}
    if not skills_root.is_dir():
        return bodies
    for path in sorted(skills_root.glob("*/SKILL.md")):
        bodies[path.parent.name] = path.read_text(encoding="utf-8")
    return bodies


def test_oc427_developer_chat_opens_pack_skill_with_warning_and_does_not_copy(operator_client):
    """REQ-427-001 and REQ-427-002. Chat skill_view reads the pack file. No operator-store copy."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    kernel = client.app.state.kernel
    assert isinstance(kernel, AgentKernel)
    user_data = wiki.parent
    live = user_data / "packs" / "developer" / "skills" / NATIVE_SKILL / "SKILL.md"
    unrelated = user_data / "packs" / "developer" / "skills" / "operator-notes" / "SKILL.md"
    operator_copy = user_data / "skills" / NATIVE_SKILL
    assert live.is_file()
    assert not operator_copy.exists()

    developer = registry.get_agent("developer")
    assert developer is not None
    prompt = f"{PROMPT_MARK}\n{developer.system_prompt}"
    _mark_developer(registry, store, prompt)
    developer = registry.get_agent("developer")
    assert developer is not None
    assert NATIVE_SKILL in (developer.allowed_skill or [])
    tools_before = list(developer.allowed_tool_names or [])

    live.write_text(OLDER_SKILL, encoding="utf-8")
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text(UNRELATED_SKILL, encoding="utf-8")
    before_pack = _skill_bodies(live.parent.parent)
    before_store = _skill_bodies(user_data / "skills")

    install_platform_agent_packs(user_data, registry, tools)

    warned = live.read_text(encoding="utf-8")
    assert warned.startswith(OLDER_SKILL)
    assert OPERATOR_KEPT in warned
    assert LEGACY_LOADER_WARNING_MARKER in warned
    assert LEGACY_LOADER_WARNING_HEADING in warned
    assert "Legacy pack tool" in warned
    developer = registry.get_agent("developer")
    assert developer is not None
    assert developer.system_prompt == prompt
    assert store.get_agent_profile("developer").system_prompt == prompt

    index = render_skill_index(developer.allowed_skill, registry.user_skill_catalog)
    assert NATIVE_SKILL in index or "Native AutoReiv Tool Engineering" in index
    assert "Older runbook" in index
    assert LEGACY_LOADER_WARNING_MARKER not in index
    assert OPERATOR_KEPT not in index
    assert "Do not open a skill id that is not listed here." in index

    effective = kernel._build_effective_system_message(developer, "Open the native-tool-engineering runbook.")
    assert PROMPT_MARK in effective.content
    assert "Native AutoReiv Tool Engineering" in effective.content
    assert LEGACY_LOADER_WARNING_MARKER not in effective.content
    assert developer.system_prompt == prompt

    opened = asyncio.run(
        tools.execute(
            ToolCall(id="oc427", name=SKILL_VIEW, arguments={"pack_id": NATIVE_SKILL}),
            developer,
        )
    )
    assert opened.success is True, opened.error
    body = opened.output or {}
    assert body.get("success") is True, body
    assert Path(body["path"]).resolve() == live.resolve()
    assert OPERATOR_KEPT in (body.get("instructions") or "")
    assert LEGACY_LOADER_WARNING_MARKER in (body.get("instructions") or "")
    assert "Legacy pack tool" in (body.get("instructions") or "")
    assert "legacy in-process loader" in (body.get("instructions") or "")

    turn_tools = kernel._resolve_active_tools(
        developer,
        user_content="Open the native-tool-engineering skill and show the legacy pack loader warning.",
    )
    turn_names = [getattr(tool, "name", "") for tool in turn_tools]
    assert SKILL_VIEW in turn_names, (
        "REQ-427-001 FAIL: developer chat turn cannot call skill_view to open the pack runbook"
    )

    assert not operator_copy.exists(), "REQ-427-002 FAIL: pack runbook was copied into $DATA_DIR/skills/"
    assert not (operator_copy / "SKILL.md").exists()
    assert list(developer.allowed_tool_names or []) == tools_before
    assert developer.system_prompt == prompt
    assert store.get_agent_profile("developer").system_prompt == prompt
    override = store.get_agent_override("developer")
    assert override is not None
    assert override.system_prompt == prompt
    assert LEGACY_LOADER_WARNING_MARKER not in developer.system_prompt

    after_pack = _skill_bodies(live.parent.parent)
    assert set(after_pack) == set(before_pack)
    for skill_id, text in before_pack.items():
        if skill_id == NATIVE_SKILL:
            continue
        assert after_pack[skill_id] == text, f"REQ-427-002 FAIL: unrelated skill {skill_id} was rewritten"
    assert unrelated.read_text(encoding="utf-8") == UNRELATED_SKILL
    assert _skill_bodies(user_data / "skills") == before_store
