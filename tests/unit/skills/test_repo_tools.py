"""CARD-262 repo checkout tools [REQ-REPO-001..002]."""

from __future__ import annotations

from pathlib import Path

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety import tool_policy_gate as tpg
from src.application.skills.repo_tools import RepoCheckoutTools, is_denied_path
from src.domain.gateway.models import ToolCall


class _DummyStore:
    pass


def _skill(tmp_path: Path) -> RepoCheckoutTools:
    (tmp_path / "AGENTS.md").write_text("# Cards\nWalk cards with Jacob.\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    return RepoCheckoutTools(default_checkout_root=str(tmp_path))


def test_list_and_read_under_checkout(tmp_path: Path):
    skill = _skill(tmp_path)
    listed = skill.repo_file_list(path=".")
    assert listed["success"] is True
    names = {e["name"] for e in listed["entries"]}
    assert "AGENTS.md" in names
    assert ".env" not in names
    read = skill.repo_file_read(path="AGENTS.md")
    assert read["success"] is True
    assert read["path"] == "AGENTS.md"
    assert "Cards" in read["content"]
    assert read["tool"] == "repo_file_read"


def test_jail_denies_dotdot(tmp_path: Path):
    skill = _skill(tmp_path)
    denied = skill.repo_file_read(path="../secret.txt")
    assert denied["success"] is False


def test_deny_env_and_db(tmp_path: Path):
    skill = _skill(tmp_path)
    env = skill.repo_file_read(path=".env")
    assert env["success"] is False
    assert "denied" in (env.get("error") or "").lower()
    assert is_denied_path("packs/assistant/memory.db")


def test_missing_file_honest(tmp_path: Path):
    skill = _skill(tmp_path)
    miss = skill.repo_file_read(path="TotallyFakeCheckoutFile-ZZZ.md")
    assert miss["success"] is False
    assert "not found" in (miss.get("error") or "").lower()


def test_register_hitl_safe_and_policy(tmp_path: Path):
    skill = _skill(tmp_path)
    reg = ScopedToolRegistry()
    skill.register_tools(reg)
    for name in ("repo_file_list", "repo_file_read"):
        assert name in reg
    engine = HITLApprovalEngine(store=_DummyStore())  # type: ignore[arg-type]
    assert not engine.requires_approval(
        ToolCall(id="1", name="repo_file_read", arguments={"path": "AGENTS.md"})
    )
    assert not engine.requires_approval(ToolCall(id="2", name="repo_file_list", arguments={}))
    assert "repo_file_read" in tpg._DEFAULT_SAFE
    assert "repo_file_list" in tpg._DEFAULT_SAFE
    assert "repo_file_read" not in tpg._DEFAULT_REQUIRE_CONFIRM
