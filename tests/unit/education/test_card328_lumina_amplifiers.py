"""Unit tests for CARD-328: Education Learning OS Amplifiers & Lumina Studio integration."""

from __future__ import annotations

from pathlib import Path

from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _wiki(tmp_path: Path) -> WikiTools:
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    return WikiTools(wiki_root=wiki_root)


def test_lumina_starter_lessons():
    """Verify that seeded Lumina starter lessons are valid and conform to the 14-archetype schema."""
    from src.application.education.lumina import (
        STARTERS,
        VISUAL_KINDS,
        get_starter_lesson,
    )

    assert len(STARTERS) >= 5
    photosynthesis = get_starter_lesson("photosynthesis")
    assert photosynthesis is not None
    assert photosynthesis["topic"] == "Photosynthesis"
    assert len(photosynthesis["scenes"]) >= 3

    for s in photosynthesis["scenes"]:
        assert "headline" in s
        assert "narration" in s
        assert "durationMs" in s
        assert s["durationMs"] >= 5000
        viz = s.get("visual") or {}
        assert viz.get("kind") in VISUAL_KINDS
        assert len(viz.get("nodes", [])) >= 2


def test_lumina_lesson_normalization():
    """Verify normalize_lesson repairs and validates raw LLM JSON outputs."""
    from src.application.education.lumina import normalize_lesson

    raw = {
        "title": "Quantum Entanglement",
        "essence": "Two particles linked across space.",
        "scenes": [
            {
                "headline": "Twin particles born",
                "narration": "A single event splits energy into two entangled states.",
                "visual": {
                    "kind": "split",
                    "nodes": [{"id": "source", "label": "Laser"}, {"id": "p1", "label": "Photon A"}],
                }
            },
            {
                "headline": "Distance expands",
                "narration": "They travel light-years apart without breaking connection.",
                "visual": {
                    "kind": "wave",
                    "nodes": [{"id": "p1", "label": "Photon A"}, {"id": "p2", "label": "Photon B"}],
                }
            },
            {
                "headline": "Measurement collapses both",
                "narration": "Measuring one instantly dictates the state of the other.",
                "visual": {
                    "kind": "compare",
                    "nodes": [{"id": "obs", "label": "Measurement"}, {"id": "state", "label": "Instant Spin"}],
                }
            }
        ]
    }

    lesson = normalize_lesson(raw, "Quantum Entanglement")
    assert lesson["topic"] == "Quantum Entanglement"
    assert lesson["title"] == "Quantum Entanglement"
    assert len(lesson["scenes"]) == 3
    assert lesson["scenes"][0]["visual"]["kind"] == "split"


def test_complete_course_step_amplifiers_wires_ledger(tmp_path: Path):
    """Verify course pipeline step 'amplifiers' produces a real visual amplifier note and ledger anchor."""
    from src.application.education.course import complete_course_step, jump_to_course_step, start_or_resume_course

    repo = _repo(tmp_path)
    tools = _wiki(tmp_path)

    course = start_or_resume_course(repo, topic_id="Neural Networks")
    jump_to_course_step(repo, course_id=course["course_id"], step="amplifiers")

    result = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
    )

    assert result["success"] is True
    assert result["completed_step"] == "amplifiers"
    assert "00_Inbox/" in result["wiki_path"]
    assert len(result["item_ids"]) == 1

    item_id = result["item_ids"][0]
    mastery = repo.get_education_mastery(item_id)
    assert mastery is not None
    assert mastery["topic"] == "Neural Networks"
    assert "amplifier" in mastery["prompt"].lower()

    fact = repo.get_semantic_fact("edu_course_neural_networks_amplifiers")
    assert fact is not None
    assert fact["entity"] == "education_learner"
    assert "course_step_amplifiers" in fact["attribute"]

    artifact = result.get("artifact", {})
    assert artifact.get("kind") == "course_amplifiers"
    assert "visual_spec" in artifact or "mermaid" in artifact


def test_lumina_send_to_course_bridge(tmp_path: Path):
    """Verify that a Lumina lesson can be converted into an active education_course."""
    from src.application.education.course import course_chrome_snapshot, start_or_resume_course
    from src.application.education.lumina import get_starter_lesson

    repo = _repo(tmp_path)
    starter = get_starter_lesson("photosynthesis")
    assert starter is not None

    course = start_or_resume_course(repo, topic_id=starter["topic"])
    assert course["status"] == "active"
    assert course["topic_id"] == "Photosynthesis"

    snapshot = course_chrome_snapshot(repo, topic_id="Photosynthesis")
    assert snapshot["status"] == "active"
    assert "amplifiers" in snapshot["steps"]


def test_lumina_api_endpoints(tmp_path: Path):
    """Verify Lumina starters, lesson retrieval, compose, and send-to-course API endpoints."""
    from fastapi.testclient import TestClient

    from src.web.app import app

    repo = _repo(tmp_path)
    app.state.memory_repo = repo
    client = TestClient(app)

    # 1. Starters
    res_starters = client.get("/api/lumina/starters")
    assert res_starters.status_code == 200
    sdata = res_starters.json()
    assert "starters" in sdata
    assert len(sdata["starters"]) >= 5

    # 2. Get lesson
    res_lesson = client.get("/api/lumina/lesson/photosynthesis")
    assert res_lesson.status_code == 200
    ldata = res_lesson.json()
    assert ldata["lesson"]["topic"] == "Photosynthesis"

    # 3. Compose (deterministic fallback without gateway)
    res_compose = client.post("/api/lumina/compose", json={"topic": "Black holes"})
    assert res_compose.status_code == 200
    cdata = res_compose.json()
    assert cdata["ok"] is True
    assert cdata["lesson"]["topic"] == "Black holes"

    # 4. Send to course
    res_bridge = client.post("/api/lumina/send-to-course", json={"topic": "Photosynthesis"})
    assert res_bridge.status_code == 200
    bdata = res_bridge.json()
    assert bdata["ok"] is True
    assert bdata["course"]["topic_id"] == "Photosynthesis"
    assert bdata["snapshot"]["status"] == "active"

