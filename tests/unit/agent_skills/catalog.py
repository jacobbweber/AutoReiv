"""Helpers to load the shipped agent files (``platform/agents/<id>.md``) in tests (CARD-570)."""

from pathlib import Path
from types import SimpleNamespace

from src.infrastructure.content.store import (
    CONSOLIDATED_SKILL_ALIASES,
    REPO_PLATFORM,
    ContentFile,
    ContentStore,
)

PLATFORM_SKILL_IDS = ("autoreiv", "tutor", "direct")

_LEGACY_RETIRED_AGENT_SPECS: dict[str, dict] = {
    "developer": {
        "name": "Developer",
        "description": "Retired coding worker persona (consolidated into AutoReiv software-development + project-cards; ADR-0066).",
        "tone": "concise",
        "purpose": "coding",
        "avatar": "code-2",
        "show_in_chat": True,
        "max_turns": 25,
        "skills": ["project-cards", "software-development"],
        "body": (
            "You are Developer (consolidated into AutoReiv via ADR-0066). "
            "Read AGENTS.md first and run run_project_checks before In Review. "
            "Building AutoReiv tools was Toolsmith's job."
        ),
    },
    "architect": {
        "name": "Architect",
        "description": "Retired planning/review persona (consolidated into AutoReiv project-cards; ADR-0066).",
        "tone": "concise",
        "purpose": "reasoning",
        "avatar": "compass",
        "show_in_chat": True,
        "max_turns": 15,
        "skills": ["project-cards", "wiki-knowledge"],
        "body": "You are Architect (consolidated into AutoReiv via ADR-0066).",
    },
    "toolsmith": {
        "name": "Toolsmith",
        "description": "Retired tool builder persona (consolidated into AutoReiv capability-authoring; ADR-0066).",
        "tone": "concise",
        "purpose": "coding",
        "avatar": "hammer",
        "show_in_chat": False,
        "visibility": "internal",
        "max_turns": 12,
        "skills": ["capability-authoring", "proposals"],
        "body": "You are Toolsmith (consolidated into AutoReiv via ADR-0066).",
    },
}


def platform_dir() -> Path:
    return REPO_PLATFORM / "agents"


def _item(agent_id: str):
    item = ContentStore(data_root=None).agents.load(agent_id)
    if item is not None:
        return item
    spec = _LEGACY_RETIRED_AGENT_SPECS.get(agent_id)
    assert spec is not None, f"no shipped agent file for {agent_id}"
    meta = {k: v for k, v in spec.items() if k != "body"}
    return ContentFile(
        id=agent_id,
        kind="agent",
        meta=meta,
        body=spec["body"],
        path=REPO_PLATFORM / "agents" / f"{agent_id}.md",
        source="shipped",
        shipped=True,
        shipped_hash="legacy",
    )


def load_platform_manifest(agent_id: str):
    """Shipped agent file as a simple object (id, name, system_prompt, allowed_skill, ...)."""
    item = _item(agent_id)
    meta = item.meta
    return SimpleNamespace(
        id=agent_id,
        name=meta.get("name", agent_id),
        description=meta.get("description", ""),
        system_prompt=item.body,
        purpose=meta.get("purpose", "general"),
        tone=meta.get("tone", "default"),
        avatar_icon=meta.get("avatar", ""),
        model=meta.get("model", "default"),
        provider=meta.get("provider", "default"),
        allowed_skill=list(meta.get("skills") or []),
        show_in_chat=bool(meta.get("show_in_chat", True)),
        skills=[
            SimpleNamespace(id=sid, tools=list(shipped_skill_tools().get(sid, ())))
            for sid in (meta.get("skills") or [])
        ],
    )


def platform_pack_profile(agent_id: str):
    """AgentProfile from a shipped agent file (tools follow from its ticked skills)."""
    from src.infrastructure.agents.agent_files import profile_from_file

    profile = profile_from_file(_item(agent_id))
    return profile.model_copy(update={"is_builtin": False})


def shipped_skill_tools() -> dict[str, tuple[str, ...]]:
    """Every shipped skill id -> its SKILL.md ``tools:`` list (plus ADR-0066 consolidated aliases)."""
    store = ContentStore(data_root=None)
    mapping = {item.id: tuple(item.tools) for item in store.skills.list()}
    for old_id, target_id in CONSOLIDATED_SKILL_ALIASES.items():
        if old_id not in mapping and target_id in mapping:
            mapping[old_id] = mapping[target_id]
    return mapping


SHIPPED_SKILL_TOOLS = shipped_skill_tools()
BUNDLED_SKILL_IDS: tuple[str, ...] = tuple(
    sorted({item.id for item in ContentStore(data_root=None).skills.list()} | set(CONSOLIDATED_SKILL_ALIASES))
)


def bundled_skill_md(skill_id: str) -> Path:
    target = CONSOLIDATED_SKILL_ALIASES.get(skill_id, skill_id)
    return REPO_PLATFORM / "skills" / target / "SKILL.md"


def pack_dict(agent_id: str) -> dict:
    """Shipped agent as a dict: ticked skills plus each skill's tools (replaces reading pack.json)."""
    m = load_platform_manifest(agent_id)
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "system_prompt": m.system_prompt,
        "allowed_skill": list(m.allowed_skill),
        "skills": [{"id": sid, "tools": list(SHIPPED_SKILL_TOOLS.get(sid, ()))} for sid in m.allowed_skill],
        "show_in_chat": m.show_in_chat,
    }


def seed_bundled_skill_rows(skills_path, skill_ids=None) -> None:
    """Test fixture only: copy shipped skills into a skills folder (the app no longer seeds)."""
    import shutil

    dest_root = Path(skills_path)
    for sid in skill_ids or BUNDLED_SKILL_IDS:
        target = CONSOLIDATED_SKILL_ALIASES.get(sid, sid)
        src = REPO_PLATFORM / "skills" / target
        if src.is_dir() and not (dest_root / sid).exists():
            shutil.copytree(src, dest_root / sid)
