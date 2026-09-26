"""CARD-497 tests 7-17: Factory backend removed; Studio, gaps, packs and upgrade stay whole [REQ-497-005..015]."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import logging
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "card497"

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
def test_7_app_state_has_no_factory_and_lifespan_starts_no_factory_task(tmp_path, monkeypatch):
    _, db = _env(tmp_path, monkeypatch)
    app = _app(db)
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
def test_10_registry_has_inspect_agent_pack_not_launch_factory_training(tmp_path, monkeypatch):
    _, db = _env(tmp_path, monkeypatch)
    app = _app(db)
    names = {t.name for t in app.state.tool_registry.list_tools()}
    assert "inspect_agent_pack" in names
    assert "launch_factory_training" not in names


@pytest.fixture
def pack_tools(tmp_path):
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.skills.agent_pack_tools import AgentPackTools
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    registry = MagicMock(spec=BuiltinAgentRegistry)
    profile = MagicMock()
    profile.id = "test-agent"
    profile.name = "Test Agent"
    profile.description = "A test agent"
    profile.pack_tool_names = ["read_file", "write_file"]
    profile.allowed_skill = ["filesystem"]
    profile.skills = [MagicMock(id="filesystem", tools=["read_file", "write_file"])]
    registry.get_profile.side_effect = lambda ag: profile if ag == "test-agent" else None
    registry.get_agent.side_effect = lambda ag: profile if ag == "test-agent" else None
    tool_reg = ScopedToolRegistry()
    tools = AgentPackTools(agent_registry=registry, tool_registry=tool_reg, store=None, data_dir=tmp_path / "data")
    tools.register_tools(tool_reg)
    return tools, tool_reg


@pytest.mark.asyncio
async def test_10b_agent_pack_tools_inspect_success(pack_tools):
    tools, reg = pack_tools
    assert "inspect_agent_pack" in {t.name for t in reg.list_tools()}
    res = await tools.inspect_agent_pack(agent_id="test-agent")
    assert res["success"] is True
    assert res["name"] == "Test Agent"
    assert {"read_file", "write_file"} <= set(res["tools"])
    assert "filesystem" in res["skills"]


@pytest.mark.asyncio
async def test_10c_agent_pack_tools_inspect_not_found(pack_tools):
    tools, _ = pack_tools
    res = await tools.inspect_agent_pack(agent_id="nonexistent-agent")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


# 11 ------------------------------------------------------------------------
def test_11_retired_tools_strip_launch_factory_training_from_user_modified_pack(tmp_path):
    from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
    from src.infrastructure.skills.platform_packs import RETIRED_TOOL_NAMES, promote_platform_packs

    assert "launch_factory_training" in RETIRED_TOOL_NAMES

    checkout = tmp_path / "checkout"
    pack = checkout / "platform-packs" / "fixturepack"
    (pack / "skills" / "skill-a").mkdir(parents=True)
    (pack / "skills" / "skill-a" / "SKILL.md").write_text("# a\nv1\n", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "name": "Fixturepack",
                "version": "1",
                "system_prompt": "SHIPPED",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "a", "tools": ["wiki_note_read"]}],
                "pack_tool_names": ["wiki_note_read"],
                "allowed_tool_names": ["wiki_note_read"],
                "model": "default",
            }
        ),
        encoding="utf-8",
    )
    profile = AgentProfile(
        id="fixturepack",
        name="Fixturepack",
        description="fixture",
        system_prompt="OPERATOR PROMPT",
        origin=AgentOrigin.PACK,
        tone=AgentTone.DEFAULT,
        purpose=ModelPurpose.TASK_EXECUTION,
        allowed_skill=["skill-a"],
        pack_tool_names=["wiki_note_read", "launch_factory_training"],
        allowed_tool_names=["wiki_note_read", "launch_factory_training"],
        user_modified=True,
        seed_content_hash="deadbeef",
        seed_version="1",
    )

    class _Store:
        def __init__(self):
            self.profiles = {"fixturepack": profile}
            self.settings = {}

        def get_agent_profile(self, agent_id):
            return self.profiles.get(agent_id)

        get_custom_agent_profile = get_agent_profile

        def save_agent_profile(self, p):
            self.profiles[p.id] = p

        save_custom_agent_profile = save_agent_profile

        def get_agent_override(self, agent_id):
            return None

        def save_agent_override(self, ov):
            pass

        def list_custom_agent_profiles(self):
            return list(self.profiles.values())

        def get_setting(self, key):
            return self.settings.get(key)

        def set_setting(self, key, value):
            self.settings[key] = value

        def mark_agent_user_modified(self, agent_id, *, modified=True):
            self.profiles[agent_id].user_modified = modified

    class _Registry:
        def __init__(self, store):
            self.state_store = store

        def get_agent(self, agent_id):
            return self.state_store.profiles.get(agent_id)

    store = _Store()
    report = promote_platform_packs(tmp_path / "data", _Registry(store), None, checkout_root=checkout, pack_ids=["fixturepack"])
    assert report.results[0].status == "skipped_user_modified"
    stored = store.profiles["fixturepack"]
    assert "launch_factory_training" not in (stored.allowed_tool_names or [])
    assert stored.system_prompt == "OPERATOR PROMPT"


# 12 ------------------------------------------------------------------------
def test_12_agent_authoring_is_intake_and_no_shipped_text_mentions_factory_training():
    from tests.unit.agent_packs.catalog import load_platform_manifest

    manifest = load_platform_manifest("autoreiv")
    skill = next(s for s in manifest.skills if s.id == "agent-authoring")
    assert set(skill.tools) == {"inspect_agent_pack", "lookup_agents", "handoff_to_agent", "propose_skill"}
    assert "launch_factory_training" not in manifest.pack_tool_names

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


# 13 ------------------------------------------------------------------------
def test_13_unedited_shipped_seed_is_refreshed(tmp_path):
    from src.infrastructure.skills.seed import bundled_skill_md, seed_bundled_skill_packs

    dest = tmp_path / "skills" / "build-agent-pack" / "SKILL.md"
    dest.parent.mkdir(parents=True)
    old = (FIXTURES / "build-agent-pack.shipped-1f6a64cf.SKILL.md").read_bytes()
    dest.write_bytes(old.replace(b"\n", b"\r\n"))  # Windows checkout copies CRLF
    seed_bundled_skill_packs(tmp_path / "skills", ["build-agent-pack"])
    now = dest.read_text(encoding="utf-8")
    assert "trained in the Factory" not in now
    assert now.replace("\r\n", "\n") == bundled_skill_md("build-agent-pack").read_text(encoding="utf-8").replace("\r\n", "\n")


def test_13b_edited_seed_is_left_alone_and_logged(tmp_path):
    from src.infrastructure.skills.seed import seed_bundled_skill_packs

    records: list[logging.LogRecord] = []

    class _Keep(logging.Handler):
        def emit(self, record):
            records.append(record)

    seed_logger = logging.getLogger("src.infrastructure.skills.seed")
    handler = _Keep(level=logging.INFO)
    old_level = seed_logger.level
    seed_logger.addHandler(handler)
    seed_logger.setLevel(logging.INFO)

    dest = tmp_path / "skills" / "build-agent-pack" / "SKILL.md"
    dest.parent.mkdir(parents=True)
    edited = (FIXTURES / "build-agent-pack.shipped-1f6a64cf.SKILL.md").read_text(encoding="utf-8") + "\nOperator note.\n"
    dest.write_text(edited, encoding="utf-8")
    try:
        seed_bundled_skill_packs(tmp_path / "skills", ["build-agent-pack"])
    finally:
        seed_logger.removeHandler(handler)
        seed_logger.setLevel(old_level)
    assert dest.read_text(encoding="utf-8") == edited
    assert any("build-agent-pack" in r.getMessage() and "edited" in r.getMessage().lower() for r in records)


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


def test_14b_pack_export_omits_and_import_ignores_auto_training_fields():
    from src.application.agent_packs.schema import AgentPackManifest

    assert "allow_autonomous_training" not in AgentPackManifest.model_fields
    assert "max_training_retries" not in AgentPackManifest.model_fields
    manifest = AgentPackManifest.model_validate(
        {"id": "old-pack", "name": "Old Pack", "allow_autonomous_training": True, "max_training_retries": 3}
    )
    dumped = manifest.model_dump(mode="json")
    assert "allow_autonomous_training" not in dumped
    assert "max_training_retries" not in dumped


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


# 17 ------------------------------------------------------------------------
def test_17_existing_factory_rows_survive_startup(tmp_path, monkeypatch):
    _, db = _env(tmp_path, monkeypatch)
    _app(db)  # creates schema, including the kept factory_* tables
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO factory_jobs (id, target_agent_id, session_id, status, seed_intent) "
        "VALUES ('fjob_old', 'autoreiv', 'sess_x', 'running', 'legacy job')"
    )
    conn.commit()
    conn.close()

    app = _app(db)
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT id, status FROM factory_jobs").fetchall()
    conn.close()
    assert rows == [("fjob_old", "running")]
