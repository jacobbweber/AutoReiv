"""Skill Studio workshop persistence: SKILL.md files; ``tools:`` is the only tool list [CARD-411, CARD-570]."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from src.application.skills.runbook_frontmatter import (
    apply_workshop_metadata,
    frontmatter_view,
    split_skill_markdown,
)
from src.application.skills.user_catalog import ARCHIVE_DIRNAME
from src.infrastructure.content.store import get_store, split_frontmatter

# Same jail as user skills: letters, digits, dot, underscore, hyphen, nested segments.
_SKILL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$")
_SKIP_SEGMENTS = frozenset({"snapshots", "_archive", ".", ".."})


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


def accept_skill_id(skill_id: str) -> Optional[str]:
    """Return a jailed skill id, or None when the id cannot name a runbook file."""
    raw = (skill_id or "").strip().replace("\\", "/").strip("/")
    if not raw or not _SKILL_ID_RE.match(raw):
        return None
    parts = raw.split("/")
    if any(part in _SKIP_SEGMENTS for part in parts):
        return None
    return raw


def _id_under_skills_dir(skills_dir: Path, skill_file: Path) -> Optional[str]:
    try:
        rel = skill_file.parent.relative_to(skills_dir).as_posix()
    except ValueError:
        return None
    if not rel or rel == ".":
        return None
    return accept_skill_id(rel)


def locate_skill_markdown(
    data_root: Path,
    skill_id: str,
    agent_id: Optional[str] = None,
) -> Optional[Path]:
    """Resolve a picker id to the winning SKILL.md: data ``skills/`` copy, else ``platform/skills``."""
    clean = accept_skill_id(skill_id)
    if not clean:
        return None
    loaded = get_store().skills.load(clean, include_hidden=True)
    if loaded is not None:
        return loaded.path
    direct = Path(data_root) / "skills" / clean / "SKILL.md"
    return direct if direct.is_file() else None

def operator_skill_deletable(data_root: Path, skill_id: str, path: Optional[Path] = None) -> bool:
    """True only for an operator skill-store file that is not a bundled seed."""
    clean = accept_skill_id(skill_id) or ""
    if not clean or get_store().skills.shipped_path(clean.split("/")[0]).is_file():
        return False
    if path is None:
        return False
    skills_root = (Path(data_root) / "skills").resolve()
    try:
        relative = Path(path).resolve().relative_to(skills_root)
    except ValueError:
        return False
    if ARCHIVE_DIRNAME in relative.parts:
        return False
    return Path(path).is_file()


def clear_operator_skill_side_effects(
    data_root: Path,
    skill_id: str,
    db_path: Optional[str] = None,
) -> None:
    """Nothing else holds a skill's tools since CARD-570 (the SKILL.md is the only source)."""
    return None

def _row_for_skill_file(path: Path, skill_id: str, source: str, data_root: Path) -> dict[str, Any]:
    view = frontmatter_view(_read_text(path) or "")
    name = str(view.get("name") or "").strip() or skill_id
    description = str(view.get("description") or "").strip()
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "source": source,
        "tools": list(view.get("tools") or []),
        "deletable": operator_skill_deletable(data_root, skill_id, path) if source == "store" else False,
    }


def list_workshop_skills(data_root: Path) -> list[dict[str, str]]:
    """Skills the workshop loader can open: user copies/user skills, then shipped platform skills."""
    root = Path(data_root)
    found: dict[str, dict[str, str]] = {}
    hidden = get_store().skills.hidden()
    for item in get_store().skills.list(include_hidden=True):
        source = "store" if item.source == "user" else "platform"
        found[item.id] = _row_for_skill_file(item.path, item.id, source, root)
        if item.id in hidden:
            found[item.id]["hidden"] = True  # still openable in Skill Studio so it can be unhidden
    skills_root = root / "skills"
    if skills_root.is_dir():
        for skill_file in sorted(skills_root.glob("**/SKILL.md")):
            if any(part in _SKIP_SEGMENTS for part in skill_file.relative_to(skills_root).parts[:-1]):
                continue
            skill_id = _id_under_skills_dir(skills_root, skill_file)
            if skill_id and skill_id not in found:
                found[skill_id] = _row_for_skill_file(skill_file, skill_id, "store", root)
    return [found[key] for key in sorted(found)]

def operator_store_skills(data_root: Path) -> list[dict[str, Any]]:
    """Operator skill-store files. Platform seeds and skill homes stay out of this list."""
    rows: list[dict[str, Any]] = []
    for row in list_workshop_skills(data_root):
        if row.get("source") != "store" or row.get("deletable") is not True:
            continue
        skill_id = str(row.get("id") or "").strip()
        if not skill_id:
            continue
        tools = [str(item).strip() for item in (row.get("tools") or []) if str(item).strip()]
        rows.append(
            {
                "id": skill_id,
                "name": str(row.get("name") or skill_id),
                "description": str(row.get("description") or ""),
                "tools": tools,
            }
        )
    return rows


def load_workshop_skill(
    data_root: Path,
    skill_id: str,
    *,
    agent_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    clean = accept_skill_id(skill_id)
    if not clean:
        return None
    path = locate_skill_markdown(data_root, clean, agent_id=agent_id)
    if path is None:
        return None
    raw = _read_text(path) or ""
    view = frontmatter_view(raw)
    view["binding_source"] = "frontmatter"
    loaded = get_store().skills.load(clean, include_hidden=True)
    if loaded is not None:
        view["status"] = {**loaded.status(), "hidden": clean in get_store().skills.hidden()}
    view["skill_id"] = clean
    view["path"] = str(path)
    view["markdown_content"] = raw
    view["deletable"] = operator_skill_deletable(data_root, clean, path)
    return view



def workshop_skill_occupancy(data_root: Path, skill_id: str) -> Optional[dict[str, str]]:
    """Return {id, name} when a workshop-visible skill already uses this id [CARD-628]."""
    clean = accept_skill_id(skill_id)
    if not clean:
        return None
    view = load_workshop_skill(data_root, clean)
    if not view:
        return None
    name = str(view.get("name") or "").strip() or clean
    return {"id": clean, "name": name}


def suggest_free_skill_id(data_root: Path, skill_id: str) -> str:
    """Next free id: base, then base_2, base_3, ... [CARD-628]."""
    clean = accept_skill_id(skill_id) or str(skill_id or "").strip().lower()
    if not clean:
        return "skill"
    if workshop_skill_occupancy(data_root, clean) is None:
        return clean
    for n in range(2, 100):
        cand = f"{clean}_{n}"
        if workshop_skill_occupancy(data_root, cand) is None:
            return cand
    return f"{clean}_new"


def persist_workshop_skill(
    *,
    data_root: Path,
    agent_id: Optional[str],
    skill_id: str,
    skill_content: str,
    catalog_ids: Iterable[str],
    name: Optional[str] = None,
    description: Optional[str] = None,
    tier: Optional[str] = None,
    safety: Optional[dict[str, Any]] = None,
    tools: Optional[Sequence[str]] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Write the SKILL.md user copy (data ``skills/<id>``); its ``tools:`` is the only tool list.

    Raises UnknownCatalogToolError before any write when a tool id is not in the catalog.
    """
    catalog = list(catalog_ids)
    rendered, view = apply_workshop_metadata(
        skill_content,
        name=name,
        description=description,
        tier=tier,
        safety=safety,
        tools=tools,
        catalog_ids=catalog,
    )
    if not rendered.endswith("\n"):
        rendered += "\n"

    meta, body = split_frontmatter(rendered)
    meta["tools"] = list(view["tools"])
    content = get_store()
    if content.data_root is not None and Path(content.data_root).resolve() == Path(data_root).resolve():
        saved = content.skills.save(skill_id, meta, body)
        store_file = saved.path
        rendered = store_file.read_text(encoding="utf-8")
    else:
        from src.infrastructure.content.store import join_frontmatter

        store_file = data_root / "skills" / skill_id / "SKILL.md"
        store_file.parent.mkdir(parents=True, exist_ok=True)
        rendered = join_frontmatter(meta, body)
        store_file.write_text(rendered, encoding="utf-8")
    return {
        "markdown": rendered,
        "frontmatter": view,
        "tools": list(view["tools"]),
        "tier": view["tier"],
        "safety": view["safety"],
        "skill_store_path": str(store_file),
        "user_skill_path": None,
        "binding_store": "skill_md",
    }


def extract_tools(skill_content: str) -> list[str]:
    meta, _body = split_skill_markdown(skill_content)
    raw = meta.get("tools") if meta.get("tools") is not None else meta.get("tools") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
