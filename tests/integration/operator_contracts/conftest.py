"""Shared fixtures for operator contracts - temp user-data only [ADR-0055]."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def operator_client(tmp_path, monkeypatch):
    """Real FastAPI + SQLite under an isolated temp user-data root."""
    # Lazy imports: src.web.app eagerly create_app() at import time.
    from starlette.testclient import TestClient

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    user_data = (tmp_path / "user-data").resolve()
    wiki = user_data / "wiki"
    db = user_data / "autoreiv.db"
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)

    # Refuse the live Jarvis user-data root (not pytest Temp under LOCALAPPDATA).
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if local_app:
        live_root = (Path(local_app) / "AutoReiv").resolve()
        ud = str(user_data).replace("\\", "/").lower()
        live = str(live_root).replace("\\", "/").lower()
        assert ud != live and not ud.startswith(live + "/"), (
            f"operator contracts must not use live user-data: {user_data}"
        )

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    # Isolate from process-level docker probes left by live tests
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    with TestClient(app) as client:
        yield client, store, Path(wiki)
