"""
Global Pytest Configuration & Hermetic Test Environment Isolation.
Ensures no automated tests ever mutate or overwrite the production/development database (./data/autoreiv.db).
"""

import os
import tempfile
from pathlib import Path

import pytest


def _load_smoke_guard():
    """Shared live-data guard from scripts/smoke_server.py [CARD-467]."""
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "smoke_server.py"
    spec = importlib.util.spec_from_file_location("autoreiv_smoke_server", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolate_pytest_data_env(environ=None, base=None):
    """Force every AutoReiv data path to a temp tree, whatever the shell already set [CARD-467].

    ``setdefault`` was a no-op when the shell had the live ``AUTOREIV_DATA_DIR``, so the
    import-time ``src.web.app.app`` bootstrapped against live AppData packs (CARD-455).
    """
    environ = os.environ if environ is None else environ
    base = Path(tempfile.mkdtemp(prefix="autoreiv-pytest-")) if base is None else Path(base)
    environ["AUTOREIV_DATA_DIR"] = str(base / "data")
    environ["AUTOREIV_DB_PATH"] = str(base / "pytest_bootstrap.db")
    environ["AUTOREIV_WIKI_PATH"] = str(base / "wiki")
    environ.pop("AUTOREIV_BACKUP_DIR", None)
    return base


# CARD-672: unit tests never reach a real model. The default Ollama provider points at a closed local port and the
# remote providers are blank (not unset), so neither the operator's env nor load_repo_dotenv() (.env only fills
# unset keys) can aim a test at Spark/Nimo. Tests that need a provider set it themselves (monkeypatch/config dict).
HERMETIC_OLLAMA_HOST = "http://127.0.0.1:9"
BLANK_PROVIDER_VARS = (
    "VLLM_HOST",
    "VLLM_BASE_URL",
    "LMSTUDIO_HOST",
    "LMSTUDIO_BASE_URL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "TOGETHER_API_KEY",
)


def isolate_pytest_provider_env(environ=None):
    """Point model providers away from real servers for the whole test session [CARD-672]."""
    environ = os.environ if environ is None else environ
    environ["OLLAMA_HOST"] = HERMETIC_OLLAMA_HOST
    for name in BLANK_PROVIDER_VARS:
        environ[name] = ""
    # The factory registers these providers when the base URL is merely present, so they are removed, not blanked.
    for name in ("OPENAI_BASE_URL", "GEMINI_BASE_URL", "ANTHROPIC_BASE_URL"):
        environ.pop(name, None)
    return environ


def live_appdata_problems(environ=None):
    """Messages for any resolved data path that lands in live user data (empty = safe)."""
    from src.infrastructure.data.resolver import DataDirResolver

    guard = _load_smoke_guard()
    environ = os.environ if environ is None else environ
    resolved = DataDirResolver().resolve()
    paths = {
        "root": resolved.root,
        "db_path": resolved.db_path,
        "wiki_path": resolved.wiki_path,
        "agents_path": resolved.agents_path,
        "skills_path": resolved.skills_path,
        "backups_path": resolved.backups_path,
    }
    return guard.live_data_problems(paths, guard.live_data_roots(environ))


def pytest_configure(config):
    """Isolate data-dir env before any src.web.app import can bootstrap or migrate live data."""
    isolate_pytest_data_env()
    isolate_pytest_provider_env()
    import hang_watchdog  # CARD-672: tests/ is on sys.path (rootdir conftest, no __init__.py)

    if not config.pluginmanager.is_registered(hang_watchdog):
        config.pluginmanager.register(hang_watchdog, "autoreiv-hang-watchdog")
    problems = live_appdata_problems()
    if problems:
        pytest.exit(
            "CARD-467: refusing to run tests against live AutoReiv data:\n  " + "\n  ".join(problems),
            returncode=3,
        )


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Hermetically isolate the state database and wiki paths to temp folders for every test."""
    data_dir = str(tmp_path / "test_isolated_data")
    test_db = str(tmp_path / "test_isolated_autoreiv.db")
    test_wiki = str(tmp_path / "test_isolated_wiki")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", data_dir)
    monkeypatch.setenv("AUTOREIV_DB_PATH", test_db)
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", test_wiki)
    from src.infrastructure.content.store import reset_store

    reset_store()  # CARD-570: the agent/skill file store follows this test's data dir
    yield
    reset_store()



# --- CARD-560: one create_app() per test module for read-only route tests -------------------------
# create_app() seeds the catalog, installs platform packs and builds the registry (~0.3-0.7 s). Tests
# that only GET pages/routes or assert removed routes 404 can share one app per module.
# Rules: use ``shared_app``/``shared_client`` ONLY when the test never mutates app.state, settings,
# the DB or the data dir. Anything that saves, posts real data, swaps app.state.* or depends on a fresh
# data dir keeps its own function-scoped create_app(). dependency_overrides are reset after each test.


@pytest.fixture(scope="module")
def _shared_app_module(tmp_path_factory):
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    root = tmp_path_factory.mktemp("shared_app")
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AUTOREIV_DATA_DIR", str(root / "data"))
        mp.setenv("AUTOREIV_DB_PATH", str(root / "api.db"))
        mp.setenv("AUTOREIV_WIKI_PATH", str(root / "wiki"))
        store = SQLiteStateStore(db_path=str(root / "api.db"))
        app = create_app(state_store=store, wiki_path=str(root / "wiki"))
    finally:
        mp.undo()
    return app


@pytest.fixture
def shared_app(_shared_app_module):
    """Module-shared FastAPI app for read-only tests; overrides restored after each test [CARD-560]."""
    app = _shared_app_module
    saved = dict(app.dependency_overrides)
    yield app
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def shared_client(shared_app):
    """TestClient on the module-shared app (no lifespan), for GET/404-style tests [CARD-560]."""
    from fastapi.testclient import TestClient

    return TestClient(shared_app)


TOOL_SKILL_PREFIX = "tool:"


@pytest.fixture(autouse=True)
def bind_skills(monkeypatch):
    """CARD-539: tools reach an agent only through ticked skills.

    In tests a skill id ``"tool:<name>"`` binds exactly that tool (like a SKILL.md ``tools:`` list), so a
    fixture agent ticks ``allowed_skill=["tool:calculator"]``. ``bind_skills({"s": ["a", "b"]})`` binds
    any other skill and returns the ids to tick.
    """
    from src.infrastructure.content.store import ContentStore

    bound = {}
    real = ContentStore.skill_tools

    def fake(self, skill_ids):
        ids = list(skill_ids)
        out = dict(real(self, ids))
        for sid in ids:
            if sid in bound:
                out[sid] = list(bound[sid])
            elif str(sid).startswith(TOOL_SKILL_PREFIX):
                out[sid] = [str(sid)[len(TOOL_SKILL_PREFIX):]]
        return out

    monkeypatch.setattr(ContentStore, "skill_tools", fake)

    def bind(mapping):
        bound.update({str(k): list(v) for k, v in mapping.items()})
        return list(mapping)

    return bind
