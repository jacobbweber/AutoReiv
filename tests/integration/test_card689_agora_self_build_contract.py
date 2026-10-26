"""CARD-689 Operator Contract: Inline Agora skill folder authoring & risk-tiered auto-enable."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import create_app


def test_agora_self_build_contract(tmp_path: Path, monkeypatch):
    from src.application.skills.session_skills import clear_session_skill_activations
    from src.infrastructure.content import store as store_mod
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    wiki_dir = data_dir / "wiki"
    skills_dir = data_dir / "skills"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "autoreiv.db"

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki_dir))
    store_mod.configure(data_dir)

    state_store = SQLiteStateStore(db_path=str(db_path))
    state_store.initialize_db()
    app = create_app(state_store=state_store, wiki_path=str(wiki_dir))

    try:
        with TestClient(app) as client:
            # 1. Write SKILL.md via PUT /api/capabilities/skills/self-built-math/file
            md_res = client.put(
                "/api/capabilities/skills/self-built-math/file",
                json={
                    "path": "SKILL.md",
                    "content": "---\nname: Self Built Math\ndescription: Custom math helpers.\n---\n# Self Built Math\n",
                },
            )
            assert md_res.status_code == 200, md_res.text
            assert md_res.json()["saved"] is True

            # 2. Write a pure read_only tool -> passes ToolCheckService and auto-enables + mounts
            pure_res = client.put(
                "/api/capabilities/skills/self-built-math/file",
                json={
                    "path": "tools/calc_hypotenuse_sq.py",
                    "content": (
                        '"""Return a^2 + b^2."""\n'
                        'RISK = "read_only"\n'
                        "def run(a: int = 3, b: int = 4) -> dict:\n"
                        '    return {"hypotenuse_sq": int(a) * int(a) + int(b) * int(b)}\n'
                    ),
                },
            )
            assert pure_res.status_code == 200, pure_res.text
            pure_body = pure_res.json()
            assert pure_body["saved"] is True
            assert pure_body["auto_enabled"] is True
            assert pure_body["enabled"] is True
            assert pure_body["approval"] == "enabled"
            assert pure_body["mounted"] is True
            assert "calc_hypotenuse_sq" in app.state.tool_reg

            # 3. Negative assertion: write a tool that uses file/network access -> saved disabled, NOT auto-enabled
            flagged_res = client.put(
                "/api/capabilities/skills/self-built-math/file",
                json={
                    "path": "tools/write_audit_log.py",
                    "content": (
                        '"""Write an audit line to disk."""\n'
                        "from pathlib import Path\n\n"
                        "def run(line: str = 'ok') -> dict:\n"
                        '    return {"written": line}\n'
                    ),
                },
            )
            assert flagged_res.status_code == 200, flagged_res.text
            flagged_body = flagged_res.json()
            assert flagged_body["saved"] is True
            assert flagged_body["auto_enabled"] is False
            assert flagged_body["enabled"] is False
            assert flagged_body["approval"] == "disabled"
            assert flagged_body["mounted"] is False
            assert "files" in flagged_body["access"]
            assert "write_audit_log" not in app.state.tool_reg

            # 4. CARD-743: When authored from an agent turn (session_id in tool context), a non-read_only
            # colocated tool creates an inline `enable_skill_tool` pending approval that enables + mounts on Approve.
            import asyncio

            from src.application.kernel.tool_registry import _tool_context
            from src.application.skills.agora_authoring import save_skill_file
            from src.application.skills.session_skills import get_session_activated_skills

            sess = state_store.create_session(agent_id="autoreiv", title="Inline Approval Session")
            token = _tool_context.set({"agent_id": "autoreiv", "session_id": sess.id})
            try:
                agent_res = asyncio.run(
                    save_skill_file(
                        store_mod.get_store(),
                        "self-built-math",
                        "tools/write_audit_log.py",
                        (
                            '"""Write an audit line to disk."""\n'
                            "from pathlib import Path\n\n"
                            "def run(line: str = 'ok') -> dict:\n"
                            '    return {"written": line}\n'
                        ),
                        tool_registry=app.state.tool_reg,
                        state_store=state_store,
                    )
                )
            finally:
                _tool_context.reset(token)

            assert agent_res["saved"] is True
            assert agent_res["enabled"] is False
            approval_id = agent_res.get("approval_id")
            assert approval_id, f"Expected approval_id when saving non-read_only tool in session, got: {agent_res}"

            pending = client.get(f"/api/approvals/pending?session_id={sess.id}").json()
            assert any(p["id"] == approval_id and p["tool_name"] == "enable_skill_tool" for p in pending)

            decide_res = client.post(
                f"/api/approvals/{approval_id}/decision",
                json={"decision": "APPROVED", "session_id": sess.id},
            )
            assert decide_res.status_code == 200, decide_res.text
            decide_body = decide_res.json()
            assert decide_body["status"] == "approved"
            assert decide_body["resume_chat"] is False
            assert "write_audit_log" in app.state.tool_reg
            assert "self-built-math" in get_session_activated_skills(session_id=sess.id)
    finally:
        clear_session_skill_activations()
        store_mod.reset_store()

