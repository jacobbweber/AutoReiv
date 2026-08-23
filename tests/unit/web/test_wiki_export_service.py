"""
Unit tests for WikiExportService [REQ-WEB-003].
"""

from pathlib import Path

import pytest

from src.application.web.wiki_export_service import WikiExportService


@pytest.fixture
def wiki_dir(tmp_path):
    w = tmp_path / "wiki"
    w.mkdir()
    return w


def test_export_message_to_wiki(wiki_dir):
    service = WikiExportService(base_wiki_path=str(wiki_dir))

    result = service.export_message(
        title="Linux Disk Analysis",
        content="Here is the output of `df -h`:\n\n```\n/dev/sda1 100G 40G\n```",
        agent_id="linux-sysadmin",
        session_id="sess-456",
        category="01_Projects",
        tags=["disk", "sysadmin"],
    )

    assert result["status"] == "success"
    filepath = Path(result["filepath"])
    assert filepath.exists()
    assert filepath.is_relative_to(wiki_dir)

    content = filepath.read_text(encoding="utf-8")
    assert "---" in content
    assert 'title: "Linux Disk Analysis"' in content
    assert 'agent: "linux-sysadmin"' in content
    assert 'session_id: "sess-456"' in content
    assert '  - "disk"' in content
    assert "# Linux Disk Analysis" in content
    assert "Here is the output of `df -h`" in content


def test_export_session_to_wiki(wiki_dir):
    service = WikiExportService(base_wiki_path=str(wiki_dir))

    messages = [
        {"role": "user", "content": "What is the status of the server?"},
        {"role": "assistant", "content": "The server is running smoothly."},
    ]

    result = service.export_session(
        title="Server Health Check",
        messages=messages,
        agent_id="general-assistant",
        session_id="sess-789",
        category="03_Resources",
        tags=["health", "server"],
    )

    assert result["status"] == "success"
    filepath = Path(result["filepath"])
    assert filepath.exists()

    content = filepath.read_text(encoding="utf-8")
    assert 'title: "Server Health Check"' in content
    assert "**User**:" in content
    assert "**Assistant**:" in content


def test_path_traversal_prevention(wiki_dir):
    service = WikiExportService(base_wiki_path=str(wiki_dir))

    # Attempt directory traversal in title or category
    result = service.export_message(
        title="../../../etc/passwd",
        content="Malicious payload",
        agent_id="general-assistant",
        category="../../evil",
    )

    assert result["status"] == "success"
    filepath = Path(result["filepath"])
    assert filepath.exists()
    # File MUST reside securely within wiki_dir
    assert filepath.resolve().is_relative_to(wiki_dir.resolve())


@pytest.mark.asyncio
async def test_api_export_wiki_routes_to_inbox(tmp_path):
    """Verify POST /api/export/wiki creates notes directly in inbox/ [REQ-WIKI-008]."""
    from httpx import ASGITransport, AsyncClient

    from src.web.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/export/wiki",
            json={
                "title": "API Test Export",
                "content": "Important research finding.",
                "agent_id": "librarian",
                "category": "inbox",
                "tags": ["research", "ai"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["filepath"].startswith("inbox/")
        assert "api_test_export" in data["filepath"]
