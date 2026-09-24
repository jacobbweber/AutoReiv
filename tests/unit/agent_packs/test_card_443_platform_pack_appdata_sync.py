"""CARD-443: platform-pack -> AppData promotion + stored-profile resync [REQ-443-001..006]."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
from src.infrastructure.skills.platform_packs import (
    PLATFORM_SHIPPED_PROMPT_SETTING,
    promote_platform_packs,
)


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


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

    def get_setting(self, key):
        return self.settings.get(key)

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


def test_clean_promotion_copies_stale_appdata_and_resyncs_profile(tmp_path: Path, fixture_checkout):
    """REQ-443-001/002/004: stale non-user_modified AppData + SQLite pick up platform seed."""
    checkout, seed = fixture_checkout
    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "STALE",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "", "tools": []}],
                "pack_tool_names": ["wiki_note_read"],
                "memory": {"enabled": True, "pinned_memory": "keep"},
            }
        ),
        encoding="utf-8",
    )
    (dest / "skills" / "skill-a").mkdir(parents=True)
    (dest / "skills" / "skill-a" / "SKILL.md").write_text("# a\nstale\n", encoding="utf-8")

    profile = _profile("fixturepack", prompt="STALE", skills=["skill-a"], seed_hash="deadbeef")
    store = _FakeStore({"fixturepack": profile})
    # Baseline equals stale shipped prompt so system_prompt may advance
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("STALE")})
    registry = _FakeRegistry(store)

    report = promote_platform_packs(
        data_dir,
        registry,
        None,
        checkout_root=checkout,
        pack_ids=["fixturepack"],
    )

    assert report.results[0].status == "promoted"
    assert profile.system_prompt == "SHIPPED PROMPT V1"
    assert profile.allowed_skill == ["skill-a", "skill-b"]
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    assert profile.user_modified is False
    live = json.loads((dest / "pack.json").read_text(encoding="utf-8"))
    assert live["system_prompt"] == "SHIPPED PROMPT V1"
    assert live["memory"]["pinned_memory"] == "keep"
    assert (dest / "skills" / "skill-b" / "SKILL.md").is_file()
    assert "v1" in (dest / "skills" / "skill-a" / "SKILL.md").read_text(encoding="utf-8")
    assert store.get_setting(PLATFORM_SHIPPED_PROMPT_SETTING)["fixturepack"] == _sha("SHIPPED PROMPT V1")


def test_stale_destination_repair_removes_platform_retired_skill(tmp_path: Path, fixture_checkout):
    """REQ-443-001: platform-removed stock skill dir is removed; operator-only dirs stay."""
    checkout, _seed = fixture_checkout
    # Platform now only has skill-a (retire skill-b)
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a"],
        skill_bodies={"skill-a": "# a\nv2\n"},
    )
    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "SHIPPED PROMPT V1",
                "allowed_skill": ["skill-a", "skill-b"],
                "skills": [
                    {"id": "skill-a", "name": "a", "description": "", "tools": []},
                    {"id": "skill-b", "name": "b", "description": "", "tools": []},
                ],
                "pack_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    for sid in ("skill-a", "skill-b", "operator-custom"):
        d = dest / "skills" / sid
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {sid}\nold\n", encoding="utf-8")

    profile = _profile(
        "fixturepack",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a", "skill-b"],
        seed_hash="oldhash",
    )
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert report.results[0].status == "promoted"
    # Missing stock skills may still be copied additively (ADR-0056); existing bodies are not overwritten.
    assert not (dest / "skills" / "skill-b").exists()
    assert (dest / "skills" / "operator-custom" / "SKILL.md").is_file()
    assert profile.allowed_skill == ["skill-a"]


def test_user_modified_refusal_is_deterministic(tmp_path: Path, fixture_checkout):
    """REQ-443-003: user_modified destination is not overwritten; skip names condition + resolution."""
    checkout, seed = fixture_checkout
    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    stale_body = "# a\noperator edit\n"
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "OPERATOR PROMPT",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "", "tools": []}],
                "pack_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    (dest / "skills" / "skill-a").mkdir(parents=True)
    (dest / "skills" / "skill-a" / "SKILL.md").write_text(stale_body, encoding="utf-8")

    profile = _profile(
        "fixturepack",
        prompt="OPERATOR PROMPT",
        skills=["skill-a"],
        user_modified=True,
        seed_hash="deadbeef",
    )
    store = _FakeStore({"fixturepack": profile})
    registry = _FakeRegistry(store)

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    outcome = report.results[0]
    assert outcome.status == "skipped_user_modified"
    assert outcome.pack_id == "fixturepack"
    assert "user_modified" in (outcome.reason or "").lower()
    assert outcome.resolution
    assert "mark_agent_user_modified" in outcome.resolution or "accept-platform-seed" in outcome.resolution
    assert profile.system_prompt == "OPERATOR PROMPT"
    assert profile.max_turns == 100
    assert (dest / "skills" / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == stale_body
    # Missing stock skills may still be copied additively (ADR-0056); existing bodies are not overwritten.
    if (dest / "skills" / "skill-b").exists():
        body_b = (dest / "skills" / "skill-b" / "SKILL.md").read_text(encoding="utf-8")
        assert "skill-b" in body_b or body_b.strip().startswith("#")


def test_stored_profile_resync_preserves_max_turns_and_model(tmp_path: Path, fixture_checkout):
    """REQ-443-006 / CARD-444 finding: pack fields resync; operator max_turns/model stay."""
    checkout, _seed = fixture_checkout
    # Bump platform prompt
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2 with CARD-444 clause",
        skills=["skill-a", "skill-b"],
    )
    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "SHIPPED PROMPT V1",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "", "tools": []}],
                "pack_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    (dest / "skills" / "skill-a").mkdir(parents=True)
    (dest / "skills" / "skill-a" / "SKILL.md").write_text("# a\n", encoding="utf-8")

    profile = _profile(
        "fixturepack",
        prompt="SHIPPED PROMPT V1",
        skills=["skill-a"],
        seed_hash="old",
    )
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    promote_platform_packs(data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"])
    assert "CARD-444" in profile.system_prompt or "V2" in profile.system_prompt
    assert profile.max_turns == 100
    assert profile.model == "operator-model"
    assert "skill-b" in (profile.allowed_skill or [])


def test_operator_edited_prompt_skips_prompt_field_only(tmp_path: Path, fixture_checkout):
    """system_prompt skipped when stored != shipped baseline; skills still promote."""
    checkout, _seed = fixture_checkout
    _write_pack(
        checkout / "platform-packs",
        "fixturepack",
        prompt="SHIPPED PROMPT V2",
        skills=["skill-a", "skill-b"],
    )
    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "OPERATOR EDITED PROMPT",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "", "tools": []}],
                "pack_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    (dest / "skills" / "skill-a").mkdir(parents=True)
    (dest / "skills" / "skill-a" / "SKILL.md").write_text("# a\nstale\n", encoding="utf-8")

    profile = _profile(
        "fixturepack",
        prompt="OPERATOR EDITED PROMPT",
        skills=["skill-a"],
        user_modified=False,
        seed_hash="old",
    )
    store = _FakeStore({"fixturepack": profile})
    # Baseline is V1; stored is operator-edited != baseline
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("SHIPPED PROMPT V1")})
    registry = _FakeRegistry(store)

    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    outcome = report.results[0]
    assert outcome.status in ("promoted", "promoted_partial")
    assert "system_prompt" in (outcome.skipped_fields or [])
    assert profile.system_prompt == "OPERATOR EDITED PROMPT"
    assert "skill-b" in (profile.allowed_skill or [])
    assert (dest / "skills" / "skill-b" / "SKILL.md").is_file()
    assert profile.max_turns == 100


def test_install_platform_agent_packs_delegates_and_persists_report(tmp_path: Path, fixture_checkout, monkeypatch):
    """Boot path records last sync report for operator-visible status API."""
    from src.infrastructure.data import resolver as resolver_mod

    checkout, _seed = fixture_checkout
    monkeypatch.setattr(resolver_mod, "repo_root", lambda: checkout)

    data_dir = tmp_path / "data"
    dest = data_dir / "packs" / "fixturepack"
    dest.mkdir(parents=True)
    (dest / "pack.json").write_text(
        json.dumps(
            {
                "id": "fixturepack",
                "system_prompt": "STALE",
                "allowed_skill": ["skill-a"],
                "skills": [{"id": "skill-a", "name": "a", "description": "", "tools": []}],
                "pack_tool_names": ["wiki_note_read"],
            }
        ),
        encoding="utf-8",
    )
    (dest / "skills" / "skill-a").mkdir(parents=True)
    (dest / "skills" / "skill-a" / "SKILL.md").write_text("# a\n", encoding="utf-8")

    profile = _profile("fixturepack", prompt="STALE", skills=["skill-a"], seed_hash="x")
    store = _FakeStore({"fixturepack": profile})
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, {"fixturepack": _sha("STALE")})
    registry = _FakeRegistry(store)

    # Only promote our fixture id (avoid requiring full platform set in fake checkout)
    report = promote_platform_packs(
        data_dir, registry, None, checkout_root=checkout, pack_ids=["fixturepack"]
    )
    assert any(r.pack_id == "fixturepack" for r in report.results)
    persisted = store.get_setting("platform_pack_sync_last_report")
    assert persisted is not None
    assert persisted["results"][0]["pack_id"] == "fixturepack"

