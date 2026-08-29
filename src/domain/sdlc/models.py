"""
Card statuses, legal transitions, and frontmatter [REQ-SDLC-010, REQ-SDLC-011, REQ-SDLC-070].

Supports AutoReiv blockquote `> **Key**: value` and YAML `---` KEY: VALUE `---` (no PyYAML).
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
_YAML_KV = re.compile(r"^([A-Za-z_][\w -]*?)\s*:\s*(.*)$")
_CARD_ID_RE = re.compile(r"CARD-\d+", re.IGNORECASE)

_SPEC_REFERENCE_ALIASES = ("Spec Reference", "spec_reference", "spec")
_STATUS_ALIASES = ("Status", "status")


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


def _strip_wrapping_quotes(value: str) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def _lookup_field(fields: Dict[str, str], *names: str) -> str:
    """Case-insensitive lookup; first matching non-empty alias wins."""
    lowered = {k.lower(): v for k, v in fields.items()}
    for name in names:
        val = lowered.get(name.lower())
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _parse_yaml_frontmatter(
    lines: List[str], start: int
) -> Optional[Tuple[Dict[str, str], List[Tuple[str, str]], int]]:
    """Parse a leading `---` ... `---` block of simple KEY: VALUE lines.

    Nested / indented / list-only lines are skipped. Returns None when the
    block is not YAML (for example the AutoReiv body `---` separator).
    """
    if start >= len(lines) or lines[start].strip() != "---":
        return None
    fields: Dict[str, str] = {}
    pairs: List[Tuple[str, str]] = []
    idx = start + 1
    closed = False
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if stripped == "---":
            closed = True
            idx += 1
            break
        idx += 1
        if stripped == "" or stripped.startswith("#"):
            continue
        if raw[:1] in " \t" or stripped.startswith("- "):
            continue
        match = _YAML_KV.match(stripped)
        if not match:
            return None
        key = match.group(1).strip()
        value = _strip_wrapping_quotes(match.group(2))
        if not key:
            return None
        fields[key] = value
        pairs.append((key, value))
    if not closed or not fields:
        return None
    return fields, pairs, idx


def _extract_blockquote(
    lines: List[str],
) -> Tuple[Dict[str, str], str, str, bool]:
    """Parse `> **Key**: value` lines. had_bq False means remainder is not frontmatter."""
    fields: Dict[str, str] = {}
    prefix: List[str] = []
    idx = 0
    while idx < len(lines) and not lines[idx].startswith("> **"):
        prefix.append(lines[idx])
        idx += 1
    if idx >= len(lines) or not lines[idx].startswith("> **"):
        return {}, "", "", False
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
    raw_prefix = "\n".join(prefix).rstrip() + "\n"
    return fields, raw_prefix, body, True


class CardFrontmatter:
    """Parsed blockquote and/or YAML frontmatter plus leftover body."""

    def __init__(
        self,
        fields: Optional[Dict[str, str]] = None,
        body: str = "",
        raw_prefix: str = "",
        origin: str = "blockquote",
        yaml_pairs: Optional[List[Tuple[str, str]]] = None,
    ):
        self.fields: Dict[str, str] = dict(fields or {})
        self.body = body
        self.raw_prefix = raw_prefix
        self.origin = origin if origin in {"yaml", "blockquote"} else "blockquote"
        self.yaml_pairs: List[Tuple[str, str]] = list(yaml_pairs or [])

    def _set_aliased(self, aliases: Tuple[str, ...], value: str, default_key: str) -> None:
        for key in list(self.fields):
            if key.lower() == aliases[0].lower() or key.lower() in {a.lower() for a in aliases}:
                self.fields[key] = value
                return
        self.fields[default_key] = value

    @property
    def status(self) -> str:
        return normalize_status(_lookup_field(self.fields, *_STATUS_ALIASES) or "Discuss") or "Discuss"

    @status.setter
    def status(self, value: str) -> None:
        self._set_aliased(_STATUS_ALIASES, normalize_status(value), "Status")

    @property
    def spec_reference(self) -> str:
        return _lookup_field(self.fields, *_SPEC_REFERENCE_ALIASES).strip("`").strip()

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
    """Parse YAML `---` KEY: VALUE `---` and/or CARD-079 `> **Key**: value` lines.

    YAML fills missing keys; blockquote wins on conflict.
    """
    lines = (content or "").splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    yaml_parsed = _parse_yaml_frontmatter(lines, idx) if idx < len(lines) else None
    if yaml_parsed is not None:
        yaml_fields, yaml_pairs, idx = yaml_parsed
        rest = lines[idx:]
        bq_fields, bq_prefix, bq_body, had_bq = _extract_blockquote(rest)
        fields = dict(yaml_fields)
        fields.update(bq_fields)
        if had_bq:
            body = bq_body
            raw_prefix = bq_prefix
        else:
            body = "\n".join(rest)
            raw_prefix = ""
        if content.endswith("\n") and body and not body.endswith("\n"):
            body += "\n"
        return CardFrontmatter(
            fields=fields,
            body=body,
            raw_prefix=raw_prefix,
            origin="yaml",
            yaml_pairs=yaml_pairs,
        )

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
    return CardFrontmatter(
        fields=fields,
        body=body,
        raw_prefix="\n".join(prefix).rstrip() + "\n",
        origin="blockquote",
    )


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


def render_yaml_card_frontmatter(fm: CardFrontmatter) -> str:
    """Rewrite a YAML-origin card in place, preserving key order and body."""
    lines = ["---"]
    used_lower = set()
    fields_lower = {k.lower(): v for k, v in fm.fields.items()}
    for orig_key, orig_val in fm.yaml_pairs:
        lk = orig_key.lower()
        current = fields_lower[lk] if lk in fields_lower else orig_val
        lines.append(f"{orig_key}: {current}")
        used_lower.add(lk)
    for key, val in fm.fields.items():
        if key.lower() not in used_lower:
            lines.append(f"{key}: {val}")
            used_lower.add(key.lower())
    lines.append("---")
    rendered = "\n".join(lines)
    body = fm.body
    if body and not body.startswith("\n"):
        return rendered + "\n" + body
    return rendered + body


def serialize_card_frontmatter(fm: CardFrontmatter) -> str:
    """YAML-origin cards stay YAML; AutoReiv cards stay blockquote."""
    if fm.origin == "yaml":
        return render_yaml_card_frontmatter(fm)
    return render_card_frontmatter(fm)


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
