"""CARD-539 / ADR-0061 architecture guard: only resolve_allowed_tools decides an agent's tools.

Fails when any module other than src/application/agent_packs/allowed_tools.py:
1. references resolve_scoped_tools (retired);
2. imports the skill-to-tool seed tables or the SQLite binding reader to build a tool set;
3. reads the legacy allowed_tool_names / pack_tool_names fields inside permission,
   selection or prompt code;
4. special-cases the 'autoreiv' id inside permission or selection code.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src"
DECIDER = "application/agent_packs/allowed_tools.py"

SEED_NAMES = {"PLATFORM_SKILL_TOOLS", "DYNAMIC_SKILL_TOOLS", "tools_for_platform_skills", "sqlite_tools_for_skills"}
# Where the seed tables are defined, and Skill Studio's single-skill binding view (not agent permission).
SEED_OK = {DECIDER, "application/agent_packs/schema.py", "application/skills/workshop.py",
           "infrastructure/memory/repositories/skill_bindings.py"}

LEGACY_FIELDS = {"allowed_tool_names", "pack_tool_names"}
PERMISSION_DIRS = (
    "application/kernel/",
    "application/safety/",
    "application/orchestration/",
    "application/capabilities/",
    "application/tools/",
    "application/skills/",
)
# Pack export keeps the legacy field in interchange files; the migration reads it once.
LEGACY_OK = {"application/skills/agent_pack_tools.py", "application/agent_packs/capability_migration.py"}

SPECIAL_CASE_FILES = {
    "application/kernel/tool_registry.py",
    "application/kernel/agent_kernel.py",
    "application/safety/tool_policy_gate.py",
    "application/skills/platform_primitives.py",
    DECIDER,
}


def _modules():
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        yield rel, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_resolve_scoped_tools_is_retired():
    offenders = []
    for rel, tree in _modules():
        for node in ast.walk(tree):
            name = getattr(node, "id", None) or getattr(node, "attr", None) or getattr(node, "name", None)
            if name == "resolve_scoped_tools":
                offenders.append(rel)
    assert not offenders, f"resolve_scoped_tools must be gone (ADR-0061): {sorted(set(offenders))}"


def test_seed_tables_only_read_by_the_decider():
    offenders = []
    for rel, tree in _modules():
        if rel in SEED_OK:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                hit = SEED_NAMES & {a.name for a in node.names}
                if hit:
                    offenders.append(f"{rel}: {sorted(hit)}")
    assert not offenders, f"Only allowed_tools.py may map skills to tools: {offenders}"


def test_permission_code_never_reads_legacy_tool_lists():
    offenders = []
    for rel, tree in _modules():
        if not rel.startswith(PERMISSION_DIRS) or rel in LEGACY_OK:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in LEGACY_FIELDS:
                offenders.append(f"{rel}:{node.lineno} .{node.attr}")
            if isinstance(node, ast.Constant) and node.value in LEGACY_FIELDS:
                offenders.append(f"{rel}:{node.lineno} '{node.value}'")
    assert not offenders, f"Permission code must call resolve_allowed_tools, not legacy lists: {offenders}"


def test_no_autoreiv_special_case_in_permission_or_selection():
    offenders = []
    for rel, tree in _modules():
        if rel not in SPECIAL_CASE_FILES:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                parts = [node.left, *node.comparators]
                if any(isinstance(p, ast.Constant) and p.value == "autoreiv" for p in parts):
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"No agent-id special case (ADR-0061 rule 3): {offenders}"
