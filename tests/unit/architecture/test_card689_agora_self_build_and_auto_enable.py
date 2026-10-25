"""CARD-689 / ADR-0065 Guard Test: Inline Agora skill folder authoring & risk-tiered tool auto-enable.

Invariants enforced:
1. `save_skill_file` writes `SKILL.md`, `references/<name>.md`, and `tools/<name>.py` only into
   `<data>/skills/<skill_id>/` (never `platform/skills/`) and rejects path traversal (`..`).
2. Saving `tools/<name>.py` runs `ToolCheckService.check_native` first:
   - Broken code (syntax error, missing `def run`, failed sample call, or path traversal) is refused
     (`saved=False`) and nothing is written to disk.
   - Pure `read_only` code (`check.status == "passed"`, `check.access == []`, `risk == "read_only"`)
     is auto-enabled (`auto_enabled=True`, `enabled=True`, `approval="enabled"`), mounted into
     `ScopedToolRegistry`, and activated for the current session.
   - Code with outside access (`network`, `files`, `programs`, `hidden_imports`) or non-`read_only`
     risk (`write`, `network`, `destructive`) is saved disabled (`auto_enabled=False`,
     `enabled=False`, `approval="disabled"`), not mounted, and surfaces `access_warning`.
3. Overwriting an enabled tool with outside-access code immediately disables and unmounts it.
4. Both `PUT /api/capabilities/skills/{skill_id}/file` and `write_skill_file` delegate to `save_skill_file`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.skills.agora_authoring import save_skill_file
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    get_session_activated_skills,
)
from src.infrastructure.content import store as content_store

pytestmark = pytest.mark.guard


@pytest.fixture(autouse=True)
def _clean_store(tmp_path: Path):
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    yield data_dir
    clear_session_skill_activations()
    content_store.reset_store()


async def test_pure_read_only_tool_auto_enables_and_mounts(_clean_store: Path):
    st = content_store.get_store()
    reg = ScopedToolRegistry()
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": "sess-689"})
    try:
        md_res = await save_skill_file(
            st,
            "unit-conversions",
            "SKILL.md",
            "---\nname: Unit Conversions\ndescription: Convert temperature and weight units.\n---\n# Unit Conversions\n",
            tool_registry=reg,
        )
        assert md_res["success"] is True
        assert md_res["saved"] is True

        ref_res = await save_skill_file(
            st,
            "unit-conversions",
            "references/formulas.md",
            "# Formulas\nKelvin = Celsius + 273\n",
            tool_registry=reg,
        )
        assert ref_res["success"] is True
        assert (_clean_store / "skills" / "unit-conversions" / "references" / "formulas.md").is_file()

        pure_code = (
            '"""Convert Celsius to Kelvin."""\n\n'
            'RISK = "read_only"\n\n'
            "def run(celsius: int = 25) -> dict:\n"
            '    return {"kelvin": int(celsius) + 273}\n'
        )
        tool_res = await save_skill_file(
            st,
            "unit-conversions",
            "tools/celsius_to_kelvin.py",
            pure_code,
            tool_registry=reg,
        )
    finally:
        _tool_context.reset(token)

    assert tool_res["success"] is True
    assert tool_res["saved"] is True
    assert tool_res["auto_enabled"] is True
    assert tool_res["enabled"] is True
    assert tool_res["approval"] == "enabled"
    assert tool_res["mounted"] is True
    assert "celsius_to_kelvin" in reg
    assert "unit-conversions" in get_session_activated_skills(session_id="sess-689")


async def test_outside_access_or_write_tool_saves_disabled_and_unmounted(_clean_store: Path):
    st = content_store.get_store()
    reg = ScopedToolRegistry()

    # 1. Pure tool first -> auto-enabled and mounted
    pure_code = (
        '"""Pure helper."""\n'
        'RISK = "read_only"\n'
        "def run(x: int = 1) -> dict:\n"
        '    return {"val": x + 1}\n'
    )
    first = await save_skill_file(
        st,
        "net-skill",
        "tools/fetch_status.py",
        pure_code,
        tool_registry=reg,
    )
    assert first["auto_enabled"] is True
    assert "fetch_status" in reg

    # 2. Overwrite with network access -> must save disabled and unmount immediately
    net_code = (
        '"""Fetch remote status."""\n'
        "import urllib.request\n\n"
        "def run(url: str = 'https://example.com') -> dict:\n"
        '    return {"url": url}\n'
    )
    second = await save_skill_file(
        st,
        "net-skill",
        "tools/fetch_status.py",
        net_code,
        tool_registry=reg,
    )
    assert second["success"] is True
    assert second["saved"] is True
    assert second["auto_enabled"] is False
    assert second["enabled"] is False
    assert second["approval"] == "disabled"
    assert second["mounted"] is False
    assert "network" in second["access"]
    assert "the network" in second["access_warning"]
    assert "fetch_status" not in reg


async def test_broken_or_unsafe_tool_is_refused_and_not_written(_clean_store: Path):
    st = content_store.get_store()
    reg = ScopedToolRegistry()

    broken_code = '"""Broken tool."""\ndef run(x: int = 1) -> dict:\n    raise ValueError("boom")\n'
    res = await save_skill_file(
        st,
        "broken-skill",
        "tools/always_fails.py",
        broken_code,
        tool_registry=reg,
    )
    assert res["success"] is False
    assert res["saved"] is False
    assert not (_clean_store / "skills" / "broken-skill" / "tools" / "always_fails.py").exists()
    assert "always_fails" not in reg

    with pytest.raises(ValueError, match="Path traversal"):
        await save_skill_file(st, "broken-skill", "../escape.md", "bad")


async def test_card743_rejects_untyped_kwargs_and_hallucinated_imports(_clean_store: Path):
    st = content_store.get_store()
    reg = ScopedToolRegistry()

    # 1. Bare def run(**kwargs) with no explicit typed parameters must be rejected
    untyped_kwargs_code = (
        '"""Delete a note."""\n'
        "from pathlib import Path\n\n"
        "def run(**kwargs) -> dict:\n"
        '    return {"deleted": True}\n'
    )
    res_kwargs = await save_skill_file(
        st,
        "wiki-note-delete",
        "tools/delete_note.py",
        untyped_kwargs_code,
        tool_registry=reg,
    )
    assert res_kwargs["success"] is False
    assert res_kwargs["saved"] is False
    assert "explicit typed parameters" in (res_kwargs.get("message") or "")
    assert not (_clean_store / "skills" / "wiki-note-delete" / "tools" / "delete_note.py").exists()

    # 2. Hallucinated platform/MCP imports (`from functions import ...` or `from mcp_* import ...`) must fail static check
    hallucinated_import_code = (
        '"""Delete a note."""\n'
        "from pathlib import Path\n"
        "from functions import wiki_note_update\n\n"
        "def run(note_path: str = '01_Notes/test.md') -> dict:\n"
        '    return {"deleted": Path(note_path).name}\n'
    )
    res_import = await save_skill_file(
        st,
        "wiki-note-delete",
        "tools/delete_note.py",
        hallucinated_import_code,
        tool_registry=reg,
    )
    assert res_import["success"] is False
    assert res_import["saved"] is False
    assert "No module named 'functions'" in (res_import.get("message") or "")
    assert not (_clean_store / "skills" / "wiki-note-delete" / "tools" / "delete_note.py").exists()


def test_card743_capability_authoring_and_mcp_engineering_mount_on_demand(_clean_store: Path):
    from src.application.agent_skills.allowed_tools import ON_DEMAND_SHIPPED_SKILLS, pinned_skills
    from src.infrastructure.agents.agent_files import profile_from_file

    st = content_store.get_store()
    autoreiv_file = st.agents.load("autoreiv")
    assert autoreiv_file is not None
    profile = profile_from_file(autoreiv_file)

    for skill_id in ("capability-authoring", "mcp-engineering"):
        assert skill_id in ON_DEMAND_SHIPPED_SKILLS
        assert skill_id in profile.allowed_skill
        assert skill_id not in pinned_skills(profile)

