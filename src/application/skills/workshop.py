"""Factory workshop persistence: skill-store body + SQLite bindings [CARD-411]."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from src.application.skills.runbook_frontmatter import (
    apply_workshop_metadata,
    frontmatter_view,
    split_skill_markdown,
)
from src.infrastructure.memory.repositories.skill_bindings import SkillToolBindingRepository, operational_db_path


def catalog_tool_ids(tool_registry: Any) -> list[str]:
    if tool_registry is None:
        return []
    names: list[str] = []
    lister = getattr(tool_registry, "list_tools", None)
    tools = lister() if callable(lister) else []
    for tool in tools or []:
        name = getattr(tool, "name", None) or (tool.get("name") if isinstance(tool, dict) else None)
        if name and str(name) not in names:
            names.append(str(name))
    return names


def _read_text(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        return None
    return None


def locate_skill_markdown(
    data_root: Path,
    skill_id: str,
    agent_id: Optional[str] = None,
) -> Optional[Path]:
    """Prefer the operator skill store, then the agent pack home, then platform seeds."""
    clean_skill = (skill_id or "").strip()
    if not clean_skill or "/" in clean_skill or ".." in clean_skill:
        return None
    store_path = data_root / "skills" / clean_skill / "SKILL.md"
    if store_path.is_file():
        return store_path
    if agent_id:
        pack_path = data_root / "packs" / agent_id / "skills" / clean_skill / "SKILL.md"
        if pack_path.is_file():
            return pack_path
    packs_dir = data_root / "packs"
    if packs_dir.is_dir():
        for candidate in packs_dir.glob(f"*/skills/{clean_skill}/SKILL.md"):
            if candidate.is_file():
                return candidate
    repo_root = Path(__file__).resolve().parents[3]
    platform_root = repo_root / "platform-packs"
    if platform_root.is_dir():
        for candidate in platform_root.glob(f"*/skills/{clean_skill}/SKILL.md"):
            if candidate.is_file():
                return candidate
    return None


def load_workshop_skill(
    data_root: Path,
    skill_id: str,
    *,
    agent_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    path = locate_skill_markdown(data_root, skill_id, agent_id=agent_id)
    if path is None:
        return None
    raw = _read_text(path) or ""
    view = frontmatter_view(raw)
    bindings = SkillToolBindingRepository(db_path=db_path).tools_for_skills([skill_id])
    if skill_id in bindings:
        view["requires_tools"] = list(bindings[skill_id])
        view["binding_source"] = "sqlite"
    else:
        view["binding_source"] = "frontmatter"
    view["skill_id"] = skill_id
    view["path"] = str(path)
    view["markdown_content"] = raw
    return view


def persist_workshop_skill(
    *,
    data_root: Path,
    agent_id: str,
    skill_id: str,
    skill_content: str,
    catalog_ids: Iterable[str],
    name: Optional[str] = None,
    description: Optional[str] = None,
    tier: Optional[str] = None,
    safety: Optional[dict[str, Any]] = None,
    requires_tools: Optional[Sequence[str]] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Write one SKILL.md projection to the skill store and the agent pack home, and bind tools in SQLite.

    Raises UnknownCatalogToolError before any write when a tool id is not in the catalog.
    """
    catalog = list(catalog_ids)
    rendered, view = apply_workshop_metadata(
        skill_content,
        name=name,
        description=description,
        tier=tier,
        safety=safety,
        requires_tools=requires_tools,
        catalog_ids=catalog,
    )
    if not rendered.endswith("\n"):
        rendered += "\n"

    store_file = data_root / "skills" / skill_id / "SKILL.md"
    pack_file = data_root / "packs" / agent_id / "skills" / skill_id / "SKILL.md"
    store_file.parent.mkdir(parents=True, exist_ok=True)
    pack_file.parent.mkdir(parents=True, exist_ok=True)
    store_file.write_text(rendered, encoding="utf-8")
    pack_file.write_text(rendered, encoding="utf-8")

    resolved_db = operational_db_path(db_path or os.environ.get("AUTOREIV_DB_PATH"))
    record = SkillToolBindingRepository(db_path=resolved_db).replace(
        skill_id,
        view["requires_tools"],
        tier=view["tier"],
        safety=view["safety"],
    )
    return {
        "markdown": rendered,
        "frontmatter": view,
        "requires_tools": list(record.get("requires_tools") or []),
        "tier": record.get("tier") or view["tier"],
        "safety": record.get("safety") or view["safety"],
        "skill_store_path": str(store_file),
        "pack_skill_path": str(pack_file),
        "binding_store": "sqlite",
    }


def extract_requires_tools(skill_content: str) -> list[str]:
    meta, _body = split_skill_markdown(skill_content)
    raw = meta.get("requires_tools") if meta.get("requires_tools") is not None else meta.get("tools") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
