"""CARD-428 operator contract: list_user_skill_packs names allowlisted pack runbooks.

REQ-428-001: an allowlisted skill whose live body is
packs/<agent>/skills/<id>/SKILL.md, and which is absent from $DATA_DIR/skills/,
appears in list_user_skill_packs for that agent as name and description only.
REQ-428-002: that call does not copy the runbook into $DATA_DIR/skills/, and an
agent whose allowlist omits the id does not see it.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.application.kernel.agent_kernel import AgentKernel
from src.application.skills.user_catalog import LIST_USER_SKILL_PACKS, render_skill_index
from src.domain.gateway.models import ToolCall

NATIVE_SKILL = "native-tool-engineering"
UNTICKED_SKILL = "operator-notes"
NAME = "Native AutoReiv Tool Engineering"
DESCRIPTION = "CARD-428 pack runbook blurb for the list tool."
BODY_TOKEN = "BODY TOKEN CARD-428 must stay out of the list."

PACK_SKILL = f"""---
name: {NAME}
description: {DESCRIPTION}
---

# Native AutoReiv Tool Engineering

{BODY_TOKEN}
"""

UNTICKED_BODY = """---
name: Operator Notes
description: Unticked pack skill that must stay off the list.
---

# Operator Notes

UNTICKED BODY CARD-428
"""


def _files(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            found[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return found


def _listed(tools, agent):
    return asyncio.run(
        tools.execute(
            ToolCall(id="oc428", name=LIST_USER_SKILL_PACKS, arguments={}),
            agent,
        )
    )


def test_oc428_list_user_skill_packs_includes_allowlisted_pack_runbook_only(operator_client):
    """REQ-428-001 and REQ-428-002. Pack runbook is listed by name. No operator-store copy."""
    client, _store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    kernel = client.app.state.kernel
    assert isinstance(kernel, AgentKernel)
    user_data = wiki.parent
    live = user_data / "packs" / "developer" / "skills" / NATIVE_SKILL / "SKILL.md"
    unticked = user_data / "packs" / "developer" / "skills" / UNTICKED_SKILL / "SKILL.md"
    operator_copy = user_data / "skills" / NATIVE_SKILL
    assert live.is_file()
    assert not operator_copy.exists()

    developer = registry.get_agent("developer")
    assert developer is not None
    assert NATIVE_SKILL in (developer.allowed_skill or [])
    live.write_text(PACK_SKILL, encoding="utf-8")
    unticked.parent.mkdir(parents=True, exist_ok=True)
    unticked.write_text(UNTICKED_BODY, encoding="utf-8")
    before_store = _files(user_data / "skills")
    before_live = live.read_text(encoding="utf-8")

    index = render_skill_index(
        developer.allowed_skill,
        registry.user_skill_catalog,
        agent_id="developer",
    )
    assert NAME in index
    assert DESCRIPTION in index
    assert BODY_TOKEN not in index

    opened = _listed(tools, developer)
    assert opened.success is True, opened.error
    body = opened.output or {}
    packs = {row["id"]: row for row in body.get("packs") or []}
    assert NATIVE_SKILL in packs, "REQ-428-001 FAIL: allowlisted pack runbook missing from list_user_skill_packs"
    entry = packs[NATIVE_SKILL]
    assert entry["name"] == NAME
    assert entry["description"] == DESCRIPTION
    assert set(entry) == {"id", "name", "description"}
    assert BODY_TOKEN not in str(body)
    assert "instructions" not in entry
    assert UNTICKED_SKILL not in packs, "REQ-428-002 FAIL: unticked pack skill was listed"

    turn_tools = kernel._resolve_active_tools(
        developer,
        user_content="Call list_user_skill_packs and show the catalog.",
    )
    turn_names = [getattr(tool, "name", "") for tool in turn_tools]
    assert LIST_USER_SKILL_PACKS in turn_names, (
        "REQ-428-001 FAIL: developer chat turn cannot call list_user_skill_packs"
    )

    without = developer.model_copy(
        update={
            "allowed_skill": [skill for skill in (developer.allowed_skill or []) if skill != NATIVE_SKILL],
        }
    )
    assert NATIVE_SKILL not in (without.allowed_skill or [])
    assert without.allowed_skill
    hidden = _listed(tools, without)
    assert hidden.success is True, hidden.error
    hidden_ids = {row["id"] for row in (hidden.output or {}).get("packs") or []}
    assert NATIVE_SKILL not in hidden_ids, "REQ-428-002 FAIL: skill id listed for an agent that does not allow it"

    assert not operator_copy.exists(), "REQ-428-002 FAIL: pack runbook was copied into $DATA_DIR/skills/"
    assert not (operator_copy / "SKILL.md").exists()
    assert _files(user_data / "skills") == before_store
    assert live.read_text(encoding="utf-8") == before_live
    assert unticked.read_text(encoding="utf-8") == UNTICKED_BODY
