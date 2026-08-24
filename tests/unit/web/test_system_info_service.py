"""
Unit tests for System Info Knowledge Hub Service [REQ-SYST-001, REQ-SYST-003].
"""

import pytest

from src.application.web.system_info_service import SystemInfoService


@pytest.fixture
def system_info_service():
    return SystemInfoService()


def test_get_topics_index(system_info_service):
    """Verify system info topics index returns categorized topics with metadata [REQ-SYST-001]."""
    index = system_info_service.get_topics_index()
    assert len(index) >= 3  # At least 3 major sections

    # Check categories
    categories = [cat["title"] for cat in index]
    assert any("Architecture" in c or "Core" in c for c in categories)
    assert any("Capability" in c or "Tool" in c or "Skill" in c for c in categories)

    # Check topics
    all_topics = [t for cat in index for t in cat.get("topics", [])]
    assert len(all_topics) >= 5
    topic_ids = [t["id"] for t in all_topics]
    assert "concept-hierarchy" in topic_ids
    assert "skill-packs-guide" in topic_ids
    assert "purpose-matrix-and-models" in topic_ids


def test_get_topic_content_concept_hierarchy(system_info_service):
    """Verify concept hierarchy topic contains the 5 tiers with Mermaid diagram [REQ-SYST-003]."""
    doc = system_info_service.get_topic_content("concept-hierarchy")
    assert doc is not None
    assert doc["title"]
    assert "Agents" in doc["content"]
    assert "Workflows" in doc["content"]
    assert "Routines" in doc["content"]
    assert "Skill Packs" in doc["content"]
    assert "Tools" in doc["content"]
    assert "```mermaid" in doc["content"]


def test_get_topic_content_skill_packs_guide(system_info_service):
    """Verify skill packs reference contains all standard packs [REQ-SYST-003]."""
    doc = system_info_service.get_topic_content("skill-packs-guide")
    assert doc is not None
    assert "Sysadmin" in doc["content"]
    assert "Librarian" in doc["content"]
    assert "Verification" in doc["content"]
    assert "Planning" in doc["content"]
    assert "Orchestration" in doc["content"]


def test_get_topic_not_found(system_info_service):
    """Verify querying an invalid topic ID returns None gracefully."""
    doc = system_info_service.get_topic_content("non-existent-topic-12345")
    assert doc is None
