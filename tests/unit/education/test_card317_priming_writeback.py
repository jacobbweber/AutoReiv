"""CARD-317: Priming write-back — Wiki schema + memory.db ledger anchors + soft-fail."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.application.education.learner_model import LEARNER_ENTITY, summarize_learner_model
from src.application.education.priming import (
    PRIMING_FORBIDDEN_TOOLS,
    PRIMING_KIND,
    PRIMING_LEARNER_ATTR,
    PRIMING_WIKI_TOOLS,
    assert_priming_tool_allowed,
    build_priming_ask_clause,
    build_priming_schema_markdown,
    priming_writeback,
    seed_ledger_anchors_from_priming_note,
    soft_fail_unregistered_tool,
)
from src.application.safety.tool_policy_gate import EDUCATION_WIKI_NOTE_TOOLS
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.skills.seed import bundled_skill_md


def _assert_memory_db_path(db: Path) -> None:
    name = db.name.lower()
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in name or "memory" in path_s
    assert "storage.db" not in path_s


def test_priming_allowlist_matches_card241():
    assert PRIMING_WIKI_TOOLS == set(EDUCATION_WIKI_NOTE_TOOLS)
    assert "wiki_note_create" in PRIMING_WIKI_TOOLS
    assert "wiki_overview" in PRIMING_FORBIDDEN_TOOLS


def test_assert_forbids_wiki_overview():
    with pytest.raises(ValueError, match="wiki_overview"):
        assert_priming_tool_allowed("wiki_overview")
    assert_priming_tool_allowed("wiki_note_create")


def test_soft_fail_unregistered_does_not_abort():
    soft = soft_fail_unregistered_tool("wiki_overview")
    assert soft["success"] is True
    assert soft["fail_soft"] is True
    assert soft["skipped"] is True
    soft2 = soft_fail_unregistered_tool("totally_ghost_wiki_tool")
    assert soft2["fail_soft"] is True


def test_build_priming_schema_has_outline_and_quiz():
    body = build_priming_schema_markdown(topic="Standing Jobs", teach_style="bite-size")
    low = body.lower()
    assert "## outline" in low
    assert "## prerequisites" in low
    assert "## learning goals" in low
    assert "## quiz" in low
    assert "wiki_note_create" in body
    assert "never wiki_overview" in low
    assert PRIMING_KIND in body
    assert "memory.db" in body or "ledger" in low


def test_writeback_wiki_and_ledger_anchors(tmp_path: Path):
    """[REQ-EDU-PRIM-001/002] Wiki note + education_mastery (+ learner) anchors."""
    wiki_root = tmp_path / "wiki"
    wiki = WikiStore(root_dir=wiki_root)
    wiki.scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    result = priming_writeback(
        topic="Standing Jobs",
        wiki_tools_or_store=tools,
        memory_repo=repo,
        teach_style="schema first",
        search_first=True,
        attempt_forbidden_tools=["wiki_overview", "wiki_graph"],
    )
    assert result["success"] is True
    assert result["inbox"] is True
    path = result["path"].replace("\\", "/")
    assert path.startswith("00_Inbox/")
    assert "wiki_note_create" in result["tools_used"]
    assert "wiki_overview" not in result["tools_used"]
    assert result["soft_fails"]
    assert all(s.get("fail_soft") for s in result["soft_fails"])

    note = wiki.read_note(path)
    assert note.get("success") is not False
    content = note.get("content") or ""
    assert "Standing Jobs" in content or "standing jobs" in content.lower()
    assert "## Outline" in content
    assert "## Quiz" in content

    ledger = result["ledger"]
    assert ledger.get("success") is True
    assert ledger.get("count", 0) >= 1
    rows = repo.list_education_mastery()
    assert any(r.get("topic") == "Standing Jobs" for r in rows)
    assert any((r.get("wiki_path") or "").replace("\\", "/") == path for r in rows)

    facts = repo.list_facts_for_entity(LEARNER_ENTITY)
    assert any(
        f.get("attribute") == PRIMING_LEARNER_ATTR and "Standing Jobs" in (f.get("value") or "")
        for f in facts
    )


def test_soft_fail_does_not_block_note_when_create_succeeds(tmp_path: Path):
    """[REQ-EDU-PRIM-003] Unregistered tools soft-fail; note still lands."""
    tools = WikiTools(wiki_root=tmp_path / "wiki")
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    result = priming_writeback(
        topic="Soft Fail Topic",
        wiki_tools_or_store=tools,
        memory_repo=repo,
        attempt_forbidden_tools=["wiki_overview", "not_a_real_tool", "wiki_graph"],
    )
    assert result["success"] is True
    assert result["path"]
    assert len(result["soft_fails"]) >= 2
    assert result["ledger"].get("success") is True


def test_reopen_memory_db_preserves_topic_anchors(tmp_path: Path):
    """[REQ-EDU-PRIM-004] After restart-style reopen, topic still in mastery + learner."""
    tools = WikiTools(wiki_root=tmp_path / "wiki")
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)

    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    result = priming_writeback(
        topic="Restart Priming",
        wiki_tools_or_store=tools,
        memory_repo=repo1,
    )
    assert result["success"] is True
    path = result["path"]
    ids = list(result["ledger"].get("item_ids") or [])
    assert ids

    close = getattr(repo1, "close", None)
    if callable(close):
        close()
    del repo1

    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    rows = repo2.list_education_mastery()
    assert any(r.get("item_id") in ids for r in rows)
    assert any(r.get("topic") == "Restart Priming" for r in rows)
    assert any((r.get("wiki_path") or "") == path for r in rows)

    summary = summarize_learner_model(repo2)
    blob = " ".join(
        str(f.get("value") or "") + " " + str(f.get("attribute") or "")
        for f in (summary.get("facts") or [])
    )
    assert "Restart Priming" in blob or PRIMING_LEARNER_ATTR in blob


def test_seed_from_existing_note_body(tmp_path: Path):
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    body = build_priming_schema_markdown(topic="Seed Only")
    out = seed_ledger_anchors_from_priming_note(
        repo,
        content=body,
        wiki_path="00_Inbox/seed-only.md",
        topic="Seed Only",
    )
    assert out["success"] is True
    assert out["count"] >= 1
    row = repo.get_education_mastery(out["item_ids"][0])
    assert row is not None
    assert row["wiki_path"] == "00_Inbox/seed-only.md"


def test_ask_clause_mentions_ledger_and_soft_fail():
    clause = build_priming_ask_clause(topic="Jobs", teach_style="clear")
    low = clause.lower()
    assert "priming" in low
    assert "wiki_note_create" in low
    assert "never wiki_overview" in low
    assert "ledger" in low or "mastery" in low or "memory.db" in low
    assert "soft-fail" in low or "soft fail" in low


def test_skill_mentions_ledger_or_writeback():
    body = bundled_skill_md("education-priming").read_text(encoding="utf-8")
    assert "wiki_note_create" in body
    assert "wiki_overview" in body
    # CARD-317: skill Done-when / order should acknowledge durable ledger anchors
    low = body.lower()
    assert "ledger" in low or "mastery" in low or "memory.db" in low


def test_no_second_tutor_runtime_in_priming_module():
    import src.application.education.priming as priming_mod

    src = inspect.getsource(priming_mod)
    assert "openai" not in src.lower()
    assert "ollama" not in src.lower()
    assert "complete(" not in src
