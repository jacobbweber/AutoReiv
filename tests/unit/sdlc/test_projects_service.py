"""
Projects root jail, create, delete confirm [REQ-SDLC-050, REQ-SDLC-051].
"""

from pathlib import Path

from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.card_tools import CardTools
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _svc(tmp_path: Path) -> ProjectsService:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, default_checkout=tmp_path / "checkout")
    (tmp_path / "checkout").mkdir()
    svc.set_projects_root(str(tmp_path / "lab"))
    (tmp_path / "lab").mkdir()
    return svc


def test_create_list_jail_and_delete_confirm(tmp_path: Path):
    svc = _svc(tmp_path)
    created = svc.create_project(slug="demo-app")
    assert created["success"] is True
    assert (tmp_path / "lab" / "demo-app").is_dir()
    listed = svc.list_projects()
    assert any(p["slug"] == "demo-app" for p in listed["projects"])
    escape = svc.create_project(slug="../outside")
    assert escape["success"] is False
    denied = svc.delete_project(slug="demo-app", confirm=False)
    assert denied["success"] is False
    assert "confirm" in denied["error"]
    assert (tmp_path / "lab" / "demo-app").is_dir()
    deleted = svc.delete_project(slug="demo-app", confirm=True)
    assert deleted["success"] is True
    assert not (tmp_path / "lab" / "demo-app").exists()


def test_selected_project_is_card_default_root(tmp_path: Path):
    svc = _svc(tmp_path)
    svc.create_project(slug="alpha")
    svc.set_selected(slug="alpha")
    skill = CardTools(root_resolver=svc.resolve_root)
    (tmp_path / "lab" / "alpha" / ".github" / "cards").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lab" / "alpha" / "AGENTS.md").write_text("# A\n", encoding="utf-8")
    listed = skill.list_cards()
    assert listed["success"] is True
    assert "alpha" in listed["project_root"]


def test_create_project_tool_registered_and_hitl():
    from src.application.kernel.hitl_engine import HITLApprovalEngine
    from src.application.telemetry.collector import TelemetryCollector
    from src.domain.gateway.models import ToolCall
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    _, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store))
    engine = HITLApprovalEngine(store=store)
    assert engine.requires_approval(ToolCall(id="1", name="create_project", arguments={"slug": "x"}))


def test_create_project_scaffolds_dotagents_and_kiro_artifacts(tmp_path: Path):
    """[REQ-SDLC-060, REQ-SDLC-062] create_project scaffolds .agents/ with Kiro steering and templates."""
    svc = _svc(tmp_path)
    res = svc.create_project(slug="kiro-app")
    assert res["success"] is True

    proj_dir = tmp_path / "lab" / "kiro-app"
    assert (proj_dir / ".gitignore").is_file()
    assert (proj_dir / ".git").is_dir()
    assert (proj_dir / ".agents" / "cards").is_dir()
    assert (proj_dir / ".agents" / "specs").is_dir()
    assert (proj_dir / ".agents" / "adr").is_dir()

    # Kiro steering
    assert (proj_dir / ".agents" / "steering" / "product.md").is_file()
    assert (proj_dir / ".agents" / "steering" / "tech.md").is_file()
    assert (proj_dir / ".agents" / "steering" / "structure.md").is_file()
    assert (proj_dir / ".agents" / "steering" / "roadmap.md").is_file()

    # Standard templates with Three Beats
    card_tmpl = proj_dir / ".agents" / "templates" / "card.template.md"
    assert card_tmpl.is_file()
    content = card_tmpl.read_text(encoding="utf-8")
    assert "Three Beats" in content
    assert "What you mean" in content
    assert "What AutoReiv does now" in content
    assert "What will change" in content

    # Check other templates
    assert (proj_dir / ".agents" / "templates" / "requirements.template.md").is_file()
    assert (proj_dir / ".agents" / "templates" / "design.template.md").is_file()
    assert (proj_dir / ".agents" / "templates" / "tasks.template.md").is_file()
    assert (proj_dir / ".agents" / "templates" / "adr.template.md").is_file()

