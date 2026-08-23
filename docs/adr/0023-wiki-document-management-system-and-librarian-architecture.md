# ADR-0023: Wiki Document Management System and Librarian Architecture

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Author**: Jacob Weber (Human Visionary) & Antigravity (AI Agent)  
> **Applies to**: `AutoReiv.Wiki`, `AutoReiv.Skills`, `AutoReiv.Web`

---

## 1. Context & Problem Statement
AutoReiv previously possessed basic markdown note creation tools in `LibrarianSkill` with minimal metadata (4 fields) and no distinction between unorganized inbox capture and curated permanent notes. The operator requires a comprehensive local-first Document Management System named simply **Wiki** (independent of agent working memory), adopting the simplified Degree/Class taxonomy (`inbox/`, `notes/<domain>/<topic>/`, `resources/`) and the full additive 35-field YAML frontmatter standard.

---

## 2. Decision & Architecture

1. **Naming & Taxonomy**:
   - Product name is strictly **Wiki** (no external framework naming).
   - Folder structure:
     - `inbox/`: Staging area (`need_to_do/`, `should_do/`, `want_to_do/`).
     - `notes/<domain>/<topic>/`: Permanent knowledge warehouse organized by Degree Level 1 (`<domain>`) and Class/Subject Level 2 (`<topic>`).
     - `resources/`: System operational aids (`operating_manuals/`, `templates/`).
2. **YAML Frontmatter Data Contract**:
   - Enforce 35-field additive schema (`uid` timestamp `YYYYMMDD-HHMMSS`, `domain`, `topic`, `document_type`, `tags`, `parent`, `related`, `moc`, `summary`, `status`, `word_count`, `context_tokens`).
3. **Core Engine Capabilities**:
   - Non-destructive updates (`write_note` preserves metadata while modifying body).
   - Knowledge Graph (`[[wikilink]]` extraction for `{nodes, edges}`).
   - Prompt-ready `overview()` (<150 tokens) for Librarian agent context efficiency.
4. **Dedicated Web UI**:
   - `[📚 Wiki Studio]` view in the AutoReiv control plane for human document management.

---

## 3. Consequences

### Positive
- Strict separation between persistent human documents and agent transient working memory.
- Standardized taxonomy allows both human and Librarian agent to systematically navigate and maintain the knowledge base.
- Small LLM context efficiency preserved via passive on-demand retrieval and compact summaries.

### Negative / Trade-offs
- Updating notes requires frontmatter parsing overhead, mitigated by lightweight in-memory parsing.
