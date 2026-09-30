"""CARD-552: read_document_file reads only inside the allowed roots (attachments/data folder, wiki vault, selected
project, scratch); anything else is refused with a pointer to the right tool."""

from __future__ import annotations

from src.application.skills.document_tools import DocumentTools, read_document_file


def _setup(tmp_path):
    data = tmp_path / "data"
    (data / "attachments").mkdir(parents=True)
    (data / "attachments" / "report.csv").write_text("Year,Users\n2026,2000\n", encoding="utf-8")
    (data / "autoreiv.db").write_bytes(b"SQLite format 3\x00")
    (data / ".env").write_text("SECRET=1\n", encoding="utf-8")
    outside = tmp_path / "checkout" / "src"
    outside.mkdir(parents=True)
    (outside / "app.py").write_text("SECRET_CODE = 1\n", encoding="utf-8")
    return data, outside


def test_an_attachment_is_read(tmp_path):
    data, _ = _setup(tmp_path)
    out = read_document_file(str(data / "attachments" / "report.csv"), root_provider=lambda: [data])
    assert "2000" in out and not out.startswith("Error")


def test_relative_path_resolves_under_a_root(tmp_path):
    data, _ = _setup(tmp_path)
    out = read_document_file("attachments/report.csv", root_provider=lambda: [None, data])
    assert "2000" in out


def test_a_path_outside_the_roots_is_refused(tmp_path):
    data, outside = _setup(tmp_path)
    out = read_document_file(str(outside / "app.py"), root_provider=lambda: [data])
    assert out.startswith("Error:") and "repo_file_read" in out and "SECRET_CODE" not in out
    escape = read_document_file(str(data / ".." / "checkout" / "src" / "app.py"), root_provider=lambda: [data])
    assert escape.startswith("Error:") and "SECRET_CODE" not in escape
    assert read_document_file("../checkout/src/app.py", root_provider=lambda: [data]).startswith("Error:")


def test_database_and_env_files_are_refused_even_inside_a_root(tmp_path):
    data, _ = _setup(tmp_path)
    assert "not a document" in read_document_file(str(data / "autoreiv.db"), root_provider=lambda: [data])
    assert "not a document" in read_document_file(str(data / ".env"), root_provider=lambda: [data])


def test_no_roots_means_nothing_is_readable(tmp_path):
    data, _ = _setup(tmp_path)
    assert read_document_file(str(data / "attachments" / "report.csv")).startswith("Error:")


def test_the_registered_tool_uses_the_provider(tmp_path):
    data, outside = _setup(tmp_path)
    tools = DocumentTools(root_provider=lambda: [data])
    registered = {}

    class Reg:
        def register_tool(self, name, description, parameters, handler):
            registered[name] = handler

    tools.register_tools(Reg())
    handler = registered["read_document_file"]
    assert "2000" in handler(path=str(data / "attachments" / "report.csv"))
    assert handler(path=str(outside / "app.py")).startswith("Error:")
