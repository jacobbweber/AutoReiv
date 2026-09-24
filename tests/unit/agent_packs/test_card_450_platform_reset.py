"""CARD-450: Reset to platform defaults + backup restore for platform agents [REQ-450-003..010]."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.skills.platform_pack_promotion import (
    PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING,
    PLATFORM_PACK_SYNC_REPORT_SETTING,
    PLATFORM_SHIPPED_PROMPT_SETTING,
    get_last_platform_pack_sync_report,
    list_pack_content_backups,
    promote_platform_packs,
    reset_platform_pack_to_defaults,
)
from src.web.app import create_app
from tests.unit.agent_packs.test_card_449_pack_lock_granularity import (
    _FakeRegistry,
    _FakeStore,
    _profile,
    _seed_dest,
    _sha,
    _write_pack,
)

EDIT_MARKER = "EDITED BY CARD-450 TEST"


@pytest.fixture
def checkout_v2(tmp_path: Path) -> Path:
    """Checkout whose platform seed moved from V1 to V2."""
    checkout = tmp_path / "checkout"
    _write_pack(checkout / "platform-packs", "fixturepack", prompt="SHIPPED PROMPT V2", skills=["skill-a", "skill-b"])
    return checkout


def _locked_store() -> tuple[_FakeStore, object]:
    profile = _profile("fixturepack", prompt="OPERATOR PROMPT", skills=["skill-a"], user_modified=True, seed_hash="stale")
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    store.set_setting(PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING, {"fixturepack": ["skill-b"]})
    return store, profile


def test_reset_replaces_edited_prompt_and_disabled_skills_keeps_scalars(tmp_path: Path, checkout_v2: Path):
    """REQ-450-005: Reset replaces pack-owned content even when the prompt diverged; scalars stay."""
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    store, profile = _locked_store()
    registry = _FakeRegistry(store)

    report = reset_platform_pack_to_defaults(data_dir, registry, None, pack_id="fixturepack", checkout_root=checkout_v2)

    outcome = report.results[0]
    assert outcome.pack_id == "fixturepack"
    assert outcome.status == "force_reset"
    assert outcome.skipped_fields == []
    assert profile.system_prompt == "SHIPPED PROMPT V2"
    assert profile.allowed_skill == ["skill-a", "skill-b"]
    assert profile.user_modified is False
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    assert "fixturepack" not in (store.get_setting(PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING) or {})
    backups = list_pack_content_backups(store, "fixturepack")
    assert len(backups) == 1, "exactly one backup per reset"
    assert backups[0]["reason"] == "reset_to_platform_defaults"
    assert backups[0]["system_prompt"] == "OPERATOR PROMPT"
    assert backups[0]["allowed_skill"] == ["skill-a"]


def test_reset_on_unlocked_partial_pack_still_replaces_prompt(tmp_path: Path, checkout_v2: Path):
    """REQ-450-005: promoted_partial (unlocked, prompt diverged) resets to the seed prompt too."""
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    profile = _profile("fixturepack", prompt="OPERATOR PROMPT", skills=["skill-a", "skill-b"], user_modified=False)
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    before = promote_platform_packs(data_dir, registry, None, checkout_root=checkout_v2, pack_ids=["fixturepack"])
    assert before.results[0].status == "promoted_partial"
    assert before.results[0].skipped_fields == ["system_prompt"]

    reset_platform_pack_to_defaults(data_dir, registry, None, pack_id="fixturepack", checkout_root=checkout_v2)
    assert profile.system_prompt == "SHIPPED PROMPT V2"
    last = get_last_platform_pack_sync_report(store)
    assert [r["status"] for r in last["results"] if r["pack_id"] == "fixturepack"] == ["force_reset"]


def test_skip_outcome_says_whether_a_newer_platform_version_exists(tmp_path: Path, checkout_v2: Path):
    """REQ-450-001: skipped status is honest about an upstream update vs a customization only."""
    from src.infrastructure.skills.platform_packs import compute_platform_seed_hash

    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    store, profile = _locked_store()  # seed hash "stale" -> a newer platform version exists
    registry = _FakeRegistry(store)
    stale = promote_platform_packs(data_dir, registry, None, checkout_root=checkout_v2, pack_ids=["fixturepack"])
    assert stale.results[0].status == "skipped_user_modified"
    assert stale.results[0].seed_update_available is True

    src = checkout_v2 / "platform-packs" / "fixturepack"
    import json as _json

    profile.seed_content_hash = compute_platform_seed_hash(_json.loads((src / "pack.json").read_text("utf-8")), src)
    current = promote_platform_packs(data_dir, registry, None, checkout_root=checkout_v2, pack_ids=["fixturepack"])
    assert current.results[0].status == "skipped_user_modified"
    assert current.results[0].seed_update_available is False
    assert current.to_dict()["results"][0]["seed_update_available"] is False


def test_single_pack_run_merges_into_last_report(tmp_path: Path, checkout_v2: Path):
    """REQ-450-010: a pack_ids subset run replaces only its own entries."""
    _write_pack(checkout_v2 / "platform-packs", "otherpack", prompt="OTHER", skills=["skill-a"])
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    store, _profile_obj = _locked_store()
    store.profiles["otherpack"] = _profile("otherpack", prompt="OTHER", skills=["skill-a"])
    registry = _FakeRegistry(store)

    promote_platform_packs(data_dir, registry, None, checkout_root=checkout_v2, pack_ids=["fixturepack", "otherpack"])
    full = store.get_setting(PLATFORM_PACK_SYNC_REPORT_SETTING)
    other_before = next(r for r in full["results"] if r["pack_id"] == "otherpack")
    assert next(r for r in full["results"] if r["pack_id"] == "fixturepack")["status"] == "skipped_user_modified"

    returned = reset_platform_pack_to_defaults(
        data_dir, registry, None, pack_id="fixturepack", checkout_root=checkout_v2
    )
    assert [r.pack_id for r in returned.results] == ["fixturepack"]

    merged = store.get_setting(PLATFORM_PACK_SYNC_REPORT_SETTING)
    by_id = {r["pack_id"]: r for r in merged["results"]}
    assert set(by_id) == {"fixturepack", "otherpack"}
    assert by_id["fixturepack"]["status"] == "force_reset"
    assert by_id["otherpack"] == other_before
    assert [r["pack_id"] for r in merged["results"]] == [r["pack_id"] for r in full["results"]]


def _status(client: TestClient, pack_id: str) -> dict | None:
    report = client.get("/api/platform-packs/sync-status").json()
    return next((r for r in report.get("results") or [] if r.get("pack_id") == pack_id), None)


def test_reset_and_restore_end_to_end_on_fixture_app():
    """REQ-450-003/005/009/010 end to end on an isolated app (never live AppData)."""
    app = create_app()
    with TestClient(app) as client:
        stock = client.get("/api/agents/developer")
        assert stock.status_code == 200, stock.text
        stock_body = stock.json()
        assert stock_body["is_platform_pack"] is True
        stock_prompt = stock_body["system_prompt"]
        model_before = stock_body["model"]

        edited = dict(stock_body)
        edited["system_prompt"] = stock_prompt + "\n" + EDIT_MARKER
        edited["max_turns"] = 77
        put = client.put("/api/agents/developer", json=edited)
        assert put.status_code == 200, put.text

        sync = client.post("/api/platform-packs/sync")
        assert sync.status_code == 200, sync.text
        dev = _status(client, "developer")
        assert dev is not None and dev["status"] == "skipped_user_modified"
        tutor_before = _status(client, "tutor")
        assert tutor_before is not None and tutor_before["status"] in ("unchanged", "promoted")

        reset = client.post("/api/agents/developer/accept-platform-seed")
        assert reset.status_code == 200, reset.text
        assert reset.json()["sync"]["results"][0]["status"] == "force_reset"

        after = client.get("/api/agents/developer").json()
        assert EDIT_MARKER not in after["system_prompt"]
        assert after["max_turns"] == 77
        assert after["model"] == model_before
        assert _status(client, "developer")["status"] == "force_reset"
        assert _status(client, "tutor") == tutor_before, "single-pack reset must not drop other agents"

        backups = client.get("/api/agents/developer/pack-content-backups").json()["backups"]
        assert backups, "reset must write a backup first"
        newest = backups[0]
        assert newest["reason"] == "reset_to_platform_defaults"
        assert EDIT_MARKER in newest["system_prompt"]

        restored = client.post(f"/api/agents/developer/pack-content-backups/{newest['id']}/restore")
        assert restored.status_code == 200, restored.text
        back = client.get("/api/agents/developer").json()
        assert EDIT_MARKER in back["system_prompt"]
        assert back["max_turns"] == 77
        assert _status(client, "developer")["status"] == "skipped_user_modified"
        assert _status(client, "tutor") == tutor_before

        missing = client.post("/api/agents/developer/pack-content-backups/nope/restore")
        assert missing.status_code == 404


def test_restore_sticks_when_keep_customizations_is_off():
    """REQ-450-009: Restore is not undone by its own status refresh when keep-customizations is off.

    The next full sync still force-resets (the CARD-449 global contract), which the dialog states.
    """
    app = create_app()
    with TestClient(app) as client:
        off = client.put("/api/settings/platform-pack-keep-customizations", json={"enabled": False})
        assert off.status_code == 200 and off.json()["enabled"] is False
        body = client.get("/api/agents/developer").json()
        body["system_prompt"] = body["system_prompt"] + "\n" + EDIT_MARKER
        assert client.put("/api/agents/developer", json=body).status_code == 200

        assert client.post("/api/agents/developer/accept-platform-seed").status_code == 200
        backups = client.get("/api/agents/developer/pack-content-backups").json()["backups"]
        newest = next(b for b in backups if EDIT_MARKER in b["system_prompt"])

        restored = client.post(f"/api/agents/developer/pack-content-backups/{newest['id']}/restore")
        assert restored.status_code == 200, restored.text
        assert restored.json()["sync"]["results"][0]["status"] == "skipped_user_modified"
        assert EDIT_MARKER in client.get("/api/agents/developer").json()["system_prompt"]
        assert _status(client, "developer")["status"] == "skipped_user_modified"
        after = client.get("/api/agents/developer/pack-content-backups").json()["backups"]
        assert len(after) == len(backups), "restore refresh must not write a force-reset backup"

        client.post("/api/platform-packs/sync")
        assert EDIT_MARKER not in client.get("/api/agents/developer").json()["system_prompt"]


def test_reset_rejects_non_platform_agent():
    """REQ-450-003: Reset only exists for platform agents."""
    app = create_app()
    with TestClient(app) as client:
        res = client.post("/api/agents/not-a-platform-pack/accept-platform-seed")
        assert res.status_code == 400
