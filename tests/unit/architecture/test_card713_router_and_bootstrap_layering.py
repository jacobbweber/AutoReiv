"""Guard tests for CARD-713: chat router decomposition and bootstrap/busy layering."""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def test_chat_router_and_extracted_modules_under_800_lines():
    """src/web/routers/chat.py and every extracted src/application/chat/*.py module must be < 800 lines."""
    chat_router = ROOT / "src/web/routers/chat.py"
    chat_lines = len(chat_router.read_text(encoding="utf-8").splitlines())
    assert chat_lines < 800, f"src/web/routers/chat.py is {chat_lines} lines (must be < 800)"

    chat_pkg = ROOT / "src/application/chat"
    assert chat_pkg.is_dir(), "src/application/chat/ package must exist"
    expected_modules = {"stream_registry.py", "turn_streamer.py", "job_runner.py", "attachments.py"}
    actual_modules = {p.name for p in chat_pkg.glob("*.py") if p.name != "__init__.py"}
    assert expected_modules.issubset(actual_modules), f"Missing modules: {expected_modules - actual_modules}"

    for py_file in sorted(chat_pkg.glob("*.py")):
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        assert lines < 800, f"{py_file.relative_to(ROOT)} is {lines} lines (must be < 800)"


def test_infrastructure_agent_registry_does_not_import_application_skills():
    """src/infrastructure/agents/registry.py must delegate bootstrap to src/application/bootstrap/ecosystem.py."""
    registry_path = ROOT / "src/infrastructure/agents/registry.py"
    src = registry_path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    forbidden_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("src.application.") and node.module != "src.application.bootstrap.ecosystem":
                # Allow TYPE_CHECKING imports only
                forbidden_imports.append(node.module)

    # Check non-TYPE_CHECKING imports
    top_or_fn_forbidden = []
    for node in tree.body:
        if isinstance(node, ast.If):
            # Skip if TYPE_CHECKING:
            test_name = getattr(node.test, "id", "")
            if test_name == "TYPE_CHECKING":
                continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.ImportFrom) and sub.module:
                if (
                    sub.module.startswith("src.application.")
                    and sub.module != "src.application.bootstrap.ecosystem"
                ):
                    top_or_fn_forbidden.append(sub.module)

    assert top_or_fn_forbidden == [], (
        f"src/infrastructure/agents/registry.py still imports from src.application: {top_or_fn_forbidden}"
    )
    ecosystem_path = ROOT / "src/application/bootstrap/ecosystem.py"
    assert ecosystem_path.is_file(), "src/application/bootstrap/ecosystem.py must exist"
    eco_lines = len(ecosystem_path.read_text(encoding="utf-8").splitlines())
    assert eco_lines < 800, f"src/application/bootstrap/ecosystem.py is {eco_lines} lines"


def test_busy_detector_does_not_import_from_web_layer():
    """src/application/system/busy.py must not import upward from src.web.*."""
    busy_path = ROOT / "src/application/system/busy.py"
    src = busy_path.read_text(encoding="utf-8")
    assert "src.web" not in src, "src/application/system/busy.py must not import from src.web"


def test_web_app_single_instantiation_and_lazy_default_app():
    """src/web/app.py must not have duplicate UserSkillCatalog/JobPhaseOrchestrator wiring or NameError hacks."""
    app_src = (ROOT / "src/web/app.py").read_text(encoding="utf-8")
    assert "except NameError:" not in app_src
    assert app_src.count("JobPhaseOrchestrator(") == 1
    assert "\napp = create_app()" not in app_src
