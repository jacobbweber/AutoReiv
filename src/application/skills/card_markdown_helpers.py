"""Markdown card formatting, ID extraction, and evidence section helpers [CARD-562, CARD-715]."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

STEERING_EXCERPT_CHARS = 4000
SPEC_FILENAMES = ("requirements.md", "design.md", "tasks.md")
# CARD-562 D2: the status moves Developer may make itself.
DEVELOPER_TRANSITIONS = frozenset(
    {("Ready", "In Progress"), ("In Progress", "In Review"), ("Returned", "In Progress")}
)
# CARD-563: Architect plans cards. Its review verdict (Done / Returned) goes through finish_review (CARD-564).
ARCHITECT_TRANSITIONS = frozenset({("Discuss", "Ready"), ("Proposed", "Ready"), ("Ready", "Proposed")})
ARCHITECT_NEW_STATUSES = ("Proposed", "Ready")
ARCHITECT_LOCKED_STATUSES = ("In Progress", "In Review")
# CARD-562: preferred card folder first; the other two are fallbacks for older projects.
CARD_DIRS = (".agents/cards", "docs/cards", ".github/cards")
_CARD_NUM = re.compile(r"^CARD-(\d+)", re.IGNORECASE)


def cards_folder_refusal(root: Path, target: Path) -> str:
    """CARD-562: generic file tools never write cards; write_card owns ids, filenames and status rules."""
    try:
        rel = Path(target).resolve().relative_to(Path(root).resolve()).as_posix()
    except (OSError, ValueError):
        return ""
    for d in CARD_DIRS:
        if rel == d or rel.startswith(d + "/"):
            return (
                f"Refusing to write '{rel}' with a file tool: cards are written with write_card (new cards get the "
                "next CARD-N id and filename automatically) and moved with set_card_status. Reading cards is fine."
            )
    return ""


def _slug(title: str) -> str:
    title = re.sub(r"^\s*\[?[A-Z]+(?:-[A-Z]+)*-(?:\d+|<n>|n)\]?:?\s*", "", title or "", flags=re.IGNORECASE)
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower())
    return re.sub(r"-+", "-", slug).strip("-")[:60].strip("-") or "card"


EVIDENCE_AUTO_HEADER = "Recorded by set_card_status (In Review):"


def _drop_auto_evidence(section: str) -> str:
    """Remove an earlier tool-written evidence block (header plus its '- ' lines) from an Evidence section."""
    out: List[str] = []
    skipping = False
    for line in section.split("\n"):
        if line.strip() == EVIDENCE_AUTO_HEADER:
            skipping = True
            continue
        if skipping and line.strip().startswith("- "):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def insert_evidence(card: str, lines: List[str]) -> str:
    """Put the tool's evidence first in ## Evidence (or ## Results), keeping what the model already wrote below it."""
    block = EVIDENCE_AUTO_HEADER + "\n" + "\n".join(lines) + "\n"
    text = card if card.endswith("\n") else card + "\n"
    m = re.search(r"(?m)^##\s+(Evidence|Results)\s*$", text)
    if not m:
        return text + "\n## Evidence\n\n" + block
    nxt = re.search(r"(?m)^##\s+", text[m.end() :])
    end = m.end() + nxt.start() if nxt else len(text)
    existing = _drop_auto_evidence(text[m.end() : end]).strip("\n")  # CARD-564: a new round replaces the old block
    body = "\n\n" + block + (("\n" + existing + "\n") if existing.strip() else "")
    return text[: m.end()] + body + ("\n" if nxt else "") + text[end:]


def apply_card_title(content: str, title: str, new: bool) -> str:
    """CARD-562: a `title` argument sets the frontmatter title and the heading text (and so the new card's slug)."""
    text = content.replace("\r\n", "\n")
    safe = title.replace('"', "'")
    if text.lstrip().startswith("---"):
        start = text.index("---")
        end = text.find("\n---", start + 3)
        if end != -1:
            head, rest = text[:end], text[end:]
            if re.search(r"(?m)^title:", head):
                head = re.sub(r"(?m)^title:.*$", lambda _m: f'title: "{safe}"', head, count=1)
            else:
                head = head + f'\ntitle: "{safe}"'
            text = head + rest
    m = re.search(r"(?m)^#\s+(\[?[A-Z]+(?:-[A-Z]+)*-\d+\]?\s*)?.*$", text)
    if m:
        ident = (m.group(1) or "").strip()
        heading = f"# {ident + ' ' if ident else ''}{title}"
        text = text[: m.start()] + heading + text[m.end() :]
    elif new:
        text = re.sub(r"(?s)^(---.*?\n---\n)?", lambda mm: (mm.group(0) or "") + f"\n# {title}\n", text, count=1)
    return text


_OWN_ID_FRONTMATTER = re.compile(r"(?im)^id:\s*[\"']?(CARD-\d+)\b")
_OWN_ID_HEADING = re.compile(r"^#+\s*\[?(CARD-\d+)\b", re.IGNORECASE)


def own_card_id(content: str) -> str:
    """The card's own id: frontmatter ``id:`` or its first heading, never a card it mentions [CARD-581]."""
    text = (content or "").replace("\r\n", "\n")
    if text.lstrip().startswith("---"):
        start = text.index("---")
        end = text.find("\n---", start + 3)
        m = _OWN_ID_FRONTMATTER.search(text[start : end if end != -1 else len(text)])
        if m:
            return m.group(1).upper()
    for line in text.splitlines():
        if line.strip().startswith("#"):
            m = _OWN_ID_HEADING.match(line.strip())
            return m.group(1).upper() if m else ""
    return ""


def stamp_new_card(content: str, card_id: str, status: Optional[str] = None) -> str:
    """Set the frontmatter id (and optionally status) and the heading id of a new card."""
    text = content.replace("\r\n", "\n")
    if not text.lstrip().startswith("---"):
        if status:  # a status is forced (Developer): give the card YAML frontmatter
            text = f"---\nid: {card_id}\nstatus: {status}\n---\n" + text
    else:
        start = text.index("---")
        end = text.find("\n---", start + 3)
        if end == -1:
            end = len(text)
        head, rest = text[:end], text[end:]
        head = (
            re.sub(r"(?m)^id:.*$", f"id: {card_id}", head, count=1)
            if re.search(r"(?m)^id:", head)
            else (head[: start + 3] + f"\nid: {card_id}" + head[start + 3 :])
        )
        if status:
            head = (
                re.sub(r"(?m)^status:.*$", f"status: {status}", head, count=1)
                if re.search(r"(?m)^status:", head)
                else (head + f"\nstatus: {status}")
            )
        text = head + rest
    return re.sub(
        r"(?m)^(#\s+)(?:\[?[A-Z]+(?:-[A-Z]+)*-(?:\d+|<n>|N)\]?:?\s*)?",  # CARD-563: also the CARD-<n> placeholder
        lambda m: f"{m.group(1)}{card_id} ",
        text,
        count=1,
    )
