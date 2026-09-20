"""
Unit tests for CARD-390: Mechanical Skill Linting API.
Tests POST /api/skills/lint against ADR-0054 capability invariants:
- [REQ-390-001]: Endpoint lint evaluation without disk writes.
- [REQ-390-002]: Structured diagnostic reporting (pass/fail, violations, tool counts).
- [REQ-390-003]: God-Agent threshold enforcement (> 6 tools per skill).
- [REQ-390-004]: Verification contract enforcement (mandatory Done-When criteria).
"""

from fastapi.testclient import TestClient

from src.web.app import app

client = TestClient(app)


def test_lint_endpoint_valid_runbook_passes():
    """Valid runbook with tools <= 6 and Done-When criteria passes cleanly."""
    valid_markdown = """---
name: System Health Auditor
description: Inspect and verify node health metrics and service status.
requires_tools:
  - inspect_system_health
  - get_system_logs
---

# System Health Auditor

## Operating Principles
1. Check CPU, memory, and disk health before executing deep diagnostics.
2. Formulate concise health summaries for the operator.

## Available Tools
- `inspect_system_health`: Query node resource utilization.
- `get_system_logs`: Fetch recent syslog entries.

## Done-When
- CPU, memory, and disk metrics have been collected and verified.
- Target service status is confirmed running without active alerts.
"""
    res = client.post("/api/skills/lint", json={"text": valid_markdown})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["error_count"] == 0
    assert data["violations"] == []
    assert data["contract"]["name"] == "System Health Auditor"
    assert data["contract"]["tools_count"] == 2
    assert "inspect_system_health" in data["contract"]["requires_tools"]
    assert "get_system_logs" in data["contract"]["requires_tools"]


def test_lint_endpoint_missing_verification_fails_cap_002():
    """Runbook lacking a ## Done-When or ## Verification section fails rule CAP-002."""
    unverified_markdown = """---
name: Unfinished Runner
description: Runs batch scripts without verifying completion.
requires_tools:
  - execute_code
---

# Unfinished Runner

## Operating Principles
1. Just run the script and immediately return.
"""
    res = client.post("/api/skills/lint", json={"text": unverified_markdown})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["error_count"] >= 1
    rule_ids = [v["rule_id"] for v in data["violations"]]
    assert "CAP-002" in rule_ids


def test_lint_endpoint_excessive_tools_fails_cap_001():
    """Runbook declaring more than 6 tools triggers CAP-001 (God-Agent tool budget)."""
    bloated_markdown = """---
name: Overloaded Specialist
description: Tries to do everything under a single skill.
requires_tools:
  - tool_one
  - tool_two
  - tool_three
  - tool_four
  - tool_five
  - tool_six
  - tool_seven
---

# Overloaded Specialist

## Done-When
- All seven tools have finished running.
"""
    res = client.post("/api/skills/lint", json={"text": bloated_markdown})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    rule_ids = [v["rule_id"] for v in data["violations"]]
    assert "CAP-001" in rule_ids
    assert data["contract"]["tools_count"] == 7


def test_lint_endpoint_separate_form_fields():
    """Can pass separate name, description, and instructions fields instead of raw text."""
    payload = {
        "name": "Database Archiver",
        "description": "Archives old records from the agent database.",
        "instructions": """## Operating Principles
1. Query database records older than retention limit.
2. Safely purge completed rows.

## Available Tools
- `query_agent_database`: Query old records.
- `execute_agent_database`: Purge records.

## Done-When
- Old records are verified removed and count reported.
""",
    }
    res = client.post("/api/skills/lint", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["contract"]["name"] == "Database Archiver"
    assert data["contract"]["tools_count"] == 2


def test_lint_endpoint_yaml_syntax_error():
    """Malformed YAML frontmatter produces SYN-001 syntax error violation."""
    malformed = """---
name: Broken YAML
description: [unclosed list
---

# Content
## Done-When
- Done
"""
    res = client.post("/api/skills/lint", json={"text": malformed})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    rule_ids = [v["rule_id"] for v in data["violations"]]
    assert "SYN-001" in rule_ids
