"""
Document Reading & Extraction Tools [CARD-145, REQ-DOC-004].
Exposes agent tools to extract, parse, and analyze text and tables from PDFs, Excel, Word, CSV, and text documents.
"""

from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from src.application.skills.document_extractors import extract_document
from src.domain.gateway.models import ToolDefinition

# CARD-552: never hand back secrets or the database even inside an allowed root.
_BLOCKED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".key", ".pem", ".pfx", ".p12"}
RootProvider = Callable[[], Iterable[Optional[Path]]]


def _roots(provider: Optional[RootProvider]) -> List[Path]:
    out: List[Path] = []
    if provider is None:
        return out
    try:
        items = list(provider() or [])
    except Exception:
        items = []
    for item in items:
        if not item:
            continue
        try:
            root = Path(item).expanduser().resolve()
        except (OSError, ValueError):
            continue
        if root not in out:
            out.append(root)
    return out


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_document_path(path: str, roots: List[Path]) -> tuple[Optional[Path], str]:
    """(resolved path, "") when ``path`` is inside an allowed root, else (None, reason). Relative paths are tried
    under each root in order."""
    raw = Path(str(path or "").strip()).expanduser()
    if not str(path or "").strip():
        return None, "path is required"
    candidates = [raw] if raw.is_absolute() else [root / raw for root in roots]
    for cand in candidates:
        try:
            target = cand.resolve()
        except (OSError, ValueError):
            continue
        if not any(_within(target, root) for root in roots):
            continue
        if target.suffix.lower() in _BLOCKED_SUFFIXES or target.name.lower().startswith(".env"):
            return None, f"{target.name} is not a document this tool may read"
        if raw.is_absolute() or target.exists():
            return target, ""
    names = ", ".join(str(r) for r in roots) or "none configured"
    return None, (
        f"read_document_file only reads files in the attachments/data folder, the wiki vault, the selected project or "
        f"the scratch folder (allowed: {names}). For code in the AutoReiv checkout ask the Developer (repo_file_read); "
        "for project files use read_project_file."
    )


def read_document_file(
    path: str, max_pages: int = 20, max_rows: int = 50, *, root_provider: Optional[RootProvider] = None
) -> str:
    """[REQ-DOC-004] Read and extract text, tables, and content from a document file.

    CARD-552: only inside the allowed roots (attachments/data folder, wiki vault, selected project, scratch)."""
    target, reason = resolve_document_path(path, _roots(root_provider))
    if target is None:
        return f"Error: {reason}"
    res = extract_document(str(target), max_pages=max_pages, max_rows=max_rows)
    if not res.get("success"):
        return f"Error: {res.get('error', 'Failed to read document')}"
    return res.get("content", "")


class DocumentTools:
    """Tool group providing safe, comprehensive document inspection for agents."""

    def __init__(self, root_provider: Optional[RootProvider] = None):
        self.root_provider = root_provider

    def read_document_file(self, path: str, max_pages: int = 20, max_rows: int = 50) -> str:
        return read_document_file(path, max_pages=max_pages, max_rows=max_rows, root_provider=self.root_provider)

    def get_tool_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_document_file",
                description=(
                    "Read, extract, and analyze content from documents including PDFs (.pdf), "
                    "Excel spreadsheets (.xlsx, .xls), Word documents (.docx), CSVs (.csv), "
                    "and structured text/code files. Returns formatted markdown text and tables."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path of the document: an attachment, a wiki vault note, a file in the selected project or the scratch folder (absolute, or relative to one of those).",
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum number of PDF pages to extract (default: 20).",
                            "default": 20,
                        },
                        "max_rows": {
                            "type": "integer",
                            "description": "Maximum number of rows to extract per spreadsheet/table (default: 50).",
                            "default": 50,
                        },
                    },
                    "required": ["path"],
                },
            )
        ]

    def register_tools(self, registry: Any) -> None:
        for tool_def in self.get_tool_definitions():
            registry.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                parameters=tool_def.parameters,
                handler=self.read_document_file,
            )
