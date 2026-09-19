"""
Unit tests for CARD-363: Mechanical Capability Linter & Contract Compiler.
Grounded in ADR-0054 [REQ-CAP-LINT-001..005].
"""


from src.application.skills.linter import CapabilityLinter, SkillContractCompiler
from src.cli.main import main
from src.domain.skills.contract import (
    LintSeverity,
    VerificationKind,
)


def test_compiler_accepts_valid_contract():
    """Verify compiler accepts fully compliant SKILL.md with <=6 tools and verification."""
    raw = """---
name: Code Inspection
description: Read and inspect project files.
version: 1.0.0
requires_tools:
  - repo_file_read
  - repo_file_list
verification:
  kind: command
  rule: git status --porcelain
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
---

# Code Inspection
Procedural guidelines for inspecting code safely.
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    assert contract is not None
    assert contract.name == "Code Inspection"
    assert len(contract.requires_tools) == 2
    assert contract.verification is not None
    assert contract.verification.kind == VerificationKind.COMMAND
    assert contract.verification.rule == "git status --porcelain"
    assert contract.safety.read_only is True

    errors = [v for v in violations if v.severity == LintSeverity.ERROR]
    assert len(errors) == 0


def test_compiler_rejects_more_than_6_tools_cap_001():
    """Rule CAP-001: len(requires_tools) <= 6 to preserve Rule of 7 headroom [REQ-CAP-LINT-001]."""
    raw = """---
name: Bloated Skill
description: Too many tools declared.
requires_tools:
  - tool_1
  - tool_2
  - tool_3
  - tool_4
  - tool_5
  - tool_6
  - tool_7
verification:
  kind: command
  rule: pytest
---
# Bloated
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_001 = [v for v in violations if v.rule_id == "CAP-001"]
    assert len(cap_001) == 1
    assert cap_001[0].severity == LintSeverity.ERROR
    assert "7 tools declared" in cap_001[0].message
    assert "maximum allowed is 6" in cap_001[0].message


def test_compiler_rejects_missing_verification_cap_002():
    """Rule CAP-002: Mandatory deterministic verification contract [REQ-CAP-LINT-002]."""
    raw = """---
name: Unverified Skill
description: No verification contract.
requires_tools:
  - repo_file_read
---
# Unverified
Conversational steps without testable done-when.
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_002 = [v for v in violations if v.rule_id == "CAP-002"]
    assert len(cap_002) == 1
    assert cap_002[0].severity == LintSeverity.ERROR
    assert "verification" in cap_002[0].message.lower()


def test_compiler_accepts_markdown_done_when_fallback_cap_002():
    """Rule CAP-002: Accepts testable markdown ## Done-when fallback when frontmatter lacks verification [REQ-CAP-LINT-002]."""
    raw = """---
name: Fallback Skill
description: Verification declared in markdown section.
requires_tools:
  - repo_file_read
---
# Fallback Skill

Procedural steps.

## Done-when

- pytest tests/unit/ passes with zero failures.
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_002 = [v for v in violations if v.rule_id == "CAP-002"]
    assert len(cap_002) == 0
    assert contract is not None
    assert contract.verification is not None
    assert "pytest tests/unit/ passes" in contract.verification.rule


def test_compiler_rejects_security_collision_cap_003():
    """Rule CAP-003: untrusted_input_allowed cannot co-mingle with mutating levers without requires_hitl [REQ-CAP-LINT-003]."""
    raw = """---
name: Hazardous Web Scraper
description: Scrapes web and writes to local disk without HITL.
requires_tools:
  - web_search
  - cli_exec
safety:
  untrusted_input_allowed: true
  requires_hitl: false
verification:
  kind: command
  rule: echo done
---
# Dangerous
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_003 = [v for v in violations if v.rule_id == "CAP-003"]
    assert len(cap_003) == 1
    assert cap_003[0].severity == LintSeverity.ERROR
    assert "cli_exec" in cap_003[0].message
    assert "Security boundary collision" in cap_003[0].message


def test_compiler_permits_mutating_tools_when_hitl_protected_cap_003():
    """Rule CAP-003: Mutating tools permitted with untrusted input if requires_hitl is true [REQ-CAP-LINT-003]."""
    raw = """---
name: Guarded Web Agent
description: Scrapes web but pauses for approval before mutating.
requires_tools:
  - web_search
  - cli_exec
safety:
  untrusted_input_allowed: true
  requires_hitl: true
verification:
  kind: command
  rule: echo done
---
# Safe
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_003 = [v for v in violations if v.rule_id == "CAP-003"]
    assert len(cap_003) == 0


def test_compiler_warns_on_oversized_runbook_cap_004():
    """Rule CAP-004: Runbook body > 8,000 characters triggers WARNING [REQ-CAP-LINT-001]."""
    huge_body = "word " * 2000  # 10,000 chars
    raw = f"""---
name: Verbose Skill
description: Extremely long runbook.
requires_tools:
  - repo_file_read
verification:
  kind: command
  rule: pytest
---
# Verbose
{huge_body}
"""
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(raw, path="test/SKILL.md")

    cap_004 = [v for v in violations if v.rule_id == "CAP-004"]
    assert len(cap_004) == 1
    assert cap_004[0].severity == LintSeverity.WARNING
    assert "body exceeds 8,000 characters" in cap_004[0].message


def test_linter_directory_scan(tmp_path):
    """Verify CapabilityLinter recursively discovers and lints SKILL.md files [REQ-CAP-LINT-004]."""
    good_dir = tmp_path / "packs" / "good_pack" / "skills" / "read_code"
    good_dir.mkdir(parents=True)
    (good_dir / "SKILL.md").write_text(
        """---
name: Good Skill
description: Valid skill.
requires_tools:
  - tool_a
verification:
  kind: command
  rule: echo 0
---
# Good
""",
        encoding="utf-8",
    )

    bad_dir = tmp_path / "packs" / "bad_pack" / "skills" / "bloated"
    bad_dir.mkdir(parents=True)
    (bad_dir / "SKILL.md").write_text(
        """---
name: Bad Skill
description: Missing verification and 7 tools.
requires_tools:
  - t1
  - t2
  - t3
  - t4
  - t5
  - t6
  - t7
---
# Bad
""",
        encoding="utf-8",
    )

    linter = CapabilityLinter()
    report = linter.lint_paths([tmp_path])

    assert report.scanned_count == 2
    assert report.valid_count == 1
    assert report.error_count >= 2  # CAP-001 and CAP-002
    assert report.passed is False


def test_platform_packs_all_pass_mechanical_linter():
    """Verify all shipped platform seed skills pass the mechanical linter cleanly [REQ-CAP-LINT-001..004]."""
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    platform_packs_dir = repo_root / "platform-packs"

    linter = CapabilityLinter()
    report = linter.lint_paths([platform_packs_dir])

    assert report.scanned_count >= 12
    assert report.error_count == 0
    assert report.passed is True


def test_cli_lint_skills_human_format_success(tmp_path, capsys):
    """Test autoreiv lint-skills on compliant skill [REQ-CAP-LINT-004]."""
    skill_dir = tmp_path / "skills" / "sample"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: Sample Skill
requires_tools:
  - tool_a
verification:
  kind: command
  rule: echo 0
---
# Sample Skill
""",
        encoding="utf-8",
    )

    exit_code = main(["lint-skills", str(skill_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "AutoReiv Mechanical Capability Linter" in captured.out
    assert "All capability contracts compliant" in captured.out
    assert "Scanned: 1" in captured.out


def test_cli_lint_skills_json_format(tmp_path, capsys):
    """Test autoreiv lint-skills --json produces valid JSON report [REQ-CAP-LINT-004]."""
    import json

    skill_dir = tmp_path / "skills" / "sample"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: Sample Skill
requires_tools:
  - tool_a
verification:
  kind: command
  rule: echo 0
---
# Sample Skill
""",
        encoding="utf-8",
    )

    exit_code = main(["lint-skills", str(skill_dir), "--json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["scanned_count"] == 1
    assert data["valid_count"] == 1
    assert data["passed"] is True
    assert data["error_count"] == 0


def test_cli_lint_skills_failure_exit_code(tmp_path, capsys):
    """Test autoreiv lint-skills exits 1 when errors exist [REQ-CAP-LINT-004]."""
    skill_dir = tmp_path / "skills" / "bad"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: Bad Skill
requires_tools:
  - t1
  - t2
  - t3
  - t4
  - t5
  - t6
  - t7
---
# Bad
""",
        encoding="utf-8",
    )

    exit_code = main(["lint-skills", str(skill_dir)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "❌ Capability contract linting failed" in captured.out
    assert "CAP-001" in captured.out


def test_cli_lint_skills_strict_flag(tmp_path, capsys):
    """Test autoreiv lint-skills --strict fails on warnings [REQ-CAP-LINT-004]."""
    huge_body = "word " * 2000
    skill_dir = tmp_path / "skills" / "oversized"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: Oversized Skill
requires_tools:
  - tool_a
verification:
  kind: command
  rule: echo 0
---
# Oversized
{huge_body}
""",
        encoding="utf-8",
    )

    # Without strict: passes with warning
    exit_code = main(["lint-skills", str(skill_dir)])
    assert exit_code == 0

    # With strict: fails due to warning
    exit_code_strict = main(["lint-skills", str(skill_dir), "--strict"])
    assert exit_code_strict == 1


def test_rest_api_lint_skill_valid():
    """Test POST /api/skills/lint with valid content [REQ-CAP-LINT-005]."""
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    app = create_app()
    client = TestClient(app)

    payload = {
        "content": """---
name: Inspect Code
requires_tools:
  - repo_file_read
verification:
  kind: command
  rule: pytest
safety:
  read_only: true
---
# Inspect
""",
        "path": "test/SKILL.md",
    }
    response = client.post("/api/skills/lint", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["error_count"] == 0
    assert data["contract"]["name"] == "Inspect Code"
    assert data["contract"]["requires_tools"] == ["repo_file_read"]
    assert data["contract"]["verification"]["kind"] == "command"


def test_rest_api_lint_skill_invalid():
    """Test POST /api/skills/lint with invalid content returning violations [REQ-CAP-LINT-005]."""
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    app = create_app()
    client = TestClient(app)

    payload = {
        "content": """---
name: Bad Contract
requires_tools:
  - t1
  - t2
  - t3
  - t4
  - t5
  - t6
  - t7
---
# Bad Contract
""",
    }
    response = client.post("/api/skills/lint", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error_count"] >= 2
    rule_ids = [v["rule_id"] for v in data["violations"]]
    assert "CAP-001" in rule_ids
    assert "CAP-002" in rule_ids


def test_rest_api_lint_skill_empty_request():
    """Test POST /api/skills/lint with neither content nor path returns 400 [REQ-CAP-LINT-005]."""
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    app = create_app()
    client = TestClient(app)

    response = client.post("/api/skills/lint", json={})
    assert response.status_code == 400
    assert "Either 'content' or 'path' must be provided" in response.json()["detail"]


