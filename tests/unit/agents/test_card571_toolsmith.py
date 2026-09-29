"""CARD-571: Toolsmith builds runtime tools; Jacob enables them (one step with the attach proposal)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.application.agent_skills import tool_attachment
from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.tool_attachment import ATTACH_TOOL_PROPOSAL, propose_tool_attachment
from src.application.tools.tool_check import access_warning, detect_access
from src.infrastructure.content import store as content_store
from src.infrastructure.content.runtime_tools import RuntimeToolFiles
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import hitl  # imported before the fixture configures the content store
from tests.unit.agent_skills.catalog import platform_pack_profile

ROOT = Path(__file__).resolve().parents[3]
CODE = "def run(**kw):\n    return 1\n"
TOOLSMITH_TOOLS = {"register_native_tool", "view_native_tool", "plan_native_folder", "list_available_skills_and_tools"}
FORBIDDEN = {
    "cli_exec", "execute_code", "shell_exec", "run_shell", "run_command", "python_exec", "commit_skill",
    "propose_skill", "propose_tool", "write_file", "patch_project_file", "write_project_file", "git_commit",
}


def test_toolsmith_has_only_the_tool_building_tools():
    from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS

    names = set(resolve_allowed_tools(platform_pack_profile("toolsmith")))
    # every agent with tools gets the platform set plus the read-only skill catalog
    assert names == TOOLSMITH_TOOLS | set(REQUIRED_PLATFORM_TOOLS) | {"skill_view", "list_user_skills"}, names
    assert not names & FORBIDDEN
    assert not {n for n in names if n.endswith("_exec") or "shell" in n or "enable" in n}


def test_no_agent_tool_can_enable_a_tool_or_skip_the_check():
    """Guard: enable/accept run only from the Tools Studio route; saving a runtime tool only after the check."""
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "accept_attach_proposals(" in text and rel not in {
            "src/application/agent_skills/tool_attachment.py", "src/web/routers/native_tools.py"
        }:
            offenders.append(rel)
        if "runtime_tool_files()" in text and rel not in {
            "src/application/tools/native_packaging.py", "src/application/agent_skills/tool_attachment.py"
        }:
            offenders.append(rel)
    assert offenders == []
    pkg = (ROOT / "src/application/tools/native_packaging.py").read_text(encoding="utf-8")
    register = pkg[pkg.index("    async def register(") : pkg.index("    def view(")]
    assert pkg.count("files.save(") == 1 and "files.save(" in register
    assert register.index("check_native(") < register.index("if not check.ok") < register.index("files.save(")
    assert pkg.count("runtime_tool_files().enable(") == 1
    enable = pkg[pkg.index("    def enable_by_operator(") : pkg.index("    def disable_by_operator(")]
    assert "runtime_tool_files().enable(" in enable
    # tool_attachment only reads approval state
    att = (ROOT / "src/application/agent_skills/tool_attachment.py").read_text(encoding="utf-8")
    assert not re.search(r"files\.(enable|save|disable)\(", att)


def test_detect_access_names_network_files_and_programs():
    assert detect_access(CODE) == []
    assert detect_access("import urllib.request\ndef run(**k):\n    return 1\n") == ["network"]
    assert detect_access("def run(**k):\n    return open('x').read()\n") == ["files"]
    assert detect_access("import subprocess, os\ndef run(**k):\n    os.system('x')\n") == ["programs"]
    assert detect_access("import importlib\ndef run(**k):\n    importlib.import_module('x')\n") == ["hidden_imports"]
    text = access_warning(["network", "files"])
    assert "the network" in text and "does not block" in text
    assert access_warning([]) == ""


def test_ask_developer_talk_opens_a_toolsmith_chat_with_the_target_agent():
    from src.application.tools.developer_mediation import ToolsDeveloperMediationService

    made = {}
    toolsmith = SimpleNamespace(id="toolsmith", allowed_skill=["native-tool-engineering"])
    registry = SimpleNamespace(get_profile=lambda aid: toolsmith if aid == "toolsmith" else None)

    def create_session(**kw):
        made.update(kw)
        return SimpleNamespace(id="s-1", title=kw.get("title"))

    svc = ToolsDeveloperMediationService(store=SimpleNamespace(create_session=create_session), orchestrator=None, registry=registry)
    out = svc.open_chat("create", {"tool_name": "x_tool", "behavior": "does x", "target_agent_id": "tutor"})
    assert out["agent_id"] == "toolsmith" and made["agent_id"] == "toolsmith"
    assert 'target_agent_id "tutor"' in out["prompt"]
    assert "not blocked" in out["prompt"]


@pytest.fixture
def data(tmp_path):
    root = tmp_path / "data"
    (root / "skills").mkdir(parents=True)
    content_store.configure(root)
    state = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    state.initialize_db()
    yield root, state
    content_store.reset_store()


def test_attach_is_refused_until_the_runtime_tool_is_enabled(data):
    root, state = data
    files = RuntimeToolFiles(root / "tools")
    files.save({"name": "c571_tool", "code": CODE, "description": "d", "risk_level": "low"})
    assert "not enabled" in (tool_attachment.runtime_tool_not_enabled("c571_tool") or "")
    assert tool_attachment.runtime_tool_not_enabled("wiki_note_read") is None  # built-in tools are not gated
    with pytest.raises(ValueError, match="not enabled"):
        tool_attachment.apply_tool_attachment(state, None, None, {"tool": "c571_tool", "agent_id": "tutor", "skill_id": "x"}, data_root=root)

    pid = propose_tool_attachment(state, tool="c571_tool", agent_id="tutor")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=state)))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(hitl.resolve_approval_endpoint(request, pid, hitl.DecisionRequest(decision="APPROVED")))
    assert exc.value.status_code == 409 and "Tools Studio" in exc.value.detail
    assert state.get_approval(pid)["status"] == "pending"  # still waiting for the enable
    files.enable("c571_tool")
    assert tool_attachment.runtime_tool_not_enabled("c571_tool") is None


def test_enabling_accepts_the_pending_attach_in_one_step(data, monkeypatch):
    root, state = data
    pid = propose_tool_attachment(state, tool="c571_tool", agent_id="tutor", skill_id="tutor-extra")
    other = propose_tool_attachment(state, tool="other_tool", agent_id="tutor")
    applied = []
    monkeypatch.setattr(tool_attachment, "apply_tool_attachment", lambda s, a, t, args, data_root: applied.append(dict(args)) or {"tool": args["tool"], "agent_id": args["agent_id"]})
    listed = tool_attachment.pending_attach_proposals(state, "c571_tool")
    assert [(p["agent_id"], p["skill_id"]) for p in listed] == [("tutor", "tutor-extra")]
    done = tool_attachment.accept_attach_proposals(state, None, None, "c571_tool", data_root=root)
    assert [d["approval_id"] for d in done] == [pid]
    assert applied[0]["skill_id"] == "tutor-extra"
    assert state.get_approval(pid)["status"] == "approved"
    assert state.get_approval(other)["status"] == "pending"
    assert all(p["tool_name"] == ATTACH_TOOL_PROPOSAL for p in state.get_pending_approvals())
