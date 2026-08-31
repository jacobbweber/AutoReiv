"""Skills Studio API and nav [REQ-DATA-012 - REQ-DATA-014]."""

from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import create_app

SAMPLE_SKILL_MD = """---
name: weekly-review
description: SOP for rolling weekly notes into the next week.
---

# Weekly Review

Follow this playbook. Distinctive-body-token.

```json
{
  "name": "list_open_loops",
  "description": "List open loops from the weekly note",
  "parameters": {
    "type": "object",
    "properties": {
      "week_str": {"type": "string"}
    }
  }
}
```
"""

PLAYBOOK_ONLY_MD = """---
name: inbox-triage
description: SOP with no JSON tools.
---

Triage the inbox. Playbook-only-token.
"""

REPO_ROOT = Path(__file__).resolve().parents[3]


def _skills_root():
    import os

    return Path(os.environ["AUTOREIV_DATA_DIR"]) / "skills"


def _write_pack(slug, content):
    pack_dir = _skills_root() / slug
    pack_dir.mkdir(parents=True, exist_ok=True)
    skill = pack_dir / "SKILL.md"
    skill.write_text(content, encoding="utf-8")
    return skill


def test_index_html_has_one_agent_studio_and_no_skills_studio_nav():
    html = (REPO_ROOT / "src" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Skills Studio" not in html
    assert 'id="tab-skills"' not in html
    assert 'id="view-skills"' not in html
    assert "Agent Studio" in html
    assert 'id="tab-agents"' in html
    assert "Agent Forge" not in html
    assert "Workflow Studio" not in html
    assert "studioRunbookBody" in html
    assert "studioNewRunbookBtn" in html
    assert "Skills (runbooks)" in html
    page = TestClient(create_app()).get("/").text
    assert "Skills Studio" not in page
    assert "Agent Studio" in page
    assert "Agent Forge" not in page
    assert 'id="tab-skills"' not in page


def test_list_and_get_user_packs_from_temp_skills_dir():
    _write_pack("weekly-review", SAMPLE_SKILL_MD)
    _write_pack("inbox-triage", PLAYBOOK_ONLY_MD)
    client = TestClient(create_app())

    listed = client.get("/api/skills/user-packs")
    assert listed.status_code == 200
    packs = listed.json()["packs"]
    ids = {p["id"] for p in packs}
    assert "weekly-review" in ids
    assert "inbox-triage" in ids
    weekly = next(p for p in packs if p["id"] == "weekly-review")
    assert weekly["name"] == "weekly-review"
    assert weekly["description"].startswith("SOP for rolling")
    assert "instructions" not in weekly
    assert "tools" not in weekly
    assert "Distinctive-body-token" not in str(weekly)

    opened = client.get("/api/skills/user-packs/weekly-review")
    assert opened.status_code == 200
    body = opened.json()
    assert body["manifest"]["id"] == "weekly-review"
    assert "Distinctive-body-token" in body["instructions"]
    assert any(t["name"] == "list_open_loops" for t in body["tools"])
    assert any("List open loops" in (t.get("description") or "") for t in body["tools"])

    playbook = client.get("/api/skills/user-packs/inbox-triage")
    assert playbook.status_code == 200
    assert playbook.json()["tools"] == []
    assert "Playbook-only-token" in playbook.json()["instructions"]

    missing = client.get("/api/skills/user-packs/no-such-pack")
    assert missing.status_code == 404


def test_put_writes_skill_md_on_disk_and_creates_pack():
    client = TestClient(create_app())
    created = client.put(
        "/api/skills/user-packs/new-playbook",
        json={
            "name": "new-playbook",
            "description": "Created from Agent Studio.",
            "instructions": "Do the thing. Unique-save-token.",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["manifest"]["name"] == "new-playbook"
    skill_path = _skills_root() / "new-playbook" / "SKILL.md"
    assert skill_path.is_file()
    disk = skill_path.read_text(encoding="utf-8")
    assert "Unique-save-token" in disk
    assert "Created from Agent Studio." in disk
    agents_skills = REPO_ROOT / ".agents" / "skills" / "new-playbook" / "SKILL.md"
    assert not agents_skills.exists()

    updated = client.put(
        "/api/skills/user-packs/new-playbook",
        json={
            "name": "new-playbook",
            "description": "Updated description.",
            "instructions": "Updated body. Second-save-token.",
        },
    )
    assert updated.status_code == 200
    disk2 = skill_path.read_text(encoding="utf-8")
    assert "Second-save-token" in disk2
    assert "Updated description." in disk2
    assert "Unique-save-token" not in disk2


def test_put_rejects_path_traversal_out_of_skills_tree():
    from src.application.skills.user_catalog import PackJailError, UserSkillCatalog

    catalog = UserSkillCatalog(skills_dir=_skills_root())
    for pack_id in ("../escape", "foo/../../escape", r"..\escape", "/tmp/evil"):
        try:
            catalog.resolve_skill_md(pack_id)
        except PackJailError:
            continue
        raise AssertionError(f"expected PackJailError for {pack_id!r}")

    client = TestClient(create_app())
    payload = {
        "name": "evil",
        "description": "should not write",
        "instructions": "nope",
    }
    for pack_id in ("../escape", "..%2Fescape", "foo/../../escape"):
        res = client.put(f"/api/skills/user-packs/{pack_id}", json=payload)
        assert res.status_code in (400, 404, 422), (pack_id, res.status_code, res.text)
        assert res.status_code != 200
    escaped = REPO_ROOT / "escape" / "SKILL.md"
    assert not escaped.exists()
    assert not (_skills_root().parent / "escape" / "SKILL.md").exists()


def test_post_creates_empty_pack_and_conflicts_on_duplicate():
    client = TestClient(create_app())
    first = client.post(
        "/api/skills/user-packs",
        json={"id": "blank-pack", "name": "blank-pack", "description": "Empty playbook."},
    )
    assert first.status_code == 200
    skill_path = _skills_root() / "blank-pack" / "SKILL.md"
    assert skill_path.is_file()
    assert "Empty playbook." in skill_path.read_text(encoding="utf-8")
    assert first.json()["tools"] == []

    dup = client.post(
        "/api/skills/user-packs",
        json={"id": "blank-pack", "name": "blank-pack", "description": "Empty playbook."},
    )
    assert dup.status_code == 409
