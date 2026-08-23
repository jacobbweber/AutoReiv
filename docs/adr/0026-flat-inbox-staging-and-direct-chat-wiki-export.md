# ADR-0026: Flat Inbox Staging & Direct Chat to Wiki Export

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 25 (`CARD-025`)  
> **Requirements**: `[REQ-WIKI-007]`, `[REQ-WIKI-008]`, `[REQ-WIKI-009]`

---

## Context
1. `inbox` in `data/wiki/` had artificial priority subfolders (`need_to_do`, `should_do`, `want_to_do`). Because inbox is simply a staging area before notes are categorized by domain/topic or archived, subfolders added unnecessary mental overhead and file hierarchy depth.
2. Chat "Save to Wiki" and "Export to Wiki" were delegating to a legacy service targeting outdated paths (`03_Resources/`) instead of creating genuine Wiki notes inside the new vault staging area `data/wiki/inbox/`.

---

## Decision
1. **Flat Staging Inbox**:
   - `data/wiki/inbox/` is a flat staging folder containing `.md` notes directly without subfolders.
2. **Unified Chat Export**:
   - `POST /api/export/wiki` delegates directly to `WikiService.file_note()` targeting `inbox/<slug>.md` with full 35-field YAML frontmatter.

---

## Consequences
- Chat exports land immediately in Wiki Studio's flat Inbox.
- Zero subfolder friction in staging.
