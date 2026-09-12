"""CARD-260 Wiki-thin fail-closed grounding [REQ-WIKITHIN-001..002]."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.wiki_thin_grounding import (
    ACTION_GROUNDED_ONLY,
    ACTION_NEED_SOURCES,
    ACTION_PROCEED_WITH_HITS,
    ACTION_SKIP,
    apply_standing_wiki_thin_grounding,
    assess_wiki_thin_grounding,
    collect_provenanced_paths_from_tool_result,
    extract_claimed_wiki_paths,
    format_grounding_constraint_block,
    format_need_sources_park_message,
    format_ungrounded_claim_honesty,
    is_wiki_create_ask,
    is_wiki_related_ask,
    is_wiki_source_dependent_ask,
    ungrounded_claimed_paths,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.orchestration.models import PhaseStatus
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


EMPTY_TOPIC_ASK = (
    "Write a short Wiki note in 00_Inbox about Zorblax-9 quantum flute maintenance "
    "(obscure topic with no vault notes). Done-when: I can open that note via "
    "wiki_note_read. Keep it under 80 words."
)

SOURCE_DEP_ASK = (
    "Summarize what the wiki says about Zorblax-9 quantum flute maintenance "
    "using only matched wiki notes. Done-when: sources are cited via wiki_note_read."
)

EXISTING_TOPIC_ASK = (
    "Write a short Wiki note in 00_Inbox summarizing standing Jobs in AutoReiv "
    "using only matched wiki notes. Done-when: I can open that note via wiki_note_read. "
    "Keep it under 120 words."
)


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
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def resolver(store):
    return CapabilityCatalogResolver(CapabilityCatalogRepository(store))


@pytest.fixture
def orch(store, resolver):
    return JobPhaseOrchestrator(store, capability_resolver=resolver)


@pytest.fixture
def empty_wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "00_Inbox").mkdir(parents=True)
    (root / "01_Notes").mkdir(parents=True)
    return root


@pytest.fixture
def seeded_wiki(empty_wiki: Path) -> Path:
    note = empty_wiki / "01_Notes" / "standing_job_in_autoreiv.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "---\ntitle: Standing Job in AutoReiv\ntags: [standing, job]\n---\n"
        "# Standing Job\n\nFormulate then Execute with done-when.\n",
        encoding="utf-8",
    )
    return empty_wiki


def _seed_wiki_tools(resolver: CapabilityCatalogResolver) -> None:
    for cid, name, kws in (
        (
            "tool.wiki_note_create",
            "wiki_note_create",
            ["wiki", "create", "note", "write", "inbox"],
        ),
        (
            "tool.wiki_note_read",
            "wiki_note_read",
            ["wiki", "note", "read", "open", "inbox"],
        ),
        (
            "tool.wiki_note_search",
            "wiki_note_search",
            ["wiki", "search", "notes", "inventory"],
        ),
    ):
        resolver.upsert(
            CapabilityIndexEntry(
                id=cid,
                kind=CapabilityKind.TOOL,
                name=name,
                summary=name,
                keywords=kws,
                roles=["assistant"],
                trust_tier=TrustTier.TRUSTED,
                source="card260_test",
            )
        )


# --- classifiers -------------------------------------------------------------


def test_wiki_related_and_create_shaped():
    assert is_wiki_related_ask(EMPTY_TOPIC_ASK) is True
    assert is_wiki_create_ask(EMPTY_TOPIC_ASK) is True
    assert is_wiki_source_dependent_ask(SOURCE_DEP_ASK) is True
    assert is_wiki_related_ask("what is the weather") is False


# --- REQ-WIKITHIN-001 --------------------------------------------------------


def test_empty_create_ask_is_grounded_only():
    d = assess_wiki_thin_grounding(EMPTY_TOPIC_ASK, hits=[])
    assert d.thin is True
    assert d.action == ACTION_GROUNDED_ONLY
    assert "create" in d.reason


def test_thin_source_dependent_parks_need_sources():
    d = assess_wiki_thin_grounding(SOURCE_DEP_ASK, hits=[])
    assert d.thin is True
    assert d.action == ACTION_NEED_SOURCES
    assert "need_sources" in d.reason
    msg = format_need_sources_park_message(d, job_id="job_test")
    assert "need sources" in msg.lower()
    assert "job_test" in msg


def test_vault_hits_proceed_grounded():
    d = assess_wiki_thin_grounding(
        EXISTING_TOPIC_ASK,
        hits=[{"path": "01_Notes/standing_job_in_autoreiv.md"}],
    )
    assert d.thin is False
    assert d.action == ACTION_PROCEED_WITH_HITS
    assert "01_Notes/standing_job_in_autoreiv.md" in d.hit_paths


def test_matched_reads_ground_thin_vault():
    d = assess_wiki_thin_grounding(
        EXISTING_TOPIC_ASK,
        hits=[],
        matched_read_paths=["01_Notes/standing_job_in_autoreiv.md"],
    )
    assert d.thin is True
    assert d.action == ACTION_GROUNDED_ONLY
    assert d.reason == "thin_vault_grounded_on_matched_reads"


def test_non_wiki_skipped():
    d = assess_wiki_thin_grounding("ping health endpoint", hits=[])
    assert d.action == ACTION_SKIP


def test_constraint_block_forbids_invent():
    d = assess_wiki_thin_grounding(EMPTY_TOPIC_ASK, hits=[])
    block = format_grounding_constraint_block(d)
    assert "CARD-260" in block
    assert "Never invent" in block
    assert "wiki_note_create" in block


# --- REQ-WIKITHIN-002 --------------------------------------------------------


def test_okta_class_ungrounded_path_detected():
    text = (
        "Done. The note exists at 00_Inbox/okta_sso_how_it_works.md "
        "and you can open it via wiki_note_read."
    )
    claims = extract_claimed_wiki_paths(text)
    assert "00_Inbox/okta_sso_how_it_works.md" in claims
    bad = ungrounded_claimed_paths(text, provenanced=[])
    assert bad == ["00_Inbox/okta_sso_how_it_works.md"]
    honesty = format_ungrounded_claim_honesty(bad, [], job_id="job_x")
    assert "Not done" in honesty
    assert "okta_sso_how_it_works.md" in honesty
    assert "job_x" in honesty


def test_provenanced_create_path_allowed():
    tool_out = json.dumps(
        {"success": True, "path": "00_Inbox/zorblax_9_quantum_flute.md", "title": "Z"}
    )
    paths = collect_provenanced_paths_from_tool_result("wiki_note_create", tool_out)
    assert paths == ["00_Inbox/zorblax_9_quantum_flute.md"]
    text = "Created 00_Inbox/zorblax_9_quantum_flute.md — open via wiki_note_read."
    assert ungrounded_claimed_paths(text, paths) == []


def test_read_tool_output_provenances_path():
    paths = collect_provenanced_paths_from_tool_result(
        "wiki_note_read",
        {"success": True, "path": "01_Notes/standing_job_in_autoreiv.md", "content": "x"},
    )
    assert paths == ["01_Notes/standing_job_in_autoreiv.md"]


def test_unrelated_tool_does_not_provenance():
    assert collect_provenanced_paths_from_tool_result("health_check", {"path": "x.md"}) == []


# --- standing apply / park ---------------------------------------------------


def test_apply_parks_formulate_on_need_sources(orch, resolver, empty_wiki):
    _seed_wiki_tools(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=SOURCE_DEP_ASK,
        session_id="sess_card260_park",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
        matched_capability_ids=[
            "tool.wiki_note_read",
            "tool.wiki_note_search",
        ],
    )
    decision = apply_standing_wiki_thin_grounding(
        orch,
        job,
        wiki_root=str(empty_wiki),
        intent=SOURCE_DEP_ASK,
        park=True,
    )
    assert decision.action == ACTION_NEED_SOURCES
    phases = orch._store.list_phases_for_job(job.id)
    formulate = next(p for p in phases if p.name.lower().startswith("formulate"))
    assert formulate.status == PhaseStatus.WAITING_APPROVAL
    refreshed = orch._store.get_job(job.id)
    assert refreshed.status.value == "waiting_approval"


def test_apply_create_thin_does_not_park(orch, resolver, empty_wiki):
    _seed_wiki_tools(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=EMPTY_TOPIC_ASK,
        session_id="sess_card260_create",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
        matched_capability_ids=[
            "tool.wiki_note_create",
            "tool.wiki_note_read",
        ],
    )
    decision = apply_standing_wiki_thin_grounding(
        orch,
        job,
        wiki_root=str(empty_wiki),
        intent=EMPTY_TOPIC_ASK,
        park=True,
    )
    assert decision.action == ACTION_GROUNDED_ONLY
    phases = orch._store.list_phases_for_job(job.id)
    formulate = next(p for p in phases if p.name.lower().startswith("formulate"))
    assert formulate.status == PhaseStatus.QUEUED


def test_apply_with_seeded_hits_proceeds(orch, resolver, seeded_wiki):
    _seed_wiki_tools(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=EXISTING_TOPIC_ASK,
        session_id="sess_card260_hits",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
        matched_capability_ids=[
            "tool.wiki_note_create",
            "tool.wiki_note_read",
            "tool.wiki_note_search",
        ],
    )
    decision = apply_standing_wiki_thin_grounding(
        orch,
        job,
        wiki_root=str(seeded_wiki),
        intent=EXISTING_TOPIC_ASK,
        park=True,
    )
    assert decision.action == ACTION_PROCEED_WITH_HITS
    assert decision.thin is False
    assert any("standing_job" in p for p in decision.hit_paths)


def test_generic_token_hits_do_not_count():
    """Hits that only share generic tokens stay thin."""
    d = assess_wiki_thin_grounding(
        SOURCE_DEP_ASK,
        hits=[{"path": "01_Notes/ops/server_maintenance.md", "title": "Server maintenance"}],
    )
    assert d.thin is True
    assert d.action == ACTION_NEED_SOURCES


def test_vault_hit_path_counts_as_grounded_claim():
    """Formulate may cite vault probe hit paths (RAG allow-list) without tool yet."""
    text = "Plan: read 01_Notes/standing_job_in_autoreiv.md then summarize."
    allowed = ["01_Notes/standing_job_in_autoreiv.md"]
    assert ungrounded_claimed_paths(text, allowed) == []


def test_ellipsis_paths_are_not_claimed():
    text = "See 01_Notes/.../standing_job_in_autoreiv.md in the table."
    assert extract_claimed_wiki_paths(text) == []
