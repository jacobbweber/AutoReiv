"""CARD-688 Operator Contract: Auto-scoped agents (`*`) and session-mounted skill tools."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.domain.gateway.models import ToolCall
from src.web.app import create_app


def _seed_skill_folder(data_dir: Path, skill_id: str, tool_name: str) -> None:
    sdir = data_dir / "skills" / skill_id
    (sdir / "tools").mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nname: {skill_id}\ndescription: Dynamic skill {skill_id}.\n---\nCall `{tool_name}`.\n",
        encoding="utf-8",
    )
    (sdir / "tools" / f"{tool_name}.py").write_text(
        '"""Compute bonus."""\n\nRISK = "read_only"\n\ndef run(base: int, bonus: int = 5) -> dict:\n    return {"total": base + bonus}\n',
        encoding="utf-8",
    )


def test_auto_scoped_agent_contract(tmp_path: Path, monkeypatch):
    from src.application.skills.session_skills import clear_session_skill_activations
    from src.infrastructure.content import store as store_mod
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    wiki_dir = data_dir / "wiki"
    skills_dir = data_dir / "skills"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki_dir))

    state_store = SQLiteStateStore(db_path=str(data_dir / "autoreiv.db"))
    state_store.initialize_db()
    app = create_app(state_store=state_store, wiki_path=str(wiki_dir))
    try:
        with TestClient(app) as client:
            # 1. Switch autoreiv to Auto-discover all skills ("*") via PUT /api/agents/autoreiv
            ag_res = client.get("/api/agents/autoreiv")
            assert ag_res.status_code == 200
            ag_data = ag_res.json()

            put_res = client.put(
                "/api/agents/autoreiv",
                json={
                    "name": ag_data["name"],
                    "description": ag_data["description"],
                    "system_prompt": ag_data["system_prompt"],
                    "allowed_skill": ["*"],
                },
            )
            assert put_res.status_code == 200

            # 2. Drop a brand-new Agora skill folder AFTER the agent was saved with ["*"]
            _seed_skill_folder(data_dir, "dynamic-bonus", "calc_bonus")
            toggle_res = client.post(
                "/api/capabilities/skills/dynamic-bonus/tools/calc_bonus/toggle",
                json={"enabled": True},
            )
            assert toggle_res.status_code == 200
            assert toggle_res.json()["enabled"] is True

            # 3. Verify GET /api/agents/autoreiv automatically includes calc_bonus in allowed_tools
            # without ever adding "dynamic-bonus" to allowed_skill
            updated_ag = client.get("/api/agents/autoreiv").json()
            assert updated_ag["allowed_skill"] == ["*"]
            assert "calc_bonus" in updated_ag["allowed_tools"]

            # 4. Negative assertion: before skill_view("dynamic-bonus") in session, calc_bonus is NOT in active_tools
            kernel = app.state.kernel
            profile = app.state.registry.get_agent("autoreiv")
            before_names = {t.name for t in kernel._resolve_active_tools(profile, session_id="contract-sess", history=[])}
            assert "calc_bonus" not in before_names
            assert "skill_view" in before_names

            # 5. Calling skill_view("dynamic-bonus") in session "contract-sess" activates the skill and mounts calc_bonus
            import asyncio

            view_res = asyncio.run(
                app.state.tool_reg.execute(
                    ToolCall(id="tc-view", name="skill_view", arguments={"skill_id": "dynamic-bonus"}),
                    profile,
                    session_id="contract-sess",
                )
            )
            assert view_res.success is True
            assert "calc_bonus" in (view_res.output.get("activated_tools") or [])

            after_names = {t.name for t in kernel._resolve_active_tools(profile, session_id="contract-sess", history=[])}
            assert "calc_bonus" in after_names

            exec_res = asyncio.run(
                app.state.tool_reg.execute(
                    ToolCall(id="tc-run", name="calc_bonus", arguments={"base": 12, "bonus": 8}),
                    profile,
                    session_id="contract-sess",
                    offered=after_names,
                )
            )
            assert exec_res.success is True
            assert exec_res.output == {"total": 20}
    finally:
        clear_session_skill_activations()
        store_mod.reset_store()
