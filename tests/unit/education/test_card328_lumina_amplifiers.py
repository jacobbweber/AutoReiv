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


def test_lumina_api_endpoints(tmp_path: Path):
    """Verify Lumina starters, lesson retrieval, and compose API endpoints."""
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

