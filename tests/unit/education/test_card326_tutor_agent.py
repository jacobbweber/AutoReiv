"""
CARD-326: Education Learning OS — Tutor Agent (Wiki + Ledger Aware).
Tests [REQ-EDU-TUTOR-001] through [REQ-EDU-TUTOR-004].
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.application.agent_packs.schema import (
    AgentPackManifest,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.skills.platform_packs import (
    platform_packs_root,
)
from src.web.app import app


def test_req_edu_tutor_001_platform_pack_exists_and_valid():
    """Verify tutor capability exists as socratic-tutoring skill in autoreiv [REQ-EDU-TUTOR-001, CARD-366]."""
    root = platform_packs_root()
    pack_dir = root / "autoreiv"
    manifest_path = pack_dir / "pack.json"
    skill_path = pack_dir / "skills" / "socratic-tutoring" / "SKILL.md"

    assert manifest_path.is_file(), f"Expected manifest at {manifest_path}"
    assert skill_path.is_file(), f"Expected runbook at {skill_path}"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = AgentPackManifest.model_validate(data)

    assert manifest.id == "autoreiv"
    assert "socratic-tutoring" in {s.id for s in manifest.skills}
    assert "socratic-tutoring" in manifest.allowed_skill

    skill_text = skill_path.read_text(encoding="utf-8")
    assert "tutoring" in skill_text.lower()
    assert "socratic" in skill_text.lower()


def test_req_edu_tutor_002_context_loads_wiki_and_ledger_from_same_memory_db(tmp_path: Path):
    """Verify tutor context loads wiki notes + mastery ledger from same memory.db [REQ-EDU-TUTOR-002]."""
    from src.application.education.tutor import assemble_tutor_topic_context

    db_path = tmp_path / "assistant_memory.db"
    memory_repo = AgentMemoryRepository(db_path=db_path)
    memory_repo.initialize_schema()

    # Seed an item into education_mastery
    from src.infrastructure.memory.repositories.education_mastery_ops import (
        record_education_grade,
        upsert_education_mastery,
    )

    upsert_education_mastery(
        memory_repo,
        item_id="edu_photosynthesis_01",
        topic="Photosynthesis",
        wiki_path="00_Inbox/photosynthesis.md",
        prompt="Where does light-dependent reaction occur?",
        expected_answer="Thylakoid membrane",
    )
    record_education_grade(
        memory_repo,
        item_id="edu_photosynthesis_01",
        correct=False,
    )

    # Call context assembly
    ctx = assemble_tutor_topic_context(
        topic="Photosynthesis",
        memory_repo=memory_repo,
    )

    assert ctx["topic"] == "Photosynthesis"
    assert ctx["tutor_agent_id"] == "tutor"
    assert len(ctx["weak_items"]) >= 1
    assert ctx["weak_items"][0]["item_id"] == "edu_photosynthesis_01"
    assert "Photosynthesis" in ctx["context_prompt_clause"]
    assert "Thylakoid membrane" in ctx["context_prompt_clause"] or "miss" in ctx["context_prompt_clause"]


def test_req_edu_tutor_003_never_invents_second_tutor_storage_db(tmp_path: Path):
    """Verify tutor strictly uses memory.db and never invents storage.db or second DB [REQ-EDU-TUTOR-003]."""
    from src.application.education.tutor import assemble_tutor_topic_context

    db_path = tmp_path / "assistant_memory.db"
    memory_repo = AgentMemoryRepository(db_path=db_path)
    memory_repo.initialize_schema()

    assemble_tutor_topic_context(
        topic="Cellular Respiration",
        memory_repo=memory_repo,
    )

    created_files = [f.name for f in tmp_path.glob("*")]
    assert "assistant_memory.db" in created_files
    for f in created_files:
        assert "storage.db" not in f
        assert "tutor_storage" not in f
        assert "education_storage" not in f


def test_req_edu_tutor_004_api_endpoint_returns_tutor_context():
    """Verify /api/education/tutor/context endpoint returns structured context [REQ-EDU-TUTOR-004]."""
    client = TestClient(app)
    resp = client.post(
        "/api/education/tutor/context",
        json={"agent_id": "assistant", "topic": "Cognitive Load Theory"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "Cognitive Load Theory"
    assert data["tutor_agent_id"] == "tutor"
    assert "context_prompt_clause" in data
    assert "Socratic" in data["context_prompt_clause"] or "Cognitive Load Theory" in data["context_prompt_clause"]
