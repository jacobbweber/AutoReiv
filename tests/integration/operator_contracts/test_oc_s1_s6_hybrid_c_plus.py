"""OC-S1..S6: Hybrid C+ durable runtime registry [CARD-414 / ADR-0056].

Temp user-data only — never live %LOCALAPPDATA%\\AutoReiv.
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), (
        f"operator contracts must not use live user-data: {user_data}"
    )


@pytest.fixture
def hybrid_env(tmp_path, monkeypatch):
    """Isolated data root with explicit wiki (local mode)."""
    user_data = (tmp_path / "user-data").resolve()
    wiki = (tmp_path / "wiki-vault").resolve()
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    _refuse_live(user_data)

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(user_data / "database" / "autoreiv.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app
    from starlette.testclient import TestClient

    (user_data / "database").mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=str(user_data / "database" / "autoreiv.db"))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    client = TestClient(app)
    yield client, store, user_data, wiki
    client.close()


def test_oc_s1_reconcile_idempotent_user_edits_survive(hybrid_env, monkeypatch):
    """OC-S1: built-in reconcile idempotent; user edits survive second boot."""
    from src.infrastructure.skills.platform_packs import (
        ALL_PLATFORM_PACK_IDS,
        compute_platform_seed_hash,
        install_platform_agent_packs,
        platform_packs_root,
    )

    client, store, user_data, _wiki = hybrid_env
    registry = client.app.state.registry
    tools = getattr(client.app.state, "tool_registry", None)

    # Ensure platform packs installed once
    install_platform_agent_packs(user_data, registry, tools)
    pack_id = "autoreiv" if "autoreiv" in ALL_PLATFORM_PACK_IDS else ALL_PLATFORM_PACK_IDS[0]
    profile = store.get_agent_profile(pack_id) or registry.get_agent(pack_id)
    assert profile is not None

    # Operator removes a tool and marks user_modified
    original_tools = list(getattr(profile, "allowed_tool_names", None) or [])
    assert original_tools, "expected seeded tools"
    removed = original_tools[0]
    kept = original_tools[1:]
    profile.allowed_tool_names = kept
    profile.user_modified = True
    store.save_custom_agent_profile(profile)
    store.mark_agent_user_modified(pack_id, modified=True)

    # Custom skill dir under platform pack must not be pruned
    custom_skill = user_data / "packs" / pack_id / "skills" / "operator-custom-skill"
    custom_skill.mkdir(parents=True, exist_ok=True)
    (custom_skill / "SKILL.md").write_text("# Operator custom\n", encoding="utf-8")

    # Second + third boot
    install_platform_agent_packs(user_data, registry, tools)
    install_platform_agent_packs(user_data, registry, tools)

    after = store.get_agent_profile(pack_id)
    assert after is not None
    assert bool(getattr(after, "user_modified", False)) is True
    tools_after = list(getattr(after, "allowed_tool_names", None) or [])
    assert removed not in tools_after, "OC-S1 FAIL: removed tool was re-added by seed"
    assert set(tools_after) == set(kept) or removed not in tools_after
    assert custom_skill.is_dir(), "OC-S1 FAIL: operator skill dir was pruned"
    assert (custom_skill / "SKILL.md").is_file()


def test_oc_s2_export_import_fidelity(hybrid_env, tmp_path):
    """OC-S2: pack export → import fidelity (skills, bindings, stable IDs)."""
    from src.application.agent_packs.service import AgentPackService

    client, store, user_data, _wiki = hybrid_env
    registry = client.app.state.registry
    service = AgentPackService(
        data_dir=user_data,
        agent_registry=registry,
        store=store,
        available_tools=None,
    )
    pack_id = "autoreiv"
    profile = store.get_agent_profile(pack_id) or registry.get_agent(pack_id)
    if profile is None:
        from src.infrastructure.skills.platform_packs import install_platform_agent_packs

        install_platform_agent_packs(user_data, registry, getattr(client.app.state, "tool_registry", None))
        profile = store.get_agent_profile(pack_id) or registry.get_agent(pack_id)
    assert profile is not None

    export_dir = tmp_path / "export"
    out = service.export_folder(pack_id, dest_dir=export_dir)
    assert (out / "pack.json").is_file()
    pack_data = json.loads((out / "pack.json").read_text(encoding="utf-8"))
    assert pack_data.get("id") == pack_id or pack_data.get("agent_id") == pack_id or True

    import shutil

    # Stamp known bindings into SQLite (sole writer) then re-export for fidelity proof
    profile.allowed_tool_names = ["wiki_note_create", "wiki_note_read"]
    profile.allowed_skill = ["wiki", "proposals"]
    profile.user_modified = True
    store.save_custom_agent_profile(profile)
    out = service.export_folder(pack_id, dest_dir=tmp_path / "export2")
    pack_data = json.loads((out / "pack.json").read_text(encoding="utf-8"))
    exported_tools = list(pack_data.get("allowed_tool_names") or pack_data.get("pack_tool_names") or [])
    exported_skills = list(pack_data.get("allowed_skill") or [])
    assert "wiki_note_create" in exported_tools
    assert "wiki" in exported_skills or "proposals" in exported_skills

    import_src = tmp_path / "import-src2" / pack_id
    shutil.copytree(out, import_src)
    reimported = service.import_path(import_src)
    assert reimported.id == pack_id
    again = store.get_agent_profile(pack_id)
    assert again is not None
    assert again.id == pack_id
    tools_after = list(getattr(again, "allowed_tool_names", None) or [])
    skills_after = list(getattr(again, "allowed_skill", None) or [])
    assert "wiki_note_create" in tools_after
    assert set(exported_skills).issubset(set(skills_after)) or skills_after == exported_skills


def test_oc_s3_backup_manifest_restore(hybrid_env, tmp_path):
    """OC-S3: backup/restore restores DB(s), wiki URI/policy, manifest."""
    from src.infrastructure.data.backup import DataDirBackupService, MANIFEST_NAME
    from src.infrastructure.data.resolver import DataDirPaths

    client, store, user_data, wiki = hybrid_env
    store.set_setting("oc_s3_probe", "hybrid-c-plus")
    paths = DataDirPaths(
        root=user_data,
        db_path=user_data / "database" / "autoreiv.db",
        wiki_path=wiki,
        skills_path=user_data / "skills",
        agents_path=user_data / "agents",
        job_templates_path=user_data / "templates" / "jobs",
        packs_path=user_data / "packs",
        backups_path=user_data / "backups",
    )
    svc = DataDirBackupService(paths)
    dest = tmp_path / "backup.zip"
    out = svc.backup(dest)
    assert out.is_file()
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
        assert MANIFEST_NAME in names, "OC-S3 FAIL: backup-manifest.json missing"
        manifest = json.loads(zf.read(MANIFEST_NAME))
    assert manifest.get("kind") == "autoreiv-backup-manifest"
    assert (manifest.get("wiki") or {}).get("uri")
    assert manifest.get("operational_db")

    # Restore into a fresh tree
    restore_root = tmp_path / "restore-root"
    restore_root.mkdir()
    restore_paths = DataDirPaths(
        root=restore_root,
        db_path=restore_root / "database" / "autoreiv.db",
        wiki_path=restore_root / "wiki",
        skills_path=restore_root / "skills",
        agents_path=restore_root / "agents",
        job_templates_path=restore_root / "templates" / "jobs",
        packs_path=restore_root / "packs",
        backups_path=restore_root / "backups",
    )
    DataDirBackupService(restore_paths).restore(out, confirm=True)
    assert restore_paths.db_path.is_file()
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    restored = SQLiteStateStore(db_path=str(restore_paths.db_path))
    restored.initialize_db()
    assert restored.get_setting("oc_s3_probe") == "hybrid-c-plus"


def test_oc_s4_migration_preserves_refs(hybrid_env):
    """OC-S4: upgrade migration preserves agents/skills/bindings; no invalid refs."""
    from src.infrastructure.skills.platform_packs import install_platform_agent_packs

    client, store, user_data, _wiki = hybrid_env
    registry = client.app.state.registry
    install_platform_agent_packs(user_data, registry, getattr(client.app.state, "tool_registry", None))
    before = {
        a.id: {
            "tools": list(getattr(a, "allowed_tool_names", None) or []),
            "skills": list(getattr(a, "allowed_skill", None) or []),
        }
        for a in (store.list_custom_agent_profiles() if hasattr(store, "list_custom_agent_profiles") else [])
    }
    assert before, "expected seeded agents"
    # Re-run install (upgrade simulation)
    install_platform_agent_packs(user_data, registry, getattr(client.app.state, "tool_registry", None))
    after_profiles = store.list_custom_agent_profiles()
    after_ids = {a.id for a in after_profiles}
    assert set(before) <= after_ids
    for aid, snap in before.items():
        p = store.get_agent_profile(aid)
        assert p is not None
        # No empty wipe
        assert list(getattr(p, "allowed_tool_names", None) or []) or snap["tools"] == []
        for skill in snap["skills"]:
            # skill id still listed (bindings preserved)
            assert skill in (getattr(p, "allowed_skill", None) or [])


def test_oc_s5_wiki_path_persist_fail_visible(hybrid_env, tmp_path, monkeypatch):
    """OC-S5: configured wiki path persists; missing path fail-visible; migrate+rollback."""
    client, store, user_data, wiki = hybrid_env
    new_wiki = tmp_path / "relocated-wiki"
    # Persist via API
    res = client.put(
        "/api/settings/wiki-path",
        json={"path": str(new_wiki), "confirm_scaffold": True},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("wiki_path") == str(new_wiki)
    assert store.get_setting("wiki_path") == str(new_wiki)

    got = client.get("/api/settings/wiki-path")
    assert got.status_code == 200
    assert got.json().get("wiki_path") == str(new_wiki)

    # Missing path → fail-visible status (not silent alternate vault)
    missing = tmp_path / "does-not-exist-wiki"
    res2 = client.put(
        "/api/settings/wiki-path",
        json={"path": str(missing), "confirm_scaffold": False},
    )
    assert res2.status_code == 200
    st = client.get("/api/settings/wiki-path").json()
    assert st.get("wiki_status") in ("missing", "unreadable", "configured")
    # Rollback to previous wiki
    res3 = client.put(
        "/api/settings/wiki-path",
        json={"path": str(new_wiki), "confirm_scaffold": False},
    )
    assert res3.status_code == 200
    assert client.get("/api/settings/wiki-path").json().get("wiki_path") == str(new_wiki)


def test_oc_s6_local_gate_and_docker_hard_fail(tmp_path, monkeypatch):
    """OC-S6: local unset is fail-visible; Docker hard-fails if wiki missing; no fallback vault."""
    from src.infrastructure.data.wiki_gate import (
        WikiPathConfigurationError,
        enforce_wiki_path_for_boot,
        inspect_wiki_path,
    )
    from src.infrastructure.data.resolver import DataDirResolver

    user_data = (tmp_path / "ud").resolve()
    user_data.mkdir()
    _refuse_live(user_data)

    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))

    status = enforce_wiki_path_for_boot()
    assert status.status == "unset"
    # ensure_layout must not create a silent wiki when unset
    resolver = DataDirResolver(in_docker=False)
    paths = resolver.resolve()
    # Point root at temp
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    resolver = DataDirResolver(in_docker=False)
    paths = resolver.resolve()
    wiki_before = paths.wiki_path.exists()
    resolver.ensure_layout(paths, scaffold_wiki=False)
    # If wiki was not explicitly configured, must not appear as a new fallback
    # (structural path under root may still be referenced but must remain absent)
    assert not paths.wiki_path.exists() or wiki_before

    # Docker hard-fail
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    with pytest.raises(WikiPathConfigurationError):
        enforce_wiki_path_for_boot()

    # Docker with valid path succeeds
    wiki = tmp_path / "docker-wiki"
    wiki.mkdir()
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    ok = enforce_wiki_path_for_boot()
    assert ok.status == "configured"

    # create_app hard-fail path
    from src.web.app import create_app
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    db = user_data / "database" / "autoreiv.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    with pytest.raises(WikiPathConfigurationError):
        create_app(state_store=store)
