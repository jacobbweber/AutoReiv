# [CARD-145] Comprehensive Document Extraction Pipeline

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Skills`, `AutoReiv.Web`

---

## 1. Why / Intent

When users upload documents in Chat Studio—such as PDFs, Excel spreadsheets, CSVs, and Word documents—agents need to be able to extract text, tables, columns, and data directly so they can summarize documents, analyze financial sheets, answer questions about files, and draft reports.

---

## 2. What to Build

1. **Document Extractor Service (`src/application/skills/document_extractors.py`)**:
   - **PDF Extractor**: Extracts text, page numbers, and table blocks using `pypdf` (falls back gracefully if encrypted or scanned).
   - **Excel & CSV Extractor**: Extracts sheet names, headers, rows, and statistical summaries using standard Python CSV and `openpyxl`.
   - **Word Document Extractor**: Extracts headings, paragraphs, and tables from `.docx` files using `python-docx`.
   - **Plain Text / Code**: Formats code files (`.py`, `.json`, `.yaml`, `.md`, `.sql`, `.sh`, `.log`) into syntax-highlighted blocks.
2. **Agent Document Tool (`src/application/skills/document_tools.py`)**:
   - Provide `read_document_file(path: str, max_pages: int = 10, max_rows: int = 100)` callable by Assistant and AutoReiv.
3. **Automatic Turn-1 Inlining (`src/web/routers/chat.py`)**:
   - For attached files with readable text under a safe token budget (< 16 KB), automatically extract and inline the document text into the prompt so the LLM has immediate answers on turn 1.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-DOC-001]`: Parse `.pdf` files into readable markdown text with page numbers.
- [ ] `[REQ-DOC-002]`: Parse `.xlsx`, `.xls`, and `.csv` files into formatted table previews with row/column counts.
- [ ] `[REQ-DOC-003]`: Parse `.docx` files into clean markdown paragraphs and tables.
- [ ] `[REQ-DOC-004]`: Provide `read_document_file` tool registered in platform agent profiles.
- [ ] Automated tests green via `pytest tests/unit/skills`.
- [ ] Zero linting errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Standard honor constraints apply.
- Use pure Python / lightweight packages; fail-safe fallbacks if external binary tools are absent.
