"""CARD-638: Lumina Studio is removed from the back end: no module, no /api/lumina routes, no Lumina fields."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
LUMINA = re.compile(r"lumina(?!nce)", re.IGNORECASE)


@pytest.fixture(scope="module")
def client():
    from src.web.app import app

    return TestClient(app)


def test_lumina_module_is_deleted():
    assert not (ROOT / "src/application/education/lumina.py").exists()
    with pytest.raises(ImportError):
        __import__("src.application.education.lumina")


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/lumina/starters", None),
        ("get", "/api/lumina/lesson/photosynthesis", None),
        ("post", "/api/lumina/compose", {"topic": "Black holes"}),
        ("post", "/api/lumina/send-to-course", {"topic": "Photosynthesis"}),
    ],
)
def test_lumina_routes_are_gone(client, method, path, body):
    res = client.get(path) if method == "get" else client.post(path, json=body)
    assert res.status_code in (404, 405), (path, res.status_code)


def test_no_lumina_route_is_registered():
    from src.web.app import app

    paths = [getattr(r, "path", "") for r in app.routes]
    assert [p for p in paths if "lumina" in p.lower()] == []


def test_no_python_source_mentions_lumina():
    hits = [str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py") if LUMINA.search(p.read_text(encoding="utf-8"))]
    assert hits == []


def test_amplifier_summary_has_no_lumina_field(tmp_path):
    from src.application.education.visual_amplifiers import summarize_amplifiers
    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

    repo = AgentMemoryRepository(db_path=tmp_path / "m.db")
    repo.initialize_schema()
    summary = summarize_amplifiers(repo)
    assert "lumina_film" not in summary
    assert summary["retrieval_required"] is True
