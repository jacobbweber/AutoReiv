"""CARD-568 guard: no flat tool lists anywhere; an agent's tools come only from its ticked skills (ADR-0061).

The only place the old key names may appear in src/ is the constant that rejects them on pack import.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.application.agent_packs.schema import REJECTED_TOOL_LIST_KEYS, AgentPackManifest
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

OLD_NAMES = re.compile(r"allowed_tool_names|pack_tool_names|allowed_tools_json|pack_tools_json|capability_migration")
SCANNED = ("src", "platform-packs", "tests/e2e", "tests/fixtures")
ALLOWED = {"src/application/agent_packs/schema.py"}  # REJECTED_TOOL_LIST_KEYS
TEXT_SUFFIXES = {".py", ".js", ".mjs", ".json", ".md", ".html", ".sql", ".yaml", ".yml", ".txt"}


def test_old_tool_list_names_appear_nowhere_but_the_rejecting_constant():
    offenders = []
    for root in SCANNED:
        for path in Path(root).rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES or "node_modules" in path.parts:
                continue
            rel = path.as_posix()
            if rel in ALLOWED:
                continue
            if OLD_NAMES.search(path.read_text(encoding="utf-8", errors="replace")):
                offenders.append(rel)
    assert not offenders, f"old tool-list names are back: {offenders}"
    schema_hits = OLD_NAMES.findall(Path("src/application/agent_packs/schema.py").read_text(encoding="utf-8"))
    assert len(schema_hits) == 2, schema_hits  # only the two names in REJECTED_TOOL_LIST_KEYS


def test_profile_and_customization_have_no_tool_list_fields():
    for model in (AgentProfile, AgentCustomization, AgentPackManifest):
        assert not set(REJECTED_TOOL_LIST_KEYS) & set(model.model_fields), model


def test_the_database_has_no_tool_list_columns(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "g.db"))
    store.initialize_db()
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "g.db"))
    try:
        for table in ("agent_overrides", "custom_agents"):
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            assert cols and not {"allowed_tools_json", "pack_tools_json"} & cols, table
    finally:
        conn.close()


@pytest.mark.parametrize("key", REJECTED_TOOL_LIST_KEYS)
def test_a_pack_with_a_flat_tool_list_is_rejected_with_a_clear_message(key):
    with pytest.raises(ValidationError, match="flat tool lists are not supported"):
        AgentPackManifest.model_validate({"id": "a", "name": "A", "skills": [{"id": "s", "tools": ["t1"]}], key: []})


def test_shipped_packs_load_and_keep_tools_in_skills():
    packs = sorted(Path("platform-packs").glob("*/pack.json"))
    assert packs
    for path in packs:
        manifest = AgentPackManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        assert not set(REJECTED_TOOL_LIST_KEYS) & set(manifest.model_dump(mode="json")), path
