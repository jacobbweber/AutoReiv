"""CARD-411: skill frontmatter serialization keeps the body and valid tools."""

import pytest

from src.application.skills.runbook_frontmatter import (
    UnknownCatalogToolError,
    apply_workshop_metadata,
    frontmatter_view,
    split_skill_markdown,
)

BODY = """
# Widget Notes

## Procedure
1. Read the widget.
Keep-this-sentence.
"""

SAMPLE = f"""---
name: Widget Notes
description: Read widget notes
version: 1.0.0
tier: user
tools:
  - inspect_widget
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Widget was read.
---
{BODY}"""


def test_apply_tools_updates_tools_and_preserves_body():
    """CARD-411 REQ-411-002: add/remove tools rewrites tools; body stays."""
    catalog = ["inspect_widget", "wiki_note_read"]
    rendered, view = apply_workshop_metadata(
        SAMPLE,
        tools=["wiki_note_read", "inspect_widget", "wiki_note_read"],
        catalog_ids=catalog,
    )
    assert view["tools"] == ["wiki_note_read", "inspect_widget"]
    assert "Keep-this-sentence." in rendered
    assert "kind: assertion" in rendered or "assertion" in rendered
    meta, body = split_skill_markdown(rendered)
    assert "Keep-this-sentence." in body
    assert meta["verification"]["rule"] == "Widget was read."
    assert meta["version"] == "1.0.0"

    removed, removed_view = apply_workshop_metadata(
        rendered,
        tools=["wiki_note_read"],
        catalog_ids=catalog,
    )
    assert removed_view["tools"] == ["wiki_note_read"]
    assert "inspect_widget" not in removed_view["tools"]
    assert "Keep-this-sentence." in removed


def test_unknown_catalog_tool_is_rejected_and_not_serialized():
    """CARD-411: invalid tool ids must not land in tools."""
    with pytest.raises(UnknownCatalogToolError) as exc:
        apply_workshop_metadata(
            SAMPLE,
            tools=["inspect_widget", "not_a_tool"],
            catalog_ids=["inspect_widget"],
        )
    assert "not_a_tool" in exc.value.rejected
    view = frontmatter_view(SAMPLE)
    assert view["tools"] == ["inspect_widget"]
    assert view["tier"] == "user"
    assert view["safety"]["read_only"] is True
