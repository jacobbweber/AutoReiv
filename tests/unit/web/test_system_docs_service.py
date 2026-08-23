"""
Unit tests for System Documentation & Specs Service [REQ-SKIL-004].
"""

import pytest

from src.application.web.system_docs_service import SystemDocumentationService


def test_get_docs_navigation_tree():
    service = SystemDocumentationService()
    nav = service.get_navigation_tree()

    assert "sections" in nav
    assert len(nav["sections"]) >= 3

    # Check for core sections
    section_titles = [s["title"] for s in nav["sections"]]
    assert any("Specifications" in t for t in section_titles)
    assert any("Architecture Decisions" in t or "ADR" in t for t in section_titles)
    assert any("Constitution" in t or "SDLC" in t for t in section_titles)


def test_get_docs_nested_folder_tree():
    """Verify platform specs are structured into nested subfolders [REQ-DOCS-001]."""
    service = SystemDocumentationService()
    nav = service.get_navigation_tree()

    specs_section = next(s for s in nav["sections"] if "Specifications" in s["title"])
    assert "folders" in specs_section
    assert len(specs_section["folders"]) >= 1

    # Check that each feature folder contains requirements, design, or tasks files
    feature_folder = specs_section["folders"][0]
    assert "name" in feature_folder
    assert "files" in feature_folder
    assert any("requirements.md" in f["name"] or "requirements" in f["title"].lower() for f in feature_folder["files"])


def test_get_doc_content_valid_path():
    service = SystemDocumentationService()
    doc = service.get_doc_content("AGENTS.md")

    assert doc is not None
    assert doc["path"] == "AGENTS.md"
    assert "Master Agent Constitution" in doc["content"] or "Hard Invariants" in doc["content"]


def test_get_doc_content_path_traversal_blocked():
    service = SystemDocumentationService()

    with pytest.raises(ValueError, match="Access denied"):
        service.get_doc_content("../../etc/passwd")

    with pytest.raises(ValueError, match="Access denied"):
        service.get_doc_content("..\\windows\\system32\\cmd.exe")


def test_get_doc_content_non_existent():
    service = SystemDocumentationService()

    with pytest.raises(FileNotFoundError):
        service.get_doc_content("docs/specs/non_existent_spec_12345/requirements.md")
