"""CARD-564: Architect reviews In Review work; Done and Returned rules live in review_card / finish_review."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.kernel import tool_registry as tr
from src.application.sdlc.check_record import GreenCheckRecord
from src.application.skills.card_handoff_tools import CardHandoffTools, card_directive
from src.application.skills.card_review_tools import CardReviewTools
from src.application.skills.card_tools import EVIDENCE_AUTO_HEADER, CardTools
from src.application.skills.git_tools import GitTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.domain.orchestration.models import HandoffResult

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

PY = f'"{sys.executable}"'
AGENTS = f"# AGENTS.md\n\nBase branch: main\n\n## Checks\n- fast: {PY} -c \"print('ok')\"\n"
NOTES = "- divide(): met, raises on zero.\n- README: not met, add a line documenting the zero rule in README.md."
DONE = "- divide(): met, raises ValueError on zero (calc.py).\n- README: met, documents the zero rule."


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def _card(status: str, extra: str = "") -> str:
    return f"---\nid: CARD-2\ntitle: c2\nstatus: {status}\n{extra}---\n# CARD-2 c2\n\n## Evidence\n\n## Findings\n"


@pytest.fixture
def s(tmp_path: Path):
    root = tmp_path / "proj"
    (root / ".agents" / "cards").mkdir(parents=True)
    (root / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (root / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    (root / ".agents/cards/CARD-2-c2.md").write_text(_card("Ready"), encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "qa@example.invalid")
    _git(root, "config", "user.name", "QA")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: fixture")
    rec = GreenCheckRecord(tmp_path / "data" / "green-checks.json")
    cards = CardTools(root_resolver=lambda _=None: root, check_record=rec)
    dev = ProjectDevTools(root_resolver=lambda _=None: root, card_tools=cards, check_record=rec)
    git = GitTools(root_resolver=lambda _=None: root)
    review = CardReviewTools(root_resolver=lambda _=None: root, card_tools=cards, dev_tools=dev, check_record=rec)
    ns = SimpleNamespace(root=root, cards=cards, dev=dev, git=git, review=review, main=_git(root, "rev-parse", "main"))
    ns.as_dev = lambda: _as("developer")
    ns.as_arch = lambda: _as("architect")
    return ns


class _as:
    def __init__(self, agent: str):
        self.agent = agent

    def __enter__(self):
        self.token = tr._tool_context.set({"agent_id": self.agent, "session_id": "sess"})

    def __exit__(self, *exc):
        tr._tool_context.reset(self.token)


def _develop(s, text: str, branch: str = "card/2-c2") -> None:
    with s.as_dev():
        assert s.git.git_create_branch(branch)["success"]
        (s.root / "calc.py").write_text(text, encoding="utf-8")
        _git(s.root, "commit", "-q", "-am", "fix: divide")
        assert s.dev.run_project_checks("fast")["green_recorded"]
        res = s.cards.set_card_status("CARD-2", "In Review")
        assert res["success"], res


def _card_text(s) -> str:
    return (s.root / ".agents/cards/CARD-2-c2.md").read_text(encoding="utf-8")


def test_return_then_rework_then_done_never_merges(s):
    _develop(s, "def divide(a, b):\n    if b == 0:\n        raise ValueError\n    return a / b\n")
    with s.as_arch():
        early = s.review.finish_review("CARD-2", "Done", DONE)
        assert early.startswith("=== Verdict refused") and "review_card" in early  # no green check for this HEAD
        packet = s.review.review_card("CARD-2")
        assert packet.startswith("=== Review packet: CARD-2 (round 1 of 3")
        assert "raise ValueError" in packet and "fast (`" in packet and "green recorded" in packet
        assert s.review.finish_review("CARD-2", "Returned", "fix it").startswith("=== Verdict refused")
        out = s.review.finish_review("CARD-2", "Returned", NOTES)
    assert out.startswith("=== Review Returned: CARD-2 (round 1 of 3)"), out
    text = _card_text(s)
    assert "status: Returned" in text and "review_rounds: 1" in text
    assert "## Review\n\n### Round 1 - Returned" in text and "README: not met" in text
    assert text.index("## Review") < text.index("## Findings")
    assert _git(s.root, "log", "-1", "--format=%s") == "docs(card): CARD-2 Returned (round 1)"
    assert _git(s.root, "show", "--name-only", "--format=", "HEAD") == ".agents/cards/CARD-2-c2.md"

    # Developer reworks on the existing branch (from main too: git_create_branch switches to it), Returned -> In Review
    with s.as_dev():
        _git(s.root, "switch", "-q", "main")
        assert s.git.git_create_branch("card/2-c2")["switched"] is True
    (s.root / "README.md").write_text("divide() raises on zero\n", encoding="utf-8")
    _git(s.root, "add", "README.md")
    _develop(s, "def divide(a, b):\n    if b == 0:\n        raise ValueError('b is 0')\n    return a / b\n")
    text = _card_text(s)
    assert "status: In Review" in text and text.count(EVIDENCE_AUTO_HEADER) == 1  # the old round's block is replaced
    assert "### Round 1 - Returned" in text

    with s.as_arch():
        assert "round 2 of 3" in s.review.review_card("CARD-2")
        done = s.review.finish_review("CARD-2", "Done", DONE)
    assert done.startswith("=== Review Done: CARD-2 (round 2 of 3)") and "Nothing merged or pushed" in done
    text = _card_text(s)
    assert "status: Done" in text and "completed: " in text and "### Round 2 - Done" in text
    assert _git(s.root, "rev-parse", "main") == s.main  # no merge
    assert _git(s.root, "remote") == "" and _git(s.root, "status", "--porcelain") == ""


def test_last_round_cannot_return_and_goes_to_jacob(s):
    (s.root / ".agents/cards/CARD-2-c2.md").write_text(_card("Ready", "review_rounds: 2\nmax_review_rounds: 3\n"))
    _git(s.root, "commit", "-q", "-am", "chore: two rounds used")
    _develop(s, "def divide(a, b):\n    return a / b if b else 0\n")
    with s.as_arch():
        packet = s.review.review_card("CARD-2")
        assert "last review round (3 of 3)" in packet
        out = s.review.finish_review("CARD-2", "Returned", NOTES)
    assert out.startswith("=== Verdict refused") and "Bring the card to Jacob" in out
    assert "status: In Review" in _card_text(s)


def test_refusals_caller_branch_status_and_set_card_status(s):
    with s.as_arch():
        assert "not In Review" in s.review.review_card("CARD-2")  # Ready
    _develop(s, "def divide(a, b):\n    return a / b  # reviewed\n")
    with s.as_dev():
        assert "Only Architect" in s.review.review_card("CARD-2")
    with s.as_arch():
        refused = s.cards.set_card_status("CARD-2", "Done")
        assert refused["success"] is False and "finish_review" in refused["error"]
        (s.root / "calc.py").write_text("dirty\n", encoding="utf-8")
        assert "Uncommitted changes" in s.review.review_card("CARD-2")
        _git(s.root, "checkout", "--", "calc.py")
        _git(s.root, "switch", "-q", "main")
        assert "lives on its card branch" in s.review.review_card("CARD-2")  # on main the card still reads Ready
        assert s.review.finish_review("CARD-2", "Merged", DONE).startswith("=== Verdict refused")


class _Engine:
    def __init__(self):
        self.envelopes = []
        self.parent_tool_outcomes = {}
        self.agent_registry = SimpleNamespace(get_agent=lambda aid: SimpleNamespace(id=aid))

    async def execute_handoff(self, envelope):
        self.envelopes.append(envelope)
        return HandoffResult(correlation_id=envelope.correlation_id, sender_agent_id="architect",
                             recipient_agent_id="developer", status="completed", summary="ok", turns_used=1)


def test_hand_off_card_takes_a_returned_card_back_with_the_review_directive(s):
    (s.root / ".agents/cards/CARD-2-c2.md").write_text(_card("Returned", "review_rounds: 1\n"))
    engine = _Engine()
    tool = CardHandoffTools(root_resolver=lambda _=None: s.root, card_tools=s.cards, handoff_engine=engine)
    with s.as_arch():
        asyncio.run(tool.hand_off_card("CARD-2"))
        env = engine.envelopes[0]
        assert env.packet.goal == card_directive("CARD-2", returned=True) and "## Review" in env.packet.goal
        assert env.context_payload["child_session_title"] == "CARD-2: rework after review"
        (s.root / ".agents/cards/CARD-2-c2.md").write_text(_card("Returned", "review_rounds: 3\n"))
        refused, _, _ = tool.refusal("CARD-2", "architect")
        assert "Bring it to Jacob" in refused
