"""CARD-479: attachment text sized from the model's context window; Direct mode gets the text itself."""

from __future__ import annotations

from src.application.gateway.attachment_text import (
    MAX_BUDGET_CHARS,
    MIN_BUDGET_CHARS,
    attachment_char_budget,
    build_attachment_prompt,
)
from src.web.routers.chat import format_prompt_with_attachments


def _att(path, name=None, ctype="text/plain"):
    return {"filename": name or path.name, "url": f"/api/chat/attachments/x/{path.name}", "content_type": ctype,
            "size_bytes": path.stat().st_size if path.exists() else 0, "path": str(path)}


def test_budget_follows_the_context_window():
    assert attachment_char_budget(262144) == 262144  # nemotron: a quarter of 262k tokens at ~4 chars/token
    assert attachment_char_budget(8192) == MIN_BUDGET_CHARS + 192
    assert attachment_char_budget(None) == MIN_BUDGET_CHARS
    assert attachment_char_budget(10_000_000) == MAX_BUDGET_CHARS


def test_big_text_file_is_inlined_when_the_window_is_large(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("line of notes\n" * 4000, encoding="utf-8")  # 56 KB, was path-only above 8 KB
    out = build_attachment_prompt("summarize", [_att(f)], char_budget=attachment_char_budget(262144))
    assert out.text.count("line of notes") == 4000
    assert "Cut short" not in out.text
    assert out.failures == []


def test_big_file_is_cut_and_marked_on_a_small_window_agent_mode(tmp_path):  # REQ-479-001
    f = tmp_path / "notes.txt"
    f.write_text("x" * 50_000, encoding="utf-8")
    out = build_attachment_prompt("summarize", [_att(f)], char_budget=8_000)
    assert "Cut short: showing the first 8,000 of 50,000 characters; read the rest with `read_document_file`" in out.text
    assert "read_document_file" in out.text


def test_direct_mode_has_the_text_and_no_tool_note(tmp_path):  # REQ-479-002
    f = tmp_path / "notes.txt"
    f.write_text("x" * 50_000, encoding="utf-8")
    out = build_attachment_prompt("summarize", [_att(f)], char_budget=8_000, direct=True)
    assert "read_document_file" not in out.text
    assert "filesystem tools" not in out.text
    assert "the rest was not included" in out.text
    assert "x" * 8_000 in out.text


def test_large_csv_document_is_extracted_whatever_its_file_size(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name,score\n" + "".join(f"row{i},{i}\n" for i in range(3000)), encoding="utf-8")
    assert f.stat().st_size > 16_384  # was path-only above 16 KB
    out = build_attachment_prompt("what is in it?", [_att(f, ctype="text/csv")], char_budget=attachment_char_budget(262144))
    assert "**Document Content:**" in out.text
    assert "row2999" in out.text or "row1" in out.text


def test_unreadable_file_is_told_to_model_and_user(tmp_path):  # REQ-479-003
    missing = tmp_path / "gone.pdf"
    out = build_attachment_prompt("read this", [_att(missing, ctype="application/pdf")], char_budget=8_000)
    assert "Could not read `gone.pdf`" in out.text
    assert out.failures and "gone.pdf" in out.failures[0]


def test_budget_is_shared_between_files(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("a" * 9_000, encoding="utf-8")
    b.write_text("b" * 9_000, encoding="utf-8")
    out = build_attachment_prompt("", [_att(a), _att(b)], char_budget=10_000)
    assert "showing the first 5,000 of 9,000" in out.text
    assert out.text.count("Cut short") == 2


def test_images_unchanged_and_wrapper_keeps_its_shape(tmp_path):
    img = {"filename": "shot.png", "url": "/u/shot.png", "content_type": "image/png", "size_bytes": 68, "path": str(tmp_path / "shot.png")}
    text = format_prompt_with_attachments("what is this?", [img])
    assert "*(Attached Image: `shot.png`, 68 bytes, format: `image/png`, Local Path:" in text
    assert format_prompt_with_attachments("Hello", None) == "Hello"
