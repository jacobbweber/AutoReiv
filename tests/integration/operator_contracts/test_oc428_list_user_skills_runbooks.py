"""CARD-428 / CARD-725 operator contract: list_user_skills names allowlisted platform runbooks.

REQ-428-001: an allowlisted skill whose live body is
platform/skills/<id>/SKILL.md, and which is absent from $DATA_DIR/skills/,
appears in list_user_skills for that agent as name and description (no body tokens).
REQ-428-002: that call does not copy the runbook into $DATA_DIR/skills/, and an
agent whose allowlist omits the id does not see it.

Temp user-data only [ADR-0055, ADR-0062].
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.application.kernel.agent_kernel import AgentKernel
from src.application.skills.user_catalog import LIST_USER_SKILLS, render_skill_index
from src.domain.gateway.models import ToolCall
from src.infrastructure.content.store import REPO_PLATFORM

PLATFORM_SKILL = "capability-authoring"
UNTICKED_SKILL = "study"
EXPECTED_NAME = "Capability Authoring"
BODY_TOKEN = "author_mcp_companion_skill"
WORKFLOW_HEADER = "## Workflow"


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
            ToolCall(id="oc428", name=LIST_USER_SKILLS, arguments={}),
            agent,
        )
    )


def test_oc428_list_user_skills_includes_allowlisted_pack_runbook_only(operator_client):
    """REQ-428-001 and REQ-428-002. Platform runbook is listed by name/description without copying to $DATA_DIR/skills/."""
    client, _store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    kernel = client.app.state.kernel
    assert isinstance(kernel, AgentKernel)
    user_data = wiki.parent
    shipped = REPO_PLATFORM / "skills" / PLATFORM_SKILL / "SKILL.md"
    operator_copy = user_data / "skills" / PLATFORM_SKILL
    assert shipped.is_file()
    assert not operator_copy.exists()

    autoreiv = registry.get_agent("autoreiv")
    assert autoreiv is not None
    assert PLATFORM_SKILL in (autoreiv.allowed_skill or [])
    assert UNTICKED_SKILL not in (autoreiv.allowed_skill or [])
    before_store = _files(user_data / "skills")
    before_shipped = shipped.read_text(encoding="utf-8")
    assert WORKFLOW_HEADER in before_shipped

    index = render_skill_index(
        autoreiv.allowed_skill,
        registry.user_skill_catalog,
        agent_id="autoreiv",
    )
    assert EXPECTED_NAME in index
    assert "Ask Developer" in index
    assert WORKFLOW_HEADER not in index

    opened = _listed(tools, autoreiv)
    assert opened.success is True, opened.error
    body = opened.output or {}
    packs = {row["id"]: row for row in body.get("skills") or []}
    assert PLATFORM_SKILL in packs, "REQ-428-001 FAIL: allowlisted platform runbook missing from list_user_skills"
    entry = packs[PLATFORM_SKILL]
    assert entry["name"] == EXPECTED_NAME
    assert "Ask Developer" in entry["description"]
    assert WORKFLOW_HEADER not in str(body)
    assert "instructions" not in entry
    assert UNTICKED_SKILL not in packs, "REQ-428-002 FAIL: unticked platform skill was listed"

    turn_tools = kernel._resolve_active_tools(
        autoreiv,
        user_content="Call list_user_skills and show the catalog.",
    )
    turn_names = [getattr(tool, "name", "") for tool in turn_tools]
    assert LIST_USER_SKILLS in turn_names, (
        "REQ-428-001 FAIL: autoreiv chat turn cannot call list_user_skills"
    )

    without = autoreiv.model_copy(
        update={
            "allowed_skill": [
                skill
                for skill in (autoreiv.allowed_skill or [])
                if skill not in (PLATFORM_SKILL, "user:*", "*")
            ],
        }
    )
    assert PLATFORM_SKILL not in (without.allowed_skill or [])
    assert without.allowed_skill
    hidden = _listed(tools, without)
    assert hidden.success is True, hidden.error
    hidden_ids = {row["id"] for row in (hidden.output or {}).get("skills") or []}
    assert PLATFORM_SKILL not in hidden_ids, "REQ-428-002 FAIL: skill id listed for an agent that does not allow it"

    assert not operator_copy.exists(), "REQ-428-002 FAIL: platform runbook was copied into $DATA_DIR/skills/"
    assert not (operator_copy / "SKILL.md").exists()
    assert _files(user_data / "skills") == before_store
    assert shipped.read_text(encoding="utf-8") == before_shipped
