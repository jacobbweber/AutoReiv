"""Helpers to load repo catalog packs in tests (not auto-loaded at startup)."""

from pathlib import Path
from typing import Any, List

from src.application.agent_packs.schema import AgentPackManifest
from src.application.agent_packs.service import AgentPackService
from src.infrastructure.data.resolver import repo_root

SDLC_PACK_IDS = ("conductor", "coding", "review")


def catalog_dir() -> Path:
    return repo_root() / "agent-packs"


def load_catalog_manifest(pack_id: str) -> AgentPackManifest:
    path = catalog_dir() / pack_id / "pack.json"
    return AgentPackManifest.model_validate_json(path.read_text(encoding="utf-8"))


def import_sdlc_packs(data_dir: Any, registry: Any, tool_reg: Any) -> List[Any]:
    available = {t.name for t in tool_reg.list_tools()} if tool_reg is not None else None
    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=getattr(registry, "state_store", None),
        available_tools=available,
    )
    return [service.import_path(catalog_dir() / pack_id) for pack_id in SDLC_PACK_IDS]
