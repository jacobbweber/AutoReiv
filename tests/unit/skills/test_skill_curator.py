"""Skill curator: stale unused user packs archive, seeds never deleted [REQ-IMPROVE-013 - REQ-IMPROVE-016]."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.orchestration.ace_online import record_failed_turn_delta
from src.application.routines.skill_eval_sleep import run_skill_eval_job
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.application.skills.skill_curator import (
    ARCHIVE_AFTER_DAYS,
    ROUTINE_ID,
    STALE_AFTER_DAYS,
    archive_pack,
    classify_age,
    curate_user_skill_packs,
    last_used_at,
    maybe_curate_from_routine,
    unarchive_pack,
)
from src.application.skills.user_catalog import ARCHIVE_DIRNAME, UserSkillCatalog
from src.domain.routines.manifests import (
    BUILTIN_ROUTINES,
    SKILL_CURATOR_ROUTINE,
    SKILL_EVAL_SLEEP_ROUTINE,
    get_builtin_routine,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.seed import (
    OKTA_ADMIN_PACK_ID,
    bundled_okta_admin_skill_md,
    seed_bundled_skill_packs,
)
from src.web.app import create_app

USER_PACK_MD = """---
name: old-experiment
description: A user pack that should go stale then archive.
---

Playbook body. Distinctive-archive-token.
"""

FRESH_PACK_MD = """---
name: fresh-pack
description: Recently used user pack.
---

Still active.
"""


def _write_pack(skills: Path, slug: str, content: str) -> Path:
    pack = skills / slug
    pack.mkdir(parents=True, exist_ok=True)
    skill = pack / "SKILL.md"
    skill.write_text(content, encoding="utf-8")
    return skill


def _age_mtime(path: Path, days: int, now: datetime) -> None:
    ts = (now - timedelta(days=days)).timestamp()
    import os

    os.utime(path, (ts, ts))


def _env(tmp_path: Path, now: datetime):
    data_dir = tmp_path / "data"
    skills = data_dir / "skills"
    skills.mkdir(parents=True)
    seed_bundled_skill_packs(skills)
    okta = skills / OKTA_ADMIN_PACK_ID / "SKILL.md"
    _age_mtime(okta, 200, now)
    old = _write_pack(skills, "old-experiment", USER_PACK_MD)
    _age_mtime(old, 100, now)
    fresh = _write_pack(skills, "fresh-pack", FRESH_PACK_MD)
    _age_mtime(fresh, 2, now)
    catalog = UserSkillCatalog(skills_dir=skills)
    store = SQLiteStateStore(db_path=str(tmp_path / "autoreiv.db"))
    store.initialize_db()
    return {
        "data_dir": data_dir,
        "skills": skills,
        "catalog": catalog,
        "store": store,
        "now": now,
        "okta": okta,
        "old": old,
        "fresh": fresh,
        "seed_src": bundled_okta_admin_skill_md(),
    }


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def env(tmp_path, now):
    return _env(tmp_path, now)


def test_thresholds_are_30_stale_90_archive():
    assert STALE_AFTER_DAYS == 30
    assert ARCHIVE_AFTER_DAYS == 90
    now = datetime(2026, 8, 30, tzinfo=timezone.utc)
    assert classify_age(now - timedelta(days=10), now=now) == "active"
    assert classify_age(now - timedelta(days=35), now=now) == "stale"
    assert classify_age(now - timedelta(days=91), now=now) == "archive"
    assert classify_age(None, now=now) == "unknown"


def test_okta_admin_never_auto_archived(env):
    seed_before = env["seed_src"].read_bytes()
    seed_mtime = env["seed_src"].stat().st_mtime
    dest_before = env["okta"].read_bytes()
    result = curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    assert result["success"] is True
    assert env["okta"].is_file()
    assert env["okta"].read_bytes() == dest_before
    assert not (env["skills"] / ARCHIVE_DIRNAME / OKTA_ADMIN_PACK_ID).exists()
    ids = {row["pack_id"] for row in result["classified"] if row.get("status") == "bundled"}
    assert OKTA_ADMIN_PACK_ID in ids
    assert all(row["pack_id"] != OKTA_ADMIN_PACK_ID for row in result["archived"])
    assert env["seed_src"].is_file()
    assert env["seed_src"].read_bytes() == seed_before
    assert env["seed_src"].stat().st_mtime == seed_mtime
    assert result["repo_seeds_untouched"] is True
    assert result["skill_md_deleted"] is False


def test_bundled_archive_requires_explicit_confirm(env):
    denied = archive_pack(env["catalog"], OKTA_ADMIN_PACK_ID, confirm=False)
    assert denied["success"] is False
    assert denied["archived"] is False
    assert env["okta"].is_file()
    confirmed = archive_pack(env["catalog"], OKTA_ADMIN_PACK_ID, confirm=True)
    assert confirmed["success"] is True
    assert confirmed["archived"] is True
    assert not env["okta"].exists()
    archived_skill = env["skills"] / ARCHIVE_DIRNAME / OKTA_ADMIN_PACK_ID / "SKILL.md"
    assert archived_skill.is_file()
    assert archived_skill.read_text(encoding="utf-8")
    assert env["seed_src"].is_file()


def test_old_unused_user_pack_moves_to_archive(env):
    result = curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    live = env["skills"] / "old-experiment"
    archived = env["skills"] / ARCHIVE_DIRNAME / "old-experiment"
    assert not live.exists()
    assert archived.is_dir()
    skill = archived / "SKILL.md"
    assert skill.is_file()
    assert "Distinctive-archive-token" in skill.read_text(encoding="utf-8")
    archived_ids = {row["pack_id"] for row in result["archived"]}
    assert "old-experiment" in archived_ids
    assert "fresh-pack" not in archived_ids
    assert (env["skills"] / "fresh-pack" / "SKILL.md").is_file()
    assert result["skill_md_deleted"] is False


def test_stale_but_under_archive_window_stays_live(env):
    mid = env["skills"] / "mid-pack" / "SKILL.md"
    mid.parent.mkdir()
    mid.write_text(FRESH_PACK_MD.replace("fresh-pack", "mid-pack"), encoding="utf-8")
    _age_mtime(mid, 40, env["now"])
    result = curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    row = next(r for r in result["classified"] if r["pack_id"] == "mid-pack")
    assert row["status"] == "stale"
    assert row["archived"] is False
    assert mid.is_file()
    assert not (env["skills"] / ARCHIVE_DIRNAME / "mid-pack").exists()


def test_unknown_last_used_fails_closed(env):
    result = curate_user_skill_packs(
        env["catalog"],
        now=env["now"],
        auto_archive=True,
        last_used_by_id={"old-experiment": None},
    )
    assert (env["skills"] / "old-experiment" / "SKILL.md").is_file()
    assert not (env["skills"] / ARCHIVE_DIRNAME / "old-experiment").exists()
    row = next(r for r in result["classified"] if r["pack_id"] == "old-experiment")
    assert row["status"] == "unknown"
    assert row["archived"] is False


def test_auto_archive_default_is_not_destructive(env):
    result = curate_user_skill_packs(env["catalog"], now=env["now"])
    assert result["auto_archive"] is False
    assert result["archived_count"] == 0
    assert (env["skills"] / "old-experiment" / "SKILL.md").is_file()
    hooked = maybe_curate_from_routine(env["catalog"], SKILL_EVAL_SLEEP_ROUTINE, now=env["now"])
    assert hooked.get("auto_archive") is False
    assert hooked.get("archived_count", 0) == 0
    assert (env["skills"] / "old-experiment" / "SKILL.md").is_file()


def test_list_user_skill_packs_hides_archived(env):
    curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    listed = env["catalog"].list_user_skill_packs()
    ids = {p["id"] for p in listed["packs"]}
    assert "old-experiment" not in ids
    assert "fresh-pack" in ids
    assert OKTA_ADMIN_PACK_ID in ids
    assert all(ARCHIVE_DIRNAME not in p["id"] for p in listed["packs"])
    loader_ids = {m.id for m in DynamicSkillLoader.list_skill_manifests(str(env["skills"]))}
    assert "old-experiment" not in loader_ids
    assert all(ARCHIVE_DIRNAME not in i for i in loader_ids)


def test_unarchive_restores_and_dest_exists_fails_closed(env):
    curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    moved = unarchive_pack(env["catalog"], "old-experiment")
    assert moved["success"] is True
    assert moved["proposal_id"] is None
    live = env["skills"] / "old-experiment" / "SKILL.md"
    assert live.is_file()
    assert "Distinctive-archive-token" in live.read_text(encoding="utf-8")
    ids = {p["id"] for p in env["catalog"].list_user_skill_packs()["packs"]}
    assert "old-experiment" in ids
    # archive again then plant a live dest to prove fail-closed
    curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    _write_pack(env["skills"], "old-experiment", FRESH_PACK_MD)
    clash = unarchive_pack(env["catalog"], "old-experiment")
    assert clash["success"] is False
    assert clash.get("conflict") is True
    assert (env["skills"] / "old-experiment" / "SKILL.md").is_file()
    assert (env["skills"] / ARCHIVE_DIRNAME / "old-experiment" / "SKILL.md").is_file()


def test_copy_if_missing_seed_still_does_not_overwrite(env):
    marker = "user-edit-token-do-not-clobber"
    env["okta"].write_text(env["okta"].read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8")
    curate_user_skill_packs(env["catalog"], now=env["now"], auto_archive=True)
    seed_bundled_skill_packs(env["skills"])
    assert marker in env["okta"].read_text(encoding="utf-8")
    assert marker not in env["seed_src"].read_text(encoding="utf-8")


def test_curator_does_not_run_during_interactive_ace_turn(env):
    before = (env["skills"] / "old-experiment" / "SKILL.md").read_bytes()
    drafted = record_failed_turn_delta(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_curator",
        agent_id="agent-builder",
        error_message="checker miss",
        catalog=env["catalog"],
    )
    assert drafted.get("status") == "draft"
    assert (env["skills"] / "old-experiment" / "SKILL.md").read_bytes() == before
    assert (env["skills"] / "old-experiment").is_dir()
    assert not (env["skills"] / ARCHIVE_DIRNAME / "old-experiment").exists()


def test_skill_eval_sleep_default_does_not_archive(env):
    result = run_skill_eval_job(
        env["store"],
        env["data_dir"],
        routine=SKILL_EVAL_SLEEP_ROUTINE,
        now=env["now"],
        catalog=env["catalog"],
    )
    assert (env["skills"] / "old-experiment" / "SKILL.md").is_file()
    curator = result.get("curator") or {}
    assert curator.get("auto_archive") in (False, None)
    assert curator.get("archived_count", 0) == 0


def test_skill_curator_routine_is_paused_sibling():
    assert SKILL_CURATOR_ROUTINE in BUILTIN_ROUTINES
    assert SKILL_CURATOR_ROUTINE.enabled is False
    assert SKILL_CURATOR_ROUTINE.agent_id == "agent-builder"
    assert SKILL_CURATOR_ROUTINE.id == ROUTINE_ID
    assert SKILL_CURATOR_ROUTINE.metadata.get("auto_archive") is True
    assert SKILL_CURATOR_ROUTINE.metadata.get("stale_days") == 30
    assert SKILL_CURATOR_ROUTINE.metadata.get("archive_days") == 90
    assert SKILL_EVAL_SLEEP_ROUTINE.metadata.get("auto_archive") is False
    seeded = get_builtin_routine("skill-curator")
    assert seeded is not None
    assert seeded.enabled is False


def test_last_used_uses_mtime_and_sidecar(env):
    used = last_used_at(env["old"].parent, pack_id="old-experiment")
    assert used is not None
    age = env["now"] - used
    assert age.days >= 90
    env["catalog"].record_pack_use("fresh-pack")
    used_fresh = last_used_at(env["fresh"].parent, pack_id="fresh-pack")
    assert used_fresh is not None
    assert (env["now"] - used_fresh).days < 1 or used_fresh >= env["now"] - timedelta(minutes=5)


def test_api_hides_archived_and_unarchive_reopens(tmp_path, now, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    skills = tmp_path / "data" / "skills"
    skills.mkdir(parents=True)
    seed_bundled_skill_packs(skills)
    old = _write_pack(skills, "old-experiment", USER_PACK_MD)
    _age_mtime(old, 100, now)
    client = TestClient(create_app())
    catalog = UserSkillCatalog(skills_dir=skills)
    curate_user_skill_packs(catalog, now=now, auto_archive=True)

    listed = client.get("/api/skills/user-packs")
    assert listed.status_code == 200
    ids = {p["id"] for p in listed.json()["packs"]}
    assert "old-experiment" not in ids
    assert OKTA_ADMIN_PACK_ID in ids

    archived = client.get("/api/skills/archived-packs")
    assert archived.status_code == 200
    arch_ids = {p["id"] for p in archived.json()["packs"]}
    assert "old-experiment" in arch_ids

    restored = client.post("/api/skills/user-packs/old-experiment/unarchive")
    assert restored.status_code == 200
    opened = client.get("/api/skills/user-packs/old-experiment")
    assert opened.status_code == 200
    assert "Distinctive-archive-token" in opened.json()["instructions"]

    deny = client.post("/api/skills/user-packs/okta-admin/archive", json={"confirm": False})
    assert deny.status_code == 400
    assert (skills / OKTA_ADMIN_PACK_ID / "SKILL.md").is_file()
