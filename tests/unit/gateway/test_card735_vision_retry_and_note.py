"""CARD-735: vision attachment timeout in docker-compose, retry carry-forward after failed turns, and image-only prompt note."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from src.application.gateway.attachment_images import prepare_image_turn
from src.application.gateway.attachment_text import build_attachment_prompt
from src.domain.gateway.models import ChatMessage, Role

pytestmark = pytest.mark.guard

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def _image(tmp_path: Path, name: str = "shot.png") -> Path:
    p = tmp_path / f"abc123_{name}"
    p.write_bytes(PNG)
    return p


def _image_turn(path: Path, name: str = "shot.png", text: str = "Review these images closely") -> str:
    return (
        f"{text}\n\n---\n![{name}](/api/chat/attachments/abc123/{name})\n"
        f"*(Attached Image: `{name}`, {len(PNG)} bytes, format: `image/png`, Local Path: `{path}`)*"
    )


def test_docker_compose_does_not_clamp_gateway_timeout_to_180s():
    """CARD-735: docker-compose.yml must not set GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180.0 (which overrides 1800s default)."""
    repo_root = Path(__file__).resolve().parents[3]
    compose_text = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "GATEWAY_DEFAULT_TIMEOUT_SECONDS:-180" not in compose_text
    assert "AUTOREIV_PROVIDER_IDLE_SECONDS" in compose_text


def test_image_only_attachment_prompt_does_not_instruct_read_document_file(tmp_path: Path):
    """CARD-735: image-only turns in agent mode must not tell the model to call read_document_file on .png files."""
    img_path = _image(tmp_path)
    att = {
        "filename": "shot.png",
        "url": "/api/chat/attachments/abc123/shot.png",
        "content_type": "image/png",
        "size_bytes": len(PNG),
        "path": str(img_path),
    }
    prompt = build_attachment_prompt("Review these images", [att], direct=False, attachments_dir=tmp_path)
    assert "You can read documents using `read_document_file`" not in prompt.text
    assert "do not call `read_document_file` on image files" in prompt.text


def test_mixed_image_and_doc_attachment_prompt_keeps_read_document_file_note(tmp_path: Path):
    """When a turn attaches both an image and a text/document file, AGENT_NOTE still mentions read_document_file."""
    img_path = _image(tmp_path)
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("hello world", encoding="utf-8")
    atts = [
        {
            "filename": "shot.png",
            "url": "/api/chat/attachments/abc123/shot.png",
            "content_type": "image/png",
            "size_bytes": len(PNG),
            "path": str(img_path),
        },
        {
            "filename": "notes.txt",
            "url": "/api/chat/attachments/abc123/notes.txt",
            "content_type": "text/plain",
            "size_bytes": 11,
            "path": str(txt_path),
        },
    ]
    prompt = build_attachment_prompt("Review both", atts, direct=False, attachments_dir=tmp_path)
    assert "You can read documents using `read_document_file`" in prompt.text


@pytest.mark.parametrize(
    "failed_reply",
    [
        "Job job_102c9da3b55f FAILED during Formulate: phase failed. Not done — Journey shows FAILED; no deliverable claimed.",
        "⚠️ **Error**: [ollama] Ollama timed out at http://192.168.1.29:11434: ",
        "Partial output\n\n*[Stopped.]*",
    ],
)
def test_prepare_image_turn_carries_forward_unanswered_images_after_failed_turn(tmp_path: Path, failed_reply: str):
    """CARD-735: if an image turn failed/timed out/stopped, a follow-up retry turn on a vision model keeps the images."""
    img_path = _image(tmp_path, "slide1.png")
    messages = [
        ChatMessage(role=Role.USER, content=_image_turn(img_path, "slide1.png")),
        ChatMessage(role=Role.ASSISTANT, content=failed_reply),
        ChatMessage(role=Role.USER, content="Looks like we hit a timeout. Let's try it again"),
    ]
    out, dropped, attached = prepare_image_turn(messages, can_view_images=True, attachments_dir=tmp_path)
    assert attached is True
    assert dropped is None
    assert not out[0].images
    assert out[-1].images and out[-1].images[0]["filename"] == "slide1.png"


def test_prepare_image_turn_does_not_carry_forward_after_successful_reply(tmp_path: Path):
    """Negative assertion: once an image turn is answered normally, a later text turn never re-sends those images."""
    img_path = _image(tmp_path, "slide1.png")
    messages = [
        ChatMessage(role=Role.USER, content=_image_turn(img_path, "slide1.png")),
        ChatMessage(role=Role.ASSISTANT, content="Here are the notes from slide 1."),
        ChatMessage(role=Role.USER, content="Thanks, now format that as a table"),
    ]
    out, dropped, attached = prepare_image_turn(messages, can_view_images=True, attachments_dir=tmp_path)
    assert attached is False
    assert dropped is None
    assert all(not m.images for m in out)
