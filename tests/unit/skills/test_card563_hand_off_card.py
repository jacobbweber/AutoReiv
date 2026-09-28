"""CARD-563: hand_off_card refuses in the tool, runs Developer through the handoff engine, and reports from git."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.kernel import tool_registry as tr
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.sdlc.check_record import GreenCheckRecord
from src.application.sdlc.paths import ProjectPathError
from src.application.skills.card_handoff_tools import CardHandoffTools, card_directive
from src.application.skills.card_tools import CardTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.orchestration.models import HandoffResult

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

PY = f'"{sys.executable}"'
AGENTS = f"# AGENTS.md\n\nBase branch: main\n\n## Checks\n- fast: {PY} -c \"print('ok')\"\n"


def _card(n: int, status: str) -> str:
    return f"---\nid: CARD-{n}\ntitle: c{n}\nstatus: {status}\n---\n# CARD-{n} c{n}\n\n## Evidence\n"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".agents" / "cards").mkdir(parents=True)
    (root / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (root / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    (root / ".agents/cards/CARD-1-c1.md").write_text(_card(1, "Done"), encoding="utf-8")
    (root / ".agents/cards/CARD-2-c2.md").write_text(_card(2, "Ready"), encoding="utf-8")
    (root / ".agents/cards/CARD-3-c3.md").write_text(_card(3, "Proposed"), encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "qa@example.invalid")
    _git(root, "config", "user.name", "QA")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: fixture")
    return root


class FakeDeveloperEngine:
    """Stands in for HandoffIsolationEngine: works the card like Developer would, through the real tools."""

    def __init__(self, repo: Path, cards: CardTools, dev: ProjectDevTools):
        self.repo, self.cards, self.dev = repo, cards, dev
        self.envelopes = []
        self.parent_tool_outcomes = {}
        self.agent_registry = SimpleNamespace(get_agent=lambda aid: SimpleNamespace(id=aid) if aid == "developer" else None)

    async def execute_handoff(self, envelope):
        self.envelopes.append(envelope)
        token = tr._tool_context.set({"agent_id": "developer"})
        try:
            _git(self.repo, "switch", "-q", "-c", "card/2-c2")
            (self.repo / "calc.py").write_text(
                "def divide(a, b):\n    if b == 0:\n        raise ValueError('b is 0')\n    return a / b\n", encoding="utf-8"
            )
            _git(self.repo, "commit", "-q", "-am", "fix: divide refuses zero")
            assert self.dev.run_project_checks("fast")["green_recorded"]
            assert self.cards.set_card_status("CARD-2", "In Review")["success"]
        finally:
            tr._tool_context.reset(token)
        return HandoffResult(
            correlation_id=envelope.correlation_id, sender_agent_id="architect", recipient_agent_id="developer",
            status="completed", summary="Done, CARD-2 is In Review.", turns_used=9,
        )


@pytest.fixture
def setup(repo: Path, tmp_path: Path):
    rec = GreenCheckRecord(tmp_path / "data" / "green-checks.json")
    cards = CardTools(root_resolver=lambda _=None: repo, check_record=rec)
    dev = ProjectDevTools(root_resolver=lambda _=None: repo, card_tools=cards, check_record=rec)
    engine = FakeDeveloperEngine(repo, cards, dev)
    tool = CardHandoffTools(root_resolver=lambda _=None: repo, card_tools=cards, handoff_engine=engine)
    token = tr._tool_context.set({"agent_id": "architect", "session_id": "sess-arch"})
    yield SimpleNamespace(repo=repo, cards=cards, engine=engine, tool=tool)
    tr._tool_context.reset(token)


def _run(coro):
    return asyncio.run(coro)


def test_success_runs_developer_with_fixed_directive_and_reports_from_git(setup):
    out = _run(setup.tool.hand_off_card("CARD-2"))
    env = setup.engine.envelopes[0]
    assert env.recipient_agent_id == "developer" and env.packet.goal == card_directive("CARD-2")
    assert env.packet.facts == ["card_id: CARD-2"] and env.context_payload["card_handoff"] == "CARD-2"
    assert env.max_turns == 40
    assert "Card status: In Review" in out
    assert "Branch: card/2-c2 (base main)" in out
    assert "fix: divide refuses zero" in out and "docs(card): CARD-2 In Review" in out
    assert "Working tree: clean" in out
    assert "Recorded by" not in out and "- Green run_project_checks" in out  # the tool-written Evidence lines
    assert "Developer conversation: sess-arch_child_" in out
    assert "Developer's own summary:" in out


@pytest.mark.parametrize(
    "card,expect",
    [("CARD-3", "is Proposed, not Ready"), ("CARD-1", "is Done, not Ready"), ("CARD-99", "is not a card in the active project")],
)
def test_refuses_cards_that_are_not_ready_or_not_here(setup, card, expect):
    out = _run(setup.tool.hand_off_card(card))
    assert out.startswith("=== Hand-off refused") and expect in out
    assert setup.engine.envelopes == []


def test_refuses_when_another_card_is_in_progress(setup):
    (setup.repo / ".agents/cards/CARD-4-c4.md").write_text(_card(4, "In Progress"), encoding="utf-8")
    out = _run(setup.tool.hand_off_card("CARD-2"))
    assert "CARD-4 is already In Progress" in out and setup.engine.envelopes == []


def test_refuses_callers_other_than_architect(setup):
    token = tr._tool_context.set({"agent_id": "developer"})
    try:
        out = _run(setup.tool.hand_off_card("CARD-2"))
    finally:
        tr._tool_context.reset(token)
    assert "Only Architect hands cards to Developer" in out and setup.engine.envelopes == []


def test_refuses_without_a_selected_project(setup):
    def no_project(_=None):
        raise ProjectPathError("No project is selected. Select one in Projects Studio.")

    tool = CardHandoffTools(root_resolver=no_project, card_tools=setup.cards, handoff_engine=setup.engine)
    out = _run(tool.hand_off_card("CARD-2"))
    assert "No project is selected" in out and setup.engine.envelopes == []


def test_refuses_when_developer_is_missing_or_disabled(setup):
    setup.engine.agent_registry = SimpleNamespace(get_agent=lambda aid: None)
    tool = CardHandoffTools(root_resolver=lambda _=None: setup.repo, card_tools=setup.cards, handoff_engine=setup.engine)
    assert "Developer is not available" in _run(tool.hand_off_card("CARD-2"))
    setup.engine.agent_registry = SimpleNamespace(get_agent=lambda aid: SimpleNamespace(id=aid, enabled=False))
    tool = CardHandoffTools(root_resolver=lambda _=None: setup.repo, card_tools=setup.cards, handoff_engine=setup.engine)
    assert "Developer is not available" in _run(tool.hand_off_card("CARD-2"))


def test_parked_developer_tool_surfaces_as_approval_with_the_developer_session(setup):
    async def parks(envelope):
        return HandoffResult(
            correlation_id=envelope.correlation_id, sender_agent_id="architect", recipient_agent_id="developer",
            status="approval_required", summary="Approve patch", approval_id="ap-1", parked_tool_name="patch_project_file",
        )

    setup.engine.execute_handoff = parks
    out = _run(setup.tool.hand_off_card("CARD-2"))
    assert out["status"] == "approval_required" and out["approval_id"] == "ap-1"
    assert out["tool_name"] == "patch_project_file" and out["developer_session_id"].startswith("sess-arch_child_")


class _Store:
    def __init__(self, parent_msgs):
        self.msgs = {"sess-arch": list(parent_msgs)}
        self.saved = []

    def get_messages(self, session_id):
        return self.msgs.get(session_id, [])

    def get_session(self, session_id):
        return SimpleNamespace(agent_id="developer")

    def save_message(self, session_id, agent_id, message):
        self.saved.append((session_id, message))


class _Kernel:
    def __init__(self, work):
        self.work = work

    async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
        self.work()
        yield SimpleNamespace(event_type="turn_end", content="All done.", is_finished=True)


def test_resumed_developer_run_writes_the_git_outcome_onto_the_hand_off_row(setup):
    """After Jacob approves Developer's last prompt, the parent's hand_off_card row gets the outcome read from git."""
    call = ToolCall(id="tc-9", name="hand_off_card", arguments={"card_id": "CARD-2"})
    store = _Store([ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[call])])
    registry = SimpleNamespace(get_agent=lambda aid: SimpleNamespace(id=aid), get_profile=lambda aid: None)

    def developer_finishes():
        _run_sync_fake(setup)

    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=_Kernel(developer_finishes))
    CardHandoffTools(root_resolver=lambda _=None: setup.repo, card_tools=setup.cards, handoff_engine=engine)
    res = _run(engine.resume_nested_child("sess-arch_child_abcd1234", parent_session_id="sess-arch", agent_id="developer"))
    assert res["status"] == "completed"
    sid, row = store.saved[-1]
    assert sid == "sess-arch" and row.name == "hand_off_card" and row.tool_call_id == "tc-9"
    assert "Card status: In Review" in row.content and "Developer conversation: sess-arch_child_abcd1234" in row.content


def _run_sync_fake(setup):
    asyncio.get_event_loop  # noqa: B018 - keep the fake synchronous
    token = tr._tool_context.set({"agent_id": "developer"})
    try:
        repo = setup.repo
        _git(repo, "switch", "-q", "-c", "card/2-c2")
        (repo / "calc.py").write_text("def divide(a, b):\n    return a / b if b else 0\n", encoding="utf-8")
        _git(repo, "commit", "-q", "-am", "fix: divide")
        assert setup.engine.dev.run_project_checks("fast")["green_recorded"]
        assert setup.cards.set_card_status("CARD-2", "In Review")["success"]
    finally:
        tr._tool_context.reset(token)
