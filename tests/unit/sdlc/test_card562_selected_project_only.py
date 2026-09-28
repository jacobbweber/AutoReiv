"""CARD-562: project tools work only in the selected project; project_root cannot bypass or redirect it."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.sdlc.paths import ProjectPathError
from src.application.sdlc.projects_service import NO_PROJECT_MESSAGE, ProjectsService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

PROJECT_TOOL_CLASSES = ("CardTools", "GitTools", "ProjectFileTools", "GitHubIssueTools", "ProjectDevTools")


@pytest.fixture
def svc():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return ProjectsService(store=store)


def test_refuses_without_selection_even_with_project_root(svc, tmp_path: Path):
    with pytest.raises(ProjectPathError, match="No project is selected"):
        svc.selected_or_refuse(str(tmp_path))
    with pytest.raises(ProjectPathError) as exc:
        svc.selected_or_refuse()
    assert str(exc.value) == NO_PROJECT_MESSAGE


def test_selected_project_root_must_match(svc, tmp_path: Path):
    active = tmp_path / "calc"
    other = tmp_path / "other"
    active.mkdir()
    other.mkdir()
    svc.set_selected(slug="calc", path=str(active))
    assert svc.selected_or_refuse() == active.resolve()
    assert svc.selected_or_refuse(str(active)) == active.resolve()
    with pytest.raises(ProjectPathError, match="not the active project") as exc:
        svc.selected_or_refuse(str(other))
    assert "calc" in str(exc.value)


def test_registry_wires_every_project_tool_through_selected_or_refuse(tmp_path: Path):
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    skills = tmp_path / "data" / "skills"
    skills.mkdir(parents=True)
    _, reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store), skills_dir=str(skills))
    owners = {}
    for name, registration in reg._tools.items():
        owner = getattr(registration.handler, "__self__", None)
        if owner is not None and type(owner).__name__ in PROJECT_TOOL_CLASSES:
            owners.setdefault(type(owner).__name__, (name, owner))
    assert set(owners) == set(PROJECT_TOOL_CLASSES), set(PROJECT_TOOL_CLASSES) - set(owners)
    for cls, (name, owner) in owners.items():
        resolver = getattr(owner, "_root_resolver", None)
        assert resolver is not None, cls
        assert getattr(resolver, "__name__", "") == "selected_or_refuse", (cls, name, resolver)


def test_project_tools_schemas_do_not_offer_project_root(tmp_path: Path):
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    skills = tmp_path / "data" / "skills"
    skills.mkdir(parents=True)
    _, reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store), skills_dir=str(skills))
    offending = []
    for name, registration in reg._tools.items():
        owner = getattr(registration.handler, "__self__", None)
        if owner is not None and type(owner).__name__ in PROJECT_TOOL_CLASSES:
            if "project_root" in ((registration.definition.parameters or {}).get("properties") or {}):
                offending.append(name)
    assert offending == []


def test_list_cards_refuses_after_project_cleared_even_with_root(svc, tmp_path: Path):
    from src.application.skills.card_tools import CardTools

    root = tmp_path / "calc"
    (root / ".agents" / "cards").mkdir(parents=True)
    cards = CardTools(root_resolver=svc.selected_or_refuse)
    svc.set_selected(slug="calc", path=str(root))
    assert cards.list_cards()["success"]
    svc.set_selected(slug=None, path=None)
    with pytest.raises(ProjectPathError, match="No project is selected"):
        cards.list_cards(project_root=str(root))
