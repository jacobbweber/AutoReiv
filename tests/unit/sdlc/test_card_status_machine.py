"""
Card status machine and frontmatter parse [REQ-SDLC-010, REQ-SDLC-011].
"""

from src.domain.sdlc.models import (
    CardStatusMachine,
    parse_card_frontmatter,
    render_card_frontmatter,
)

SAMPLE = """# [CARD-080] Example

> **Status**: Discuss
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/example/`
> **Labels**: `type:feature`

---

## 1. Why / Intent
Body text.
"""


def test_parse_blockquote_frontmatter():
    fm = parse_card_frontmatter(SAMPLE)
    assert fm.status == "Discuss"
    assert fm.spec_reference == "docs/specs/example/"
    assert fm.review_rounds == 0
    assert fm.max_review_rounds == 3
    assert "Why / Intent" in fm.body


def test_render_preserves_body_and_adds_round_fields():
    fm = parse_card_frontmatter(SAMPLE)
    rendered = render_card_frontmatter(fm)
    assert "> **Status**: Discuss" in rendered
    assert "> **review_rounds**: 0" in rendered
    assert "## 1. Why / Intent" in rendered


def test_discuss_to_ready_requires_spec():
    machine = CardStatusMachine()
    ok, err = machine.validate("Discuss", "Ready", spec_exists=False)
    assert ok is False
    assert "spec" in err.lower()
    ok2, _ = machine.validate("Discuss", "Ready", spec_exists=True)
    assert ok2 is True


def test_illegal_transition_denied():
    machine = CardStatusMachine()
    ok, err = machine.validate("Discuss", "Done")
    assert ok is False
    assert "Illegal" in err


def test_returned_requires_reason_and_max_rounds_deny():
    machine = CardStatusMachine()
    ok, err = machine.validate("In Review", "Returned", return_reason="")
    assert ok is False
    assert "return_reason" in err
    ok2, _ = machine.validate("In Review", "Returned", return_reason="gap in REQ-1")
    assert ok2 is True
    ok3, err3 = machine.validate(
        "Returned",
        "In Progress",
        review_rounds=3,
        max_review_rounds=3,
    )
    assert ok3 is False
    assert "operator" in err3.lower()
    ok4, _ = machine.validate(
        "Returned",
        "In Progress",
        review_rounds=2,
        max_review_rounds=3,
    )
    assert ok4 is True


def test_happy_path_transitions():
    machine = CardStatusMachine()
    assert machine.validate("Discuss", "Discuss")[0] is True
    assert machine.validate("Ready", "In Progress")[0] is True
    assert machine.validate("In Progress", "In Review")[0] is True
    assert machine.validate("In Review", "Done")[0] is True
