"""CARD-666: the day1_routines_seeded setting is obsolete and is removed.

CARD-636 replaced the day-one routine seed (RoutineScheduler.seed_default_routines and its copy-pasted loops) with
src/application/routines/seed.py, which never reads or writes this flag. Existing databases still carry the row. On
start it is deleted, and only that key: every other setting stays.
"""

import sqlite3
import subprocess
from pathlib import Path

from src.infrastructure.memory.connection import RETIRED_SETTING_KEYS, SQLiteConnectionManager
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPO = Path(__file__).resolve().parents[3]
KEY = "day1_routines_seeded"


def test_the_key_is_listed_as_retired():
    assert KEY in RETIRED_SETTING_KEYS


def test_start_deletes_only_the_retired_key(tmp_path):
    db = tmp_path / "old.db"
    SQLiteConnectionManager(db_path=str(db))
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO settings (key, value_json) VALUES (?, ?)",
        [(KEY, "true"), ("theme", '"dark"'), ("deleted_builtin_routines", '["x"]')],
    )
    conn.commit()
    conn.close()

    store = SQLiteStateStore(db_path=str(db))
    assert store.get_setting(KEY) is None
    assert store.get_setting("theme") == "dark"
    assert store.get_setting("deleted_builtin_routines") == ["x"]
    SQLiteStateStore(db_path=str(db))  # idempotent: a second start is fine
    assert store.get_setting("theme") == "dark"


def test_no_code_reads_or_writes_the_key():
    out = subprocess.run(["git", "grep", "-l", KEY, "--", "src", "scripts", "platform"], cwd=REPO,
                         capture_output=True, text=True).stdout.split()
    assert [p.replace("\\", "/") for p in out] == ["src/infrastructure/memory/connection.py"]
