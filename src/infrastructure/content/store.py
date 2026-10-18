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

from src.domain.frontmatter import join_frontmatter, split_frontmatter

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


CONSOLIDATED_SKILL_ALIASES: dict[str, str] = {
    "agent-authoring": "capability-authoring",
    "native-tool-engineering": "capability-authoring",
    "project-orientation": "project-cards",
    "brainstorm": "project-cards",
    "card-intake": "project-cards",
    "card-writing": "project-cards",
    "plan-change": "project-cards",
    "hand-off": "project-cards",
    "review": "project-cards",
    "implement-change": "software-development",
    "write-tests": "software-development",
    "debug": "software-development",
    "run-checks": "software-development",
    "git-workflow": "software-development",
    "code-review": "software-development",
    "codebase-audit": "software-development",
    "journey-qa": "software-development",
}


RETIRED_SHIPPED_AGENT_IDS: frozenset[str] = frozenset({"architect", "developer", "toolsmith"})
_STALE_RETIRED_AGENT_PROMPT_RE = re.compile(
    r"\b(?:Developer/Toolsmith|Toolsmith/Developer|open\s+(?:Developer|Toolsmith|Architect)\s+in\s+Chat|"
    r"route\s+to\s+(?:the\s+)?(?:Developer|Toolsmith|Architect)|skill_view\(skill_id=[\"']agent-authoring[\"']\))\b",
    re.IGNORECASE,
)


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
        ids = self._ids(self.user_dir)
        if self.kind == "agent" and self.shipped_dir == REPO_PLATFORM / "agents":
            ids = [i for i in ids if not self._is_retired_shipped_user_copy(i)]
        return ids

    def _is_retired_shipped_user_copy(self, item_id: str) -> bool:
        if item_id not in RETIRED_SHIPPED_AGENT_IDS:
            return False
        user = self.user_path(item_id)
        if not user or not user.is_file():
            return False
        try:
            meta, _ = split_frontmatter(user.read_text(encoding="utf-8"))
        except OSError:
            return False
        return bool(meta.get("based_on"))

    def _reconcile_user_agent(
        self,
        item_id: str,
        user_file: Path,
        meta: dict[str, Any],
        body: str,
        based_on: Optional[str],
        s_hash: Optional[str],
    ) -> tuple[dict[str, Any], str, Optional[str]]:
        if (
            self.kind != "agent"
            or item_id != "autoreiv"
            or self.shipped_dir != REPO_PLATFORM / "agents"
            or not s_hash
            or based_on == s_hash
        ):
            return meta, body, based_on
        shipped_file = self.shipped_path(item_id)
        if not shipped_file.is_file():
            return meta, body, based_on
        shipped_meta, shipped_body = split_frontmatter(shipped_file.read_text(encoding="utf-8"))
        shipped_skills = [str(s).strip() for s in (shipped_meta.get("skills") or []) if str(s).strip()]
        raw_skills = [str(s).strip() for s in (meta.get("skills") or []) if str(s).strip()]
        normalized = [CONSOLIDATED_SKILL_ALIASES.get(s, s) for s in raw_skills]
        consolidated_req = {"capability-authoring", "project-cards", "software-development", "web-search", "user:*"}
        missing_consolidated = not consolidated_req.issubset(set(normalized)) and "*" not in normalized
        stale_prompt = bool(_STALE_RETIRED_AGENT_PROMPT_RE.search(body or ""))
        if not missing_consolidated and not stale_prompt and normalized == raw_skills:
            return meta, body, based_on
        merged_skills = list(dict.fromkeys(normalized + shipped_skills))
        new_meta = dict(meta)
        new_meta["skills"] = merged_skills
        new_body = shipped_body if stale_prompt else body
        persisted_meta = dict(new_meta)
        persisted_meta["based_on"] = s_hash
        try:
            user_file.write_text(join_frontmatter(persisted_meta, new_body), encoding="utf-8", newline="\n")
        except OSError:
            pass
        return new_meta, new_body, s_hash

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
        if self.kind == "agent" and self.shipped_dir == REPO_PLATFORM / "agents" and self._is_retired_shipped_user_copy(clean):
            return None
        shipped = self.shipped_path(clean).is_file()
        if shipped and not include_hidden and clean in self.hidden():
            return None
        user = self.user_path(clean)
        path, source = (user, "user") if user and user.is_file() else (self.shipped_path(clean), "shipped")
        if not path.is_file():
            if self.kind == "skill" and clean in CONSOLIDATED_SKILL_ALIASES and self.shipped_dir == REPO_PLATFORM / "skills":
                alias_target = CONSOLIDATED_SKILL_ALIASES[clean]
                aliased = self.load(alias_target, include_hidden=include_hidden)
                if aliased is not None:
                    return ContentFile(
                        id=clean,
                        kind=aliased.kind,
                        meta=dict(aliased.meta),
                        body=aliased.body,
                        path=aliased.path,
                        source=aliased.source,
                        shipped=aliased.shipped,
                        shipped_hash=aliased.shipped_hash,
                        based_on=aliased.based_on,
                        warnings=list(aliased.warnings),
                    )
            return None
        raw_text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw_text)
        based_on = meta.pop("based_on", None) if source == "user" else None
        s_hash = (content_hash(raw_text) if source == "shipped" else self.shipped_hash(clean)) if shipped else None
        if source == "user" and user is not None:
            meta, body, based_on = self._reconcile_user_agent(
                clean, user, meta, body, str(based_on) if based_on else None, s_hash
            )
        return ContentFile(
            id=clean,
            kind=self.kind,
            meta=meta,
            body=body,
            path=path,
            source=source,
            shipped=shipped,
            shipped_hash=s_hash,
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
        from src.application.skills.agora_loader import enabled_colocated_tool_names

        out: dict[str, list[str]] = {}
        for sid in skill_ids:
            loaded = self.skills.load(sid)
            if loaded is None:
                out[sid] = []
                continue
            combined = list(loaded.tools) + enabled_colocated_tool_names(self, sid)
            out[sid] = list(dict.fromkeys(combined))
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
    if not added or _SKILL_WRITE_GUARD is None:
        return meta
    verdict = _SKILL_WRITE_GUARD(skill_id, added)
    if not verdict:
        return meta
    held_set = set(verdict) if isinstance(verdict, (list, set, tuple, frozenset)) else set(added)
    held = dict(meta)
    held["tools"] = [t for t in new if t not in held_set]
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
        return False


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
