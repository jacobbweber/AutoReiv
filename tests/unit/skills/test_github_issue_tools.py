"""
Card to GitHub issue sync [REQ-SDLC-040..042].
"""

import json
from pathlib import Path

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.skills.card_tools import CardTools
from src.application.skills.github_issue_tools import GitHubIssueTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.domain.sdlc.github_labels import github_label_map
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

CARD = """# [CARD-400] Issue Sync

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/issue-sync/`
> **Labels**: `type:feature`, `area:sdlc`

---

Body.
"""


def test_label_map():
    assert github_label_map("Discuss", "") == ["status:discuss"]
    assert github_label_map("Ready", "") == ["status:ready"]
    assert github_label_map("In Progress", "`type:feature`, `area:sdlc`") == [
        "status:in-progress",
        "type:feature",
    ]
    assert github_label_map("In Review", "type:fix") == ["status:in-review", "type:fix"]
    assert github_label_map("Returned", "type:docs") == ["status:returned", "type:docs"]
    assert github_label_map("Done", "type:chore") == ["status:done", "type:chore"]


def test_dry_run_and_mock_create(tmp_path: Path):
    cards = CardTools(default_project_root=str(tmp_path))
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "issue-sync").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "issue-sync" / "requirements.md").write_text("# R\n", encoding="utf-8")
    cards.write_card(content=CARD, filename="CARD-400-issue-sync.md")
    skill = GitHubIssueTools(default_project_root=str(tmp_path), card_tools=cards)
    dry = skill.sync_card_issue(card_id="CARD-400", dry_run=True)
    assert dry["success"] is True
    assert dry["dry_run"] is True
    assert "status:ready" in dry["labels"]
    assert "type:feature" in dry["labels"]

    def runner(args, cwd):
        assert args[0] == "issue"
        assert args[1] == "create"
        return {"success": True, "stdout": json.dumps({"number": 42, "url": "https://example/issues/42"})}

    skill = GitHubIssueTools(default_project_root=str(tmp_path), card_tools=cards, runner=runner)
    created = skill.sync_card_issue(card_id="CARD-400")
    assert created["success"] is True
    assert created["github_issue"] == "42"
    read = cards.read_card(card_id="CARD-400")
    assert read["github_issue"] == "42"


def test_missing_gh_error(tmp_path: Path, monkeypatch):
    cards = CardTools(default_project_root=str(tmp_path))
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    cards.write_card(content=CARD, filename="CARD-400-issue-sync.md")
    monkeypatch.setattr("src.application.skills.github_issue_tools.shutil.which", lambda _name: None)
    skill = GitHubIssueTools(default_project_root=str(tmp_path), card_tools=cards)
    result = skill.sync_card_issue(card_id="CARD-400")
    assert result["success"] is False
    assert "gh is not available" in result["error"]


def test_tool_registered_and_hitl():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    _, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store))
    assert tool_reg.get_tool_definition("sync_card_issue") is not None
    engine = HITLApprovalEngine(store=store)
    assert engine.requires_approval(ToolCall(id="1", name="sync_card_issue", arguments={"card_id": "CARD-400"}))
