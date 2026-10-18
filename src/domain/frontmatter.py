"""Canonical YAML frontmatter splitting and serialization [CARD-711]."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Mapping, Optional

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_BLOCK_RE = re.compile(r"^---[ \t]*\n([\s\S]*?)\n---[ \t]*(?:\n|$)")


@lru_cache(maxsize=512)
def _split_frontmatter_cached(clean: str) -> tuple[dict[str, Any], str, Optional[str]]:
    match = _FRONTMATTER_BLOCK_RE.match(clean)
    if not match:
        return {}, clean, None
    raw_yaml = match.group(1)
    body = clean[match.end() :]
    try:
        loaded = yaml.safe_load(raw_yaml)
    except Exception as exc:
        logger.debug("Unreadable YAML frontmatter: %s", exc)
        return {}, body, str(exc)
    if loaded is None:
        return {}, body, None
    if not isinstance(loaded, dict):
        return {}, body, "YAML frontmatter must be a key-value mapping"
    return dict(loaded), body, None


def split_frontmatter_with_error(text: str) -> tuple[dict[str, Any], str, Optional[str]]:
    """Return (frontmatter_dict, body, error_message_or_none)."""
    clean = (text or "").replace("\r\n", "\n")
    meta, body, err = _split_frontmatter_cached(clean)
    return dict(meta), body, err


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Unreadable or non-mapping frontmatter yields {}."""
    meta, body, _err = split_frontmatter_with_error(text)
    return meta, body


def join_frontmatter(meta: Mapping[str, Any], body: str) -> str:
    """Serialize mapping as YAML frontmatter followed by stripped markdown body."""
    head = yaml.safe_dump(dict(meta), sort_keys=False, allow_unicode=True, width=10000)
    return f"---\n{head}---\n{(body or '').strip()}\n"
