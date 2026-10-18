"""CARD-711 guard: single-lever YAML frontmatter parsing, SKILL.md resolution, and SQLite DDL constants."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_canonical_domain_frontmatter_module_exists_and_handles_split_and_errors():
    """src/domain/frontmatter.py provides canonical split_frontmatter, split_frontmatter_with_error, and join_frontmatter."""
    from src.domain.frontmatter import (
        join_frontmatter,
        split_frontmatter,
        split_frontmatter_with_error,
    )

    raw = "---\nname: sample-skill\ndescription: A sample skill\ntools:\n  - cli_exec\n---\n# Body\nHello\n"
    meta, body = split_frontmatter(raw)
    assert meta["name"] == "sample-skill"
    assert meta["tools"] == ["cli_exec"]
    assert "# Body" in body

    roundtrip = join_frontmatter(meta, body)
    meta2, body2 = split_frontmatter(roundtrip)
    assert meta2 == meta
    assert body2.strip() == body.strip()

    bad_meta, bad_body, err = split_frontmatter_with_error("---\nname: [unclosed\n---\nBody text")
    assert bad_meta == {}
    assert "Body text" in bad_body
    assert err is not None


def test_duplicate_frontmatter_parsers_delegate_to_domain_frontmatter():
    """Modules that previously had bespoke YAML frontmatter regex/splitters must delegate to src.domain.frontmatter."""
    for rel in (
        "src/infrastructure/content/store.py",
        "src/application/skills/dynamic_loader.py",
        "src/application/skills/runbook_frontmatter.py",
        "src/application/skills/linter.py",
        "src/application/orchestration/fleet_coordinator.py",
        "src/domain/observability/tool_skill_resolver.py",
    ):
        src = _read(rel)
        assert "src.domain.frontmatter" in src, f"{rel} must delegate to src.domain.frontmatter"
        assert "yaml.safe_load" not in src, f"{rel} must not call yaml.safe_load directly for frontmatter"


def test_connection_py_has_no_inline_create_table_ddl():
    """src/infrastructure/memory/connection.py must import DDL constants from schema.py instead of inline CREATE TABLE statements."""
    conn_src = _read("src/infrastructure/memory/connection.py")
    assert "CREATE TABLE" not in conn_src
    from src.infrastructure.memory import schema

    for const_name in (
        "PROMPT_CATALOG_SQL",
        "CREDENTIALS_SQL",
        "REMOTE_HOSTS_SQL",
        "AGENT_CAPABILITY_GAPS_SQL",
    ):
        assert hasattr(schema, const_name), f"schema.py missing {const_name}"
        assert const_name in conn_src, f"connection.py should use {const_name} from schema.py"
