"""CARD-701 Guard & Operator Contract Test: Live ApprovalMode in Settings UI with read_only and state_change tool effect tiers.

Verifies:
1. `resolve_approval_mode` resolves `DB setting > AUTOREIV_APPROVAL_MODE env > default ("balanced")`
   and normalizes `"strict"`, `"balanced"`, `"hands_off"` (with `"autonomous"` alias).
2. `classify_tool_effect` classifies tools into `"read_only"`, `"state_change"`, and `"destructive"`.
3. `save_skill_file` enforces the 3-mode effect matrix live without server restart:
   - `strict`: both `read_only` and `state_change` tools save disabled (`auto_enabled=False`).
   - `balanced`: `read_only` tools auto-enable and mount (`auto_enabled=True`), while `state_change`
     and `destructive` tools save disabled (`auto_enabled=False`).
   - `hands_off`: both `read_only` and `state_change` tools auto-enable and mount (`auto_enabled=True`),
     while `destructive` tools still save disabled (`auto_enabled=False`).
4. `GET/PUT /api/settings/approval-mode` and `POST /api/settings/matrix` persist the live mode and
   `ToolPolicyGate.apply_to_tool_result` respects live `hands_off` vs `strict`/`balanced`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.kernel.reply_limits import bind_store
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.approval_mode import (
    classify_tool_effect,
    resolve_approval_mode,
     resolve_approval_mode_info,
    save_approval_mode,
)
from src.application.safety.tool_policy_gate import (
    ToolPolicyDecision,
    ToolPolicyGate,
    ToolPolicyVerdict,
)
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.skills.agora_authoring import save_skill_file
from src.application.skills.session_skills import clear_session_skill_activations
from src.domain.gateway.models import ToolCall
from src.infrastructure.content import store as content_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.capabilities import router as capabilities_router
from src.web.routers.settings import router as settings_router

pytestmark = pytest.mark.guard


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AUTOREIV_APPROVAL_MODE", raising=False)
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    db_store = SQLiteStateStore(db_path=str(data_dir / "autoreiv.db"))
    db_store.initialize_db()
    bind_store(db_store)
    yield data_dir, db_store
    bind_store(None)
    clear_session_skill_activations()
    content_store.reset_store()


def test_approval_mode_resolution_precedence_and_effect_tiers(
    _isolated_env: tuple[Path, SQLiteStateStore],
    monkeypatch: pytest.MonkeyPatch,
):
    _, db_store = _isolated_env

    # 1. Default is balanced
    assert resolve_approval_mode(db_store) == "balanced"
    info_default = resolve_approval_mode_info(db_store)
    assert info_default["approval_mode"] == "balanced"
    assert info_default["source"] == "default"

    # 2. Env overrides default
    monkeypatch.setenv("AUTOREIV_APPROVAL_MODE", "strict")
    assert resolve_approval_mode(db_store) == "strict"
    assert resolve_approval_mode_info(db_store)["source"] == "env"

    monkeypatch.setenv("AUTOREIV_APPROVAL_MODE", "autonomous")
    assert resolve_approval_mode(db_store) == "hands_off"

    # 3. DB setting overrides env
    save_approval_mode(db_store, "balanced")
    assert resolve_approval_mode(db_store) == "balanced"
    assert resolve_approval_mode_info(db_store)["source"] == "setting"

    # 4. Clearing DB setting falls back to env
    save_approval_mode(db_store, "")
    assert resolve_approval_mode(db_store) == "hands_off"

    # 5. Tool effect classification
    assert classify_tool_effect(risk="read_only", access=[]) == "read_only"
    assert classify_tool_effect(risk="read_only", access=["network"]) == "state_change"
    assert classify_tool_effect(risk="write", access=[]) == "state_change"
    assert classify_tool_effect(risk="network", access=["network"]) == "state_change"
    assert classify_tool_effect(risk="destructive", access=[]) == "destructive"


async def test_save_skill_file_enforces_live_approval_mode_and_effect_tiers(
    _isolated_env: tuple[Path, SQLiteStateStore],
):
    _, db_store = _isolated_env
    st = content_store.get_store()
    reg = ScopedToolRegistry()

    pure_code = (
        '"""Pure unit converter."""\n'
        'RISK = "read_only"\n'
        "def run(meters: int = 10) -> dict:\n"
        '    return {"feet": round(meters * 3.28084, 2)}\n'
    )
    state_change_code = (
        '"""Network URL formatter with urllib import."""\n'
        "import urllib.request\n\n"
        "def run(host: str = 'example.com') -> dict:\n"
        '    return {"endpoint": f"https://{host}/health"}\n'
    )
    destructive_code = (
        '"""Destructive operation."""\n'
        'RISK = "destructive"\n'
        "def run(target: str = 'temp') -> dict:\n"
        '    return {"wiped": target}\n'
    )

    # 1. STRICT mode: even pure read_only tool is saved disabled
    save_approval_mode(db_store, "strict")
    strict_res = await save_skill_file(
        st,
        "strict-skill",
        "tools/meters_to_feet.py",
        pure_code,
        tool_registry=reg,
        state_store=db_store,
    )
    assert strict_res["saved"] is True
    assert strict_res["effect"] == "read_only"
    assert strict_res["approval_mode"] == "strict"
    assert strict_res["auto_enabled"] is False
    assert strict_res["enabled"] is False
    assert "meters_to_feet" not in reg

    # 2. Switch live to BALANCED mode without restart:
    #    - read_only tool auto-enables and mounts
    #    - state_change tool saves disabled
    save_approval_mode(db_store, "balanced")
    bal_read = await save_skill_file(
        st,
        "balanced-skill",
        "tools/meters_to_feet.py",
        pure_code,
        tool_registry=reg,
        state_store=db_store,
    )
    assert bal_read["effect"] == "read_only"
    assert bal_read["approval_mode"] == "balanced"
    assert bal_read["auto_enabled"] is True
    assert bal_read["enabled"] is True
    assert "meters_to_feet" in reg

    bal_state = await save_skill_file(
        st,
        "balanced-skill",
        "tools/format_endpoint.py",
        state_change_code,
        tool_registry=reg,
        state_store=db_store,
    )
    assert bal_state["effect"] == "state_change"
    assert bal_state["approval_mode"] == "balanced"
    assert bal_state["auto_enabled"] is False
    assert bal_state["enabled"] is False
    assert "format_endpoint" not in reg

    # 3. Switch live to HANDS_OFF mode without restart:
    #    - state_change tool auto-enables and mounts
    #    - destructive tool still saves disabled
    save_approval_mode(db_store, "hands_off")
    ho_state = await save_skill_file(
        st,
        "balanced-skill",
        "tools/format_endpoint.py",
        state_change_code,
        tool_registry=reg,
        state_store=db_store,
    )
    assert ho_state["effect"] == "state_change"
    assert ho_state["approval_mode"] == "hands_off"
    assert ho_state["auto_enabled"] is True
    assert ho_state["enabled"] is True
    assert "format_endpoint" in reg

    ho_destr = await save_skill_file(
        st,
        "balanced-skill",
        "tools/wipe_target.py",
        destructive_code,
        tool_registry=reg,
        state_store=db_store,
    )
    assert ho_destr["effect"] == "destructive"
    assert ho_destr["approval_mode"] == "hands_off"
    assert ho_destr["auto_enabled"] is False
    assert ho_destr["enabled"] is False
    assert "wipe_target" not in reg


def test_settings_approval_mode_api_and_tool_policy_gate(
    _isolated_env: tuple[Path, SQLiteStateStore],
):
    _, db_store = _isolated_env
    reg = ScopedToolRegistry()
    gateway = MagicMock()
    gateway.default_provider_id = "ollama"
    gateway.default_model_id = "default"
    hw_calc = HardwareFitCalculator()
    agent_reg = MagicMock()
    settings_svc = SettingsService(
        state_store=db_store,
        gateway=gateway,
        agent_registry=agent_reg,
        hardware_calc=hw_calc,
    )

    app = FastAPI()
    app.state.store = db_store
    app.state.gateway = gateway
    app.state.hw_calc = hw_calc
    app.state.registry = agent_reg
    app.state.settings_service = settings_svc
    app.state.tool_registry = reg
    app.include_router(settings_router)
    app.include_router(capabilities_router)

    client = TestClient(app)

    # 1. Initial GET /api/settings/approval-mode returns balanced
    res0 = client.get("/api/settings/approval-mode")
    assert res0.status_code == 200
    assert res0.json()["approval_mode"] == "balanced"

    # 2. Switch to strict via PUT /api/settings/approval-mode
    res_strict = client.put("/api/settings/approval-mode", json={"approval_mode": "strict"})
    assert res_strict.status_code == 200
    assert res_strict.json()["approval_mode"] == "strict"

    # Authoring a pure read_only tool via PUT /api/capabilities/skills/{id}/file under strict mode saves disabled
    pure_code = '"""Pure tool."""\nRISK = "read_only"\ndef run(n: int = 2) -> dict:\n    return {"n": n * 2}\n'
    cap_strict = client.put(
        "/api/capabilities/skills/test-cap/file",
        json={"path": "tools/double_num.py", "content": pure_code},
    )
    assert cap_strict.status_code == 200
    assert cap_strict.json()["auto_enabled"] is False
    assert cap_strict.json()["approval_mode"] == "strict"

    # 3. Switch to hands_off via POST /api/settings/matrix
    res_mat = client.post(
        "/api/settings/matrix",
        json={"default_model": "default", "approval_mode": "hands_off"},
    )
    assert res_mat.status_code == 200
    assert res_mat.json()["matrix"]["approval_mode"] == "hands_off"

    # ToolPolicyGate REQUIRE_CONFIRM parks in balanced/strict when turn mode is 'ask', but runs through in hands_off
    gate = ToolPolicyGate(db_store)
    hitl = MagicMock()
    hitl.park_tool_call.return_value = "appr-123"
    tc = ToolCall(id="tc-1", name="wiki_note_create", arguments={"title": "Test"})
    decision = ToolPolicyDecision(
        verdict=ToolPolicyVerdict.REQUIRE_CONFIRM,
        tool_name="wiki_note_create",
        reason="write tool",
        policy_source="default_high_risk",
    )

    # In hands_off, apply_to_tool_result returns None (executes without parking)
    assert (
        gate.apply_to_tool_result(
            decision,
            tc,
            session_id="s1",
            agent=MagicMock(id="autoreiv"),
            hitl_engine=hitl,
            approval_mode="ask",
        )
        is None
    )

    # Switch back to balanced -> REQUIRE_CONFIRM parks for approval
    client.put("/api/settings/approval-mode", json={"approval_mode": "balanced"})
    parked = gate.apply_to_tool_result(
        decision,
        tc,
        session_id="s1",
        agent=MagicMock(id="autoreiv"),
        hitl_engine=hitl,
        approval_mode="ask",
    )
    assert parked is not None
    assert parked.error == "approval_required:appr-123"


def test_settings_approval_mode_ui_elements_and_module_exist():
    repo_root = Path(__file__).resolve().parents[3]
    index_html = (repo_root / "src" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="settingsApprovalModeCard"' in index_html
    assert 'id="approvalModeSelect"' in index_html
    assert 'id="approvalModeSaveBtn"' in index_html
    assert 'id="approvalModeStatus"' in index_html

    js_mod = (
        repo_root / "src" / "web" / "static" / "modules" / "studios" / "settings_approval_mode.js"
    ).read_text(encoding="utf-8")
    assert "/api/settings/approval-mode" in js_mod
    assert "export function setupApprovalMode" in js_mod

