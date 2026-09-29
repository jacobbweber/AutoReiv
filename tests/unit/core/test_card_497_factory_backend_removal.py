"""CARD-497 tests 7-17: Factory backend removed; Studio, gaps, packs and upgrade stay whole [REQ-497-005..015]."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
# A made-up "old shipped" build-agent-pack SKILL.md; its hash is patched in as shipped (CARD-568: no fixture copy).
OLD_SHIPPED_SKILL = "---\nname: proposals\n---\n\n# Proposals\n\nTools are trained in the Factory.\n"



DELETED_MODULES = (
    "src.application.agent_training_factory",
    "src.web.routers.agent_training_factory",
    "src.application.skills.factory_dispatch_tools",
    "src.application.orchestration.capability_graph",
    "src.application.orchestration.jit_synthesizer",
    "src.application.orchestration.tool_synthesizer",
    "src.application.orchestration.verification_battery",
    "src.application.orchestration.hyperv_tool_builders",
    "src.application.skills.sandbox_runner",
    "src.infrastructure.memory.repositories.factory_packets",
    "src.domain.orchestration.factory_packets",
)


def _module_path(mod: str) -> Path:
    base = ROOT / Path(*mod.split("."))
    return base if base.is_dir() else base.with_suffix(".py")


def _env(tmp_path, monkeypatch, name="data"):
    data_dir = tmp_path / name
    db_path = tmp_path / f"{name}.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    return data_dir, db_path


def _app(db_path):
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    return create_app(state_store=SQLiteStateStore(db_path=str(db_path)))


# 7 -------------------------------------------------------------------------
def test_7_app_state_has_no_factory_and_lifespan_starts_no_factory_task(shared_app):
    app = shared_app  # read-only app.state check [CARD-560]
    assert not hasattr(app.state, "factory_orchestrator")
    assert not hasattr(app.state, "factory_repo")
    src = (ROOT / "src/web/app.py").read_text(encoding="utf-8")
    assert "factory_orchestrator" not in src
    assert "FactoryOrchestrator" not in src
    assert "factory_task" not in src


# 8 -------------------------------------------------------------------------
def test_8_busy_detector_has_no_factory_checker():
    from src.application.system.busy import BusyDetector, make_store_busy_detector

    assert "factory_job_checker" not in inspect.signature(BusyDetector.__init__).parameters
    assert list(inspect.signature(make_store_busy_detector).parameters) == ["store"]
    busy, reason = BusyDetector(
        chat_stream_checker=lambda: True, routine_checker=lambda: True, studio_job_checker=lambda: True
    ).is_busy()
    assert busy and "Factory" not in reason and "training" not in reason

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE jobs (id TEXT, status TEXT)")
    conn.execute("INSERT INTO jobs VALUES ('j1', 'queued')")

    class _Store:
        _mem_conn = conn

        def _get_connection(self):
            return conn

    det = make_store_busy_detector(_Store())
    det._chat_stream_checker = lambda: False
    busy, reason = det.is_busy()
    assert busy and reason == "running Studio job"


# 9 -------------------------------------------------------------------------
def test_9_stranded_training_gaps_reset_to_pending_on_startup(tmp_path, monkeypatch):
    from src.infrastructure.memory.repositories.capability_gaps import (
        GAP_DISMISSED,
        GAP_PENDING,
        GAP_TRAINED,
        GAP_TRAINING,
        CapabilityGapRepository,
    )

    _, db = _env(tmp_path, monkeypatch)
    app = _app(db)
    repo: CapabilityGapRepository = app.state.capability_gap_repo
    ids = {}
    for status in (GAP_TRAINING, GAP_TRAINED, GAP_DISMISSED, GAP_PENDING):
        gap = repo.create_gap(agent_id="autoreiv", turn_text=f"t-{status}", identified_capability=f"cap {status}")
        repo.update_gap_status(gap.id, status)
        ids[status] = gap.id

    app2 = _app(db)
    repo2 = app2.state.capability_gap_repo
    assert repo2.get_gap(ids[GAP_TRAINING]).status == GAP_PENDING
    assert repo2.get_gap(ids[GAP_TRAINED]).status == GAP_TRAINED
    assert repo2.get_gap(ids[GAP_DISMISSED]).status == GAP_DISMISSED
    assert repo2.get_gap(ids[GAP_PENDING]).status == GAP_PENDING
    assert repo2.reset_stranded_training_gaps() == 0

    app3 = _app(db)
    assert app3.state.capability_gap_repo.get_gap(ids[GAP_TRAINING]).status == GAP_PENDING


# 10 ------------------------------------------------------------------------
def test_10_registry_has_inspect_agent_not_launch_factory_training(shared_app):
    app = shared_app  # read-only registry check [CARD-560]
    names = {t.name for t in app.state.tool_registry.list_tools()}
    assert "inspect_agent" in names
    assert "launch_factory_training" not in names


@pytest.fixture
def inspect_tools():
    from types import SimpleNamespace

    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.skills.agent_inspect_tools import AgentInspectTools

    profile = SimpleNamespace(id="test-agent", name="Test Agent", description="A test agent", allowed_skill=["filesystem"])
    registry = SimpleNamespace(get_agent=lambda ag: profile if ag == "test-agent" else None)
    tool_reg = ScopedToolRegistry()
    tools = AgentInspectTools(agent_registry=registry)
    tools.register_tools(tool_reg)
    return tools, tool_reg


@pytest.mark.asyncio
async def test_10b_inspect_agent_success(inspect_tools):
    tools, reg = inspect_tools
    assert "inspect_agent" in {t.name for t in reg.list_tools()}
    res = await tools.inspect_agent(agent_id="test-agent")
    assert res["success"] is True
    assert res["name"] == "Test Agent"
    assert res["skills"] == ["filesystem"]
    assert isinstance(res["tools"], list)


@pytest.mark.asyncio
async def test_10c_inspect_agent_not_found(inspect_tools):
    tools, _ = inspect_tools
    res = await tools.inspect_agent(agent_id="nonexistent-agent")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


# 11 ------------------------------------------------------------------------


# 12 ------------------------------------------------------------------------
def test_12_agent_authoring_is_intake_and_no_shipped_text_mentions_factory_training():
    from tests.unit.agent_skills.catalog import load_platform_manifest

    manifest = load_platform_manifest("autoreiv")
    skill = next(s for s in manifest.skills if s.id == "agent-authoring")
    assert set(skill.tools) == {"inspect_agent", "lookup_agents", "handoff_to_agent", "propose_skill"}
    assert "launch_factory_training" not in [t for s in manifest.skills for t in s.tools]

    offenders = []
    for base in (ROOT / "platform-packs", ROOT / "src/infrastructure/skills/seeds"):
        for path in base.rglob("*"):
            if path.suffix.lower() not in (".md", ".json"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in ("launch_factory_training", "Factory Studio", "trained in the Factory"):
                if needle in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {needle}")
    assert not offenders, offenders


# 12b -----------------------------------------------------------------------
def _authoring_skill_md():
    import yaml

    text = (ROOT / "platform/skills/agent-authoring/SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front), body


def test_12b_agent_authoring_is_found_for_teach_requests():
    """Live retest: 'Teach AutoReiv to ...' never opened agent-authoring (the index lists names, skill_view takes ids)."""
    from tests.unit.agent_skills.catalog import load_platform_manifest

    front, _ = _authoring_skill_md()
    assert "agent-authoring" in load_platform_manifest("autoreiv").allowed_skill
    for desc in (front["description"],):
        low = desc.lower()
        for needle in ("teach", "new capability", "learn to", 'skill_view(skill_id="agent-authoring")'):
            assert needle in low, (needle, desc)


def test_12c_agent_authoring_names_the_exact_handoff_arguments_and_keeps_the_flow():
    """Live retest: the model called handoff_to_agent(agent_id=, task=) and got a TypeError."""
    from src.application.skills.orchestration_tools import OrchestrationTools

    _, body = _authoring_skill_md()
    assert 'handoff_to_agent(target_agent_id="developer", task_directive=' in body
    assert "agent_id=" not in body.replace("target_agent_id=", "")
    params = inspect.signature(OrchestrationTools.handoff_to_agent).parameters
    assert "target_agent_id" in params and "task_directive" in params
    # Flow order: inspect, ask, show the brief, get a yes, then hand off.
    steps = [body.index(s) for s in ("inspect_agent", "Ask what is missing", "Show the brief", "yes", "handoff_to_agent(")]
    assert steps == sorted(steps), steps
    assert "tell the operator" in body.lower() and "fail" in body.lower()


def test_12d_autoreiv_prompt_routes_teach_requests_to_agent_authoring_via_skill_view():
    """Live retests 2-3: skill_view needs skill_id=. CARD-578 removed activate_skill, so the prompt no longer names it."""
    from tests.unit.agent_skills.catalog import load_platform_manifest

    prompt = load_platform_manifest("autoreiv").system_prompt
    lines = [ln for ln in prompt.splitlines() if "agent-authoring" in ln]
    assert len(lines) == 1, lines
    line = lines[0]
    assert 'skill_view(skill_id="agent-authoring")' in line and "activate_skill" not in line
    assert "teach" in line.lower() and "new capability" in line.lower()


# 13 ------------------------------------------------------------------------
# 14 ------------------------------------------------------------------------
def test_14_agents_api_drops_auto_training_fields(tmp_path, monkeypatch):
    _, db = _env(tmp_path, monkeypatch)
    client = TestClient(_app(db))
    got = client.get("/api/agents/autoreiv")
    assert got.status_code == 200
    body = got.json()
    agent = body.get("agent", body)
    assert "allow_autonomous_training" not in agent
    assert "max_training_retries" not in agent

    created = client.post(
        "/api/agents",
        json={
            "id": "c497-agent",
            "name": "C497 Agent",
            "system_prompt": "You help the operator with CARD-497 checks.",
            "allow_autonomous_training": True,
            "max_training_retries": 4,
        },
    )
    assert created.status_code == 200, created.text
    assert "allow_autonomous_training" not in created.json()["agent"]
    updated = client.put(
        "/api/agents/c497-agent",
        json={"name": "C497 Agent", "system_prompt": "You help the operator with more CARD-497 checks.", "allow_autonomous_training": False},
    )
    assert updated.status_code == 200, updated.text
    assert "max_training_retries" not in json.dumps(updated.json())




# 15 ------------------------------------------------------------------------
def test_15_no_auto_train_event_or_sse_branch():
    from src.domain.kernel.models import KernelEvent, KernelEventType

    assert not hasattr(KernelEventType, "AUTO_TRAIN_PROGRESS")
    assert "auto_train" not in KernelEvent.model_fields
    chat_src = (ROOT / "src/web/routers/chat.py").read_text(encoding="utf-8")
    assert "auto_train_progress" not in chat_src


# 16 ------------------------------------------------------------------------
@pytest.mark.parametrize("mod", DELETED_MODULES)
def test_16_deleted_modules_are_gone(mod):
    assert not _module_path(mod).exists(), mod
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(mod)


def test_16b_no_src_file_imports_a_deleted_module():
    bad = []
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
                names.extend(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                names.extend(a.name for a in node.names)
            for name in names:
                if any(name == d or name.startswith(d + ".") for d in DELETED_MODULES):
                    bad.append(f"{path.relative_to(ROOT)}: {name}")
    assert not bad, bad


# 17: CARD-577 exports and drops the factory_* tables (tests/unit/core/test_card577_retired_tables.py).


def test_12e_talk_opens_an_empty_developer_session_so_the_client_sends_a_real_turn():
    """REQ-497-016: /talk must not pre-save the intent as a user message; the browser sends it via /api/chat/stream."""
    from src.application.tools.developer_mediation import ToolsDeveloperMediationService

    store = MagicMock()
    store.create_session.return_value = MagicMock(id="dev-497", title="t")
    registry = MagicMock()
    registry.get_profile.return_value = MagicMock()
    out = ToolsDeveloperMediationService(store, orchestrator=None, registry=registry).open_chat(
        "create", {"tool_name": "get_tc49_tool", "behavior": "Look up TC49 things"}
    )
    assert out["session_id"] == "dev-497"
    assert out["opened_chat"] is True and out["opened_job"] is False
    assert "get_tc49_tool" in out["prompt"]
    store.save_message.assert_not_called()

