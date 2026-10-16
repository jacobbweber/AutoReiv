"""CARD-691 / ADR-0065 Guard Test: Hands-free Agora skill authoring and `user:*` auto-discovery for AutoReiv.

Invariants enforced:
1. `platform/agents/autoreiv.md` includes `user:*` in its `skills:` list while keeping specialist
   shipped skills (`coding`, `socratic-tutoring`, `coordination`) unticked.
2. `AUTO_USER_SKILL_WILDCARD = "user:*"` in `allowed_tools.py` automatically expands to all
   non-hidden user skill folders in `<data>/skills/<id>/` without expanding to unticked shipped
   skills in `platform/skills/`.
3. An agent with `user:*` keeps its base turn toolset lean (pinned shipped skills + base platform
   tools + `skill_view` + `list_user_skills`), includes user skills in `render_skill_index`, and
   mounts a user skill's tools on demand as soon as `skill_view("<skill_id>")` or
   `write_skill_file(skill_id="<skill_id>", ...)` runs in the session.
4. `platform/skills/agent-authoring/SKILL.md` binds `write_skill_file`, `read_skill_file`, and
   `list_available_skills_and_tools` so `AutoReiv` can author Agora skill folders inline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import (
    AUTO_USER_SKILL_WILDCARD,
    has_auto_skill_wildcard,
    pinned_skills,
    resolve_allowed_tools,
    ticked_skills,
)
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agora_loader import enable_skill_tool, mount_all_enabled_skill_tools
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    render_skill_index,
)
from src.application.skills.user_catalog import LIST_USER_SKILLS, SKILL_VIEW, UserSkillCatalog
from src.infrastructure.content import store as content_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile

pytestmark = pytest.mark.guard


@pytest.fixture(autouse=True)
def _clean_state(tmp_path: Path):
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    yield data_dir
    clear_session_skill_activations()
    content_store.reset_store()


def _write_user_agora_skill(data_root: Path, skill_id: str, tool_name: str, desc: str = "User skill.") -> None:
    sdir = data_root / "skills" / skill_id
    (sdir / "tools").mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nname: {skill_id.title()}\ndescription: {desc}\n---\nUse `{tool_name}` when needed.\n",
        encoding="utf-8",
    )
    (sdir / "tools" / f"{tool_name}.py").write_text(
        f'"""Run {tool_name}."""\n\nRISK = "read_only"\n\ndef run(x: int = 2) -> dict:\n    return {{"val": x * 5}}\n',
        encoding="utf-8",
    )


def test_shipped_autoreiv_and_agent_authoring_have_handsfree_agora_config(_clean_state: Path):
    st = content_store.get_store()
    autoreiv_file = st.agents.load("autoreiv")
    assert autoreiv_file is not None
    assert AUTO_USER_SKILL_WILDCARD in autoreiv_file.skills
    assert "coding" not in autoreiv_file.skills
    assert "socratic-tutoring" not in autoreiv_file.skills
    assert "coordination" not in autoreiv_file.skills

    authoring_file = st.skills.load("agent-authoring")
    assert authoring_file is not None
    assert "write_skill_file" in authoring_file.tools
    assert "skill_view" in authoring_file.tools
    assert "list_available_skills_and_tools" in authoring_file.tools


def test_user_wildcard_discovers_user_skills_without_pulling_in_unticked_shipped_skills(_clean_state: Path):
    st = content_store.get_store()
    _write_user_agora_skill(_clean_state, "custom-converter", "convert_ounces", "Convert ounces to grams.")
    enable_skill_tool(st, "custom-converter", "convert_ounces")

    reg = ScopedToolRegistry()
    for name in (*REQUIRED_PLATFORM_TOOLS, SKILL_VIEW, LIST_USER_SKILLS):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}}, handler=lambda: {})
    mount_all_enabled_skill_tools(st, reg)

    autoreiv = platform_pack_profile("autoreiv")
    assert has_auto_skill_wildcard(autoreiv) is True
    assert AUTO_USER_SKILL_WILDCARD not in pinned_skills(autoreiv)
    assert "wiki-knowledge" in pinned_skills(autoreiv)

    ticks = ticked_skills(autoreiv)
    assert "custom-converter" in ticks
    assert "wiki-knowledge" in ticks
    # Specialist shipped skills remain unticked on AutoReiv
    assert "coding" not in ticks
    assert "socratic-tutoring" not in ticks
    assert "coordination" not in ticks

    allowed = resolve_allowed_tools(autoreiv)
    assert "convert_ounces" in allowed
    assert not [t for t in allowed.names if t.startswith("repo_file_")]


def test_autoreiv_mounts_user_wildcard_skill_tools_on_demand_after_skill_view(_clean_state: Path):
    st = content_store.get_store()
    _write_user_agora_skill(_clean_state, "custom-hash", "compute_tag_hash", "Compute tag hash.")
    enable_skill_tool(st, "custom-hash", "compute_tag_hash")

    reg = ScopedToolRegistry()
    for name in (*REQUIRED_PLATFORM_TOOLS, "wiki_note_read", "write_skill_file"):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}}, handler=lambda: {})
    catalog = UserSkillCatalog(skills_dir=_clean_state / "skills", tool_registry=reg)
    catalog.mount_at_bootstrap()
    mount_all_enabled_skill_tools(st, reg)

    state_store = SQLiteStateStore(db_path=":memory:")
    state_store.initialize_db()
    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=reg,
        state_store=state_store,
        telemetry=MagicMock(),
        user_skill_catalog=catalog,
    )

    autoreiv = platform_pack_profile("autoreiv")

    # 1. Progressive skill index includes the user-created skill automatically
    idx = render_skill_index(autoreiv.allowed_skill, catalog=catalog, agent_id=autoreiv.id)
    assert "custom-hash" in idx
    assert "coding" not in idx

    # 2. Before skill_view("custom-hash"), pinned tools are active, but compute_tag_hash is not mounted yet
    before = {t.name for t in kernel._resolve_active_tools(autoreiv, session_id="sess-auto-1", history=[])}
    assert "wiki_note_read" in before
    assert "write_skill_file" in before
    assert "compute_tag_hash" not in before

    # 3. Calling skill_view("custom-hash") under AutoReiv's tool context succeeds and mounts compute_tag_hash
    from src.application.kernel.tool_registry import _tool_context

    token = _tool_context.set(
        {
            "agent_id": autoreiv.id,
            "session_id": "sess-auto-1",
            "allowed_skill": list(autoreiv.allowed_skill),
        }
    )
    try:
        view_res = catalog.skill_view(skill_id="custom-hash")
    finally:
        _tool_context.reset(token)
    assert view_res.get("success") is True, f"skill_view failed for user:* skill: {view_res}"
    after = {t.name for t in kernel._resolve_active_tools(autoreiv, session_id="sess-auto-1", history=[])}
    assert "compute_tag_hash" in after
