"""CARD-570: runtime-built tools need Jacob's enable + approved code hash; agents cannot grant tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.agent_skills.tool_attachment import ATTACH_TOOL_PROPOSAL, make_skill_write_guard
from src.application.kernel.tool_registry import _tool_context
from src.infrastructure.content import store as content_store
from src.infrastructure.content.runtime_tools import RuntimeToolFiles
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

ROOT = Path(__file__).resolve().parents[3]
CODE = "def run(**kw):\n    return 1\n"


def test_runtime_tool_needs_enable_and_reapproval_after_code_change(tmp_path):
    files = RuntimeToolFiles(tmp_path / "tools")
    row = files.save({"name": "c570_tool", "code": CODE, "description": "d", "risk_level": "low"})
    assert row["approval"] == "disabled" and not files.mountable("c570_tool")
    assert files.enable("c570_tool")["approval"] == "enabled"
    assert files.mountable("c570_tool")
    # new code (from an agent or edited on disk) changes the hash: not mounted until re-approved
    (tmp_path / "tools" / "c570_tool" / "tool.py").write_text(CODE + "# changed\n", encoding="utf-8")
    assert files.read("c570_tool")["approval"] == "needs_reapproval"
    assert not files.mountable("c570_tool")
    files.save({"name": "c570_tool", "code": CODE + "# v3\n", "description": "d"})
    assert not files.mountable("c570_tool")
    files.enable("c570_tool")
    assert files.mountable("c570_tool")
    files.disable("c570_tool")
    assert files.read("c570_tool")["approval"] == "disabled"
    assert files.delete("c570_tool") and files.read("c570_tool") is None


def test_only_tools_studio_routes_flip_the_enable():
    """No agent tool can enable a runtime tool: only the Tools Studio routes call the enable methods."""
    allowed = {
        Path("src/application/tools/native_packaging.py"),
        Path("src/web/routers/native_tools.py"),
    }
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ("enable_by_operator" in text or "disable_by_operator" in text) and rel not in allowed:
            offenders.append(str(rel))
        if "runtime_tools import" in text and rel not in allowed | {Path("src/infrastructure/content/runtime_tools.py")}:
            offenders.append(str(rel))
    assert offenders == []


@pytest.fixture
def guarded(tmp_path):
    data = tmp_path / "data"
    (data / "skills").mkdir(parents=True)
    state = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    state.initialize_db()
    store = content_store.configure(data)
    content_store.set_skill_write_guard(make_skill_write_guard(state))
    yield store, state
    content_store.reset_store()


def _as_agent(agent_id="autoreiv"):
    return _tool_context.set({"agent_id": agent_id, "session_id": "s1"})


def test_agent_tool_addition_becomes_a_proposal(guarded):
    store, state = guarded
    store.skills.save("c570-mine", {"name": "Mine", "description": "d", "tools": ["wiki_note_read"]}, "# Mine\n", create=True)
    token = _as_agent()
    try:
        saved = store.skills.save(
            "c570-mine", {"name": "Mine", "description": "d2", "tools": ["wiki_note_read", "cli_exec"]}, "# Mine v2\n"
        )
    finally:
        _tool_context.reset(token)
    assert saved.tools == ["wiki_note_read"]  # prose saved, the added tool held back
    assert "Mine v2" in saved.body
    pending = [p for p in state.get_pending_approvals(agent_id="autoreiv") if p["tool_name"] == ATTACH_TOOL_PROPOSAL]
    assert [(p["arguments"]["tool"], p["arguments"]["skill_id"]) for p in pending] == [("cli_exec", "c570-mine")]


def test_agent_cannot_regrant_a_hidden_shipped_skill(guarded):
    store, state = guarded
    shipped = store.skills.shipped_ids()[0]
    loaded = store.skills.load(shipped)
    assert loaded is not None and loaded.tools
    store.skills.delete(shipped)  # hidden: grants nothing
    token = _as_agent()
    try:
        saved = store.skills.save(shipped, dict(loaded.meta), loaded.body)
    finally:
        _tool_context.reset(token)
    assert saved.tools == []
    assert state.get_pending_approvals(agent_id="autoreiv")


def test_jacob_studio_save_adds_tools_directly(guarded):
    store, state = guarded
    saved = store.skills.save("c570-jacob", {"name": "J", "description": "d", "tools": ["cli_exec"]}, "# J\n", create=True)
    assert saved.tools == ["cli_exec"]
    assert state.get_pending_approvals(agent_id="autoreiv") == []
