"""CARD-652: POST /api/education/knowledge-artifact filled every section it was not given with fixed
text ("The core conceptual model for X establishes its structural definitions ..."). Nothing in the UI
or the course called it, so the route and its template builder are removed rather than fixed. The
knowledge-type list, shapes and step resolution (used by the course chrome) stay."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import src.application.education.knowledge_types as kt

SRC = Path(kt.__file__).resolve().parents[2]


def test_template_builder_is_gone_but_types_stay():
    assert not hasattr(kt, "build_knowledge_artifact")
    assert not hasattr(kt, "render_knowledge_note_markdown")
    assert set(kt.VALID_KNOWLEDGE_TYPES) == {"concept", "tool", "method", "problem"}
    assert kt.resolve_step_knowledge_type("construction") == "tool"
    text = Path(kt.__file__).read_text(encoding="utf-8")
    assert "establishes its structural definitions" not in text


def test_knowledge_artifact_route_is_gone_and_types_route_stays():
    from src.web.app import app

    with TestClient(app) as client:
        gone = client.post("/api/education/knowledge-artifact", json={"topic": "Raft log replication"})
        types = client.get("/api/education/knowledge-types")
    assert gone.status_code in (404, 405)
    assert types.status_code == 200
    assert set(types.json()["knowledge_types"]) == {"concept", "tool", "method", "problem"}


def test_no_source_refers_to_the_removed_route_or_builder():
    hits = []
    for path in SRC.rglob("*"):
        if path.suffix not in (".py", ".js", ".mjs", ".html") or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in ("knowledge-artifact", "build_knowledge_artifact", "render_knowledge_note_markdown"):
            if needle in text:
                hits.append(f"{path.relative_to(SRC)}: {needle}")
    assert hits == []
