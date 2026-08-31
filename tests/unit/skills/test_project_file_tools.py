"""
Project file tools jail [REQ-SDLC-021, REQ-SDLC-022].
"""

from pathlib import Path

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.skills.project_file_tools import ProjectFileTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def skill(tmp_path: Path) -> ProjectFileTools:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
    return ProjectFileTools(default_project_root=str(tmp_path))


def test_list_read_write_under_root(skill: ProjectFileTools, tmp_path: Path):
    listed = skill.list_project_dir(path="src")
    assert listed["success"] is True
    names = [e["name"] for e in listed["entries"]]
    assert "app.py" in names
    read = skill.read_project_file(path="src/app.py")
    assert read["success"] is True
    assert "print(1)" in read["content"]
    written = skill.write_project_file(path="src/new.py", content="x = 2\n")
    assert written["success"] is True
    assert (tmp_path / "src" / "new.py").read_text(encoding="utf-8") == "x = 2\n"


def test_jail_denies_dotdot_and_outside(skill: ProjectFileTools):
    denied = skill.read_project_file(path="../secret.txt")
    assert denied["success"] is False
    assert "escape" in denied["error"].lower()
    listed = skill.list_project_dir(path="../../")
    assert listed["success"] is False
    written = skill.write_project_file(path="../out.txt", content="nope")
    assert written["success"] is False


def test_bootstrap_registers_file_tools_and_hitl():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    _, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store))
    for name in ("list_project_dir", "read_project_file", "write_project_file"):
        assert tool_reg.get_tool_definition(name) is not None
    engine = HITLApprovalEngine(store=store)
    assert engine.requires_approval(ToolCall(id="1", name="write_project_file", arguments={}))
    assert not engine.requires_approval(ToolCall(id="2", name="read_project_file", arguments={}))
