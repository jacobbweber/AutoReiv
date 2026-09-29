"""Helpers to load the shipped agent files (``platform/agents/<id>.md``) in tests (CARD-570)."""

from pathlib import Path
from types import SimpleNamespace

from src.infrastructure.content.store import REPO_PLATFORM, ContentStore

PLATFORM_PACK_IDS = ("autoreiv", "developer", "tutor", "direct", "architect")


def platform_dir() -> Path:
    return REPO_PLATFORM / "agents"


def _item(agent_id: str):
    item = ContentStore(data_root=None).agents.load(agent_id)
    assert item is not None, f"no shipped agent file for {agent_id}"
    return item


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
    """Every shipped skill id -> its SKILL.md ``tools:`` list."""
    store = ContentStore(data_root=None)
    return {item.id: tuple(item.tools) for item in store.skills.list()}


SHIPPED_SKILL_TOOLS = shipped_skill_tools()
BUNDLED_PACK_IDS: tuple[str, ...] = tuple(sorted(SHIPPED_SKILL_TOOLS))


def bundled_skill_md(skill_id: str) -> Path:
    return REPO_PLATFORM / "skills" / skill_id / "SKILL.md"


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


def seed_bundled_skill_packs(skills_path, pack_ids=None) -> None:
    """Test fixture only: copy shipped skills into a skills folder (the app no longer seeds)."""
    import shutil

    dest_root = Path(skills_path)
    for sid in pack_ids or BUNDLED_PACK_IDS:
        src = REPO_PLATFORM / "skills" / sid
        if src.is_dir() and not (dest_root / sid).exists():
            shutil.copytree(src, dest_root / sid)
