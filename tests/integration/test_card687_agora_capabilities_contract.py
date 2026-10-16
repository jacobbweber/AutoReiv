"""CARD-687 operator contract: Agora skill folder capabilities tree, file reader, and tool toggle."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.infrastructure.content import store as store_mod
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def agora_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    wiki_dir = data_dir / "wiki"
    skills_dir = data_dir / "skills"
    wiki_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki_dir))

    # Seed an Agora skill folder with SKILL.md, references/guide.md, and tools/calc_checksum.py
    skill_dir = skills_dir / "checksum-kit"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "tools").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Checksum Kit\ndescription: Compute checksums and read format guides.\n---\n"
        "# Checksum Kit\nUse `calc_checksum` and read `references/guide.md`.\n",
        encoding="utf-8",
    )
    (skill_dir / "references" / "guide.md").write_text(
        "# Checksum Guide\nAlways normalize whitespace before hashing.\n",
        encoding="utf-8",
    )
    (skill_dir / "tools" / "calc_checksum.py").write_text(
        '"""Compute a simple sum-of-bytes checksum for text."""\n'
        'RISK = "read_only"\n\n'
        'def run(text: str, modulo: int = 65535) -> dict:\n'
        '    return {"checksum": sum(text.encode("utf-8")) % int(modulo), "length": len(text)}\n',
        encoding="utf-8",
    )

    # Tick checksum-kit on a custom agent so we can test execution through the registry
    agents_dir = data_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "auditor.md").write_text(
        "---\nname: Auditor\ndescription: Checksum auditor.\nskills:\n- checksum-kit\n---\nYou are Auditor.\n",
        encoding="utf-8",
    )

    db_path = str(data_dir / "autoreiv.db")
    state_store = SQLiteStateStore(db_path=db_path)
    state_store.initialize_db()
    app = create_app(state_store=state_store, wiki_path=str(wiki_dir))
    with TestClient(app) as client:
        yield client, app, data_dir
    store_mod.reset_store()


def test_agora_capabilities_tree_file_read_and_tool_toggle_contract(agora_env):
    client, app, _data_dir = agora_env

    # 1. GET /api/capabilities/tree returns the Agora folder structure for checksum-kit
    res = client.get("/api/capabilities/tree")
    assert res.status_code == 200, res.text
    tree = res.json()
    skills = {s["id"]: s for s in tree["skills"]}
    assert "checksum-kit" in skills
    kit = skills["checksum-kit"]
    assert kit["name"] == "Checksum Kit"
    assert kit["references"] == [{"name": "guide.md", "path": "references/guide.md"}]
    assert len(kit["colocated_tools"]) == 1
    tool_entry = kit["colocated_tools"][0]
    assert tool_entry["name"] == "calc_checksum"
    assert tool_entry["description"] == "Compute a simple sum-of-bytes checksum for text."
    assert tool_entry["parameters"]["required"] == ["text"]
    assert tool_entry["parameters"]["properties"]["modulo"]["default"] == 65535
    assert tool_entry["enabled"] is False
    assert tool_entry["approval"] == "disabled"

    # 2. Negative assertion: before enabling, calc_checksum is NOT mounted in ScopedToolRegistry
    assert "calc_checksum" not in app.state.tool_reg

    # 3. GET /api/capabilities/skills/checksum-kit/file reads SKILL.md, references/guide.md, and tools/calc_checksum.py
    ref_res = client.get("/api/capabilities/skills/checksum-kit/file", params={"path": "references/guide.md"})
    assert ref_res.status_code == 200
    assert "Always normalize whitespace" in ref_res.json()["content"]

    code_res = client.get("/api/capabilities/skills/checksum-kit/file", params={"path": "tools/calc_checksum.py"})
    assert code_res.status_code == 200
    assert "def run(text: str" in code_res.json()["content"]

    # Negative assertion: path traversal on file read returns 400
    bad_res = client.get("/api/capabilities/skills/checksum-kit/file", params={"path": "../agents/auditor.md"})
    assert bad_res.status_code == 400

    # 4. Enable calc_checksum via POST /api/capabilities/skills/checksum-kit/tools/calc_checksum/toggle
    toggle_on = client.post(
        "/api/capabilities/skills/checksum-kit/tools/calc_checksum/toggle",
        json={"enabled": True},
    )
    assert toggle_on.status_code == 200, toggle_on.text
    body_on = toggle_on.json()
    assert body_on["enabled"] is True
    assert body_on["approval"] == "enabled"
    assert body_on["mounted"] is True
    assert "calc_checksum" in app.state.tool_reg

    # 4b. Execute calc_checksum for the 'auditor' agent (who has 'checksum-kit' ticked)
    import asyncio

    from src.domain.gateway.models import ToolCall

    auditor = app.state.registry.get_agent("auditor")
    assert auditor is not None
    exec_res = asyncio.run(
        app.state.tool_reg.execute(
            ToolCall(id="tc1", name="calc_checksum", arguments={"text": "ABC", "modulo": 1000}),
            auditor,
        )
    )
    assert exec_res.success is True, exec_res.error
    assert exec_res.output == {"checksum": sum(b"ABC") % 1000, "length": 3}

    # 5. Disable calc_checksum -> unmounted from registry
    toggle_off = client.post(
        "/api/capabilities/skills/checksum-kit/tools/calc_checksum/toggle",
        json={"enabled": False},
    )
    assert toggle_off.status_code == 200, toggle_off.text
    assert toggle_off.json()["enabled"] is False
    assert toggle_off.json()["mounted"] is False
    assert "calc_checksum" not in app.state.tool_reg
