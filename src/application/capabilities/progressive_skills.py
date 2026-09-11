"""Progressive SKILL.md disclosure for catalog resolve + phase bind [CARD-228].

Resolve returns skill metadata only (id, title, risk, HITL).
Full runbook body loads only on phase bind/select — never dump-all at resolve.
Chat ticked tool schemas remain a separate invariant (AGENTS.md / CARD-117).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind

# Payload keys that must never appear on resolve skill views (qwen context tax).
SKILL_BODY_PAYLOAD_KEYS = frozenset(
    {
        "instructions",
        "body",
        "content",
        "skill_md",
        "skill_body",
        "runbook",
        "runbook_body",
        "markdown",
        "full_text",
        "playbook",
    }
)

FORBIDDEN_DUMP_SKILL_BODY_ATTRS = frozenset(
    {
        "dump_all_skill_bodies",
        "load_all_skill_bodies_for_resolve",
        "resolve_with_full_skill_bodies",
        "export_all_skill_bodies_to_prompt",
        "dump_skill_bodies_at_resolve",
    }
)


def _risk_str(entry: CapabilityIndexEntry) -> str:
    risk = getattr(entry, "risk_level", None)
    if hasattr(risk, "value"):
        return str(risk.value)
    return str(risk or "medium")


def _is_skill_entry(entry: CapabilityIndexEntry) -> bool:
    kind = entry.kind
    if kind == CapabilityKind.SKILL:
        return True
    raw = kind.value if hasattr(kind, "value") else str(kind or "")
    if raw.strip().lower() == "skill":
        return True
    return str(entry.id or "").startswith("skill.")


def skill_metadata_view(entry: CapabilityIndexEntry) -> Dict[str, Any]:
    """Catalog/resolve view for skills: metadata only — no SKILL.md body [REQ-PSKILL-001]."""
    return {
        "id": entry.id,
        "title": entry.name,
        "kind": "skill",
        "risk": _risk_str(entry),
        "requires_hitl": bool(entry.requires_hitl),
        "body_loaded": False,
        "metadata_only": True,
    }


def _scrub_metadata(meta: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in dict(meta or {}).items():
        if str(key).strip().lower() in SKILL_BODY_PAYLOAD_KEYS:
            continue
        # Defense: drop huge string blobs that look like smuggled runbooks.
        if isinstance(value, str) and len(value) > 400:
            continue
        out[key] = value
    return out


def entry_to_resolve_view(entry: CapabilityIndexEntry) -> Dict[str, Any]:
    """Serialize one matched capability for resolve payloads (progressive for skills)."""
    if _is_skill_entry(entry):
        return skill_metadata_view(entry)
    data = entry.model_dump(mode="json")
    data["metadata"] = _scrub_metadata(data.get("metadata"))
    data["metadata_only"] = True
    data["body_loaded"] = False
    # Ensure accidental body keys are not top-level either.
    for key in list(data.keys()):
        if str(key).strip().lower() in SKILL_BODY_PAYLOAD_KEYS:
            data.pop(key, None)
    return data


def pack_id_from_skill_capability_id(skill_id: str) -> str:
    """Map capability id `skill.<pack>` → pack id for UserSkillCatalog."""
    raw = (skill_id or "").strip().replace("\\", "/")
    if raw.startswith("skill."):
        return raw[len("skill.") :]
    return raw


def load_one_skill_body(catalog: Any, skill_id: str) -> Dict[str, Any]:
    """Load exactly one SKILL.md body via UserSkillCatalog / DynamicSkillLoader."""
    pack_id = pack_id_from_skill_capability_id(skill_id)
    if catalog is None:
        return {
            "success": False,
            "error": "skill_catalog is not configured",
            "skill_id": skill_id,
            "pack_id": pack_id,
        }

    loaded: Optional[Dict[str, Any]] = None
    load_body = getattr(catalog, "load_body", None)
    if callable(load_body):
        loaded = load_body(pack_id)

    if not loaded or not loaded.get("success"):
        from src.application.skills.dynamic_loader import DynamicSkillLoader

        path = None
        resolve_md = getattr(catalog, "resolve_skill_md", None)
        if callable(resolve_md):
            try:
                path = resolve_md(pack_id)
            except Exception:
                path = None
        if path is None or not Path(path).is_file():
            resolve_scoped = getattr(catalog, "resolve_pack_scoped_skill_md", None)
            if callable(resolve_scoped):
                path = resolve_scoped(pack_id)
        if path is not None and Path(path).is_file():
            parsed = DynamicSkillLoader.load_skill_from_markdown(str(path))
            if parsed:
                loaded = {
                    "success": True,
                    "id": pack_id,
                    "name": parsed.get("name", pack_id),
                    "description": parsed.get("description", ""),
                    "path": parsed.get("path", str(path)),
                    "instructions": parsed.get("instructions", ""),
                    "tools": [
                        {"name": t.name, "description": t.description}
                        for t in (parsed.get("tools") or [])
                    ],
                }

    if not loaded or not loaded.get("success"):
        return {
            "success": False,
            "error": (loaded or {}).get("error") or f"Failed to load SKILL.md for '{pack_id}'",
            "skill_id": skill_id,
            "pack_id": pack_id,
            "body_loaded": False,
        }

    return {
        "success": True,
        "skill_id": skill_id,
        "pack_id": pack_id,
        "title": loaded.get("name") or pack_id,
        "description": loaded.get("description") or "",
        "path": loaded.get("path"),
        "body": loaded.get("instructions") or "",
        "tools": loaded.get("tools") or [],
        "body_loaded": True,
    }
