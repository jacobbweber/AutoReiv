"""
Unit tests for Wiki YAML Frontmatter Parser & Deterministic Schema Standard [REQ-WIKI-002, CARD-125].
"""

from src.domain.wiki.frontmatter import (
    FrontmatterParser,
    WikiNoteMeta,
    compute_content_hash,
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


def test_compute_content_hash():
    text = "Important documentation body text."
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(text)
    h3 = compute_content_hash("Different text.")
    assert len(h1) == 16
    assert h1 == h2
    assert h1 != h3


def test_deterministic_key_ordering():
    meta = WikiNoteMeta(
        uid="20260831-140000",
        title="Deterministic Ordering Test",
        domain="systems_engineering",
        topic="observability",
        tags=["diagnostics", "telemetry"],
        summary="Testing fixed sequence of keys.",
        status="draft",
        priority="medium",
        author="assistant",
        model="gemini-3.5-flash-lite",
        pinned=True,
    )
    body = "System diagnostic logs..."
    raw_md = FrontmatterParser.dump(meta, body)

    expected_order = [
        "uid", "title", "aliases", "document_type", "domain", "topic",
        "tags", "summary", "status", "priority", "sensitivity", "confidence_score",
        "pinned", "parent", "related", "moc", "source", "author", "model",
        "content_hash", "date_created", "last_updated", "last_accessed",
        "access_count", "word_count", "context_tokens", "schema_version"
    ]

    lines = raw_md.splitlines()
    found_keys = []
    for line in lines:
        if line.startswith("---"):
            continue
        if ":" in line and not line.startswith("  "):
            k = line.split(":", 1)[0].strip()
            found_keys.append(k)

    filtered_expected = [k for k in expected_order if k in found_keys]
    assert found_keys == filtered_expected


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
        author="autoreiv",
        model="qwen3.8:latest",
    )
    body = "## Overview\nThis is the markdown body."
    raw_md = FrontmatterParser.dump(meta, body)
    assert raw_md.startswith("---\n")
    assert "uid: 20260823-120000" in raw_md
    assert "domain: information_technology" in raw_md
    assert "author: autoreiv" in raw_md
    assert "model: qwen3.8:latest" in raw_md
    assert "## Overview" in raw_md

    # Parse back
    parsed_meta, parsed_body = FrontmatterParser.parse(raw_md)
    assert parsed_meta.uid == "20260823-120000"
    assert parsed_meta.title == "Agent Architecture"
    assert parsed_meta.domain == "information_technology"
    assert parsed_meta.topic == "ai_engineering"
    assert parsed_meta.author == "autoreiv"
    assert parsed_meta.model == "qwen3.8:latest"
    assert "ai" in parsed_meta.tags
    assert "## Overview" in parsed_body
    assert len(parsed_meta.content_hash) == 16


def test_parse_without_frontmatter():
    raw_md = "# Plain Note\nJust regular markdown."
    parsed_meta, parsed_body = FrontmatterParser.parse(raw_md)
    assert parsed_meta.title == "Plain Note" or parsed_meta.title == "untitled"
    assert parsed_body.strip() == raw_md.strip()


def test_clean_note_content_strips_chatter_and_preserves_technical():
    from src.domain.wiki.frontmatter import clean_note_content

    raw_text = (
        "I hear you loud and clear! 🎉 Looks like we're all set and ready to go.\n\n"
        "Here is the documentation on Hyper-V switch configuration:\n\n"
        "# Hyper-V Switch Configuration\n\n"
        "To configure an internal switch run:\n"
        "```powershell\n"
        'New-VMSwitch -Name "LabSwitch" -SwitchType Internal\n'
        "```\n\n"
        "Hope this helps! Let me know if you need anything else! 😊"
    )
    cleaned = clean_note_content(raw_text)
    assert "I hear you loud and clear" not in cleaned
    assert "Hope this helps" not in cleaned
    assert "😊" not in cleaned
    assert "🎉" not in cleaned
    assert "# Hyper-V Switch Configuration" in cleaned
    assert 'New-VMSwitch -Name "LabSwitch" -SwitchType Internal' in cleaned


def test_inbox_staging_note_meta():
    from src.domain.wiki.frontmatter import WikiInboxNoteMeta

    inbox_meta = WikiInboxNoteMeta(
        title="Quick Scratchpad Capture",
        summary="A short note captured during chat.",
        domain="systems_engineering",
        topic="virtualization",
        tags=["hyperv", "vms"],
        author="assistant",
    )
    assert inbox_meta.status == "inbox"
    assert len(inbox_meta.uid) == 15
    assert inbox_meta.schema_version == "1.0"

    # Convert to graduated full 27-key meta
    graduated = inbox_meta.to_graduated(body="# Quick Scratchpad Capture\nSome content here.")
    assert graduated.status == "final"
    assert graduated.title == "Quick Scratchpad Capture"
    assert graduated.word_count > 0
    assert len(graduated.content_hash) == 16

