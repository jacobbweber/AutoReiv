"""CARD-636: five shipped routines on America/New_York night times; one seed; one-time migration; delete sticks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.routines.matcher import ScheduleMatcher, describe_schedule
from src.application.routines.seed import (
    CARD636_MIGRATION_SETTING,
    DELETED_BUILTINS_SETTING,
    seed_builtin_routines,
)
from src.domain.routines.manifests import BUILTIN_ROUTINES, REMOVED_BUILTIN_ROUTINE_IDS, get_builtin_routine
from src.domain.routines.models import Routine, RoutineRun, RoutineStatus, ScheduleType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

KEPT = {
    "hourly-sre-pulse": (2, 0, None),
    "education-retrieval-retention": (2, 30, None),
    "wiki-curation": (3, 0, None),
    "weekly-note-rollover": (4, 0, [1]),
    "telemetry-friction-auditor": (4, 30, None),
}
REMOVED = {"daily-sysinfo", "morning-briefing", "skill-curator", "nightly-hygiene", "skill-eval-sleep"}
MODEL_ROUTINES = ("hourly-sre-pulse", "wiki-curation", "weekly-note-rollover")
UTC = timezone.utc


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_exactly_five_builtins():
    assert {r.id for r in BUILTIN_ROUTINES} == set(KEPT)
    assert set(REMOVED_BUILTIN_ROUTINE_IDS) == REMOVED
    for rid in REMOVED:
        assert get_builtin_routine(rid) is None


@pytest.mark.parametrize("rid", sorted(KEPT))
def test_local_new_york_schedule_and_enabled(rid):
    r = get_builtin_routine(rid)
    hour, minute, weekdays = KEPT[rid]
    assert r.enabled is True
    assert r.metadata["timezone"] == "America/New_York"
    assert (r.metadata["hour"], r.metadata["minute"]) == (hour, minute)
    assert r.metadata.get("weekdays") == weekdays
    assert r.metadata["weekdays_only"] is False


def test_next_runs_from_monday_evening_edt():
    base = datetime(2026, 10, 5, 22, 30, tzinfo=UTC)  # Mon 18:30 EDT
    want = {
        "hourly-sre-pulse": datetime(2026, 10, 6, 6, 0, tzinfo=UTC),
        "education-retrieval-retention": datetime(2026, 10, 6, 6, 30, tzinfo=UTC),
        "wiki-curation": datetime(2026, 10, 6, 7, 0, tzinfo=UTC),
        "weekly-note-rollover": datetime(2026, 10, 12, 8, 0, tzinfo=UTC),
        "telemetry-friction-auditor": datetime(2026, 10, 6, 8, 30, tzinfo=UTC),
    }
    for rid, at in want.items():
        assert ScheduleMatcher.compute_next_run(get_builtin_routine(rid), base_time=base) == at, rid


def test_local_time_holds_across_dst_end():
    base = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)  # Mon after DST ended
    sre = ScheduleMatcher.compute_next_run(get_builtin_routine("hourly-sre-pulse"), base_time=base)
    assert sre == datetime(2026, 11, 3, 7, 0, tzinfo=UTC)  # 02:00 EST
    roll = ScheduleMatcher.compute_next_run(get_builtin_routine("weekly-note-rollover"), base_time=base)
    assert roll == datetime(2026, 11, 9, 9, 0, tzinfo=UTC)  # Mon 04:00 EST


def test_model_routines_an_hour_apart():
    mins = sorted(KEPT[r][0] * 60 + KEPT[r][1] for r in MODEL_ROUTINES)
    assert all(b - a >= 60 for a, b in zip(mins, mins[1:]))
    for r in BUILTIN_ROUTINES:
        assert 2 * 60 <= r.metadata["hour"] * 60 + r.metadata["minute"] <= 5 * 60


def test_wiki_curation_absorbs_hygiene_prompt():
    p = get_builtin_routine("wiki-curation").prompt.lower()
    assert "00_inbox" in p
    assert "frontmatter" in p and "titles and tags" in p
    assert "library index" in p


def test_sre_renamed_nightly():
    assert get_builtin_routine("hourly-sre-pulse").name == "Nightly SRE Health Pulse"


def test_describe_schedule_reads_the_real_schedule():
    assert describe_schedule(get_builtin_routine("hourly-sre-pulse")) == "Daily at 02:00 ET"
    assert describe_schedule(get_builtin_routine("weekly-note-rollover")) == "Mondays at 04:00 ET"
    every = Routine(id="x", name="x", agent_id="a", prompt="p", schedule_type=ScheduleType.INTERVAL,
                    interval_seconds=3600, cron_expression="0 8 * * *")
    assert describe_schedule(every) == "Every 1 hour"


def test_seed_fresh_store_five_rows_scheduled(store):
    now = datetime(2026, 10, 5, 22, 30, tzinfo=UTC)
    seed_builtin_routines(store, now=now)
    rows = {r.id: r for r in store.list_routines()}
    assert set(rows) == set(KEPT)
    for r in rows.values():
        assert r.next_run_at > now
    assert store.get_setting(CARD636_MIGRATION_SETTING) is True
    # the shipped manifest objects are not mutated by seeding
    assert all(b.next_run_at is None for b in BUILTIN_ROUTINES)


def _legacy_rows(store, now):
    old = [
        Routine(id="hourly-sre-pulse", name="Hourly SRE Health Pulse", agent_id="autoreiv", prompt="old",
                schedule_type=ScheduleType.INTERVAL, interval_seconds=3600, cron_expression="0 * * * *",
                last_run_at=now - timedelta(minutes=10), next_run_at=now + timedelta(minutes=50),
                last_status=RoutineStatus.SUCCESS),
        Routine(id="wiki-curation", name="Wiki Inbox Curation Routine", agent_id="autoreiv", prompt="old wiki",
                schedule_type=ScheduleType.INTERVAL, interval_seconds=3600, cron_expression="0 * * * *",
                next_run_at=now + timedelta(minutes=40)),
        Routine(id="weekly-note-rollover", name="Weekly", agent_id="autoreiv", prompt="old roll",
                schedule_type=ScheduleType.CRON, cron_expression="0 0 * * 1",
                metadata={"approval_mode": "run", "run_as_job": False}),
        Routine(id="telemetry-friction-auditor", name="Auditor", agent_id="autoreiv", prompt="old",
                schedule_type=ScheduleType.CRON, cron_expression="0 21 * * 1-5", enabled=False,
                metadata={"timezone": "America/New_York", "hour": 21, "minute": 0, "weekdays_only": True}),
    ]
    for rid in REMOVED:
        old.append(Routine(id=rid, name=rid, agent_id="autoreiv", prompt="gone"))
    for r in old:
        store.save_routine(r)
    for rid in list(REMOVED) + ["hourly-sre-pulse"]:
        store.record_routine_run(RoutineRun(id=f"run-{rid}", routine_id=rid, agent_id="autoreiv",
                                            status=RoutineStatus.SUCCESS, created_at=now - timedelta(hours=1)))


def test_migration_deletes_removed_rows_and_history_and_rewrites_kept(store):
    now = datetime(2026, 10, 5, 22, 30, tzinfo=UTC)
    _legacy_rows(store, now)
    seed_builtin_routines(store, now=now)
    ids = {r.id for r in store.list_routines()}
    assert ids == set(KEPT)
    for rid in REMOVED:
        assert store.get_routine_runs(rid) == []
    assert len(store.get_routine_runs("hourly-sre-pulse")) == 1  # kept history stays
    sre = store.get_routine("hourly-sre-pulse")
    assert sre.name == "Nightly SRE Health Pulse"
    assert sre.metadata["hour"] == 2 and sre.metadata["timezone"] == "America/New_York"
    assert sre.next_run_at == datetime(2026, 10, 6, 6, 0, tzinfo=UTC)
    assert sre.last_run_at is not None  # history fields survive
    wiki = store.get_routine("wiki-curation")
    assert "library index" in wiki.prompt.lower()
    assert wiki.next_run_at == datetime(2026, 10, 6, 7, 0, tzinfo=UTC)
    roll = store.get_routine("weekly-note-rollover")
    assert roll.metadata["approval_mode"] == "run"  # Jacob's own setting is kept
    assert roll.next_run_at == datetime(2026, 10, 12, 8, 0, tzinfo=UTC)
    aud = store.get_routine("telemetry-friction-auditor")
    assert aud.enabled is True
    assert aud.next_run_at == datetime(2026, 10, 6, 8, 30, tzinfo=UTC)


def test_migration_runs_once(store):
    now = datetime(2026, 10, 5, 22, 30, tzinfo=UTC)
    seed_builtin_routines(store, now=now)
    sre = store.get_routine("hourly-sre-pulse")
    sre.metadata = {**sre.metadata, "hour": 3}
    store.save_routine(sre)
    seed_builtin_routines(store, now=now + timedelta(days=1))
    assert store.get_routine("hourly-sre-pulse").metadata["hour"] == 3  # Jacob's later edit is not overwritten


def test_deleted_builtin_is_not_reseeded(store):
    seed_builtin_routines(store)
    from src.application.routines.seed import remember_deleted_builtin

    store.delete_routine("wiki-curation")
    remember_deleted_builtin(store, "wiki-curation")
    seed_builtin_routines(store)
    assert store.get_routine("wiki-curation") is None
    assert store.get_routine("hourly-sre-pulse") is not None


@pytest.mark.asyncio
async def test_api_delete_builtin_sticks_across_restart():
    from src.web.app import create_app

    s = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=s)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.delete("/api/routines/wiki-curation")).status_code == 200
        custom = {"id": "mine", "name": "Mine", "agent_id": "autoreiv", "prompt_template": "p", "enabled": False}
        assert (await ac.post("/api/routines", json=custom)).status_code == 200
        assert (await ac.delete("/api/routines/mine")).status_code == 200
    assert s.get_setting(DELETED_BUILTINS_SETTING) == ["wiki-curation"]
    create_app(state_store=s)  # next boot seeds again
    assert s.get_routine("wiki-curation") is None
    assert {r.id for r in s.list_routines()} == set(KEPT) - {"wiki-curation"}


@pytest.mark.asyncio
async def test_api_lists_five_with_real_schedule():
    from src.web.app import create_app

    app = create_app(state_store=SQLiteStateStore(db_path=":memory:"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        rows = {r["id"]: r for r in (await ac.get("/api/routines")).json()}
    assert set(rows) == set(KEPT)
    assert rows["hourly-sre-pulse"]["human_schedule"] == "Daily at 02:00 ET"
    assert rows["weekly-note-rollover"]["human_schedule"] == "Mondays at 04:00 ET"
    for r in rows.values():
        assert r["is_builtin"] is True
        assert r["next_run_eta"].startswith("in ")
        assert "UTC" not in r["human_schedule"]


@pytest.mark.asyncio
async def test_auditor_also_runs_skill_eval(store, tmp_path):
    from src.application.routines import executor as ex_mod

    class _Agent:
        id = "autoreiv"

    class _Reg:
        def get_profile(self, _):
            return _Agent()

    class _Kernel:
        data_dir = str(tmp_path)
        tool_registry = None

    routine = get_builtin_routine("telemetry-friction-auditor").model_copy(deep=True)
    store.save_routine(routine)
    ex = ex_mod.RoutineExecutor(agent_registry=_Reg(), kernel=_Kernel(), state_store=store, telemetry=None)
    audit = {"status": "success", "summary": "audit ok"}
    skill = {"status": "success", "reason": "empty harvest; success no-op"}
    with patch("src.application.routines.telemetry_friction_auditor.run_telemetry_friction_audit", return_value=audit), \
            patch.object(ex_mod, "run_skill_eval_job", return_value=skill) as se:
        run = await ex.execute_routine(routine)
    assert run.status == RoutineStatus.SUCCESS
    assert se.call_args.kwargs["replay"] is False
    assert se.call_args.kwargs["routine"].id == "telemetry-friction-auditor"
    assert "audit ok" in run.output and "Skill eval" in run.output


def test_one_shared_seed():
    import inspect

    import src.cli.main as cli
    import src.web.app as web
    from src.application.routines.scheduler import RoutineScheduler

    assert not hasattr(RoutineScheduler, "seed_default_routines")
    for mod in (web, cli):
        src = inspect.getsource(mod)
        assert "for r in BUILTIN_ROUTINES" not in src
        assert "seed_builtin_routines(" in src


def test_removed_routine_handlers_are_gone():
    from src.application.routines import executor as ex_mod
    from src.application.skills import skill_curator

    assert not hasattr(ex_mod, "SKILL_CURATOR_ID")
    assert not hasattr(ex_mod, "SKILL_EVAL_SLEEP_ID")
    assert not hasattr(skill_curator, "run_curator_job")
