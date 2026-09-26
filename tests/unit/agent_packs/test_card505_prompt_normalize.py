"""CARD-505: platform prompts compare as normalized text (REQ-505-001..008).

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py). A "restart" is a
second create_app on the same database and data folder. Platform updates use a temp copy of
platform-packs passed as checkout_root. Jacob's real AppData is never touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_pack_promotion import (
    PLATFORM_LOCK_MIGRATION_SETTING,
    PLATFORM_PACK_SYNC_REPORT_SETTING,
    PLATFORM_SHIPPED_PROMPT_SETTING,
    list_pack_content_backups,
    promote_platform_packs,
    prompt_content_hash,
)
from src.web.app import create_app

REPO = Path(__file__).resolve().parents[3]
UPDATE_LINE = "C505 PLATFORM UPDATE LINE."
REAL_EDIT = "Always follow SOLID and DRY principles."
BASELINE_DONE_KEY = "platform_prompt_baseline_normalized"


@pytest.fixture
def boot():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)

    def _boot():
        store = SQLiteStateStore(db_path=db)
        store.initialize_db()
        app = create_app(state_store=store, wiki_path=str(wiki))
        return TestClient(app), store, app

    return _boot


def _data_root() -> Path:
    return Path(os.environ["AUTOREIV_DATA_DIR"])


def _seed_prompt(pack_id: str = "autoreiv") -> str:
    return json.loads((REPO / "platform-packs" / pack_id / "pack.json").read_text(encoding="utf-8"))["system_prompt"]


def _raw_hash(text: str) -> str:
    """Old (pre-CARD-505) baseline format: sha256 of the exact seed bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sync_entry(store, pack_id="autoreiv"):
    report = store.get_setting(PLATFORM_PACK_SYNC_REPORT_SETTING) or {}
    return next((r for r in report.get("results") or [] if r.get("pack_id") == pack_id), {})


def _is_locked(store, pack_id="autoreiv") -> bool:
    prof = store.get_agent_profile(pack_id)
    ov = store.get_agent_override(pack_id)
    return bool(getattr(prof, "user_modified", False)) or bool(ov is not None and getattr(ov, "user_modified", False))


def _legacy_state(store, registry, *, stored: str, old_seed: str, locked: bool) -> None:
    """Put the install in a pre-CARD-505 state: raw-bytes baseline, given stored prompt and lock."""
    from src.application.agent_packs.skill_list import customization_from_profile

    baselines = dict(store.get_setting(PLATFORM_SHIPPED_PROMPT_SETTING) or {})
    baselines["autoreiv"] = _raw_hash(old_seed)
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, baselines)
    store.set_setting(BASELINE_DONE_KEY, None)
    prof = store.get_agent_profile("autoreiv")
    prof.system_prompt = stored
    prof.user_modified = locked
    store.save_custom_agent_profile(prof)
    if locked:
        ov = customization_from_profile(registry.get_agent("autoreiv"), "autoreiv")
        ov.system_prompt = stored
        ov.user_modified = True
        store.save_agent_override(ov)
    elif store.get_agent_override("autoreiv") is not None:
        ov = store.get_agent_override("autoreiv")
        ov.system_prompt = stored
        ov.user_modified = False
        store.save_agent_override(ov)
    store.mark_agent_user_modified("autoreiv", modified=locked)


def _platform_update(tmp_path: Path) -> Path:
    """Temp checkout whose AutoReiv seed prompt gained one line (keeps a trailing newline on purpose)."""
    root = tmp_path / "checkout"
    shutil.copytree(REPO / "platform-packs", root / "platform-packs")
    pj = root / "platform-packs" / "autoreiv" / "pack.json"
    data = json.loads(pj.read_text(encoding="utf-8"))
    data["system_prompt"] = data["system_prompt"].rstrip() + "\n" + UPDATE_LINE + "\n"
    pj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return root


def _promote(app, checkout_root=None):
    return promote_platform_packs(
        _data_root(), app.state.registry, getattr(app.state, "tool_reg", None),
        checkout_root=checkout_root, pack_ids=["autoreiv"],
    )


def _studio_scalar_save(client, agent_id="autoreiv"):
    """What Agent Studio sends for a Max-Turns-only save (prompt trimmed, forge.js .trim())."""
    body = client.get(f"/api/agents/{agent_id}").json()
    agent = body.get("agent") or body
    payload = {**agent, "max_turns": int(agent.get("max_turns") or 50) + 1, "system_prompt": (agent["system_prompt"] or "").strip()}
    res = client.put(f"/api/agents/{agent_id}", json=payload)
    assert res.status_code == 200, res.text


def test_prompt_hash_ignores_outer_whitespace_and_line_endings():
    """REQ-505-001 / D1."""
    from src.infrastructure.skills.platform_pack_promotion import normalize_prompt

    assert normalize_prompt("  abc\r\n") == "abc"
    assert normalize_prompt("a\r\nb\rc") == "a\nb\nc"
    assert prompt_content_hash("abc\n") == prompt_content_hash("abc") == prompt_content_hash("abc\r\n")
    assert prompt_content_hash("a\n  b") != prompt_content_hash("a\nb")  # inner spacing is content


def test_fresh_install_second_start_does_not_skip_prompt(boot):
    """REQ-505-002."""
    boot()
    _c2, store2, _a2 = boot()
    entry = _sync_entry(store2)
    assert entry.get("status") not in {"promoted_partial", "skipped_user_modified"}, entry
    assert "system_prompt" not in (entry.get("skipped_fields") or [])


@pytest.mark.parametrize("stored_variant", ["stripped", "with_newline"])
def test_max_turns_only_studio_save_never_locks(boot, stored_variant):
    """REQ-505-003 / D5: fresh install (stripped) and Jacob's install (prompt kept its newline)."""
    client, store, app = boot()
    seed = _seed_prompt().strip()
    stored = seed if stored_variant == "stripped" else seed + "\n"
    _legacy_state(store, app.state.registry, stored=stored, old_seed=seed + "\n", locked=False)
    _studio_scalar_save(client)
    assert not _is_locked(store)


@pytest.mark.parametrize("stored_variant", ["stripped", "with_newline"])
def test_platform_prompt_update_reaches_autoreiv(boot, tmp_path, stored_variant):
    """REQ-505-004 / REQ-505-007: the update lands and is stored normalized."""
    _client, store, app = boot()
    seed = _seed_prompt().strip()
    stored = seed if stored_variant == "stripped" else seed + "\n"
    _legacy_state(store, app.state.registry, stored=stored, old_seed=seed + "\n", locked=False)
    _promote(app, checkout_root=_platform_update(tmp_path))
    prompt = app.state.registry.get_agent("autoreiv").system_prompt
    assert UPDATE_LINE in prompt
    assert prompt == prompt.strip()
    assert "system_prompt" not in (_sync_entry(store).get("skipped_fields") or [])


def test_whitespace_only_false_lock_is_repaired_with_backup(boot, tmp_path):
    """REQ-505-005 / D4: locked by a scalar save before this fix; unlocked with a backup, then updates land."""
    _client, store, app = boot()
    seed = _seed_prompt().strip()
    _legacy_state(store, app.state.registry, stored=seed, old_seed=seed + "\n", locked=True)
    _promote(app)
    assert not _is_locked(store)
    reasons = [b.get("reason") for b in list_pack_content_backups(store, "autoreiv")]
    assert "card505_whitespace_unlock" in reasons
    mig = {r["pack_id"]: r for r in (store.get_setting(PLATFORM_LOCK_MIGRATION_SETTING) or {}).get("results") or []}
    assert mig["autoreiv"]["action"] == "unlocked"
    assert "spacing" in mig["autoreiv"]["reason"]
    _promote(app, checkout_root=_platform_update(tmp_path))
    assert UPDATE_LINE in app.state.registry.get_agent("autoreiv").system_prompt


def test_false_lock_against_an_older_shipped_prompt_is_repaired(boot):
    """REQ-505-005: stored = the previous shipped text (stripped), the platform has moved on since."""
    _client, store, app = boot()
    seed = _seed_prompt().strip()
    old = seed + "\nOLD C505 LINE."
    _legacy_state(store, app.state.registry, stored=old, old_seed=old + "\n", locked=True)
    _promote(app)
    assert not _is_locked(store)
    prompt = app.state.registry.get_agent("autoreiv").system_prompt
    assert "OLD C505 LINE." not in prompt
    assert prompt == seed


def test_real_prompt_edit_stays_locked_and_kept(boot, tmp_path):
    """REQ-505-006 control (must be green before and after the fix)."""
    _client, store, app = boot()
    seed = _seed_prompt().strip()
    edited = seed + "\n" + REAL_EDIT
    _legacy_state(store, app.state.registry, stored=edited, old_seed=_seed_prompt(), locked=True)
    _promote(app, checkout_root=_platform_update(tmp_path))
    assert _is_locked(store)
    prompt = app.state.registry.get_agent("autoreiv").system_prompt
    assert REAL_EDIT in prompt
    assert UPDATE_LINE not in prompt
    assert _sync_entry(store).get("status") == "skipped_user_modified"
    assert "card505_whitespace_unlock" not in [b.get("reason") for b in list_pack_content_backups(store, "autoreiv")]


def test_reset_to_platform_defaults_then_scalar_save_does_not_relock(boot):
    """REQ-505-007: Reset no longer re-arms the false lock."""
    client, store, app = boot()
    seed = _seed_prompt().strip()
    _legacy_state(store, app.state.registry, stored=seed + "\n" + REAL_EDIT, old_seed=seed + "\n", locked=True)
    assert client.post("/api/agents/autoreiv/accept-platform-seed").status_code == 200
    assert not _is_locked(store)
    _studio_scalar_save(client)
    assert not _is_locked(store)


def test_every_platform_seed_prompt_is_trimmed():
    """REQ-505-008 / D6 seed hygiene."""
    bad = []
    for pj in sorted((REPO / "platform-packs").glob("*/pack.json")):
        prompt = json.loads(pj.read_text(encoding="utf-8")).get("system_prompt") or ""
        if prompt != prompt.replace("\r\n", "\n").replace("\r", "\n").strip():
            bad.append(pj.parent.name)
    assert bad == []
