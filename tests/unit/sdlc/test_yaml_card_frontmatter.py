"""
YAML card frontmatter parse and aliases [REQ-SDLC-070, REQ-SDLC-071].
"""

from src.domain.sdlc.models import parse_card_frontmatter, serialize_card_frontmatter

YAML_CARD_001 = """---
id: CARD-001
title: Educational single-script ReAct loop in PowerShell
status: Discuss
owner: Jacob
review_rounds: 0
max_review_rounds: 3
spec: react-loop-powershell
tags: [powershell, react, ollama, education]
---

# CARD-001 - Educational single-script ReAct loop in PowerShell

## Goal
Body stays.
"""

BLOCKQUOTE = """# [CARD-080] Example

> **Status**: Discuss
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/example/`
> **Labels**: `type:feature`

---

## 1. Why / Intent
Body text.
"""


def test_parse_yaml_card_001_shape():
    fm = parse_card_frontmatter(YAML_CARD_001)
    assert fm.status == "Discuss"
    assert fm.spec_reference == "react-loop-powershell"
    assert fm.origin == "yaml"
    assert "Goal" in fm.body


def test_yaml_spec_reference_alias():
    fm = parse_card_frontmatter(
        "---\nstatus: Discuss\nspec_reference: react-loop-powershell\n---\n\n# Title\n"
    )
    assert fm.spec_reference == "react-loop-powershell"
    assert fm.status == "Discuss"


def test_blockquote_spec_reference_alias():
    fm = parse_card_frontmatter("# Title\n\n> **spec_reference**: other-slug\n> **Status**: Discuss\n")
    assert fm.spec_reference == "other-slug"
    assert fm.status == "Discuss"


def test_blockquote_spec_reference_canonical():
    fm = parse_card_frontmatter(BLOCKQUOTE)
    assert fm.spec_reference == "docs/specs/example/"
    assert fm.status == "Discuss"
    assert fm.origin == "blockquote"


def test_blockquote_wins_over_yaml_on_conflict():
    content = """---
status: Discuss
spec: from-yaml
---

# Title

> **Status**: Ready
> **Spec Reference**: from-blockquote
"""
    fm = parse_card_frontmatter(content)
    assert fm.status == "Ready"
    assert fm.spec_reference == "from-blockquote"


def test_yaml_fills_missing_blockquote_keys():
    content = """---
spec: from-yaml
status: Discuss
---

# Title

> **Created**: 2026-08-29
"""
    fm = parse_card_frontmatter(content)
    assert fm.spec_reference == "from-yaml"
    assert fm.status == "Discuss"
    assert fm.fields.get("Created") == "2026-08-29"


def test_serialize_yaml_updates_status_preserves_body():
    fm = parse_card_frontmatter(YAML_CARD_001)
    fm.status = "Ready"
    rendered = serialize_card_frontmatter(fm)
    assert rendered.startswith("---")
    assert "status: Ready" in rendered
    assert "spec: react-loop-powershell" in rendered
    assert "> **Status**" not in rendered
    assert "## Goal" in rendered
    again = parse_card_frontmatter(rendered)
    assert again.status == "Ready"
    assert again.spec_reference == "react-loop-powershell"
