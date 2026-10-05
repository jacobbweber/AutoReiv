"""
Nightly skill-eval routine (SkillOpt-Sleep shape) [REQ-IMPROVE-007 - REQ-IMPROVE-012] [REQ-IMPROVE-016].
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.application.gateway.generation_semaphore import DEFAULT_MAX_CONCURRENT_GENERATIONS
from src.application.routines.matcher import ScheduleMatcher
from src.application.routines.skill_eval_sleep import (
    AGENT_ID,
    ROUTINE_ID,
    harvest_db_is_live,
    run_skill_eval_job,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.routines.manifests import (
    BUILTIN_ROUTINES,
    REMOVED_BUILTIN_ROUTINE_IDS,
    TELEMETRY_FRICTION_AUDITOR_ROUTINE,
)
from src.domain.routines.models import Routine, ScheduleType
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.data.resolver import DataDirResolver
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SRC_ROOT = Path(__file__).resolve().parents[3] / "src"

# CARD-636 retired the skill-eval-sleep routine (skill eval now runs inside the nightly auditor).
# The job itself is unchanged, so these tests drive it with a local routine of the old shape.
SKILL_EVAL_SLEEP_ROUTINE = Routine(
    id=ROUTINE_ID,
    name="Nightly skill eval (test fixture)",
    agent_id=AGENT_ID,
    prompt="Harvest + gate + propose_skill HITL only. Do not write SKILL.md.",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 21 * * 1-5",
    enabled=False,
    metadata={
        "timezone": "America/New_York",
        "hour": 21,
        "minute": 0,
        "weekdays_only": True,
        "lookback_hours": 72,
        "replay": False,
        "auto_commit": False,
        "auto_archive": False,
    },
)


@pytest.fixture
def env(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    store.initialize_db()
    data_dir = tmp_path / "data"
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    catalog.save_skill("okta-admin", "okta-admin", "Homelab Okta admin playbook.", "List users. Stub reset.")
    skill_path = skills_dir / "okta-admin" / "SKILL.md"
    return {
        "tmp": tmp_path,
        "store": store,
        "data_dir": data_dir,
        "skills_dir": skills_dir,
        "catalog": catalog,
        "skill_path": skill_path,
        "skill_before": skill_path.read_bytes(),
        "src_before": {p: p.stat().st_mtime_ns for p in SRC_ROOT.rglob("*.py") if "pycache" not in str(p)},
    }


def _src_untouched(env) -> None:
    after = {p: p.stat().st_mtime_ns for p in SRC_ROOT.rglob("*.py") if "pycache" not in str(p)}
    for path, mtime in env["src_before"].items():
        if path.name == "skill_eval_sleep.py":
            continue
        assert after.get(path) == mtime


def _failed_turn(store, *, created_at=None, skill_id="okta-admin"):
    store.save_telemetry_span(
        TelemetrySpan(
            id="span_fail_1",
            session_id="sess_fail",
            agent_id="assistant",
            span_type="turn",
            name="turn",
            success=False,
            error_message="okta_reset_or_unlock returned playbook stub",
            metadata={"skill_id": skill_id, "tool_name": "okta_reset_or_unlock"},
            created_at=created_at or datetime.now(timezone.utc),
        )
    )


def test_skill_eval_is_hosted_by_the_auditor_with_no_new_dependency():
    """CARD-636: no standalone skill-eval routine; the enabled nightly auditor hosts it, replay and commit off."""
    assert ROUTINE_ID in REMOVED_BUILTIN_ROUTINE_IDS
    host = TELEMETRY_FRICTION_AUDITOR_ROUTINE
    assert host in BUILTIN_ROUTINES
    assert host.enabled is True
    assert host.metadata["timezone"] == "America/New_York"
    assert host.metadata["replay"] is False
    assert host.metadata["auto_commit"] is False
    src = Path("src/application/routines/skill_eval_sleep.py").read_text(encoding="utf-8")
    assert "import skillopt" not in src
    assert "from skillopt" not in src
    assert "import langgraph" not in src
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "skillopt" not in pyproject.lower()


def test_enabled_next_run_is_weekday_2100_et_not_0200_or_utc_2100():
    base = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    routine = SKILL_EVAL_SLEEP_ROUTINE
    enabled = routine.model_copy(update={"enabled": True, "last_run_at": None, "next_run_at": None})
    nxt = ScheduleMatcher.compute_next_run(enabled, base_time=base)
    assert nxt.tzinfo is not None
    assert nxt == datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
    assert nxt.hour != 21
    assert nxt != datetime(2026, 9, 1, 6, 0, tzinfo=timezone.utc)
    assert ScheduleMatcher.is_routine_due(enabled, current_time=base) is False
    due_at = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
    enabled_due = enabled.model_copy(update={"next_run_at": due_at})
    assert ScheduleMatcher.is_routine_due(enabled_due, current_time=due_at) is True
    friday = datetime(2026, 9, 5, 1, 5, tzinfo=timezone.utc)
    after = ScheduleMatcher.compute_next_run(enabled, base_time=friday)
    assert after == datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc)
    assert after.astimezone(timezone.utc).weekday() == 1


def test_job_failed_turn_creates_draft_not_skill_md(env):
    _failed_turn(env["store"])
    result = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        catalog=env["catalog"],
        session_id="sess_nightly",
        agent_id=AGENT_ID,
    )
    assert result["status"] == "success"
    assert result["proposal_id"]
    assert result["skill_md_written"] is False
    assert result["disk_written"] is False
    assert result["committed"] is False
    assert result["auto_commit"] is False
    assert result["src_written"] is False
    assert result["stream_turn_attached"] is False
    assert env["skill_path"].read_bytes() == env["skill_before"]

    proposal = env["store"].get_proposal(result["proposal_id"])
    assert proposal.status.value == "draft"
    assert proposal.kind.value == "skill"
    payload = json.loads(proposal.payload_json)
    assert payload.get("auto_commit") is False
    assert payload.get("routine_id") == ROUTINE_ID
    assert payload.get("source") == ROUTINE_ID
    pending = env["store"].get_pending_approvals(session_id="sess_nightly")
    assert any(row["tool_name"] == "propose_skill" for row in pending)
    assert any(row.get("routine_id") == ROUTINE_ID for row in pending)
    _src_untouched(env)


def test_empty_harvest_is_success_noop(env):
    result = run_skill_eval_job(env["store"], env["data_dir"], catalog=env["catalog"])
    assert result["status"] == "success"
    assert result["harvested"] == 0
    assert result["proposal_id"] is None
    assert env["skill_path"].read_bytes() == env["skill_before"]
    conn = env["store"]._get_connection()
    try:
        rows = conn.execute("SELECT id FROM proposals").fetchall()
    finally:
        if env["store"]._mem_conn is None:
            conn.close()
    assert rows == []


def test_missing_named_checker_is_skip_not_pass(env):
    _failed_turn(env["store"])
    routine = SKILL_EVAL_SLEEP_ROUTINE.model_copy(
        update={"metadata": {**SKILL_EVAL_SLEEP_ROUTINE.metadata, "checker": "skillopt_gate"}}
    )
    result = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        routine=routine,
        catalog=env["catalog"],
    )
    assert result["status"] == "skip"
    assert result["verification_passed"] is False
    assert result["proposal_id"] is None
    assert env["skill_path"].read_bytes() == env["skill_before"]


def test_checker_fail_does_not_stage(env):
    _failed_turn(env["store"])

    def boom(candidates, store=None, routine=None):
        return {"status": "fail", "passed": False, "reason": "held-out miss"}

    result = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        catalog=env["catalog"],
        checker=boom,
    )
    assert result["status"] == "fail"
    assert result["proposal_id"] is None
    assert env["skill_path"].read_bytes() == env["skill_before"]


def test_replay_default_off_and_honors_slot_cap(env):
    _failed_turn(env["store"])
    calls = {"n": 0}

    def replay_fn(_cand):
        calls["n"] += 1

    default = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        catalog=env["catalog"],
        replay_fn=replay_fn,
    )
    assert default["replay"] is False
    assert calls["n"] == 0
    assert DEFAULT_MAX_CONCURRENT_GENERATIONS == 1

    calls["n"] = 0
    on = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        catalog=env["catalog"],
        replay=True,
        replay_fn=replay_fn,
    )
    assert on["replay"] is True
    assert calls["n"] == 1
    assert on["stream_turn_attached"] is False


def test_refuses_checkout_data_when_live_is_localappdata(env, tmp_path):
    checkout = tmp_path / "repo"
    legacy_db = checkout / "data" / "autoreiv.db"
    legacy_db.parent.mkdir(parents=True)
    legacy_db.write_bytes(b"")
    live = tmp_path / "LocalAppData" / "AutoReiv"
    live.mkdir(parents=True)
    resolver = DataDirResolver(checkout_root=checkout, local_appdata=tmp_path / "LocalAppData", os_name="nt")

    class FakeStore:
        db_path = legacy_db

    check = harvest_db_is_live(FakeStore(), data_dir=legacy_db.parent, resolver=resolver)
    assert check["live"] is False
    assert "checkout" in check["reason"].lower() or "LocalAppData" in check["reason"]


def test_builtins_no_longer_include_skill_eval_sleep():
    ids = [r.id for r in BUILTIN_ROUTINES]
    assert ROUTINE_ID not in ids
