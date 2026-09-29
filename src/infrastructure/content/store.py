"""Agents and skills are files (CARD-570, ADR-0062).

Shipped content is read in place from the repo ``platform/`` folder:

- ``platform/agents/<id>.md``: YAML frontmatter (name, description, tone, purpose, avatar,
  show_in_chat, max_turns, skills) and the system prompt as the body.
- ``platform/skills/<id>/SKILL.md``: frontmatter with ``tools:``, the only skill -> tool list.

A Studio save writes a full user copy to the data dir (``agents/<id>.md`` or
``skills/<id>/SKILL.md``). A user copy wins by id; there is no field merging. The copy records
``based_on`` (hash of the shipped file when copied) so Studio can say the shipped version changed.
"Use shipped version" deletes the copy. Deleting a shipped item hides it (``.hidden.json``);
deleting a user-created item removes its file. Shipped ids are reserved for new items.

No old-format readers before 1.0: a format change comes with a wipe or "Use shipped version".
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

logger = logging.getLogger(__name__)

REPO_PLATFORM = Path(__file__).resolve().parents[3] / "platform"
HIDDEN_FILE = ".hidden.json"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ReservedIdError(ValueError):
    """A new custom agent or skill tried to take a shipped id."""


class InvalidIdError(ValueError):
    """Ids are lowercase letters, digits, - and _."""


def content_hash(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    clean = text.replace("\r\n", "\n")
    if not clean.startswith("---\n"):
        return {}, clean
    parts = clean.split("---\n", 2)
    if len(parts) < 3:
        return {}, clean
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        logger.warning("Unreadable frontmatter: %s", exc)
        meta = {}
    return (meta if isinstance(meta, dict) else {}), parts[2]


def join_frontmatter(meta: dict[str, Any], body: str) -> str:
    head = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=10000)
    return f"---\n{head}---\n{body.strip()}\n"


def check_id(item_id: str) -> str:
    clean = str(item_id or "").strip()
    if not _ID_RE.match(clean):
        raise InvalidIdError(f"Invalid id {clean!r}: use lowercase letters, digits, '-' or '_'.")
    return clean


@dataclass
class ContentFile:
    """One agent or skill as loaded: the winning file (user copy or shipped)."""

    id: str
    kind: str  # "agent" | "skill"
    meta: dict[str, Any]
    body: str
    path: Path
    source: str  # "shipped" | "user"
    shipped: bool  # a shipped file with this id exists
    shipped_hash: Optional[str] = None
    based_on: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def edited(self) -> bool:
        return self.source == "user" and self.shipped

    @property
    def shipped_changed(self) -> bool:
        return bool(self.edited and self.based_on and self.shipped_hash and self.based_on != self.shipped_hash)

    @property
    def tools(self) -> list[str]:
        raw = self.meta.get("tools") or []
        if isinstance(raw, str):
            raw = [t for t in re.split(r"[\s,]+", raw) if t]
        return [str(t).strip() for t in raw if str(t).strip()]

    @property
    def skills(self) -> list[str]:
        return [str(s).strip() for s in (self.meta.get("skills") or []) if str(s).strip()]

    def status(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "shipped": self.shipped,
            "edited": self.edited,
            "shipped_changed": self.shipped_changed,
            "warnings": list(self.warnings),
        }


class _Kind:
    def __init__(self, kind: str, shipped_dir: Path, user_dir: Optional[Path]):
        self.kind = kind
        self.shipped_dir = shipped_dir
        self.user_dir = user_dir

    # paths -------------------------------------------------------------------------------------
    def _file(self, base: Path, item_id: str) -> Path:
        return base / f"{item_id}.md" if self.kind == "agent" else base / item_id / "SKILL.md"

    def shipped_path(self, item_id: str) -> Path:
        return self._file(self.shipped_dir, item_id)

    def user_path(self, item_id: str) -> Optional[Path]:
        return self._file(self.user_dir, item_id) if self.user_dir else None

    def _ids(self, base: Optional[Path]) -> list[str]:
        if not base or not base.is_dir():
            return []
        if self.kind == "agent":
            return sorted(p.stem for p in base.glob("*.md") if not p.name.startswith("."))
        return sorted(p.name for p in base.iterdir() if (p / "SKILL.md").is_file())

    def shipped_ids(self) -> list[str]:
        return self._ids(self.shipped_dir)

    def user_ids(self) -> list[str]:
        return self._ids(self.user_dir)

    # hidden ------------------------------------------------------------------------------------
    def hidden(self) -> set[str]:
        path = self.user_dir / HIDDEN_FILE if self.user_dir else None
        if not path or not path.is_file():
            return set()
        try:
            return {str(x) for x in json.loads(path.read_text(encoding="utf-8")) or []}
        except (OSError, ValueError):
            return set()

    def _write_hidden(self, ids: Iterable[str]) -> None:
        if not self.user_dir:
            return
        self.user_dir.mkdir(parents=True, exist_ok=True)
        (self.user_dir / HIDDEN_FILE).write_text(json.dumps(sorted(set(ids)), indent=2), encoding="utf-8")

    # load --------------------------------------------------------------------------------------
    def shipped_hash(self, item_id: str) -> Optional[str]:
        path = self.shipped_path(item_id)
        return content_hash(path.read_text(encoding="utf-8")) if path.is_file() else None

    def load(self, item_id: str, include_hidden: bool = False) -> Optional[ContentFile]:
        clean = str(item_id or "").strip()
        if not clean:
            return None
        shipped = self.shipped_path(clean).is_file()
        if shipped and not include_hidden and clean in self.hidden():
            return None
        user = self.user_path(clean)
        path, source = (user, "user") if user and user.is_file() else (self.shipped_path(clean), "shipped")
        if not path.is_file():
            return None
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        based_on = meta.pop("based_on", None) if source == "user" else None
        return ContentFile(
            id=clean,
            kind=self.kind,
            meta=meta,
            body=body,
            path=path,
            source=source,
            shipped=shipped,
            shipped_hash=self.shipped_hash(clean) if shipped else None,
            based_on=str(based_on) if based_on else None,
        )

    def list(self, include_hidden: bool = False) -> list[ContentFile]:
        ids = list(dict.fromkeys(self.shipped_ids() + self.user_ids()))
        out = [self.load(i, include_hidden=include_hidden) for i in ids]
        return [f for f in out if f is not None]

    # write -------------------------------------------------------------------------------------
    def save(self, item_id: str, meta: dict[str, Any], body: str, *, create: bool = False) -> ContentFile:
        """Write the full user copy. ``create`` refuses shipped ids (reserved) and existing ids."""
        clean = check_id(item_id)
        if not self.user_dir:
            raise RuntimeError("No data dir: cannot save a user copy.")
        shipped = self.shipped_path(clean).is_file()
        user = self.user_path(clean)
        if create:
            if shipped:
                raise ReservedIdError(f"'{clean}' is a shipped {self.kind} id; pick another id.")
            if user.is_file():
                raise ReservedIdError(f"A {self.kind} named '{clean}' already exists.")
        clean_meta = {k: v for k, v in dict(meta).items() if k not in ("based_on", "id")}
        if self.kind == "skill" and _SKILL_WRITE_GUARD is not None:
            clean_meta = _hold_tool_additions(self, clean, clean_meta)
        if shipped:
            clean_meta["based_on"] = self.shipped_hash(clean)
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(join_frontmatter(clean_meta, body), encoding="utf-8", newline="\n")
        if shipped:
            self._write_hidden(self.hidden() - {clean})
        loaded = self.load(clean, include_hidden=True)
        assert loaded is not None
        return loaded

    def use_shipped(self, item_id: str) -> bool:
        """Delete the user copy of a shipped item. Returns False when there is nothing to delete."""
        clean = str(item_id or "").strip()
        user = self.user_path(clean)
        if not self.shipped_path(clean).is_file() or not user or not user.is_file():
            return False
        self._remove_user(clean)
        return True

    def _remove_user(self, item_id: str) -> None:
        user = self.user_path(item_id)
        if not user or not user.is_file():
            return
        if self.kind == "skill":
            shutil.rmtree(user.parent, ignore_errors=True)
        else:
            user.unlink()

    def delete(self, item_id: str) -> str:
        """Shipped -> hidden (persisted); user-created -> file removed. Returns 'hidden'/'deleted'/'missing'."""
        clean = str(item_id or "").strip()
        if self.shipped_path(clean).is_file():
            self._write_hidden(self.hidden() | {clean})
            return "hidden"
        user = self.user_path(clean)
        if user and user.is_file():
            self._remove_user(clean)
            return "deleted"
        return "missing"

    def unhide(self, item_id: str) -> bool:
        clean = str(item_id or "").strip()
        hidden = self.hidden()
        if clean not in hidden:
            return False
        self._write_hidden(hidden - {clean})
        return True


class ContentStore:
    """Shipped agents/skills from ``platform/``, user copies from the data dir."""

    def __init__(self, data_root: Optional[Path] = None, platform_root: Optional[Path] = None):
        self.platform_root = Path(platform_root) if platform_root else REPO_PLATFORM
        self.data_root = Path(data_root) if data_root else None
        self.agents = _Kind(
            "agent", self.platform_root / "agents", self.data_root / "agents" if self.data_root else None
        )
        self.skills = _Kind(
            "skill", self.platform_root / "skills", self.data_root / "skills" if self.data_root else None
        )

    def skill_tools(self, skill_ids: Iterable[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for sid in skill_ids:
            loaded = self.skills.load(sid)
            out[sid] = list(dict.fromkeys(loaded.tools)) if loaded else []
        return out

    def set_skill_tools(self, skill_id: str, tools: Iterable[str]) -> ContentFile:
        """Write the skill's user copy with a new ``tools:`` list (the proposal accept path)."""
        loaded = self.skills.load(skill_id, include_hidden=True)
        if loaded is None:
            raise LookupError(skill_id)
        meta = dict(loaded.meta)
        meta["tools"] = list(dict.fromkeys(str(t) for t in tools if str(t).strip()))
        return self.skills.save(skill_id, meta, loaded.body)

    def validate_tools(self, known: Iterable[str]) -> dict[str, list[str]]:
        """Unknown tool ids per skill. An unknown id is a warning and grants nothing."""
        names = set(known)
        bad: dict[str, list[str]] = {}
        for skill in self.skills.list(include_hidden=True):
            missing = [t for t in skill.tools if not _known(t, names)]
            if missing:
                bad[skill.id] = missing
        return bad


def _hold_tool_additions(kind: "_Kind", skill_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Tools a write adds to a skill are held back when the guard says the writer is an agent.

    The guard (installed at boot, see ``tool_attachment.make_skill_write_guard``) turns each held
    tool into a pending proposal for Jacob. A hidden skill counts as granting nothing.
    """
    new = [str(t) for t in (meta.get("tools") or []) if str(t).strip()]
    current = kind.load(skill_id)
    old = set(current.tools) if current else set()
    added = [t for t in new if t not in old]
    if not added or _SKILL_WRITE_GUARD is None or not _SKILL_WRITE_GUARD(skill_id, added):
        return meta
    held = dict(meta)
    held["tools"] = [t for t in new if t not in added]
    return held


def _known(tool: str, names: set[str]) -> bool:
    if tool.endswith("*"):
        return True  # wildcard bindings such as mcp_files_* match mounted MCP tools at run time
    return tool in names


_STORE: Optional[ContentStore] = None
_TOOL_REGISTRY: Any = None
_SKILL_WRITE_GUARD: Any = None


def set_skill_write_guard(guard: Any) -> None:
    """``guard(skill_id, added_tools) -> bool``: True holds the additions (agent writer) [CARD-570]."""
    global _SKILL_WRITE_GUARD
    _SKILL_WRITE_GUARD = guard


def configure(data_root: Optional[Path], platform_root: Optional[Path] = None) -> ContentStore:
    global _STORE
    _STORE = ContentStore(data_root=data_root, platform_root=platform_root)
    return _STORE


def set_tool_registry(registry: Any) -> None:
    """Called at boot; later lookups drop tool ids the registry does not know (grants nothing)."""
    global _TOOL_REGISTRY
    _TOOL_REGISTRY = registry


def is_known_tool(name: str) -> bool:
    """True when no registry is configured (plain unit tests) or the live registry has the tool."""
    if _TOOL_REGISTRY is None or name.endswith("*"):
        return True
    try:
        return _TOOL_REGISTRY.get_tool_definition(name) is not None
    except Exception:
        return True


def get_store() -> ContentStore:
    global _STORE
    if _STORE is None:
        root: Optional[Path] = None
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            root = DataDirResolver().resolve().root
        except Exception:
            root = None
        _STORE = ContentStore(data_root=root)
    return _STORE


def reset_store() -> None:
    global _STORE, _TOOL_REGISTRY, _SKILL_WRITE_GUARD
    _STORE = None
    _TOOL_REGISTRY = None
    _SKILL_WRITE_GUARD = None
