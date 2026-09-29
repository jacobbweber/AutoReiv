"""CARD-569 guard: pack import/export, the pack builder and the pack MCP server stay removed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]
SCAN_DIRS = ("src", "platform-packs", "tests/e2e")
SUFFIXES = {".py", ".js", ".html", ".json", ".md", ".css", ".ts"}
GONE = (
    "export_agent_pack",
    "import_agent_pack",
    "scaffold_agent_pack",
    "propose_agent_specification",
    "inspect_agent_pack",
    "pack_server",
    "import-pack",
    "pack.zip",
    "build-agent-pack",
    "startNewAgentPackFromStudio",
)


def test_no_pack_import_export_names_left_in_product_code():
    hits: list[str] = []
    for rel in SCAN_DIRS:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES or "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for name in GONE:
                if name in text:
                    hits.append(f"{path.relative_to(ROOT)}: {name}")
    assert hits == []


def test_pack_modules_and_seed_are_gone():
    assert importlib.util.find_spec("src.application.skills.agent_skill_tool_list") is None
    assert importlib.util.find_spec("src.infrastructure.mcp.pack_server") is None
    assert not (ROOT / "src/infrastructure/skills/seeds/build-agent-pack").exists()
    assert not (ROOT / "platform/skills/build-agent-pack").exists()


def test_pack_routes_are_gone():
    from src.web.routers.agents import router

    paths = {getattr(r, "path", "") for r in router.routes}
    assert not any(p.endswith("/pack.zip") for p in paths)
    assert "/api/agents/import-pack" not in paths


def test_inspect_agent_is_registered_read_only():
    from src.application.skills.agent_inspect_tools import INSPECT_AGENT

    assert INSPECT_AGENT == "inspect_agent"
