"""CARD-118: okta-admin is not a shipped product seed."""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.infrastructure.data.resolver import bootstrap_data_dir
from src.infrastructure.skills.seed import (
    BUNDLED_PACK_IDS,
    RETIRED_OKTA_ADMIN_PACK_ID,
    bundled_seed_root,
    seed_bundled_skill_packs,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _clear_okta_env(monkeypatch) -> None:
    for key in list(os.environ):
        if key.upper().startswith("OKTA"):
            monkeypatch.delenv(key, raising=False)


def test_okta_admin_is_not_a_bundled_product_seed():
    assert RETIRED_OKTA_ADMIN_PACK_ID not in BUNDLED_PACK_IDS
    assert BUNDLED_PACK_IDS == ()
    seed_path = bundled_seed_root() / RETIRED_OKTA_ADMIN_PACK_ID / "SKILL.md"
    assert not seed_path.exists()
    expected = REPO_ROOT / "src" / "infrastructure" / "skills" / "seeds" / "okta-admin"
    assert not expected.exists()


def test_bootstrap_does_not_seed_okta_admin(tmp_path, monkeypatch):
    _clear_okta_env(monkeypatch)
    data = tmp_path / "data"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "isolated.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    paths = bootstrap_data_dir(checkout_root=tmp_path / "checkout", migrate=False)
    dest = paths.skills_path / RETIRED_OKTA_ADMIN_PACK_ID / "SKILL.md"
    assert not dest.exists()
    seed_bundled_skill_packs(paths.skills_path)
    assert not dest.exists()


def test_seed_bundled_does_not_clobber_existing_user_runbook(tmp_path):
    skills = tmp_path / "skills"
    dest = skills / "user-runbook" / "SKILL.md"
    dest.parent.mkdir(parents=True)
    marker = "user-edit-token-do-not-clobber"
    dest.write_text(f"---\nname: user-runbook\ndescription: user edited\n---\n\n{marker}\n", encoding="utf-8")
    seed_bundled_skill_packs(skills)
    assert marker in dest.read_text(encoding="utf-8")
    assert not (skills / RETIRED_OKTA_ADMIN_PACK_ID / "SKILL.md").exists()


def test_user_packs_api_does_not_list_okta_admin_when_absent(tmp_path, monkeypatch):
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
    assert RETIRED_OKTA_ADMIN_PACK_ID not in ids
    opened = client.get(f"/api/skills/user-packs/{RETIRED_OKTA_ADMIN_PACK_ID}")
    assert opened.status_code == 404


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
