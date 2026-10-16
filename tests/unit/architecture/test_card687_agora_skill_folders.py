"""CARD-687 / ADR-0065 guard: Agora skill folders with colocated tools/*.py and references/*.md.

Verifies:
1. ADR-0065 exists and is Accepted.
2. AST schema inference extracts tool name, docstring description, JSON Schema parameters
   (types, required vs optional, defaults), and risk/access from tools/*.py without
   importing or executing top-level code.
3. Colocated tools flow through ContentStore.skill_tools and resolve_allowed_tools(agent)
   only when enabled (shipped tools enabled by default; user tools require approved SHA-256).
4. skill_view lists colocated references/*.md and tools/*.py and loads a reference on demand
    while rejecting path traversal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def test_adr_0065_exists_and_is_accepted():
    adr = ROOT / "docs" / "adr" / "0065-agora-skill-folders-and-unified-capabilities.md"
    assert adr.is_file(), "ADR-0065 must exist"
    text = adr.read_text(encoding="utf-8")
    assert "**Status**: Accepted" in text
    assert "CARD-687" in text


def test_ast_schema_inference_never_executes_top_level_code(tmp_path: Path):
    from src.application.skills.agora_loader import extract_agora_tool_spec

    marker = tmp_path / "pwned.txt"
    tool_py = tmp_path / "calc_checksum.py"
    tool_py.write_text(
        f'"""Compute a deterministic checksum for text."""\n'
        f'from pathlib import Path\n'
        f'Path({str(marker)!r}).write_text("ran")\n'
        f'RISK = "read_only"\n\n'
        f'def run(text: str, rounds: int = 1, uppercase: bool = False) -> dict:\n'
        f'    """Run checksum."""\n'
        f'    return {{"text": text, "rounds": rounds, "uppercase": uppercase}}\n',
        encoding="utf-8",
    )

    spec = extract_agora_tool_spec(tool_py)
    assert not marker.exists(), "AST schema inference must never import or execute tool.py"
    assert spec is not None
    assert spec["name"] == "calc_checksum"
    assert spec["description"] == "Compute a deterministic checksum for text."
    assert spec["risk"] == "read_only"
    params = spec["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["text"]
    assert params["properties"]["text"]["type"] == "string"
    assert params["properties"]["rounds"] == {"type": "integer", "default": 1}
    assert params["properties"]["uppercase"] == {"type": "boolean", "default": False}
    assert "files" in spec["access"]


def test_colocated_skill_tools_require_approval_for_user_skills_and_flow_through_allowed_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from src.application.agent_skills.allowed_tools import resolve_allowed_tools
    from src.application.skills.agora_loader import enable_skill_tool
    from src.infrastructure.content import store as store_mod

    platform_root = tmp_path / "platform"
    data_root = tmp_path / "data"
    (platform_root / "agents").mkdir(parents=True)
    (platform_root / "skills").mkdir(parents=True)

    # 1. Shipped skill with a colocated tool -> enabled by default
    shipped_skill = platform_root / "skills" / "shipped-demo"
    (shipped_skill / "tools").mkdir(parents=True)
    (shipped_skill / "SKILL.md").write_text(
        "---\nname: Shipped Demo\ndescription: Shipped Agora skill.\ntools: []\n---\n# Shipped Demo\n",
        encoding="utf-8",
    )
    (shipped_skill / "tools" / "shipped_ping.py").write_text(
        '"""Ping from shipped skill."""\n\ndef run(host: str = "localhost") -> dict:\n    return {"host": host}\n',
        encoding="utf-8",
    )

    # 2. User skill with a colocated tool -> disabled until approved by SHA-256
    user_skill = data_root / "skills" / "user-demo"
    (user_skill / "tools").mkdir(parents=True)
    (user_skill / "SKILL.md").write_text(
        "---\nname: User Demo\ndescription: User Agora skill.\n---\n# User Demo\n",
        encoding="utf-8",
    )
    user_tool_py = user_skill / "tools" / "user_hash.py"
    user_tool_py.write_text(
        '"""Hash input text."""\n\ndef run(value: str) -> dict:\n    return {"len": len(value)}\n',
        encoding="utf-8",
    )

    content_store = store_mod.configure(data_root=data_root, platform_root=platform_root)
    monkeypatch.setattr(store_mod, "_TOOL_REGISTRY", None)

    agent = {"id": "tester", "allowed_skill": ["shipped-demo", "user-demo"]}
    allowed_before = resolve_allowed_tools(agent)
    assert "shipped_ping" in allowed_before
    assert "user_hash" not in allowed_before, "Unapproved user colocated tool must not be granted"

    # Enable user_hash -> records approved SHA-256 and grants the tool
    enable_skill_tool(content_store, "user-demo", "user_hash")
    allowed_after = resolve_allowed_tools(agent)
    assert "user_hash" in allowed_after

    # Mutating user_hash.py invalidates the approved SHA-256 -> revoked automatically
    user_tool_py.write_text(
        '"""Hash input text (modified)."""\n\ndef run(value: str) -> dict:\n    return {"len": 0}\n',
        encoding="utf-8",
    )
    allowed_tampered = resolve_allowed_tools(agent)
    assert "user_hash" not in allowed_tampered, "Modified user tool code must lose approval until re-enabled"
    store_mod.reset_store()


def test_skill_view_lists_and_reads_references_with_jail(tmp_path: Path):
    from src.application.skills.user_catalog import UserSkillCatalog
    from src.infrastructure.content import store as store_mod

    platform_root = tmp_path / "platform"
    data_root = tmp_path / "data"
    skills_dir = data_root / "skills"
    skill_root = skills_dir / "agora-ref-test"
    (skill_root / "references").mkdir(parents=True)
    (skill_root / "tools").mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "---\nname: Agora Ref Test\ndescription: Tests references.\n---\n# Main Runbook\n",
        encoding="utf-8",
    )
    (skill_root / "references" / "api-spec.md").write_text(
        "# API Spec\nUse endpoint `/v1/status`.\n",
        encoding="utf-8",
    )
    (skill_root / "tools" / "check_status.py").write_text(
        '"""Check service status."""\n\ndef run(service: str) -> dict:\n    return {"service": service}\n',
        encoding="utf-8",
    )

    store_mod.configure(data_root=data_root, platform_root=platform_root)
    try:
        catalog = UserSkillCatalog(skills_dir=skills_dir)
        overview = catalog.skill_view(skill_id="agora-ref-test")
        assert overview["success"] is True
        assert "api-spec.md" in overview.get("references", [])
        assert any(t["name"] == "check_status" for t in overview.get("colocated_tools", []))

        ref_doc = catalog.skill_view(skill_id="agora-ref-test", reference="api-spec.md")
        assert ref_doc["success"] is True
        assert ref_doc["reference"] == "api-spec.md"
        assert "/v1/status" in ref_doc["content"]

        # Negative assertion: path traversal rejected
        traversal = catalog.skill_view(skill_id="agora-ref-test", reference="../SKILL.md")
        assert traversal["success"] is False
    finally:
        store_mod.reset_store()
