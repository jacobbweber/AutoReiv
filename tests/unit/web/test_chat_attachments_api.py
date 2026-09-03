"""
Integration tests for Chat Media and File Attachments API [CARD-143].
[REQ-ATTACH-001] [REQ-ATTACH-002]
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def chat_client():
    app = create_app()
    client = TestClient(app)
    return client


def test_chat_upload_and_download_flow(chat_client):
    file_bytes = b"Sample diagnostic log data for AutoReiv agent analysis."
    files = {
        "file": ("system_log.txt", io.BytesIO(file_bytes), "text/plain")
    }
    data = {"session_id": "test-session-attach-1"}

    # 1. Upload file
    res = chat_client.post("/api/chat/upload", files=files, data=data)
    assert res.status_code == 200, res.text
    payload = res.json()

    assert "id" in payload
    assert payload["filename"] == "system_log.txt"
    assert payload["size_bytes"] == len(file_bytes)
    assert payload["content_type"] == "text/plain"
    assert "url" in payload

    file_id = payload["id"]
    file_url = payload["url"]
    assert file_id in file_url

    # 2. Retrieve attachment via URL
    dl_res = chat_client.get(file_url)
    assert dl_res.status_code == 200
    assert dl_res.content == file_bytes
    assert "text/plain" in dl_res.headers.get("content-type", "")


def test_chat_upload_sanitizes_path_traversal(chat_client):
    file_bytes = b"Dangerous payload test"
    files = {
        "file": ("../../../../etc/passwd", io.BytesIO(file_bytes), "text/plain")
    }
    data = {"session_id": "test-session-traversal"}

    res = chat_client.post("/api/chat/upload", files=files, data=data)
    assert res.status_code == 200
    payload = res.json()
    assert ".." not in payload["filename"]
    assert "/" not in payload["filename"]
    assert "\\" not in payload["filename"]


def test_chat_attachment_not_found_returns_404(chat_client):
    res = chat_client.get("/api/chat/attachments/non-existent-id/missing.txt")
    assert res.status_code == 404


def test_format_prompt_with_attachments():
    from src.web.routers.chat import format_prompt_with_attachments

    # 1. No attachments returns raw text
    assert format_prompt_with_attachments("Hello", None) == "Hello"
    assert format_prompt_with_attachments("Hello", []) == "Hello"

    # 2. Image attachment formats with markdown image and info
    attachments = [
        {
            "filename": "diagram.png",
            "url": "/api/chat/attachments/123/diagram.png",
            "content_type": "image/png",
            "size_bytes": 1024,
            "path": "/data/attachments/test/123_diagram.png",
        }
    ]
    formatted = format_prompt_with_attachments("What is this?", attachments)
    assert "What is this?" in formatted
    assert "![diagram.png](/api/chat/attachments/123/diagram.png)" in formatted
    assert "123_diagram.png" in formatted
    assert "image/png" in formatted
