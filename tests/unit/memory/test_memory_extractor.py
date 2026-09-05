"""
Unit tests for CARD-116: Post-turn memory extraction parser and
atomic fact conflict resolution engine (ADD, UPDATE, DELETE, BUMP).
"""

from src.application.memory.extractor import (
    CandidateMemoryFact,
    MemoryExtractorService,
    parse_extraction_response,
    should_skip_extraction,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_should_skip_extraction():
    assert should_skip_extraction("thanks") is True
    assert should_skip_extraction("Thank you!") is True
    assert should_skip_extraction("ok") is True
    assert should_skip_extraction("hello there") is True
    assert should_skip_extraction("I am running AutoReiv on Windows 11 Pro with 32GB RAM") is False


def test_parse_extraction_response():
    raw_clean = """[
        {"action": "ADD", "category": "environment", "entity": "user", "attribute": "os_platform", "value": "Windows 11"},
        {"action": "BUMP", "category": "user_pref", "entity": "user", "attribute": "language", "value": "Python"}
    ]"""
    facts = parse_extraction_response(raw_clean)
    assert len(facts) == 2
    assert facts[0].action == "ADD"
    assert facts[0].attribute == "os_platform"
    assert facts[0].value == "Windows 11"
    assert facts[1].action == "BUMP"

    # Markdown block wrapped JSON
    raw_markdown = """```json
    [
        {"action": "UPDATE", "category": "domain", "entity": "project", "attribute": "database", "value": "SQLite"}
    ]
    ```"""
    facts_md = parse_extraction_response(raw_markdown)
    assert len(facts_md) == 1
    assert facts_md[0].action == "UPDATE"
    assert facts_md[0].value == "SQLite"

    # Garbage / empty string fallback
    assert parse_extraction_response("Not JSON at all") == []
    assert parse_extraction_response("") == []


def test_conflict_resolution_pipeline(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()
    service = MemoryExtractorService(repository=repo)

    # 1. ADD new fact
    c1 = CandidateMemoryFact(
        action="ADD",
        category="environment",
        entity="user",
        attribute="os_platform",
        value="Windows 10",
    )
    res1 = service.apply_candidate_fact(c1)
    assert res1["action_taken"] == "ADD"
    fact1 = repo.get_semantic_fact(res1["fact_id"])
    assert fact1["value"] == "Windows 10"
    assert fact1["access_count"] == 1

    # 2. ADD with identical value -> automatically promoted to BUMP (reinforce, avoid duplicate)
    c2 = CandidateMemoryFact(
        action="ADD",
        category="environment",
        entity="user",
        attribute="os_platform",
        value="Windows 10",
    )
    res2 = service.apply_candidate_fact(c2)
    assert res2["action_taken"] == "BUMP"
    fact2 = repo.get_semantic_fact(res1["fact_id"])
    assert fact2["access_count"] == 2
    # Ensure no duplicate record was created
    all_facts = repo.list_semantic_facts()
    assert len(all_facts) == 1

    # 3. UPDATE existing fact with new value
    c3 = CandidateMemoryFact(
        action="UPDATE",
        category="environment",
        entity="user",
        attribute="os_platform",
        value="Windows 11 Pro",
    )
    res3 = service.apply_candidate_fact(c3)
    assert res3["action_taken"] == "UPDATE"
    fact3 = repo.get_semantic_fact(res1["fact_id"])
    assert fact3["value"] == "Windows 11 Pro"
    assert len(repo.list_semantic_facts()) == 1

    # 4. Explicit BUMP action
    c4 = CandidateMemoryFact(
        action="BUMP",
        category="environment",
        entity="user",
        attribute="os_platform",
        value="Windows 11 Pro",
    )
    res4 = service.apply_candidate_fact(c4)
    assert res4["action_taken"] == "BUMP"
    fact4 = repo.get_semantic_fact(res1["fact_id"])
    assert fact4["access_count"] == 3

    # 5. DELETE action retires the fact
    c5 = CandidateMemoryFact(
        action="DELETE",
        category="environment",
        entity="user",
        attribute="os_platform",
        value="",
    )
    res5 = service.apply_candidate_fact(c5)
    assert res5["action_taken"] == "DELETE"
    assert len(repo.list_semantic_facts(active_only=True)) == 0
