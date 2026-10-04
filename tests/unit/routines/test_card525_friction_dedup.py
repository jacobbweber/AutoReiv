"""CARD-525: friction audit dedup is per (agent, tool, friction); decided cards block only for a cool-down."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit
from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.friction_dedup import (
    blocks_new_recommendation,
    friction_key,
    normalize_friction_rec,
    recommendation_status,
)
from src.domain.orchestration.models import ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    skill = d / "skills" / "wiki"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: wiki\ntools:\n  - wiki_note_read\n  - wiki_note_export\n---\n# Wiki\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStateStore:
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


def _bloat(store, *tools: str, agent: str = "autoreiv") -> None:
    sess = store.create_session(agent_id=agent, title="C525")
    for i, tool in enumerate(tools):
        store.save_message(
            session_id=sess.id,
            agent_id=agent,
            message=ChatMessage(role=Role.TOOL, content="x" * 20000, name=tool, tool_call_id=f"c{i}"),
        )


def _tools(result) -> list[str]:
    return sorted(r["tool_name"] for r in result["recommendations"])


class _Routine:
    id = "telemetry-friction-auditor"

    def __init__(self, **meta):
        self.metadata = {"lookback_hours": 24, **meta}


def test_two_unmapped_tools_with_the_same_friction_each_get_a_card(store, data_dir):
    # Repro from the card: both have skill_path None and payload_bloat; the old key collided.
    _bloat(store, "c525_inventory_dump", "c525_other_dump")
    result = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    assert _tools(result) == ["c525_inventory_dump", "c525_other_dump"]


def test_two_tools_in_the_same_skill_each_get_a_card(store, data_dir):
    _bloat(store, "wiki_note_read", "wiki_note_export")
    result = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    assert _tools(result) == ["wiki_note_export", "wiki_note_read"]
    assert {r["skill_path"] for r in result["recommendations"]} == {"skills/wiki/SKILL.md"}


def test_same_tool_twice_in_one_audit_gets_one_card(store, data_dir):
    _bloat(store, "c525_inventory_dump")
    _bloat(store, "c525_inventory_dump")
    assert _tools(run_telemetry_friction_audit(store, data_dir, lookback_hours=24)) == ["c525_inventory_dump"]


def test_no_duplicate_while_pending_or_escalated(store, data_dir):
    _bloat(store, "c525_inventory_dump")
    first = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    rec_id = first["recommendations"][0]["id"]
    later = datetime.now(timezone.utc) + timedelta(days=30)
    assert run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=later)["recommendations_count"] == 0
    store.update_proposal_payload(rec_id, store.get_proposal(rec_id).payload_json.replace('"pending"', '"escalated"'))
    store.update_proposal_status(rec_id, "approved")
    assert run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=later)["recommendations_count"] == 0


def test_a_new_tool_still_gets_a_card_while_another_is_pending(store, data_dir):
    _bloat(store, "c525_inventory_dump")
    run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    _bloat(store, "c525_other_dump")
    assert _tools(run_telemetry_friction_audit(store, data_dir, lookback_hours=24)) == ["c525_other_dump"]


def test_dismissed_comes_back_after_the_cool_down(store, data_dir):
    _bloat(store, "c525_inventory_dump")
    rec_id = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)["recommendations"][0]["id"]
    store.update_proposal_status(rec_id, "rejected")
    now = datetime.now(timezone.utc)
    assert (
        run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=now + timedelta(days=6))[
            "recommendations_count"
        ]
        == 0
    )
    again = run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=now + timedelta(days=8))
    assert _tools(again) == ["c525_inventory_dump"]
    assert again["recommendations"][0]["id"] != rec_id


def test_cool_down_comes_from_routine_metadata(store, data_dir):
    _bloat(store, "c525_inventory_dump")
    rec_id = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)["recommendations"][0]["id"]
    store.update_proposal_status(rec_id, "rejected")
    two_days = datetime.now(timezone.utc) + timedelta(days=2)
    blocked = run_telemetry_friction_audit(store, data_dir, routine=_Routine(), now=two_days)
    assert blocked["recommendations_count"] == 0
    short = run_telemetry_friction_audit(store, data_dir, routine=_Routine(dismissed_cooldown_days=1), now=two_days)
    assert short["recommendations_count"] == 1


def test_applied_blocks_for_the_cool_down_then_comes_back(store, data_dir):
    # Decision: an applied patch also waits out the cool-down; the 24 h lookback still holds the pre-fix calls.
    _bloat(store, "wiki_note_read")
    rec_id = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)["recommendations"][0]["id"]
    store.update_proposal_status(rec_id, "approved")
    now = datetime.now(timezone.utc)
    assert run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=now)["recommendations_count"] == 0
    assert (
        run_telemetry_friction_audit(store, data_dir, lookback_hours=24, now=now + timedelta(days=8))[
            "recommendations_count"
        ]
        == 1
    )


def test_other_agent_with_the_same_tool_gets_its_own_card(store, data_dir):
    _bloat(store, "c525_inventory_dump", agent="autoreiv")
    run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    _bloat(store, "c525_inventory_dump", agent="librarian")
    result = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    assert [(r["agent_id"], r["tool_name"]) for r in result["recommendations"]] == [
        ("librarian", "c525_inventory_dump")
    ]


def test_key_status_and_block_rules():
    old = normalize_friction_rec(
        {
            "agent_id": "autoreiv",
            "friction_type": "payload_bloat",
            "skill_path": None,
            "summary": "Escalate c520_inventory_dump to Factory Studio (unbounded payload).",
            "proposed_patch": "... (20790 bytes).",
        }
    )
    assert friction_key(old) == ("autoreiv", "c520_inventory_dump", "payload_bloat")
    assert friction_key({"agent_id": "a", "friction_type": "x", "skill_path": "skills/s/SKILL.md"}) == (
        "a",
        "skill:skills/s/SKILL.md",
        "x",
    )
    assert recommendation_status(ProposalStatus.DRAFT) == "pending"
    assert recommendation_status("approved", "escalated") == "escalated"
    assert recommendation_status("approved", "pending") == "applied"
    assert recommendation_status(ProposalStatus.REJECTED) == "dismissed"
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    assert blocks_new_recommendation("pending", None, now=now)
    assert blocks_new_recommendation("escalated", now - timedelta(days=99), now=now)
    assert blocks_new_recommendation("dismissed", now - timedelta(days=6), now=now)
    assert not blocks_new_recommendation("dismissed", now - timedelta(days=8), now=now)
    assert not blocks_new_recommendation("applied", datetime(2026, 9, 1), now=now)  # naive = UTC
