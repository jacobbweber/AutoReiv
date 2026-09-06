"""Persona packs retired from Agent Training Factory runtime [CARD-171].

Packs may still exist on disk under platform-packs/ but are NOT the Factory.
FACTORY_PACK_IDS is empty; RETIRED_FACTORY_PERSONA_PACK_IDS records former ids.
"""

import json
from pathlib import Path

import pytest

from src.application.agent_packs.schema import (
    FACTORY_PACK_IDS,
    RETIRED_FACTORY_PERSONA_PACK_IDS,
    AgentPackManifest,
)

ROOT = Path(__file__).resolve().parents[3]


def retired_pack_dir(pack_id: str):
    return ROOT / "platform-packs" / pack_id


def test_factory_pack_ids_retired_empty():
    assert FACTORY_PACK_IDS == frozenset()


def test_retired_persona_ids_recorded():
    assert RETIRED_FACTORY_PERSONA_PACK_IDS == {
        "conductor",
        "inspector",
        "coder",
        "sandbox_runner",
        "critic",
    }


@pytest.mark.parametrize("pack_id", sorted(RETIRED_FACTORY_PERSONA_PACK_IDS))
def test_retired_packs_not_presented_as_factory_runtime(pack_id):
    """Disk artifacts may remain; they must not claim Factory runtime role."""
    p_dir = retired_pack_dir(pack_id)
    if not p_dir.is_dir():
        pytest.skip(f"{pack_id} pack already removed from disk")
    manifest = AgentPackManifest.model_validate(
        json.loads((p_dir / "pack.json").read_text(encoding="utf-8"))
    )
    assert manifest.id == pack_id
    # Must not be visible as chat Factory workers
    assert manifest.show_in_chat is False
    assert pack_id not in FACTORY_PACK_IDS
