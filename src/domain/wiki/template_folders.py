"""Per-agent wiki template folders [CARD-603].

Each agent names one vault-relative template folder (Agent Studio > Template folder; shipped agents set it in
platform/agents/*.md). Template tools and template search are confined to that folder; other agents' template
folders are hidden from the agent's wiki search. An agent with no folder gets no template access.
"""

from __future__ import annotations

from typing import Iterable, Optional


class TemplateFolderError(ValueError):
    """A template folder that is not a relative path inside the wiki vault."""


def normalize_template_folder(raw: object) -> Optional[str]:
    """'02_Resources\\_Templates\\General/' -> '02_Resources/_Templates/General'; empty -> None."""
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None
    if text.startswith("/") or (len(text) > 1 and text[1] == ":"):
        raise TemplateFolderError(
            "Template folder must be a folder inside the wiki vault, written relative to it "
            "(for example 02_Resources/_Templates/General)."
        )
    parts = [p.strip() for p in text.split("/") if p.strip() not in ("", ".")]
    if any(p == ".." for p in parts):
        raise TemplateFolderError("Template folder cannot contain '..'.")
    return "/".join(parts) or None


def is_under(rel_path: str, folder: str) -> bool:
    """True when the vault-relative path is the folder or inside it (case-insensitive, either slash)."""
    p = str(rel_path or "").replace("\\", "/").strip("/").lower()
    f = str(folder or "").replace("\\", "/").strip("/").lower()
    return bool(f) and (p == f or p.startswith(f + "/"))


def is_hidden(rel_path: str, own: Optional[str], others: Iterable[str]) -> bool:
    """Hidden from an agent: inside another agent's template folder and not inside its own."""
    if own and is_under(rel_path, own):
        return False
    return any(is_under(rel_path, o) for o in others)
