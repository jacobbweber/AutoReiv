"""CARD-648: the unused Construction "generate" route wrote a template study artifact (the same
sections, a fixed diagram and quiz prompts such as "In one sentence, what is X?") for every topic.
Nothing in the course or the UI called it, so it is removed rather than fixed. The course labs keep
writing their grounded notes through create_study_artifact_note."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import src.application.education as edu
import src.application.education.construction as construction

SRC = Path(construction.__file__).resolve().parents[2]


def test_template_builder_and_generate_path_are_gone():
    for name in ("build_study_artifact_markdown", "construct_study_artifact", "ARTIFACT_KIND"):
        assert not hasattr(construction, name), name
        assert not hasattr(edu, name), name
    # The course lab writer still files its notes through the shared creator.
    assert callable(construction.create_study_artifact_note)


def test_generate_route_is_gone():
    from src.web.app import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/education/construction/generate" not in paths
    with TestClient(app) as client:
        res = client.post("/api/education/construction/generate", json={"topic": "Raft log replication"})
    assert res.status_code in (404, 405)


def test_no_source_refers_to_the_removed_route_or_template():
    hits = []
    for path in SRC.rglob("*"):
        if path.suffix not in (".py", ".js", ".mjs", ".html") or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in ("construction/generate", "build_study_artifact_markdown", "construct_study_artifact"):
            if needle in text:
                hits.append(f"{path.relative_to(SRC)}: {needle}")
    assert hits == []
