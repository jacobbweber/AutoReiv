"""CARD-449: pack-lock granularity — scalars must not block platform promotion [REQ-449-001..008]."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
from src.infrastructure.skills.platform_pack_promotion import (
    PLATFORM_KEEP_CUSTOMIZATIONS_SETTING,
    PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING,
    PLATFORM_PACK_CONTENT_BACKUPS_SETTING,
    PLATFORM_SHIPPED_PROMPT_SETTING,
    backup_pack_content,
    list_pack_content_backups,
    migrate_false_content_locks,
    pack_content_diverged_from_seed,
    promote_platform_packs,
    prompt_content_hash,
    should_set_content_lock,
)
from src.infrastructure.skills.platform_packs import (
    apply_user_modified_additive_skill_grants,
    apply_user_modified_developer_authoring_prompt,
)


def _sha(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()

class _FakeStore:
    def __init__(self, profiles: dict[str, AgentProfile] | None = None):
        self.profiles = dict(profiles or {})
        self.settings: dict = {}
        self.overrides: dict = {}

    def get_agent_profile(self, agent_id: str):
        return self.profiles.get(agent_id)

    def get_custom_agent_profile(self, agent_id: str):
        return self.get_agent_profile(agent_id)

    def save_custom_agent_profile(self, profile):
        self.profiles[profile.id] = profile

    def save_agent_profile(self, profile):
        self.profiles[profile.id] = profile

    def get_agent_override(self, agent_id: str):
        return self.overrides.get(agent_id)

    def save_agent_override(self, ov):
        aid = getattr(ov, "agent_id", None) or getattr(ov, "id", None)
        self.overrides[aid] = ov

    def list_custom_agent_profiles(self):
        return list(self.profiles.values())

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def mark_agent_user_modified(self, agent_id: str, *, modified: bool = True):
        p = self.profiles.get(agent_id)
        if p is not None:
            p.user_modified = bool(modified)
        ov = self.overrides.get(agent_id)
        if ov is not None:
            ov.user_modified = bool(modified)

    def delete_agent_profile(self, agent_id: str, purge_history: bool = False):
        self.profiles.pop(agent_id, None)


class _FakeRegistry:
    def __init__(self, store: _FakeStore):
        self.state_store = store

    def get_agent(self, agent_id: str):
        return self.state_store.profiles.get(agent_id)


def _write_pack(root: Path, pack_id: str, *, prompt: str, skills: list[str], skill_bodies: dict[str, str] | None = None):
    pack = root / pack_id
    pack.mkdir(parents=True, exist_ok=True)
    bodies = skill_bodies or {s: f"# {s}\nplatform body\n" for s in skills}
    for sid, body in bodies.items():
        d = pack / "skills" / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(body, encoding="utf-8")
    data = {
        "id": pack_id,
        "name": pack_id.title(),
        "version": "1",
        "system_prompt": prompt,
        "allowed_skill": list(skills),
        "skills": [{"id": s, "name": s, "description": s, "tools": ["wiki_note_read"]} for s in skills],
        "pack_tool_names": ["wiki_note_read"],
        "allowed_tool_names": ["wiki_note_read"],
        "model": "default",
        "show_in_chat": True,
    }
    (pack / "pack.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _profile(pack_id: str, *, prompt: str, skills: list[str], user_modified: bool = False, seed_hash: str = "old") -> AgentProfile:
    return AgentProfile(
        id=pack_id,
        name=pack_id.title(),
        description="fixture",
        system_prompt=prompt,
        origin=AgentOrigin.PACK,
        tone=AgentTone.DEFAULT,
        purpose=ModelPurpose.TASK_EXECUTION,
        allowed_skill=list(skills),
        pack_tool_names=["wiki_note_read"],
        allowed_tool_names=["wiki_note_read"],
        user_modified=user_modified,
        seed_content_hash=seed_hash,
        seed_version="1",
        show_in_chat=True,
        max_turns=100,
        model="operator-model",
    )


@pytest.fixture
def fixture_checkout(tmp_path: Path):
    """Minimal checkout with one generic platform pack (not Tutor-special-cased)."""
    checkout = tmp_path / "checkout"
    platform = checkout / "platform-packs"
    data = _write_pack(
        platform,
        "fixturepack",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a", "skill-b"],
        skill_bodies={"skill-a": "# a\nv1\n", "skill-b": "# b\nv1\n"},
    )
    return checkout, data



def _seed_dest(data_dir: Path, prompt: str = "SHIPPED PROMPT V1", skills: list[str] | None = None) -> Path:
    skills = skills or ["skill-a", "skill-b"]
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": prompt,
                "allowed_skill": list(skills),
                "skills": [{"id": s, "name": s, "description": "", "tools": ["wiki_note_read"]} for s in skills],
                "pack_tool_names": ["wiki_note_read"],
                "allowed_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    for s in skills:
        (dest / "skills" / s).mkdir(parents=True, exist_ok=True)
        (dest / "skills" / s / "SKILL.md").write_text(f"# {s}\nlive\n", encoding="utf-8")
    return dest


def test_settings_only_change_still_promotes(tmp_path: Path, fixture_checkout):
    """REQ-449-001: max_turns/model alone must not block promotion."""
    checkout, _seed = fixture_checkout
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a", "skill-b", "skill-c"],
        skill_bodies={"skill-a": "# a\nv2\n", "skill-b": "# b\nv2\n", "skill-c": "# c\nv2\n"},
    )
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    profile = _profile(
        "fixturepack",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a", "skill-b"],
        user_modified=False,
        seed_hash="stale",
    )
    profile.max_turns = 100
    profile.model = "operator-model"
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    assert (
        should_set_content_lock(
            existing=profile,
            new_prompt="SHIPPED PROMPT V1",
            new_skills=["skill-a", "skill-b"],
            new_tools=["wiki_note_read"],
            store=store,
            pack_id="fixturepack",
        )
        is False
    )

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report.results[0].status in ("promoted", "promoted_partial")
    assert profile.system_prompt == "SHIPPED PROMPT V2"
    assert "skill-c" in profile.allowed_skill
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    assert profile.user_modified is False


def test_edited_prompt_skipped(tmp_path: Path, fixture_checkout):
    """REQ-449-002/003: prompt != shipped baseline keeps skip path."""
    checkout, _seed = fixture_checkout
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a", "skill-b", "skill-c"],
    )
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    profile = _profile(
        "fixturepack",
        prompt="OPERATOR CUSTOM PROMPT",
        skills=["skill-a", "skill-b"],
        user_modified=True,
        seed_hash="stale",
    )
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    assert (
        pack_content_diverged_from_seed(
            profile,
            seed_prompt="SHIPPED PROMPT V2",
            seed_skills=["skill-a", "skill-b", "skill-c"],
            store=store,
            pack_id="fixturepack",
        )
        is True
    )

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report.results[0].status == "skipped_user_modified"
    assert profile.system_prompt == "OPERATOR CUSTOM PROMPT"
    assert profile.max_turns == 100


def test_disabled_skill_stays_off_while_new_skill_added(tmp_path: Path, fixture_checkout):
    """REQ-449-004: operator-disabled stock skill stays disabled; new platform skills appear."""
    checkout, _seed = fixture_checkout
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a", "skill-b", "skill-c"],
        skill_bodies={"skill-a": "# a\nv2\n", "skill-b": "# b\nv2\n", "skill-c": "# c\nv2\n"},
    )
    data_dir = tmp_path / "data"
    _seed_dest(data_dir, skills=["skill-a"])
    profile = _profile(
        "fixturepack",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a"],
        user_modified=False,
        seed_hash="stale",
    )
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    store.set_setting(PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING, {"fixturepack": ["skill-b"]})
    registry = _FakeRegistry(store)

    assert (
        should_set_content_lock(
            existing=profile,
            new_prompt="SHIPPED PROMPT V1",
            new_skills=["skill-a"],
            new_tools=["wiki_note_read"],
            store=store,
            pack_id="fixturepack",
            stock_skills=["skill-a", "skill-b"],
        )
        is False
    )

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report.results[0].status in ("promoted", "promoted_partial")
    assert "skill-b" not in profile.allowed_skill
    assert "skill-c" in profile.allowed_skill
    assert "skill-a" in profile.allowed_skill
    assert profile.user_modified is False


def test_automated_additive_grants_do_not_lock(tmp_path: Path, fixture_checkout):
    """REQ-449-005: apply_user_modified_* must not set user_modified."""
    checkout, seed = fixture_checkout
    profile = _profile(
        "fixturepack",
        prompt="OPERATOR CUSTOM PROMPT",
        skills=["skill-a"],
        user_modified=False,
        seed_hash="stale",
    )
    store = _FakeStore({"fixturepack": profile})
    apply_user_modified_additive_skill_grants(pack_id="fixturepack", pack_data=seed, store=store)
    assert profile.user_modified is False
    apply_user_modified_developer_authoring_prompt(pack_id="fixturepack", store=store)
    assert profile.user_modified is False


def test_migration_unlocks_settings_only_keeps_content_edited(tmp_path: Path, fixture_checkout):
    """REQ-449-006: one-time lock migration clears false locks."""
    checkout, _seed = fixture_checkout
    data_dir = tmp_path / "data"
    (data_dir / "packs").mkdir(parents=True)
    platform = checkout / "platform-packs"
    _write_pack(platform, "tutor", prompt="SHIPPED PROMPT V1", skills=["skill-a", "skill-b"])
    _write_pack(platform, "developer", prompt="DEV SHIPPED", skills=["skill-a"])

    tutor = _profile(
        "tutor",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a", "skill-b"],
        user_modified=True,
        seed_hash="x",
    )
    tutor.max_turns = 100
    developer = _profile(
        "developer",
        prompt="OPERATOR DEV PROMPT",
        skills=["skill-a"],
        user_modified=True,
        seed_hash="y",
    )
    store = _FakeStore({"tutor": tutor, "developer": developer})
    store.set_setting(
        PLATFORM_SHIPPED_PROMPT_SETTING,
        {"tutor": _sha("SHIPPED PROMPT V1"), "developer": _sha("DEV SHIPPED")},
    )
    registry = _FakeRegistry(store)

    results = migrate_false_content_locks(
        data_dir=data_dir,
        agent_registry=registry,
        checkout_root=checkout,
        pack_ids=["tutor", "developer"],
    )
    by_id = {r["pack_id"]: r for r in results}
    assert by_id["tutor"]["action"] == "unlocked"
    assert tutor.user_modified is False
    assert by_id["developer"]["action"] == "kept_locked"
    assert developer.user_modified is True
    assert "prompt" in by_id["developer"]["reason"]


def test_keep_customizations_default_true_and_false_force_resets(tmp_path: Path, fixture_checkout):
    """REQ-449-007/008: default keep=true; when false, force reset preserves scalars + writes backup."""
    checkout, _seed = fixture_checkout
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a", "skill-b"],
    )
    data_dir = tmp_path / "data"
    _seed_dest(data_dir)
    profile = _profile(
        "fixturepack",
        prompt="OPERATOR CUSTOM PROMPT",
        skills=["skill-a"],
        user_modified=True,
        seed_hash="stale",
    )
    profile.max_turns = 100
    profile.model = "operator-model"
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    assert store.get_setting(PLATFORM_KEEP_CUSTOMIZATIONS_SETTING) is None

    registry = _FakeRegistry(store)
    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report.results[0].status == "skipped_user_modified"
    assert profile.system_prompt == "OPERATOR CUSTOM PROMPT"

    store.set_setting(PLATFORM_KEEP_CUSTOMIZATIONS_SETTING, False)
    report2 = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report2.results[0].status in ("promoted", "promoted_partial", "force_reset")
    assert profile.system_prompt == "SHIPPED PROMPT V2"
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    assert profile.user_modified is False
    backups = list_pack_content_backups(store, "fixturepack")
    assert len(backups) >= 1
    assert backups[0]["system_prompt"] == "OPERATOR CUSTOM PROMPT"


def test_backup_helper_and_listing():
    """REQ-449-008: backup_pack_content persists snapshot; list returns it."""
    store = _FakeStore()
    profile = _profile("tutor", prompt="P", skills=["a"])
    profile.max_turns = 42
    snap = backup_pack_content(store, profile, reason="test")
    assert snap["system_prompt"] == "P"
    assert snap["max_turns"] == 42
    listed = list_pack_content_backups(store, "tutor")
    assert len(listed) == 1
    raw = store.get_setting(PLATFORM_PACK_CONTENT_BACKUPS_SETTING)
    assert "tutor" in raw


def test_prompt_content_hash_stable():
    assert prompt_content_hash("abc") == _sha("abc")
    assert prompt_content_hash(None) == _sha("")
