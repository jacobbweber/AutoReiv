"""Factory Wiki front-matter contract v1 (CARD-171).

Required keys: type (factory-grounding), agent_id, medium.
Optional: factory_job_id, status.
Written only via existing Wiki tools / WikiService.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FACTORY_NOTE_TYPE = "factory-grounding"
REQUIRED_KEYS = ("type", "agent_id", "medium")
OPTIONAL_KEYS = ("factory_job_id", "status")


def build_factory_frontmatter(
    agent_id: str,
    medium: str,
    *,
    factory_job_id: Optional[str] = None,
    status: str = "draft",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build YAML front-matter dict for a Factory grounding note (contract v1)."""
    meta: Dict[str, Any] = {
        "type": FACTORY_NOTE_TYPE,
        "agent_id": agent_id,
        "medium": medium,
        "status": status,
    }
    if factory_job_id:
        meta["factory_job_id"] = factory_job_id
    if extra:
        for k, v in extra.items():
            if k not in meta:
                meta[k] = v
    return meta


def validate_factory_frontmatter(meta: Dict[str, Any]) -> list[str]:
    """Return list of validation errors (empty = valid contract v1)."""
    errors: list[str] = []
    if not isinstance(meta, dict):
        return ["frontmatter must be a dict"]
    for key in REQUIRED_KEYS:
        val = meta.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"missing required key: {key}")
    if meta.get("type") and meta.get("type") != FACTORY_NOTE_TYPE:
        errors.append(f"type must be '{FACTORY_NOTE_TYPE}', got '{meta.get('type')}'")
    return errors


def is_factory_grounding_note(meta: Dict[str, Any]) -> bool:
    return isinstance(meta, dict) and meta.get("type") == FACTORY_NOTE_TYPE


def filter_factory_notes(
    notes: list,
    *,
    agent_id: Optional[str] = None,
    factory_job_id: Optional[str] = None,
) -> list:
    """Filter note dicts (with frontmatter) to Factory grounding notes."""
    out = []
    for note in notes or []:
        meta = note.get("frontmatter") or note.get("meta") or {}
        if not is_factory_grounding_note(meta):
            continue
        if agent_id and meta.get("agent_id") != agent_id:
            continue
        if factory_job_id and meta.get("factory_job_id") != factory_job_id:
            continue
        out.append(note)
    return out
