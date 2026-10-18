"""
Built-in Agent Registry [REQ-AGENTS-001, CARD-713].
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    RETIRED_LIVE_AGENT_IDS,
    canonical_agent_id,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.agents.agent_files import (
    MODEL_FIELDS,
    MODEL_SETTINGS_KEY,
    meta_from_profile,
    model_settings_from_profile,
    profile_from_file,
)
from src.infrastructure.content.store import ContentStore, get_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

if TYPE_CHECKING:
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.telemetry.collector import TelemetryCollector

logger = logging.getLogger(__name__)


class BuiltinAgentRegistry:
    """
    Registry of agent profiles. Agents are files [CARD-570]: shipped ``platform/agents/<id>.md``
    read in place, user copies in data ``agents/<id>.md`` win by id. Per-agent model/provider are
    separate settings. In-memory profiles (tests, BUILTIN_PROFILES) are a fallback only.
    agent-builder is retired [CARD-429] and is never registered.
    """

    def __init__(
        self,
        profiles: Optional[List[AgentProfile]] = None,
        state_store: Optional[SQLiteStateStore] = None,
        master_tool_registry: Optional[Any] = None,
        content_store: Optional[ContentStore] = None,
    ):
        self._profiles: Dict[str, AgentProfile] = {}
        self.state_store = state_store
        self.master_tool_registry = master_tool_registry
        self._content = content_store

        source = BUILTIN_PROFILES if profiles is None else profiles
        for p in source:
            self.register_profile(p)

    @property
    def content(self) -> ContentStore:
        return self._content if self._content is not None else get_store()

    # model settings ----------------------------------------------------------------------------
    def model_settings(self, agent_id: str) -> dict:
        if not self.state_store or not hasattr(self.state_store, "get_setting"):
            return {}
        raw = self.state_store.get_setting(MODEL_SETTINGS_KEY) or {}
        entry = raw.get(agent_id) if isinstance(raw, dict) else None
        return dict(entry) if isinstance(entry, dict) else {}

    def save_model_settings(self, agent_id: str, values: dict) -> None:
        if not self.state_store or not hasattr(self.state_store, "set_setting"):
            return
        raw = self.state_store.get_setting(MODEL_SETTINGS_KEY) or {}
        raw = dict(raw) if isinstance(raw, dict) else {}
        clean = {k: v for k, v in (values or {}).items() if k in MODEL_FIELDS and v not in (None, "")}
        if clean:
            raw[agent_id] = clean
        else:
            raw.pop(agent_id, None)
        self.state_store.set_setting(MODEL_SETTINGS_KEY, raw)

    # writes ------------------------------------------------------------------------------------
    def register_profile(self, profile: AgentProfile) -> None:
        if profile.id in RETIRED_LIVE_AGENT_IDS:
            return
        self._profiles[profile.id] = profile

    def register_custom_agent(self, profile: AgentProfile) -> None:
        """Save the full agent file (user copy) and its model settings. No field merging."""
        self.save_agent(profile)

    def save_agent(self, profile: AgentProfile, *, create: bool = False) -> AgentProfile:
        """Write data ``agents/<id>.md``. ``create`` refuses shipped (reserved) and existing ids."""
        if profile.id in RETIRED_LIVE_AGENT_IDS:
            raise ValueError(f"'{profile.id}' is retired.")
        meta, body = meta_from_profile(profile)
        if self.content.data_root is None:
            self._profiles[profile.id] = profile  # no data dir (unit tests): memory only
        else:
            self.content.agents.save(profile.id, meta, body, create=create)
        self.save_model_settings(profile.id, model_settings_from_profile(profile))
        return self.get_agent(profile.id) or profile

    def apply_customization(self, custom) -> AgentProfile:
        """Apply the set fields of an AgentCustomization and save (full copy; model fields to settings)."""
        existing = self.get_agent(custom.agent_id)
        if existing is None:
            raise LookupError(custom.agent_id)
        update = {
            k: v
            for k, v in custom.model_dump(exclude={"agent_id", "user_modified"}).items()
            if v is not None and k in AgentProfile.model_fields
        }
        profile = AgentProfile.model_validate({**existing.model_dump(), **update})
        return self.save_agent(profile)

    def use_shipped_version(self, agent_id: str) -> bool:
        """Delete the user copy of a shipped agent. Model settings are kept."""
        return self.content.agents.use_shipped(agent_id)

    def delete_custom_agent(self, agent_id: str, purge_history: bool = False) -> bool:
        """Shipped agent -> hidden (persisted); user-created -> file removed."""
        if agent_id in ("agent-builder", "autoreiv"):
            return False
        in_memory = self._profiles.pop(agent_id, None) is not None
        outcome = self.content.agents.delete(agent_id)
        if purge_history and self.state_store and hasattr(self.state_store, "delete_agent_history"):
            try:
                self.state_store.delete_agent_history(agent_id)
            except Exception:
                pass
        return in_memory or outcome in ("hidden", "deleted")

    def unhide_agent(self, agent_id: str) -> bool:
        return self.content.agents.unhide(agent_id)

    def agent_file_status(self, agent_id: str) -> dict:
        loaded = self.content.agents.load(agent_id, include_hidden=True)
        if loaded is None:
            return {"source": "memory", "shipped": False, "edited": False, "shipped_changed": False, "warnings": []}
        status = loaded.status()
        status["hidden"] = agent_id in self.content.agents.hidden()
        return status

    # reads -------------------------------------------------------------------------------------
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Agent file (user copy wins), else an in-memory profile; alias fallback."""
        from src.infrastructure.content.store import REPO_PLATFORM, RETIRED_SHIPPED_AGENT_IDS

        raw = (agent_id or "").strip()
        if raw in RETIRED_LIVE_AGENT_IDS or canonical_agent_id(raw) in RETIRED_LIVE_AGENT_IDS:
            return None
        for lookup in dict.fromkeys([raw, canonical_agent_id(raw)]):
            if not lookup:
                continue
            loaded = self.content.agents.load(lookup)
            if loaded is not None:
                return profile_from_file(loaded, self.model_settings(lookup))
            if lookup in self.content.agents.hidden() and self.content.agents.shipped_path(lookup).is_file():
                return None
            profile = self._profiles.get(lookup) or get_builtin_profile(lookup)
            if profile is not None:
                settings = self.model_settings(lookup)
                return profile.model_copy(update=settings) if settings else profile
        if raw.lower() in RETIRED_SHIPPED_AGENT_IDS and self.content.agents.shipped_dir == REPO_PLATFORM / "agents":
            return self.get_agent("autoreiv")
        return None

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self.get_agent(agent_id)

    def list_agents(self) -> List[AgentProfile]:
        """Every visible agent: files (shipped + user), then in-memory profiles."""
        ids: list[str] = [f.id for f in self.content.agents.list()]
        ids += [p.id for p in BUILTIN_PROFILES] + list(self._profiles)
        result: List[AgentProfile] = []
        for aid in dict.fromkeys(ids):
            if aid in RETIRED_LIVE_AGENT_IDS:
                continue
            ag = self.get_agent(aid)
            if ag is not None and ag.id not in {r.id for r in result}:
                result.append(ag)
        return result

    def list_profiles(self) -> List[AgentProfile]:
        return self.list_agents()

    @classmethod
    def bootstrap(
        cls,
        store: SQLiteStateStore,
        telemetry: "TelemetryCollector",
        wiki_root: Optional[Union[str, Path]] = None,
        skills_dir: Optional[str] = None,
    ) -> Tuple["BuiltinAgentRegistry", "ScopedToolRegistry"]:
        """Delegate ecosystem tool and skill wiring to the application bootstrap layer [CARD-713]."""
        from src.application.bootstrap.ecosystem import bootstrap_ecosystem

        return bootstrap_ecosystem(
            store=store,
            telemetry=telemetry,
            wiki_root=wiki_root,
            skills_dir=skills_dir,
            registry_cls=cls,
        )
