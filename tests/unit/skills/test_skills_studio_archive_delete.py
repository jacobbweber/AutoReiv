"""User runbook archive + confirm-delete [REQ-DATA-015 - REQ-DATA-018]. CARD-118: editor is Agent Studio."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.application.skills.user_catalog import ARCHIVE_DIRNAME
from src.infrastructure.skills.seed import seed_bundled_skill_packs
from src.web.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]

USER_PACK_MD = """---
name: test-live-pong
description: Leftover user pack that delete must remove.
---

Playbook body. Distinctive-delete-token.
"""

OTHER_PACK_MD = """---
name: keep-me
description: Stays live unless archived.
---

Keep this pack.
"""


def _skills_root() -> Path:
    import os

    return Path(os.environ["AUTOREIV_DATA_DIR"]) / "skills"


def _write_pack(slug: str, content: str) -> Path:
    pack_dir = _skills_root() / slug
    pack_dir.mkdir(parents=True, exist_ok=True)
    skill = pack_dir / "SKILL.md"
    skill.write_text(content, encoding="utf-8")
    return skill


def _client() -> TestClient:
    skills = _skills_root()
    skills.mkdir(parents=True, exist_ok=True)
    seed_bundled_skill_packs(skills)
    _write_pack("test-live-pong", USER_PACK_MD)
    _write_pack("keep-me", OTHER_PACK_MD)
    return TestClient(create_app())


def _ids(response) -> set[str]:
    return {p["id"] for p in response.json()["packs"]}


def test_archive_hides_from_live_list_and_unarchive_restores():
    client = _client()
    live = client.get("/api/skills/user-packs")
    assert live.status_code == 200
    assert "test-live-pong" in _ids(live)
    assert "okta-admin" not in _ids(live)

    archived = client.post("/api/skills/user-packs/test-live-pong/archive", json={"confirm": True})
    assert archived.status_code == 200
    assert archived.json().get("archived") is True

    live2 = client.get("/api/skills/user-packs")
    assert "test-live-pong" not in _ids(live2)
    assert "keep-me" in _ids(live2)
    assert not (_skills_root() / "test-live-pong").exists()
    assert (_skills_root() / ARCHIVE_DIRNAME / "test-live-pong" / "SKILL.md").is_file()

    listed_arch = client.get("/api/skills/archived-packs")
    assert listed_arch.status_code == 200
    assert "test-live-pong" in _ids(listed_arch)

    restored = client.post("/api/skills/user-packs/test-live-pong/unarchive")
    assert restored.status_code == 200
    live3 = client.get("/api/skills/user-packs")
    assert "test-live-pong" in _ids(live3)
    assert (_skills_root() / "test-live-pong" / "SKILL.md").is_file()
    opened = client.get("/api/skills/user-packs/test-live-pong")
    assert opened.status_code == 200
    assert "Distinctive-delete-token" in opened.json()["instructions"]


def test_delete_without_confirm_is_400_and_files_remain():
    client = _client()
    skill = _skills_root() / "test-live-pong" / "SKILL.md"
    assert skill.is_file()
    res = client.delete("/api/skills/user-packs/test-live-pong")
    assert res.status_code == 400
    assert skill.is_file()
    res2 = client.delete("/api/skills/user-packs/test-live-pong", params={"confirm": False})
    assert res2.status_code == 400
    assert skill.is_file()


def test_delete_user_pack_removes_directory():
    client = _client()
    live_dir = _skills_root() / "test-live-pong"
    assert live_dir.is_dir()
    res = client.delete("/api/skills/user-packs/test-live-pong", params={"confirm": True})
    assert res.status_code == 200
    body = res.json()
    assert body.get("deleted") is True
    assert not live_dir.exists()
    assert not (_skills_root() / ARCHIVE_DIRNAME / "test-live-pong").exists()
    listed = client.get("/api/skills/user-packs")
    assert "test-live-pong" not in _ids(listed)
    assert "keep-me" in _ids(listed)


def test_delete_archived_user_pack_removes_archive_dir():
    client = _client()
    assert client.post("/api/skills/user-packs/test-live-pong/archive", json={"confirm": True}).status_code == 200
    arch = _skills_root() / ARCHIVE_DIRNAME / "test-live-pong"
    assert arch.is_dir()
    res = client.delete("/api/skills/user-packs/test-live-pong", params={"confirm": True})
    assert res.status_code == 200
    assert not arch.exists()
    assert not (_skills_root() / "test-live-pong").exists()


def test_delete_missing_okta_admin_is_not_a_shipped_seed():
    client = _client()
    dest = _skills_root() / "okta-admin" / "SKILL.md"
    assert not dest.exists()
    missing = client.delete("/api/skills/user-packs/okta-admin", params={"confirm": True})
    assert missing.status_code == 404
    assert not dest.exists()
    seeds = REPO_ROOT / "src" / "infrastructure" / "skills" / "seeds"
    assert seeds.is_dir()
    assert not (seeds / "okta-admin").exists()


def test_delete_rejects_path_traversal_outside_skills_jail():
    client = _client()
    skills = _skills_root()
    outside = skills.parent / "escape-pack"
    outside.mkdir(parents=True, exist_ok=True)
    marker = outside / "SKILL.md"
    marker.write_text("do-not-delete", encoding="utf-8")

    for pack_id in ("../", "../escape-pack", "..%2Fescape-pack", "foo/../../escape-pack"):
        res = client.delete(f"/api/skills/user-packs/{pack_id}", params={"confirm": True})
        assert res.status_code in (400, 404, 422), (pack_id, res.status_code, res.text)
        assert res.status_code != 200

    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == "do-not-delete"
    assert skills.is_dir()


def test_agent_studio_runbook_editor_has_archive_delete_not_builtin_python_packs():
    js = (REPO_ROOT / "src" / "web" / "static" / "modules" / "studios" / "forge.js").read_text(encoding="utf-8")
    html = (REPO_ROOT / "src" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    view_start = html.find('id="view-agents"')
    view_end = html.find("</section>", view_start)
    studio_html = html[view_start:view_end] if view_start != -1 else html
    combined = js + "\n" + studio_html
    assert "archive" in combined.lower()
    assert "unarchive" in combined.lower()
    assert "delete" in combined.lower()
    assert "studioRunbookArchiveBtn" in combined
    assert "studioRunbookDeleteBtn" in combined
    assert "Skills Studio" not in html
    assert "Agent Forge" not in html
    for builtin in ("WikiTools", "execute_code", "handoff"):
        assert builtin not in studio_html
    assert "src/application/skills" not in studio_html
