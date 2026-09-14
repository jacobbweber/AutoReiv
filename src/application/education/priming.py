"""Education Priming write-back: Wiki schema/outline + memory.db ledger anchors [CARD-317].

Deterministic path (no second tutor runtime): create Priming schema note via
catalog-matched wiki_note_* only, then upsert education_mastery rows and
optional learner facts for the topic. Unregistered / forbidden wiki tools
soft-fail so note + ledger write-back still succeed.
"""

from src.application.education.priming_schema import (
    PRIMING_FORBIDDEN_TOOLS,
    PRIMING_KIND,
    PRIMING_LEARNER_ATTR,
    PRIMING_WIKI_TOOLS,
    assert_priming_tool_allowed,
    build_priming_schema_markdown,
    create_priming_note,
    is_priming_wiki_tool,
    search_grounding_notes,
    slug_topic,
    soft_fail_unregistered_tool,
    topic_anchor_id,
)
from src.application.education.priming_ledger import (
    build_priming_ask_clause,
    maybe_seed_ledger_after_priming_create,
    priming_writeback,
    record_learner_priming_anchor,
    seed_ledger_anchors_from_priming_note,
)

__all__ = [
    "PRIMING_FORBIDDEN_TOOLS",
    "PRIMING_KIND",
    "PRIMING_LEARNER_ATTR",
    "PRIMING_WIKI_TOOLS",
    "assert_priming_tool_allowed",
    "build_priming_ask_clause",
    "build_priming_schema_markdown",
    "create_priming_note",
    "is_priming_wiki_tool",
    "maybe_seed_ledger_after_priming_create",
    "priming_writeback",
    "record_learner_priming_anchor",
    "search_grounding_notes",
    "seed_ledger_anchors_from_priming_note",
    "slug_topic",
    "soft_fail_unregistered_tool",
    "topic_anchor_id",
]
