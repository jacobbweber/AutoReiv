"""
Unit tests for Wiki YAML Frontmatter Parser & Schema Standard [REQ-WIKI-002].
"""


from src.domain.wiki.frontmatter import (
    FrontmatterParser,
    WikiNoteMeta,
    compute_context_tokens,
    compute_word_count,
    generate_uid,
)


def test_generate_uid():
    uid = generate_uid()
    assert len(uid) == 15  # YYYYMMDD-HHMMSS format
    assert "-" in uid
    assert uid[:4].isdigit()


def test_compute_word_count_and_tokens():
    text = "This is a simple sentence with exactly nine words."
    words = compute_word_count(text)
    assert words == 9
    tokens = compute_context_tokens(text)
    assert tokens >= 6


def test_parse_and_dump_frontmatter():
    meta = WikiNoteMeta(
        uid="20260823-120000",
        title="Agent Architecture",
        domain="information_technology",
        topic="ai_engineering",
        document_type="atomic_note",
        tags=["ai", "agents"],
        summary="A summary of agent architecture.",
        status="final",
    )
    body = "## Overview\nThis is the markdown body."
    raw_md = FrontmatterParser.dump(meta, body)
    assert raw_md.startswith("---\n")
    assert "uid: 20260823-120000" in raw_md
    assert "domain: information_technology" in raw_md
    assert "## Overview" in raw_md

    # Parse back
    parsed_meta, parsed_body = FrontmatterParser.parse(raw_md)
    assert parsed_meta.uid == "20260823-120000"
    assert parsed_meta.title == "Agent Architecture"
    assert parsed_meta.domain == "information_technology"
    assert parsed_meta.topic == "ai_engineering"
    assert "ai" in parsed_meta.tags
    assert "## Overview" in parsed_body


def test_parse_without_frontmatter():
    raw_md = "# Plain Note\nJust regular markdown."
    parsed_meta, parsed_body = FrontmatterParser.parse(raw_md)
    assert parsed_meta.title == "Plain Note" or parsed_meta.title == "untitled"
    assert parsed_body.strip() == raw_md.strip()
