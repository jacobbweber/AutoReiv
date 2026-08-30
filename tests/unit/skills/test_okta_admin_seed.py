"""Okta admin skill pack scaffold (copy-if-missing seed) [REQ-BUILD-015] [REQ-BUILD-016]."""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.data.resolver import bootstrap_data_dir
from src.infrastructure.skills.seed import (
    OKTA_ADMIN_PACK_ID,
    bundled_okta_admin_skill_md,
    seed_bundled_skill_packs,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_TOOLS = ("okta_list_users", "okta_reset_or_unlock", "okta_assign_app")


def _clear_okta_env(monkeypatch) -> None:
    for key in list(os.environ):
        if key.upper().startswith("OKTA"):
            monkeypatch.delenv(key, raising=False)


def test_bundled_okta_admin_template_exists():
    path = bundled_okta_admin_skill_md()
    assert path.is_file()
    expected = REPO_ROOT / "src" / "infrastructure" / "skills" / "seeds" / "okta-admin" / "SKILL.md"
    assert path.resolve() == expected.resolve()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: okta-admin" in text
    assert "description:" in text
    assert "No live Okta API" in text
    assert "When to use" in text
    assert "never log" in text.lower() or "Never log API tokens" in text
    assert "not wired" in text.lower()


def test_bundled_okta_admin_declares_json_tool_stubs():
    loaded = DynamicSkillLoader.load_skill_from_markdown(str(bundled_okta_admin_skill_md()))
    assert loaded is not None
    names = {t.name for t in loaded["tools"]}
    for required in REQUIRED_TOOLS:
        assert required in names
    for tool in loaded["tools"]:
        assert tool.name
        assert isinstance(tool.parameters, dict)
        assert "okta" in tool.name
        assert "not wired" in (tool.description or "").lower() or "stub" in (tool.description or "").lower()


def test_bootstrap_seeds_okta_admin_into_empty_skills_dir(tmp_path, monkeypatch):
    _clear_okta_env(monkeypatch)
    data = tmp_path / "data"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "isolated.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    paths = bootstrap_data_dir(checkout_root=tmp_path / "checkout", migrate=False)
    dest = paths.skills_path / OKTA_ADMIN_PACK_ID / "SKILL.md"
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == bundled_okta_admin_skill_md().read_text(encoding="utf-8")
    catalog = UserSkillCatalog(skills_dir=paths.skills_path)
    ids = {m.id for m in catalog.list_manifests()}
    assert OKTA_ADMIN_PACK_ID in ids
    opened = catalog.read_pack(OKTA_ADMIN_PACK_ID)
    assert opened["success"] is True
    assert opened["manifest"]["name"] == "okta-admin"
    assert opened["manifest"]["description"]
    assert "When to use" in opened["instructions"]
    tool_names = {t["name"] for t in opened["tools"]}
    for required in REQUIRED_TOOLS:
        assert required in tool_names


def test_second_boot_does_not_overwrite_modified_skill_md(tmp_path, monkeypatch):
    _clear_okta_env(monkeypatch)
    skills = tmp_path / "skills"
    seed_bundled_skill_packs(skills)
    dest = skills / OKTA_ADMIN_PACK_ID / "SKILL.md"
    marker = "user-edit-token-do-not-clobber"
    dest.write_text(dest.read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8")
    seed_bundled_skill_packs(skills)
    data = tmp_path / "data2"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "isolated2.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki2"))
    # Second seed into the same user skills dir must keep the edit.
    seed_bundled_skill_packs(skills)
    text = dest.read_text(encoding="utf-8")
    assert marker in text
    bundled = bundled_okta_admin_skill_md().read_text(encoding="utf-8")
    assert marker not in bundled

    # Full bootstrap into a dest that already has a modified pack also leaves it.
    dest2 = data / "skills" / OKTA_ADMIN_PACK_ID / "SKILL.md"
    dest2.parent.mkdir(parents=True, exist_ok=True)
    dest2.write_text(f"---\nname: okta-admin\ndescription: user edited\n---\n\n{marker}\n", encoding="utf-8")
    paths = bootstrap_data_dir(checkout_root=tmp_path / "checkout2", migrate=False)
    assert marker in paths.skills_path.joinpath(OKTA_ADMIN_PACK_ID, "SKILL.md").read_text(encoding="utf-8")
    assert "user edited" in paths.skills_path.joinpath(OKTA_ADMIN_PACK_ID, "SKILL.md").read_text(encoding="utf-8")


def test_okta_stub_tools_are_playbook_handlers_not_http(tmp_path, monkeypatch):
    _clear_okta_env(monkeypatch)
    skills = tmp_path / "skills"
    seed_bundled_skill_packs(skills)
    catalog = UserSkillCatalog(skills_dir=skills)
    loaded = catalog.skill_view(OKTA_ADMIN_PACK_ID)
    assert loaded["success"] is True
    handler = catalog._playbook_tool_handler("okta_list_users", "okta-admin")
    result = handler(query="ada@example.test")
    assert result["success"] is False
    assert "not an executable Python builtin" in result["error"]
    assert "okta_list_users" in result["error"]


def test_src_has_no_okta_sdk_and_env_example_has_no_okta_keys():
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert not re.search(r"^\s*OKTA", env_example, re.MULTILINE)
    assert "OKTA_API" not in env_example
    forbidden = re.compile(r"^(?:from okta(?:[\.\s]| import)|import okta)\b")
    hits = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if forbidden.match(line.strip()):
                hits.append(f"{path}: {line.strip()}")
    assert hits == []


def test_skills_studio_can_open_seeded_okta_admin(tmp_path, monkeypatch):
    _clear_okta_env(monkeypatch)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    client = TestClient(create_app())
    listed = client.get("/api/skills/user-packs")
    assert listed.status_code == 200
    ids = {p["id"] for p in listed.json()["packs"]}
    assert OKTA_ADMIN_PACK_ID in ids
    opened = client.get(f"/api/skills/user-packs/{OKTA_ADMIN_PACK_ID}")
    assert opened.status_code == 200
    body = opened.json()
    assert body["manifest"]["name"] == "okta-admin"
    assert body["manifest"]["description"]
    assert "When to use" in body["instructions"]
    names = {t["name"] for t in body["tools"]}
    for required in REQUIRED_TOOLS:
        assert required in names
