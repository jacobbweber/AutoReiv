"""
Card statuses, legal transitions, and blockquote frontmatter [REQ-SDLC-010, REQ-SDLC-011].
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

CARD_STATUSES = (
    "Discuss",
    "Ready",
    "In Progress",
    "In Review",
    "Returned",
    "Done",
)

LEGAL_TRANSITIONS = {
    "Discuss": frozenset({"Discuss", "Ready"}),
    "Ready": frozenset({"In Progress"}),
    "In Progress": frozenset({"In Review"}),
    "In Review": frozenset({"Done", "Returned"}),
    "Returned": frozenset({"In Progress"}),
    "Done": frozenset(),
}

DEFAULT_MAX_REVIEW_ROUNDS = 3

_FRONTMATTER_LINE = re.compile(r"^>\s*\*\*(?P<key>[^*]+)\*\*\s*:\s*(?P<value>.*)$")
_CARD_ID_RE = re.compile(r"CARD-\d+", re.IGNORECASE)


def normalize_status(value: str) -> str:
    raw = (value or "").strip()
    lowered = raw.lower().replace("_", " ").replace("-", " ")
    aliases = {
        "discuss": "Discuss",
        "ready": "Ready",
        "in progress": "In Progress",
        "inprogress": "In Progress",
        "in review": "In Review",
        "inreview": "In Review",
        "returned": "Returned",
        "done": "Done",
    }
    if lowered in aliases:
        return aliases[lowered]
    for status in CARD_STATUSES:
        if status.lower() == lowered:
            return status
    return raw


def spec_slug_from_reference(spec_reference: str) -> str:
    text = (spec_reference or "").strip().strip("`").strip()
    text = text.replace("\\", "/")
    if "docs/specs/" in text:
        text = text.split("docs/specs/", 1)[1]
    return text.strip("/")


class CardFrontmatter:
    """Parsed blockquote frontmatter plus leftover body."""

    def __init__(self, fields: Optional[Dict[str, str]] = None, body: str = "", raw_prefix: str = ""):
        self.fields: Dict[str, str] = dict(fields or {})
        self.body = body
        self.raw_prefix = raw_prefix

    @property
    def status(self) -> str:
        return normalize_status(self.fields.get("Status", "") or "Discuss") or "Discuss"

    @status.setter
    def status(self, value: str) -> None:
        self.fields["Status"] = normalize_status(value)

    @property
    def spec_reference(self) -> str:
        return (self.fields.get("Spec Reference") or "").strip().strip("`").strip()

    @property
    def review_rounds(self) -> int:
        try:
            return int(self.fields.get("review_rounds") or 0)
        except (TypeError, ValueError):
            return 0

    @review_rounds.setter
    def review_rounds(self, value: int) -> None:
        self.fields["review_rounds"] = str(int(value))

    @property
    def max_review_rounds(self) -> int:
        try:
            raw = self.fields.get("max_review_rounds")
            if raw is None or str(raw).strip() == "":
                return DEFAULT_MAX_REVIEW_ROUNDS
            return int(raw)
        except (TypeError, ValueError):
            return DEFAULT_MAX_REVIEW_ROUNDS

    @property
    def return_reason(self) -> str:
        return (self.fields.get("return_reason") or "").strip()

    @return_reason.setter
    def return_reason(self, value: str) -> None:
        self.fields["return_reason"] = value or ""

    @property
    def github_issue(self) -> str:
        return (self.fields.get("github_issue") or "").strip()


def parse_card_frontmatter(content: str) -> CardFrontmatter:
    """Parse CARD-079-style `> **Key**: value` lines after the title."""
    lines = (content or "").splitlines()
    fields: Dict[str, str] = {}
    prefix: List[str] = []
    idx = 0
    while idx < len(lines) and not lines[idx].startswith("> **"):
        prefix.append(lines[idx])
        idx += 1
    while idx < len(lines):
        match = _FRONTMATTER_LINE.match(lines[idx])
        if not match:
            if lines[idx].strip() == "":
                idx += 1
                continue
            if lines[idx].strip() == "---":
                idx += 1
                if idx < len(lines) and lines[idx].strip() == "":
                    idx += 1
                break
            break
        key = match.group("key").strip()
        value = match.group("value").strip()
        fields[key] = value
        idx += 1
    body = "\n".join(lines[idx:])
    if content.endswith("\n") and body:
        body += "\n"
    return CardFrontmatter(fields=fields, body=body, raw_prefix="\n".join(prefix).rstrip() + "\n")


_PREFERRED_KEYS = [
    "Status",
    "Created",
    "Spec Reference",
    "Labels",
    "review_rounds",
    "max_review_rounds",
    "return_reason",
    "github_issue",
]


def render_card_frontmatter(fm: CardFrontmatter) -> str:
    """Rewrite blockquote frontmatter, preserving unknown keys."""
    seen = set()
    lines: List[str] = []
    prefix = fm.raw_prefix.rstrip()
    if prefix:
        lines.append(prefix)
        lines.append("")
    ordered = [k for k in _PREFERRED_KEYS if k in fm.fields]
    for key in fm.fields:
        if key not in ordered:
            ordered.append(key)
    for key in ordered:
        seen.add(key)
        value = fm.fields.get(key, "")
        lines.append(f"> **{key}**: {value}")
    if "review_rounds" not in seen:
        lines.append(f"> **review_rounds**: {fm.review_rounds}")
    if "max_review_rounds" not in seen:
        lines.append(f"> **max_review_rounds**: {fm.max_review_rounds}")
    if "return_reason" not in seen:
        lines.append("> **return_reason**:")
    lines.append("")
    lines.append("---")
    lines.append("")
    body = fm.body.lstrip("\n")
    if body.startswith("---"):
        rest = body.split("\n", 1)
        body = rest[1] if len(rest) > 1 else ""
        body = body.lstrip("\n")
    return "\n".join(lines) + body


def extract_card_id(filename: str, content: str = "") -> str:
    for source in (filename, content):
        match = _CARD_ID_RE.search(source or "")
        if match:
            return match.group(0).upper()
    return ""


def extract_card_title(content: str, card_id: str = "") -> str:
    for line in (content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            title = re.sub(r"^\[CARD-\d+\]\s*", "", title, flags=re.IGNORECASE)
            return title or card_id
    return card_id


class CardStatusMachine:
    """Single status table for cards [REQ-SDLC-010]."""

    def validate(
        self,
        current: str,
        target: str,
        *,
        spec_exists: bool = False,
        review_rounds: int = 0,
        max_review_rounds: int = DEFAULT_MAX_REVIEW_ROUNDS,
        return_reason: str = "",
    ) -> Tuple[bool, str]:
        current_n = normalize_status(current) or "Discuss"
        target_n = normalize_status(target)
        if target_n not in CARD_STATUSES:
            return False, f"Unknown status '{target}'. Use one of: {', '.join(CARD_STATUSES)}."
        if current_n not in LEGAL_TRANSITIONS:
            return False, f"Unknown current status '{current}'."
        if target_n not in LEGAL_TRANSITIONS[current_n]:
            allowed = ", ".join(sorted(LEGAL_TRANSITIONS[current_n])) or "(none)"
            return False, f"Illegal transition {current_n} -> {target_n}. Allowed: {allowed}."
        if current_n == "Discuss" and target_n == "Ready" and not spec_exists:
            return False, "Discuss -> Ready requires an existing spec path (docs/specs/<slug>/)."
        if current_n == "In Review" and target_n == "Returned" and not (return_reason or "").strip():
            return False, "Returned requires a concrete return_reason."
        if current_n == "Returned" and target_n == "In Progress":
            if review_rounds >= max_review_rounds:
                return (
                    False,
                    "review_rounds is at max_review_rounds. Ask the operator before returning this card to In Progress.",
                )
        return True, ""
