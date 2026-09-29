"""CARD-577: retired tables (factory_*, scaffold_spine) are exported if they have rows, then dropped on startup."""
import json
import sqlite3

from src.infrastructure.memory.connection import RETIRED_TABLES, SQLiteConnectionManager


def _tables(db):
    conn = sqlite3.connect(str(db))
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def test_a_new_database_has_no_retired_tables(tmp_path):
    db = tmp_path / "data" / "database" / "autoreiv.db"
    SQLiteConnectionManager(db_path=str(db))
    assert not set(RETIRED_TABLES) & _tables(db)


def test_legacy_rows_are_exported_then_the_tables_dropped(tmp_path):
    db = tmp_path / "data" / "database" / "autoreiv.db"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE factory_jobs (id TEXT PRIMARY KEY, status TEXT)")
    conn.execute("INSERT INTO factory_jobs VALUES ('fjob_old', 'running')")
    conn.execute("CREATE TABLE scaffold_spine (id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    SQLiteConnectionManager(db_path=str(db))

    assert not {"factory_jobs", "scaffold_spine"} & _tables(db)
    exports = list((tmp_path / "data" / "backups").glob("factory-retire-*.json"))
    assert len(exports) == 1
    dump = json.loads(exports[0].read_text(encoding="utf-8"))
    assert dump == {"factory_jobs": [{"id": "fjob_old", "status": "running"}]}


def test_the_scaffold_and_factory_routes_are_gone():
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/capabilities/scaffold/candidates").status_code in (404, 405)
    assert client.get("/api/agent_training_factory/skills", follow_redirects=False).status_code == 404
    assert client.get("/api/capabilities/registry").status_code == 200
