"""CARD-436 follow-up: hash-gated tutor seed apply refreshes SQLite + live pack.json projection."""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
from src.infrastructure.skills.platform_packs import (
    compute_platform_seed_hash,
    install_platform_agent_packs,
    refresh_live_pack_json_skill_projection,
)


LEARNING_OS = (
    "start-resume-topic",
    "quiz-turn",
    "flashcard-turn",
    "due-review",
    "education-wiki-curation",
    "progress-summary",
)


class _FakeStore:
    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.settings: dict = {}

    def get_agent_profile(self, agent_id: str):
        return self.profile if self.profile.id == agent_id else None

    def get_custom_agent_profile(self, agent_id: str):
        return self.get_agent_profile(agent_id)

    def save_custom_agent_profile(self, profile):
        self.profile = profile

    def save_agent_profile(self, profile):
        self.profile = profile

    def get_agent_override(self, agent_id: str):
        return None

    def save_agent_override(self, ov):
        return None

    def list_custom_agent_profiles(self):
        return [self.profile]

    def get_setting(self, key):
        return self.settings.get(key)

    def set_setting(self, key, value):
        self.settings[key] = value


class _FakeRegistry:
    def __init__(self, profile: AgentProfile, store: _FakeStore):
        self._profile = profile
        self.state_store = store

    def get_agent(self, agent_id: str):
        return self._profile if self._profile.id == agent_id else None


def _stale_tutor_profile() -> AgentProfile:
    return AgentProfile(
        id="tutor",
        name="Tutor",
        description="stale",
        system_prompt="old prompt without Learning OS",
        origin=AgentOrigin.PACK,
        tone=AgentTone.ACADEMIC,
        purpose=ModelPurpose.REASONING,
        allowed_skill=["socratic-tutoring"],
        pack_tool_names=["wiki_note_read"],
        allowed_tool_names=["wiki_note_read"],
        user_modified=False,
        seed_content_hash="deadbeef",
        seed_version="1",
        show_in_chat=True,
    )


def test_refresh_live_pack_json_skill_projection_merges_without_wiping_extras(tmp_path: Path):
    dest = tmp_path / "tutor"
    dest.mkdir()
    live = {
        "id": "tutor",
        "skills": [{"id": "socratic-tutoring", "name": "Old", "description": "", "tools": []}],
        "allowed_skill": ["socratic-tutoring"],
        "pack_tool_names": ["wiki_note_read"],
        "system_prompt": "old",
        "memory": {"enabled": True, "pinned_memory": "keep-me"},
        "allow_wiki_access": True,
    }
    (dest / "pack.json").write_text(json.dumps(live), encoding="utf-8")
    seed = {
        "skills": [{"id": "quiz-turn", "name": "Quiz", "description": "q", "tools": ["wiki_note_read"]}],
        "allowed_skill": ["socratic-tutoring", "quiz-turn"],
        "pack_tool_names": ["wiki_note_read", "wiki_note_search"],
        "system_prompt": "new Learning OS prompt",
    }
    assert refresh_live_pack_json_skill_projection(dest, seed) is True
    out = json.loads((dest / "pack.json").read_text(encoding="utf-8"))
    assert out["allowed_skill"] == ["socratic-tutoring", "quiz-turn"]
    assert out["system_prompt"] == "new Learning OS prompt"
    assert out["memory"]["pinned_memory"] == "keep-me"
    assert out["allow_wiki_access"] is True


def test_hash_gated_tutor_seed_applies_learning_os_skills(tmp_path: Path, monkeypatch):
    """Stale non-user_modified tutor picks up CARD-436 skills on install."""
    from src.infrastructure.data import resolver as resolver_mod

    repo = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(resolver_mod, "repo_root", lambda: repo)

    data_dir = tmp_path / "data"
    packs = data_dir / "packs" / "tutor"
    packs.mkdir(parents=True)
    # Thin live pack.json (skills catalog Agent Studio reads)
    (packs / "pack.json").write_text(
        json.dumps(
            {
                "id": "tutor",
                "name": "Tutor",
                "skills": [{"id": "socratic-tutoring", "name": "S", "description": "", "tools": []}],
                "allowed_skill": ["socratic-tutoring"],
                "pack_tool_names": ["wiki_note_read"],
                "system_prompt": "old",
                "memory": {"enabled": True},
            }
        ),
        encoding="utf-8",
    )
    (packs / "skills" / "socratic-tutoring").mkdir(parents=True)
    (packs / "skills" / "socratic-tutoring" / "SKILL.md").write_text("# s\n", encoding="utf-8")

    profile = _stale_tutor_profile()
    store = _FakeStore(profile)
    registry = _FakeRegistry(profile, store)

    install_platform_agent_packs(data_dir, registry, None, checkout_root=repo)

    assert profile.user_modified is False
    for sid in LEARNING_OS:
        assert sid in (profile.allowed_skill or [])
    assert "socratic-tutoring" in (profile.allowed_skill or [])
    seed_pack = json.loads((repo / "platform-packs" / "tutor" / "pack.json").read_text(encoding="utf-8"))
    assert profile.seed_content_hash == compute_platform_seed_hash(
        seed_pack, repo / "platform-packs" / "tutor"
    )

    live = json.loads((packs / "pack.json").read_text(encoding="utf-8"))
    assert set(LEARNING_OS) <= set(live.get("allowed_skill") or [])
    live_ids = {s["id"] for s in live.get("skills") or []}
    assert set(LEARNING_OS) <= live_ids
    assert live.get("memory", {}).get("enabled") is True
    for sid in LEARNING_OS:
        assert (packs / "skills" / sid / "SKILL.md").is_file()
