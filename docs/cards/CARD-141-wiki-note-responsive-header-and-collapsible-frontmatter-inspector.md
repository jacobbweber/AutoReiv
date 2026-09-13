# [CARD-141] Wiki Note Responsive Header and Collapsible Frontmatter Inspector

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
On mobile screens and narrow viewports, the Wiki Studio note header crams the note title, file path, Preview/Edit toggles, Save button, and Delete button onto a single cramped row. This cuts off the note title (e.g. `API Tes...`) behind the action buttons and creates visual clutter. Additionally, the YAML frontmatter metadata card takes up large static vertical space above the note body. The user wants:
1. A clean, uncluttered layout where the note title is given full breathing room and never truncated behind buttons.
2. A collapsible/expandable YAML frontmatter drawer so readers can reclaim full reading space.
3. A toggle inside the expanded frontmatter to switch between **Rendered** (badges, tags, summary) and **Raw** (literal YAML syntax with monospace formatting).

---

## 2. What to Build

### A. Responsive Note Header Layout
- **Mobile (< 768px)**:
  - Row 1: Note Title (`#activeWikiTitle`), bold text wrapped or comfortably spaced, accompanied by relative path pill (`#activeWikiPath`).
  - Row 2: Clean action toolbar:
    - Left: Preview/Edit toggle (`#wikiModePreviewBtn`, `#wikiModeEditBtn`).
    - Right: Save button (`#wikiSaveNoteBtn`), Delete button (`#wikiDeleteNoteBtn`), and Metadata toggle button (`#wikiToggleFmBtn`).
- **Desktop (>= 768px)**:
  - Left: Title + Path pill.
  - Right: Unified action cluster.

### B. Collapsible Frontmatter Inspector with Rendered / Raw Views
- **Collapsed State**:
  - Replaced by a slim 28px pill bar or toggle button (`#wikiFmSummaryBar` / `#wikiToggleFmBtn`):
    `[ ▾ Metadata: atomic_note • draft • general • 2 tags ]`
  - Takes near-zero vertical space, maximizing note reading/editing canvas.
- **Expanded State**:
  - Sub-header with:
    - Left: `Frontmatter Metadata`
    - Right: `[ Rendered | Raw ]` segmented pill toggle (`#fmModeRenderedBtn`, `#fmModeRawBtn`) and `[ ▴ Collapse ]` (`#wikiCollapseFmBtn`).
  - **Rendered View** (`#fmRenderedView`):
    - UID, Document Type, Status, Domain, Topic, Words/Tokens, Summary box, and Tags.
  - **Raw View** (`#fmRawView`):
    - Monospace `<pre class="font-mono text-[11px] bg-slate-950 p-3 rounded-lg border border-slate-800 text-amber-200 overflow-x-auto">` showing exact YAML header (`--- ... ---`) with a quick `[ Copy YAML ]` button (`#fmCopyRawBtn`).

### C. Backend Raw Frontmatter Support
- Ensure `read_note` in `src/domain/wiki/store.py` returns `raw_frontmatter` string directly from the file.

---

## 3. Wireframes

### Mobile Note Header & Collapsible Frontmatter
```text
+-----------------------------------------------------------+
| 📄 API Test Export                                        |
| inbox/api_test_export.md                                  |
+-----------------------------------------------------------+
| [ Preview | Edit ]       [ 🏷️ Meta ▾ ]  [ 💾 Save ]  [ 🗑️ ] |
+-----------------------------------------------------------+
| [▸ Metadata: atomic_note • draft • general (click to open)]|  <-- Collapsed state
+-----------------------------------------------------------+
|                                                           |
| # Note Body Content...                                    |
|                                                           |
+-----------------------------------------------------------+
```

### Expanded Frontmatter with Rendered / Raw Toggle
```text
+-----------------------------------------------------------+
| ▾ Frontmatter Metadata           [ Rendered | Raw ]  [ ▴ ]|
+-----------------------------------------------------------+
| UID: 20260829-205430  |  atomic_note  |  draft  | general |
| Words: 3 | Tokens: 7                                      |
| "Chat export from librarian (Session: default)"           |
| #research  #ai                                            |
+-----------------------------------------------------------+
```

---

## 4. Acceptance Criteria (EARS & DoD)
- [x] `[REQ-WIKI-UI-001]`: Note Title and Path must be positioned in a dedicated header container on mobile, preventing truncation or overlapping with action buttons.
- [x] `[REQ-WIKI-UI-002]`: Action buttons (`Preview/Edit`, `Save`, `Delete`, `Metadata toggle`) must be grouped into an uncluttered secondary control row.
- [x] `[REQ-WIKI-UI-003]`: The Frontmatter Inspector must be collapsible/expandable via a dedicated toggle button or summary bar (`#wikiToggleFmBtn`).
- [x] `[REQ-WIKI-UI-004]`: When expanded, the user can toggle between **Rendered** (visual badges & summary) and **Raw** (literal YAML syntax with copy capability).
- [x] `[REQ-WIKI-UI-005]`: Automated unit tests verify responsive classes, collapse/expand toggle state, and Rendered vs. Raw DOM switches.
- [x] Automated tests green via `npm run test:unit:frontend` and `pytest tests/unit/web`.
- [x] Zero lint errors via `npm run lint:frontend`.
