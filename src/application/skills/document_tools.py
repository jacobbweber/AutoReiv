"""
Document Reading & Extraction Tools [CARD-145, REQ-DOC-004].
Exposes agent tools to extract, parse, and analyze text and tables from PDFs, Excel, Word, CSV, and text documents.
"""

from typing import Any, Dict, List, Optional

from src.application.skills.document_extractors import extract_document
from src.domain.gateway.models import ToolDefinition


def read_document_file(path: str, max_pages: int = 20, max_rows: int = 50) -> str:
    """[REQ-DOC-004] Read and extract text, tables, and content from a document file."""
    res = extract_document(path, max_pages=max_pages, max_rows=max_rows)
    if not res.get("success"):
        return f"Error: {res.get('error', 'Failed to read document')}"
    return res.get("content", "")


class DocumentTools:
    """Tool group providing safe, comprehensive document inspection for agents."""

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
                            "description": "The local filesystem path to the document file to read.",
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
                handler=read_document_file,
            )
