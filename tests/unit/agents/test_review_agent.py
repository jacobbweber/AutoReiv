"""
Builtin Review allowlist [REQ-SDLC-031, REQ-SDLC-035].
"""

from pathlib import Path

import pytest

from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.skills.card_tools import CardTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

CARD = """# [CARD-200] Review Target

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/review-target/`
> **Labels**: `type:feature`

---

Body.
"""


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_review_deny_writes_and_execute_code(store, tmp_path):
    from tests.unit.agent_packs.catalog import import_sdlc_packs

    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=TelemetryCollector(store=store),
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    import_sdlc_packs(tmp_path, agent_reg, tool_reg)
    review = agent_reg.get_agent("review")
    assert review is not None
    assert review.is_builtin is False
    assert "git_diff" in review.allowed_tool_names
    assert "git_status" in review.allowed_tool_names
    assert "write_project_file" not in review.allowed_tool_names
    assert "git_commit" not in review.allowed_tool_names
    for name, args in (
        ("execute_code", {"code": "print(1)"}),
        ("write_card", {"content": "x"}),
        ("write_spec", {"slug": "x", "filename": "requirements.md"}),
        ("write_project_file", {"path": "a.py", "content": "x"}),
        ("cli_exec", {"command": "dir"}),
        ("git_commit", {"message": "x"}),
    ):
        result = await tool_reg.execute(ToolCall(id=name, name=name, arguments=args), review)
        assert result.success is False
        assert "not authorized" in (result.error or "").lower()


def test_review_can_set_returned_and_done(tmp_path: Path):
    skill = CardTools(default_project_root=str(tmp_path))
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "review-target").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "review-target" / "requirements.md").write_text("# R\n", encoding="utf-8")
    skill.write_card(content=CARD, filename="CARD-200-review-target.md")
    returned = skill.set_card_status(card_id="CARD-200", status="Returned", return_reason="missing REQ-1 test")
    assert returned["success"] is True
    assert returned["status"] == "Returned"
    # reset to In Review via In Progress then In Review
    assert skill.set_card_status(card_id="CARD-200", status="In Progress")["success"] is True
    assert skill.set_card_status(card_id="CARD-200", status="In Review")["success"] is True
    done = skill.set_card_status(card_id="CARD-200", status="Done")
    assert done["success"] is True
    assert done["status"] == "Done"


def test_lookup_agents_lists_review(store, tmp_path):
    from tests.unit.agent_packs.catalog import import_sdlc_packs

    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=TelemetryCollector(store=store),
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    import_sdlc_packs(tmp_path, agent_reg, tool_reg)
    directory = AgentDirectoryService(agent_registry=agent_reg, state_store=store)
    cards = directory.search_agents("review qa tester", limit=5)
    assert "review" in [c.id for c in cards]
