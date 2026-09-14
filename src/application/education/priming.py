"""Education Priming write-back: Wiki schema/outline + memory.db ledger anchors [CARD-317].

Deterministic path (no second tutor runtime): create Priming schema note via
catalog-matched wiki_note_* only, then upsert education_mastery rows and
optional learner facts for the topic. Unregistered / forbidden wiki tools
soft-fail so note + ledger write-back still succeed.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.quiz_engine import extract_quiz_items_from_note
from src.application.safety.tool_policy_gate import (
    EDUCATION_FORBIDDEN_WIKI_TOOLS,
    EDUCATION_WIKI_NOTE_TOOLS,
)

PRIMING_WIKI_TOOLS: frozenset[str] = frozenset(EDUCATION_WIKI_NOTE_TOOLS)
PRIMING_FORBIDDEN_TOOLS: frozenset[str] = frozenset(EDUCATION_FORBIDDEN_WIKI_TOOLS)
PRIMING_KIND = "priming_schema"
PRIMING_LEARNER_ATTR = "priming_topic"
