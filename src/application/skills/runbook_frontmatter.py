"""SKILL.md YAML frontmatter parse/serialize for the Skill Studio workshop [CARD-411].

Structured fields (name, description, tier, safety, requires_tools) round-trip
without dropping the markdown body or unrelated frontmatter keys such as
verification.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional, Sequence

import yaml

VALID_TIERS = ("platform", "pack", "user")
SAFETY_KEYS = ("read_only", "requires_hitl", "untrusted_input_allowed")
_FIELD_ORDER = (
    "name",
    "description",
    "version",
    "author",
    "tier",
    "requires_tools",
    "safety",
    "verification",
)


class UnknownCatalogToolError(ValueError):
    """requires_tools contains ids that are not in the platform tool catalog."""

    def __init__(self, rejected: Sequence[str]):
        self.rejected = [str(item) for item in rejected]
        joined = ", ".join(self.rejected) if self.rejected else "(none)"
        super().__init__(f"Unknown catalog tool ids: {joined}")


class InvalidSkillTierError(ValueError):
    def __init__(self, tier: str):
        self.tier = tier
        super().__init__(f"Invalid skill tier '{tier}'. Expected one of: {', '.join(VALID_TIERS)}.")


def split_skill_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter mapping, body). Body keeps the newline that separates it from the header."""
    raw = (text or "").replace("\r\n", "\n")
    if not raw.startswith("---"):
        return {}, raw
    match = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    if not match:
        return {}, raw
    loaded = yaml.safe_load(match.group(1))
    meta = dict(loaded) if isinstance(loaded, dict) else {}
    return meta, raw[match.end() :]


def normalize_tool_ids(
    tool_ids: Optional[Iterable[Any]],
    catalog_ids: Optional[Iterable[str]] = None,
) -> tuple[list[str], list[str]]:
    """Dedupe tool ids, preserve order, and split unknown catalog ids into rejected."""
    catalog = None if catalog_ids is None else {str(item).strip() for item in catalog_ids if str(item).strip()}
    accepted: list[str] = []
    rejected: list[str] = []
    for raw in tool_ids or []:
        tool_id = str(raw).strip()
        if not tool_id or tool_id in accepted or tool_id in rejected:
            continue
        if catalog is not None and tool_id not in catalog:
            rejected.append(tool_id)
            continue
        accepted.append(tool_id)
    return accepted, rejected


def _normalize_safety(safety: Optional[Mapping[str, Any]]) -> dict[str, bool]:
    source = dict(safety or {})
    return {key: bool(source.get(key, False)) for key in SAFETY_KEYS}


def serialize_skill_markdown(meta: Mapping[str, Any], body: str) -> str:
    """Emit YAML frontmatter + body. Body is not rewritten."""
    ordered: dict[str, Any] = {}
    for key in _FIELD_ORDER:
        if key in meta and meta[key] is not None:
            ordered[key] = meta[key]
    for key, value in meta.items():
        if key not in ordered:
            ordered[key] = value
    dumped = yaml.safe_dump(
        ordered,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    body_out = body or ""
    if body_out and not body_out.startswith("\n"):
        body_out = "\n" + body_out
    return f"---\n{dumped}\n---\n{body_out}"


def frontmatter_view(text: str) -> dict[str, Any]:
    """Structured inspector/editor view of a SKILL.md document."""
    meta, body = split_skill_markdown(text)
    tools, _rejected = normalize_tool_ids(meta.get("requires_tools") or meta.get("tools") or [])
    tier = str(meta.get("tier") or "pack").strip() or "pack"
    return {
        "name": str(meta.get("name") or "").strip(),
        "description": str(meta.get("description") or "").strip(),
        "tier": tier if tier in VALID_TIERS else "pack",
        "safety": _normalize_safety(meta.get("safety") if isinstance(meta.get("safety"), dict) else {}),
        "requires_tools": tools,
        "body": body,
    }


def apply_workshop_metadata(
    markdown: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tier: Optional[str] = None,
    safety: Optional[Mapping[str, Any]] = None,
    requires_tools: Optional[Sequence[Any]] = None,
    catalog_ids: Optional[Iterable[str]] = None,
) -> tuple[str, dict[str, Any]]:
    """Overlay structured workshop fields onto frontmatter and preserve the body.

    When ``catalog_ids`` is provided, unknown tool ids raise UnknownCatalogToolError
    and are not written into requires_tools.
    """
    meta, body = split_skill_markdown(markdown)
    if name is not None:
        meta["name"] = str(name).strip()
    if description is not None:
        meta["description"] = str(description).strip()
    if tier is not None:
        clean_tier = str(tier).strip().lower()
        if clean_tier not in VALID_TIERS:
            raise InvalidSkillTierError(clean_tier)
        meta["tier"] = clean_tier
    elif "tier" not in meta:
        meta["tier"] = "pack"
    if isinstance(safety, Mapping):
        safety_source = safety
    elif isinstance(meta.get("safety"), dict):
        safety_source = meta["safety"]
    else:
        safety_source = {}
    meta["safety"] = _normalize_safety(safety_source)

    if requires_tools is None:
        raw_tools = meta.get("requires_tools") if meta.get("requires_tools") is not None else meta.get("tools") or []
        accepted, rejected = normalize_tool_ids(raw_tools, catalog_ids)
    else:
        accepted, rejected = normalize_tool_ids(requires_tools, catalog_ids)
    if catalog_ids is not None and rejected:
        raise UnknownCatalogToolError(rejected)
    meta["requires_tools"] = accepted
    meta.pop("tools", None)
    rendered = serialize_skill_markdown(meta, body)
    return rendered, frontmatter_view(rendered)
