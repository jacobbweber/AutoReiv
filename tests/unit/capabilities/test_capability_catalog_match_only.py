"""CARD-217 Capability Catalog C [REQ-CAPCAT-001..004,007].

Match returns subset only; dump-all for prompt must not exist.
"""

from __future__ import annotations

import inspect
import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.capabilities.resolver import (
    FORBIDDEN_DUMP_ALL_ATTRS,
    CapabilityCatalogResolver,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import capabilities as capabilities_router_mod


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def resolver(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    repo = CapabilityCatalogRepository(store)
    return CapabilityCatalogResolver(repo)


def _seed(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes"],
            roles=["librarian"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="skill.platform-health",
            kind=CapabilityKind.SKILL,
            name="platform-health",
            summary="Host telemetry and health",
            keywords=["health", "sre", "telemetry"],
            roles=["sre"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator",
            keywords=["assistant", "tasks", "schedule"],
            roles=["general"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="routine.hourly-sre-pulse",
            kind=CapabilityKind.ROUTINE,
            name="Hourly SRE Pulse",
            summary="Periodic SRE health pulse",
            keywords=["sre", "pulse", "health"],
            roles=["sre"],
            requires_hitl=False,
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="pack.homelab-admin",
            kind=CapabilityKind.PACK,
            name="Homelab Admin Pack",
            summary="Homelab operations pack",
            keywords=["homelab", "vm", "opentofu"],
            roles=["homelab"],
            risk_level="high",
            requires_hitl=True,
        )
    )


def test_req_capcat_002_self_authored_starts_candidate(resolver):
    entry = CapabilityIndexEntry.self_authored(
        id="tool.demo",
        kind="tool",
        name="demo",
        keywords=["demo"],
    )
    assert entry.trust_tier == TrustTier.CANDIDATE
    assert entry.source == "self_authored"
    saved = resolver.upsert(entry)
    assert saved.trust_tier == TrustTier.CANDIDATE


def test_req_capcat_001_unknown_kind_fail_closed():
    with pytest.raises(ValueError, match="fail closed"):
        CapabilityIndexEntry(id="x", kind="wizard", name="Nope")


def test_req_capcat_003_resolve_returns_matched_subset_only(resolver):
    _seed(resolver)
    result = resolver.resolve("wiki search notes", role="librarian", limit=5)
    assert result.miss is False
    assert 0 < len(result.matched) < result.total_indexed
    assert result.as_dict()["subset_only"] is True
    ids = {e.id for e in result.matched}
    assert "tool.wiki_note_search" in ids
    assert "pack.homelab-admin" not in ids


def test_req_capcat_003_empty_intent_is_miss_not_dump(resolver):
    _seed(resolver)
    result = resolver.resolve("", role=None)
    assert result.miss is True
    assert result.matched == ()
    assert result.total_indexed >= 5


def test_req_capcat_003_unknown_kind_filter_fail_closed(resolver):
    _seed(resolver)
    with pytest.raises(ValueError, match="fail closed"):
        resolver.resolve("health", kinds=["not-a-kind"])


def test_req_capcat_004_no_dump_all_methods_on_resolver():
    for name in FORBIDDEN_DUMP_ALL_ATTRS:
        assert not hasattr(CapabilityCatalogResolver, name)
    source = inspect.getsource(CapabilityCatalogResolver)
    for name in ("dump_all", "list_all_for_prompt", "get_full_catalog_for_prompt"):
        assert name not in source


def test_req_capcat_004_no_dump_all_http_routes():
    paths = []
    for route in capabilities_router_mod.router.routes:
        path = getattr(route, "path", "") or ""
        paths.append(path)
        lowered = path.lower()
        assert "dump" not in lowered
        assert "all-for-prompt" not in lowered
        assert "full-catalog" not in lowered
    assert "/api/capabilities/resolve" in paths
    assert "/api/capabilities/registry" in paths


def test_req_capcat_005_persist_roundtrip(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    repo = CapabilityCatalogRepository(store)
    resolver = CapabilityCatalogResolver(repo)
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.persist",
            kind=CapabilityKind.TOOL,
            name="persist",
            keywords=["persist"],
        )
    )
    # Re-open store on same file
    store2 = SQLiteStateStore(db_path=temp_db_path)
    repo2 = CapabilityCatalogRepository(store2)
    got = repo2.get_entry("tool.persist")
    assert got is not None
    assert got.name == "persist"
    assert got.trust_tier == TrustTier.CANDIDATE


def test_api_resolve_and_registry_operator_cap(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    repo = CapabilityCatalogRepository(store)
    catalog = CapabilityCatalogResolver(repo)
    _seed(catalog)

    app = FastAPI()
    app.state.store = store
    app.state.capability_catalog = catalog
    app.state.capability_catalog_repo = repo
    app.include_router(capabilities_router_mod.router)
    client = TestClient(app)

    res = client.post(
        "/api/capabilities/resolve",
        json={"intent": "sre health telemetry", "role": "sre", "limit": 5},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["subset_only"] is True
    assert body["count"] >= 1
    assert body["count"] < body["total_indexed"]

    reg = client.get("/api/capabilities/registry", params={"limit": 2})
    assert reg.status_code == 200
    rbody = reg.json()
    assert rbody["operator_view"] is True
    assert rbody["prompt_dump_forbidden"] is True
    assert rbody["count"] <= 2
    assert rbody["total_indexed"] >= 5

    bad = client.post("/api/capabilities/resolve", json={"intent": "x", "kinds": ["nope"]})
    assert bad.status_code == 400
