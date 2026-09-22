"""Factory workshop persistence: skill-store body + SQLite bindings [CARD-411]."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from src.application.skills.runbook_frontmatter import (
    apply_workshop_metadata,
    frontmatter_view,
    split_skill_markdown,
)
from src.application.skills.user_catalog import ARCHIVE_DIRNAME, PackJailError, UserSkillCatalog
from src.infrastructure.data.resolver import repo_root
from src.infrastructure.memory.repositories.skill_bindings import (
    SkillToolBindingRepository,
    operational_db_path,
    sqlite_tools_for_skills,
)
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS

# Same jail as user skill packs: letters, digits, dot, underscore, hyphen, nested segments.
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
    """Resolve a picker id to SKILL.md.

    Order: operator skill store, that agent's pack home, any pack home,
    repo platform-packs, then bundled seeds (same roots as the skill catalog).
    """
    clean = accept_skill_id(skill_id)
    if not clean:
        return None
    root = Path(data_root)
    catalog = UserSkillCatalog(skills_dir=root / "skills")
    try:
        direct = catalog.resolve_skill_md(clean)
    except PackJailError:
        direct = None
    if direct is not None and direct.is_file():
        return direct

    leaf = clean.split("/")[-1]
    agent = accept_skill_id(agent_id or "")
    if agent and "/" not in agent:
        for relative in (clean, leaf):
            pack_file = root / "packs" / agent / "skills" / relative / "SKILL.md"
            if pack_file.is_file():
                return pack_file

    # Pack homes, platform-packs, and src/infrastructure/skills/seeds.
    return catalog.resolve_pack_scoped_skill_md(clean)


def operator_skill_deletable(data_root: Path, skill_id: str, path: Optional[Path] = None) -> bool:
    """True only for an operator skill-store file that is not a bundled seed."""
    clean = accept_skill_id(skill_id) or ""
    if not clean or clean in BUNDLED_PACK_IDS or clean.split("/")[0] in BUNDLED_PACK_IDS:
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
    """After the user-pack delete, drop pack projections and SQLite bindings for that id."""
    clean = accept_skill_id(skill_id)
    if not clean:
        return
    packs_root = (Path(data_root) / "packs").resolve()
    if packs_root.is_dir():
        for agent_dir in packs_root.iterdir():
            if not agent_dir.is_dir():
                continue
            target = (agent_dir / "skills" / clean).resolve()
            try:
                target.relative_to(packs_root)
            except ValueError:
                continue
            if target.is_dir():
                shutil.rmtree(target)
    resolved_db = operational_db_path(db_path or os.environ.get("AUTOREIV_DB_PATH"))
    if resolved_db:
        SkillToolBindingRepository(db_path=resolved_db).delete(clean)


def _row_for_skill_file(path: Path, skill_id: str, source: str, data_root: Path) -> dict[str, Any]:
    view = frontmatter_view(_read_text(path) or "")
    name = str(view.get("name") or "").strip() or skill_id
    description = str(view.get("description") or "").strip()
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "source": source,
        "deletable": operator_skill_deletable(data_root, skill_id, path) if source == "store" else False,
    }


def list_workshop_skills(data_root: Path) -> list[dict[str, str]]:
    """Skills the workshop loader can open. Picker options come from this list only."""
    root = Path(data_root)
    found: dict[str, dict[str, str]] = {}

    def add(skill_id: str, path: Path, source: str, *, overwrite: bool = False) -> None:
        if skill_id in found and not overwrite:
            return
        if not path.is_file():
            return
        found[skill_id] = _row_for_skill_file(path, skill_id, source, root)

    skills_root = root / "skills"
    if skills_root.is_dir():
        for skill_file in sorted(skills_root.glob("**/SKILL.md")):
            if any(part in _SKIP_SEGMENTS for part in skill_file.relative_to(skills_root).parts[:-1]):
                continue
            skill_id = _id_under_skills_dir(skills_root, skill_file)
            if skill_id:
                add(skill_id, skill_file, "store", overwrite=True)

    packs_root = root / "packs"
    if packs_root.is_dir():
        for agent_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            skills_dir = agent_dir / "skills"
            if not skills_dir.is_dir():
                continue
            for skill_file in sorted(skills_dir.glob("**/SKILL.md")):
                skill_id = _id_under_skills_dir(skills_dir, skill_file)
                if skill_id:
                    add(skill_id, skill_file, "pack")

    checkout = repo_root()
    platform_root = checkout / "platform-packs"
    if platform_root.is_dir():
        for pack_dir in sorted(p for p in platform_root.iterdir() if p.is_dir()):
            skills_dir = pack_dir / "skills"
            if not skills_dir.is_dir():
                continue
            for skill_file in sorted(skills_dir.glob("**/SKILL.md")):
                skill_id = _id_under_skills_dir(skills_dir, skill_file)
                if skill_id:
                    add(skill_id, skill_file, "platform")

    seeds_root = checkout / "src" / "infrastructure" / "skills" / "seeds"
    if seeds_root.is_dir():
        for skill_file in sorted(seeds_root.glob("*/SKILL.md")):
            skill_id = accept_skill_id(skill_file.parent.name)
            if skill_id:
                add(skill_id, skill_file, "seed")

    return [found[key] for key in sorted(found)]


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
    bindings = sqlite_tools_for_skills([clean], db_path=db_path)
    if clean in bindings:
        view["requires_tools"] = list(bindings[clean])
        view["binding_source"] = "sqlite"
    else:
        view["binding_source"] = "frontmatter"
    view["skill_id"] = clean
    view["path"] = str(path)
    view["markdown_content"] = raw
    view["deletable"] = operator_skill_deletable(data_root, clean, path)
    return view


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
    requires_tools: Optional[Sequence[str]] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Write one SKILL.md projection to the skill store and bind tools in SQLite.

    When agent_id is set, also copy the runbook into that agent's pack home.
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
    store_file.parent.mkdir(parents=True, exist_ok=True)
    store_file.write_text(rendered, encoding="utf-8")

    pack_path: Optional[str] = None
    clean_agent = (agent_id or "").strip()
    if clean_agent:
        pack_file = data_root / "packs" / clean_agent / "skills" / skill_id / "SKILL.md"
        pack_file.parent.mkdir(parents=True, exist_ok=True)
        pack_file.write_text(rendered, encoding="utf-8")
        pack_path = str(pack_file)

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
        "pack_skill_path": pack_path,
        "binding_store": "sqlite",
    }


def extract_requires_tools(skill_content: str) -> list[str]:
    meta, _body = split_skill_markdown(skill_content)
    raw = meta.get("requires_tools") if meta.get("requires_tools") is not None else meta.get("tools") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
