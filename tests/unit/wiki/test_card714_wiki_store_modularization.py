"""CARD-714: WikiStore modularization, domain layer purity, and single-pass graph/mindmap indexing."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.domain.wiki.store import WikiStore

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]


def _imported_modules(py_path: Path) -> set[str]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_layer_has_zero_upward_imports() -> None:
    """No module in src/domain/ may import from src.application, src.infrastructure, or src.web."""
    domain_root = REPO_ROOT / "src" / "domain"
    forbidden_prefixes = ("src.application", "src.infrastructure", "src.web")
    violations: list[str] = []

    for py_file in sorted(domain_root.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        for mod in sorted(_imported_modules(py_file)):
            if mod.startswith(forbidden_prefixes):
                violations.append(f"{rel} -> {mod}")

    assert not violations, f"Upward imports found in src/domain/: {violations}"


def test_wiki_domain_modules_under_800_lines() -> None:
    """Every module in src/domain/wiki/ must be under the 800-line ceiling."""
    wiki_dir = REPO_ROOT / "src" / "domain" / "wiki"
    expected_modules = (
        "store.py",
        "templates_catalog.py",
        "education_templates.py",
        "vault_migration.py",
        "graph_index.py",
        "frontmatter.py",
        "template_folders.py",
    )
    for mod_name in expected_modules:
        mod_path = wiki_dir / mod_name
        assert mod_path.is_file(), f"Expected module {mod_path} to exist"

    for py_file in sorted(wiki_dir.glob("*.py")):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 800, f"{py_file.name} is {line_count} lines (must be < 800)"


def test_get_graph_and_get_mindmap_read_each_note_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """get_graph() and get_mindmap() must read each vault note once per call, not twice."""
    vault_dir = tmp_path / "wiki"
    store = WikiStore(root_dir=vault_dir)
    store.scaffold()

    n1 = store.file_note(
        title="Alpha Architecture",
        domain="systems_engineering",
        topic="architecture",
        category="notes",
        tags=["architecture", "core"],
        content="Alpha connects to [[Beta Service]] and [[Gamma Store]].",
    )
    n2 = store.file_note(
        title="Beta Service",
        domain="systems_engineering",
        topic="architecture",
        category="notes",
        tags=["service"],
        content="Beta depends on [[Gamma Store]].",
    )
    n3 = store.file_note(
        title="Gamma Store",
        domain="systems_engineering",
        topic="storage",
        category="notes",
        tags=["storage", "core"],
        content="Leaf storage node.",
    )
    note_rel_paths = {n1["path"], n2["path"], n3["path"]}

    orig_read_text = Path.read_text
    read_counts: dict[str, int] = {}

    def counting_read_text(self: Path, *args, **kwargs) -> str:
        try:
            rel = self.resolve().relative_to(vault_dir.resolve()).as_posix()
            read_counts[rel] = read_counts.get(rel, 0) + 1
        except ValueError:
            pass
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    # 1. Verify get_graph() reads each note exactly once and ignores templates
    read_counts.clear()
    graph = store.get_graph()
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 3
    for rel_path in note_rel_paths:
        assert read_counts.get(rel_path, 0) == 1, (
            f"get_graph() read {rel_path} {read_counts.get(rel_path, 0)} times (expected 1)"
        )
    template_reads = [k for k in read_counts if "_Templates" in k]
    assert not template_reads, f"get_graph() unnecessarily read template files: {template_reads}"

    # 2. Verify get_mindmap() reads each note exactly once and produces all node/edge types
    read_counts.clear()
    mindmap = store.get_mindmap(include_tags=True, include_taxonomy=True)
    node_types = {n["type"] for n in mindmap["nodes"]}
    edge_types = {e["type"] for e in mindmap["edges"]}
    assert {"note", "tag", "domain", "topic"} <= node_types
    assert {"wikilink", "has_tag", "in_topic", "in_domain"} <= edge_types
    for rel_path in note_rel_paths:
        assert read_counts.get(rel_path, 0) == 1, (
            f"get_mindmap() read {rel_path} {read_counts.get(rel_path, 0)} times (expected 1)"
        )
    template_reads_mm = [k for k in read_counts if "_Templates" in k]
    assert not template_reads_mm, f"get_mindmap() unnecessarily read template files: {template_reads_mm}"
