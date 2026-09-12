"""CARD-264 scoped repo write/patch under HITL [REQ-RWHITL-001..005].

Red→green TDD. Deny = tree unchanged. Rollback restores prior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety import tool_policy_gate as tpg
from src.application.skills.repo_tools import RepoCheckoutTools
from src.domain.gateway.models import ToolCall


class _DummyStore:
    pass


def _skill(tmp_path: Path) -> RepoCheckoutTools:
    (tmp_path / "AGENTS.md").write_text("# Cards\nWalk cards with Jacob.\n", encoding="utf-8")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "existing.txt").write_text("PRIOR\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    return RepoCheckoutTools(default_checkout_root=str(tmp_path))


def test_write_and_patch_registered_and_require_confirm(tmp_path: Path):
    skill = _skill(tmp_path)
    reg = ScopedToolRegistry()
    skill.register_tools(reg)
    for name in ("repo_file_write", "repo_file_patch", "repo_file_rollback"):
        assert name in reg
    for name in ("repo_file_write", "repo_file_patch"):
        assert name in tpg._DEFAULT_REQUIRE_CONFIRM
        assert name not in tpg._DEFAULT_SAFE
    engine = HITLApprovalEngine(store=_DummyStore())  # type: ignore[arg-type]
    assert engine.requires_approval(
        ToolCall(id="1", name="repo_file_write", arguments={"path": "notes/x.txt", "content": "a"})
    )
    assert engine.requires_approval(
        ToolCall(id="2", name="repo_file_patch", arguments={"path": "notes/existing.txt", "content": "b"})
    )
    # reads stay SAFE
    assert not engine.requires_approval(
        ToolCall(id="3", name="repo_file_read", arguments={"path": "AGENTS.md"})
    )


def test_write_applies_under_jail(tmp_path: Path):
    skill = _skill(tmp_path)
    out = skill.repo_file_write(path="notes/_card264_probe.txt", content="CARD264-APPROVE-PROBE\n")
    assert out["success"] is True
    assert out["tool"] == "repo_file_write"
    assert out["path"] == "notes/_card264_probe.txt"
    assert out.get("created") is True
    assert (tmp_path / "notes" / "_card264_probe.txt").read_text(encoding="utf-8") == (
        "CARD264-APPROVE-PROBE\n"
    )


def test_patch_overwrites_existing(tmp_path: Path):
    skill = _skill(tmp_path)
    out = skill.repo_file_patch(path="notes/existing.txt", content="PATCHED\n")
    assert out["success"] is True
    assert out["tool"] == "repo_file_patch"
    assert out.get("created") is False
    assert (tmp_path / "notes" / "existing.txt").read_text(encoding="utf-8") == "PATCHED\n"


def test_deny_semantics_tree_unchanged_without_execute(tmp_path: Path):
    """Policy/HITL Deny means executor never called — tree stays clean.

    Unit stand-in: do not call write; assert probe file absent (mirrors Deny).
    """
    skill = _skill(tmp_path)
    probe = tmp_path / "notes" / "_card264_deny_probe.txt"
    assert not probe.exists()

    class _Store:
        def get_setting(self, key):
            return None

    class _Agent:
        allowed_tool_names = ["repo_file_write", "repo_file_patch", "repo_file_rollback"]
        mcp_servers = []

    # Simulate gate parking: REQUIRE_CONFIRM decision without execute.
    gate = tpg.ToolPolicyGate(store=_Store())
    decision = gate.evaluate(
        ToolCall(
            id="deny",
            name="repo_file_write",
            arguments={"path": "notes/_card264_deny_probe.txt", "content": "nope"},
        ),
        _Agent(),
        matched_capability_ids=["tool.repo_file_write"],
        registry_tool_names={"repo_file_write", "repo_file_patch", "repo_file_rollback"},
    )
    assert decision.verdict == tpg.ToolPolicyVerdict.REQUIRE_CONFIRM
    assert not probe.exists()
    # existing tree untouched
    assert (tmp_path / "notes" / "existing.txt").read_text(encoding="utf-8") == "PRIOR\n"


def test_rollback_restores_prior_after_write(tmp_path: Path):
    skill = _skill(tmp_path)
    written = skill.repo_file_write(path="notes/existing.txt", content="NEW\n")
    assert written["success"] is True
    assert (tmp_path / "notes" / "existing.txt").read_text(encoding="utf-8") == "NEW\n"
    rolled = skill.repo_file_rollback(path="notes/existing.txt")
    assert rolled["success"] is True
    assert rolled["tool"] == "repo_file_rollback"
    assert (tmp_path / "notes" / "existing.txt").read_text(encoding="utf-8") == "PRIOR\n"


def test_rollback_deletes_created_file(tmp_path: Path):
    skill = _skill(tmp_path)
    skill.repo_file_write(path="notes/_card264_created.txt", content="TEMP\n")
    assert (tmp_path / "notes" / "_card264_created.txt").is_file()
    rolled = skill.repo_file_rollback(path="notes/_card264_created.txt")
    assert rolled["success"] is True
    assert rolled.get("deleted") is True
    assert not (tmp_path / "notes" / "_card264_created.txt").exists()


def test_write_jail_and_sensitive_deny(tmp_path: Path):
    skill = _skill(tmp_path)
    escape = skill.repo_file_write(path="../outside.txt", content="nope")
    assert escape["success"] is False
    env = skill.repo_file_write(path=".env", content="HACK=1\n")
    assert env["success"] is False
    assert "denied" in (env.get("error") or "").lower()


def test_policy_gate_defaults_include_repo_writes():
    assert "repo_file_write" in tpg._DEFAULT_REQUIRE_CONFIRM
    assert "repo_file_patch" in tpg._DEFAULT_REQUIRE_CONFIRM
    assert "repo_file_write" not in tpg._DEFAULT_SAFE
    assert "repo_file_read" in tpg._DEFAULT_SAFE
