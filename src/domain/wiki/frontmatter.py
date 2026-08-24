"""
Wiki YAML Frontmatter Schema Standard and Parser [REQ-WIKI-002].
Provides robust serialization, parsing, and token/word telemetry calculations.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Try importing yaml; if not available, will use fallback regex parser
try:
    import yaml
    HAVE_YAML = True
except ImportError:
    yaml = None  # type: ignore
    HAVE_YAML = False


def generate_uid() -> str:
    """Generate immutable timestamp UID in format YYYYMMDD-HHMMSS."""
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def compute_word_count(text: str) -> int:
    """Count non-empty words in markdown body text."""
    if not text:
        return 0
    return len(text.strip().split())


def compute_context_tokens(text: str) -> int:
    """
    Compute estimated context tokens according to the standard formula:
    round(max(chars / 4, words * 0.75))
    """
    if not text:
        return 0
    chars = len(text)
    words = len(text.split())
    return round(max(chars / 4.0, words * 0.75))


class WikiNoteMeta(BaseModel):
    """
    Authoritative 35-field additive YAML frontmatter metadata schema.
    """

    # Category 1: Identity & Retrieval Surface
    uid: str = Field(default_factory=generate_uid, description="Timestamp format YYYYMMDD-HHMMSS")
    title: str = Field(default="untitled", description="Human-readable note title")
    aliases: List[str] = Field(default_factory=list, description="Alternate names/titles")
    document_type: str = Field(
        default="atomic_note",
        description="atomic_note, master_note, proxy_note, moc, operating_manual, template, log",
    )
    summary: str = Field(default="", description="1-3 sentence factual abstraction")

    # Category 2: Taxonomy & Mind-Mapping
    domain: str = Field(default="general", description="Level 1 Degree field, e.g. information_technology")
    topic: str = Field(default="general", description="Level 2 Class/Subject, e.g. ai_engineering")
    subtopic: str = Field(default="", description="Optional granular sub-focus")
    tags: List[str] = Field(default_factory=list, description="List of snake_case tags")
    parent: str = Field(default="", description="Wikilink [[...]] to parent topic")
    related: List[str] = Field(default_factory=list, description="Wikilinks [[...]] to related notes")
    moc: str = Field(default="", description="Wikilink [[...]] to owning Map of Content")

    # Category 3: Status & Governance
    status: str = Field(
        default="draft",
        description="backlog, draft, in_review, final, deprecated, active, archived",
    )
    priority: str = Field(
        default="medium",
        description="need_to_do, should_do, want_to_do, high, medium, low",
    )
    sensitivity: str = Field(
        default="internal",
        description="public, internal, private, secret",
    )
    confidence_score: float = Field(default=1.0, description="Float 0.0 to 1.0")

    # Category 4: Lineage & Anti-Duplication
    supersedes: List[str] = Field(default_factory=list, description="List of note UIDs/titles merged")
    superseded_by: str = Field(default="", description="Note UID/title replacing this note")

    # Category 5: Proxy Asset Tracking
    target_artifact: str = Field(default="", description="Relative path to non-markdown file")
    artifact_type: str = Field(default="", description="csv, docx, pdf, image, audio, video, other")

    # Category 6: Timestamps & Telemetry
    schema_version: str = Field(default="1.0", description="Schema version")
    date_created: str = Field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d"))
    last_updated: str = Field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d"))
    last_accessed: str = Field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d"))
    word_count: int = Field(default=0, description="Body word count")
    context_tokens: int = Field(default=0, description="Estimated body token count")


_FRONTMATTER_PATTERN = re.compile(
    r"^\s*---\r?\n(.*?(?:\r?\n)?)^---\r?\n?(.*)$",
    re.DOTALL | re.MULTILINE,
)


class FrontmatterParser:
    """
    Parses and serializes markdown text with YAML frontmatter headers.
    """

    @staticmethod
    def _parse_yaml_fallback(raw_yaml: str) -> Dict[str, Any]:
        """Lightweight line-by-line YAML parser fallback."""
        result: Dict[str, Any] = {}
        current_list_key: Optional[str] = None

        for line in raw_yaml.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("- ") and current_list_key:
                val_str = stripped[2:].strip()
                if (val_str.startswith('"') and val_str.endswith('"')) or (
                    val_str.startswith("'") and val_str.endswith("'")
                ):
                    val_str = val_str[1:-1]
                result[current_list_key].append(val_str)
                continue

            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val_str = parts[1].strip()

                if not val_str:
                    current_list_key = key
                    result[key] = []
                    continue

                current_list_key = None
                if (val_str.startswith('"') and val_str.endswith('"')) or (
                    val_str.startswith("'") and val_str.endswith("'")
                ):
                    val: Any = val_str[1:-1]
                elif val_str.lower() == "true":
                    val = True
                elif val_str.lower() == "false":
                    val = False
                elif val_str.lower() in ("null", "none", "~"):
                    val = None
                elif val_str.startswith("[") and val_str.endswith("]"):
                    inner = val_str[1:-1].strip()
                    if not inner:
                        val = []
                    else:
                        val = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
                else:
                    try:
                        if "." in val_str:
                            val = float(val_str)
                        else:
                            val = int(val_str)
                    except ValueError:
                        val = val_str

                result[key] = val

        return result

    @classmethod
    def parse(cls, content: str) -> Tuple[WikiNoteMeta, str]:
        """
        Extract YAML frontmatter and markdown body from string.
        Returns: (WikiNoteMeta, body_text)
        """
        if not content or not isinstance(content, str):
            return WikiNoteMeta(), ""

        match = _FRONTMATTER_PATTERN.match(content)
        if not match:
            # Extract first heading if present
            first_heading = ""
            for line in content.splitlines():
                clean = line.strip()
                if clean.startswith("#"):
                    first_heading = clean.lstrip("#").strip()
                    break
            words = compute_word_count(content)
            tokens = compute_context_tokens(content)
            meta = WikiNoteMeta(
                title=first_heading or "untitled",
                word_count=words,
                context_tokens=tokens,
            )
            return meta, content

        raw_yaml, body = match.group(1), match.group(2)
        meta_dict: Dict[str, Any] = {}

        if HAVE_YAML and yaml is not None:
            try:
                parsed = yaml.safe_load(raw_yaml)
                if isinstance(parsed, dict):
                    meta_dict = parsed
                elif parsed is not None:
                    meta_dict = {"value": parsed}
            except Exception as exc:
                log.warning("PyYAML parse failed (%s); falling back to regex parser", exc)
                meta_dict = cls._parse_yaml_fallback(raw_yaml)
        else:
            meta_dict = cls._parse_yaml_fallback(raw_yaml)

        # Update telemetry
        body_clean = body.strip()
        words = compute_word_count(body_clean)
        tokens = compute_context_tokens(body_clean)

        meta_dict["word_count"] = words
        meta_dict["context_tokens"] = tokens

        try:
            meta = WikiNoteMeta.model_validate(meta_dict)
        except Exception:
            # If schema validation fails on extra fields, construct standard with defaults
            valid_keys = WikiNoteMeta.model_fields.keys()
            filtered = {k: v for k, v in meta_dict.items() if k in valid_keys}
            meta = WikiNoteMeta.model_validate(filtered)

        return meta, body_clean

    @classmethod
    def dump(cls, meta: WikiNoteMeta | Dict[str, Any], body: str = "") -> str:
        """
        Serialize metadata dictionary or WikiNoteMeta to YAML frontmatter prepended to markdown body.
        """
        if isinstance(meta, WikiNoteMeta):
            meta_dict = meta.model_dump()
        else:
            meta_dict = dict(meta)

        # Recompute words and tokens
        body_clean = body.strip()
        meta_dict["word_count"] = compute_word_count(body_clean)
        meta_dict["context_tokens"] = compute_context_tokens(body_clean)

        if HAVE_YAML and yaml is not None:
            yaml_str = yaml.safe_dump(meta_dict, default_flow_style=False, sort_keys=False).strip()
        else:
            lines = []
            for k, v in meta_dict.items():
                if isinstance(v, list):
                    lines.append(f"{k}:")
                    for item in v:
                        lines.append(f"  - {item}")
                elif isinstance(v, bool):
                    lines.append(f"{k}: {'true' if v else 'false'}")
                elif v is None:
                    lines.append(f"{k}: null")
                else:
                    lines.append(f"{k}: {v}")
            yaml_str = "\n".join(lines)

        return f"---\n{yaml_str}\n---\n\n{body_clean}\n"
