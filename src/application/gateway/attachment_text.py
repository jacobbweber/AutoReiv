"""Attachment text for the prompt, sized from the model's context window [CARD-479].

Jacob's decision (2026-09-30): the inline limit comes from the model's context window, not a fixed
file size, and Direct mode (no tools) gets the content itself instead of a note about tools.

* ``attachment_char_budget``: a quarter of the context window, at ~4 characters per token, kept
  between 8,000 and 400,000 characters, shared by all text attachments of the turn.
* Every document or text file is extracted whatever its file size; text past its share is cut and
  marked. Agent mode says the rest can be read with ``read_document_file``; Direct mode says the
  rest was not included.
* A file that cannot be read is named to the model and returned in ``failures`` so the chat can
  tell the user (REQ-479-003).

CARD-625: a document or text file is only read when its path resolves inside the data root's
``attachments/`` folder (where ``/api/chat/upload`` writes), with the same check images use
(CARD-483, ``inside_attachments_dir``). Any other path, including a forged ``path`` in the chat
request, is "not an uploaded file": nothing is read and the path is not repeated to the model.
An unknown folder reads nothing (fail closed). Callers in ``src`` always pass ``attachments_dir``;
leaving it out (only the CARD-479 unit tests do) skips the folder check.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.application.gateway.attachment_images import AttachmentsDir, _resolve_root, inside_attachments_dir

CHARS_PER_TOKEN = 4
CONTEXT_SHARE = 0.25
MIN_BUDGET_CHARS = 8_000
MAX_BUDGET_CHARS = 400_000

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
DOC_SUFFIXES = (".pdf", ".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".csv", ".tsv")

AGENT_NOTE = (
    "*(Note for Agent: The user has attached the files/images above. You can read documents using "
    "`read_document_file` or filesystem tools if needed.)*"
)
DIRECT_NOTE = "*(The user attached the files above. Their text is included here; there are no tools in this chat.)*"

NOT_UPLOADED = "not an uploaded file"
MISSING = "the uploaded file is missing"
_UNCHECKED: Any = object()  # no folder given: CARD-479 unit tests only (see module note)


def attachment_char_budget(context_tokens: Optional[int]) -> int:
    """Characters of attachment text for one turn, from the model's context window (tokens)."""
    try:
        tokens = int(context_tokens or 0)
    except (TypeError, ValueError):
        tokens = 0
    raw = int(tokens * CONTEXT_SHARE * CHARS_PER_TOKEN)
    return max(MIN_BUDGET_CHARS, min(MAX_BUDGET_CHARS, raw))


@dataclass
class AttachmentPrompt:
    text: str
    failures: List[str] = field(default_factory=list)


def _extract(path: str, is_doc: bool) -> str:
    if is_doc:
        from src.application.skills.document_extractors import extract_document

        res = extract_document(path, max_pages=500, max_rows=5000)
        if not res.get("success"):
            raise ValueError(res.get("error") or "extraction failed")
        return str(res.get("content") or "")
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _lexically_inside(path: str, root: Optional[str]) -> bool:
    try:
        lexical = os.path.normcase(str(Path(path).resolve(strict=False)))
        return bool(root) and os.path.commonpath([lexical, root]) == root
    except (OSError, ValueError, RuntimeError):
        return False


def _readable_path(local_path: str, root: Optional[str], checked: bool) -> Tuple[Optional[str], Optional[str]]:
    """``(path to read, None)`` or ``(None, reason)``; only uploads are read when ``checked`` [CARD-625]."""
    if not checked:
        return (local_path, None) if local_path and Path(local_path).exists() else (None, MISSING)
    found = inside_attachments_dir(local_path, root) if local_path else None
    if found is not None and found.is_file():
        return str(found), None
    if local_path and _lexically_inside(local_path, root):
        return None, MISSING  # an upload that is gone
    return None, NOT_UPLOADED  # never says whether an outside file exists


def _cut(text: str, share: int, direct: bool) -> str:
    if len(text) <= share:
        return text
    rest = "the rest was not included" if direct else "read the rest with `read_document_file`"
    return f"{text[:share]}\n\n*(Cut short: showing the first {share:,} of {len(text):,} characters; {rest}.)*"


def build_attachment_prompt(
    content: Optional[str],
    attachments: Optional[List[Dict[str, Any]]],
    *,
    char_budget: int = MIN_BUDGET_CHARS,
    direct: bool = False,
    attachments_dir: AttachmentsDir = _UNCHECKED,
) -> AttachmentPrompt:
    text = (content or "").strip()
    if not attachments:
        return AttachmentPrompt(text)
    checked = attachments_dir is not _UNCHECKED
    root = _resolve_root(attachments_dir) if checked else None

    readable = [
        a for a in attachments
        if not (str(a.get("content_type") or "").startswith("image/") or str(a.get("filename") or "").lower().endswith(IMAGE_SUFFIXES))
    ]
    share = max(1_000, int(char_budget) // max(1, len(readable)))
    blocks: List[str] = []
    failures: List[str] = []
    for att in attachments:
        fname = att.get("filename", "attachment")
        url = att.get("url", "")
        ctype = str(att.get("content_type") or "unknown")
        size = att.get("size_bytes", 0)
        local_path = att.get("path", "")
        if att not in readable:
            blocks.append(
                f"![{fname}]({url})\n"
                f"*(Attached Image: `{fname}`, {size} bytes, format: `{ctype}`, Local Path: `{local_path}`)*"
            )
            continue
        is_doc = str(fname).lower().endswith(DOC_SUFFIXES)
        read_path, reason = _readable_path(local_path, root, checked)
        if reason == NOT_UPLOADED:  # REQ-625-001: nothing read, and the forged path is not repeated
            blocks.append(f"\U0001F4CE {fname}\n\n*(Could not read `{fname}`: {NOT_UPLOADED}.)*")
            failures.append(f"Couldn't read `{fname}`: {NOT_UPLOADED}.")
            continue
        if is_doc:
            block = f"\U0001F4C4 [{fname} ({size} bytes)]({url})\n*(Attached Document: `{fname}`, {size} bytes, Local Path: `{local_path}`)*"
        else:
            block = f"\U0001F4CE [{fname} ({size} bytes)]({url}) (Local Path: `{local_path}`)"
        try:
            if read_path is None:
                raise FileNotFoundError(reason)
            body = _extract(read_path, is_doc)
            if body.strip():
                body = _cut(body, share, direct)
                block += f"\n\n**Document Content:**\n{body}" if is_doc else f"\n```\n{body}\n```"
            else:
                block += "\n\n*(No text could be found in this file.)*"
        except Exception as exc:  # noqa: BLE001 - the model and the user are told instead
            reason = str(exc) or exc.__class__.__name__
            block += f"\n\n*(Could not read `{fname}`: {reason}.)*"
            failures.append(f"Couldn't read `{fname}`: {reason}.")
        blocks.append(block)

    note = DIRECT_NOTE if direct else AGENT_NOTE
    return AttachmentPrompt(f"{text}\n\n---\n" + "\n\n".join(blocks) + f"\n\n{note}", failures)
