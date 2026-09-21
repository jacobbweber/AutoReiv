---
id: CARD-399
title: "Wiki Studio Monolith Decomposition and Submodule Refactoring"
status: In Review
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:wiki
---

# [CARD-399] Wiki Studio Monolith Decomposition and Submodule Refactoring

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:frontend`, `domain:wiki`  

---

## 1. Why / Intent (Beat 1)

`src/web/static/modules/studios/wiki.js` stands at **1,701 lines**, more than double the 800-line monolith threshold established in `.agents/rules/code-hygiene-and-pruning.md` Section 5.
Large monolithic studio files create context-window blindness, increase cognitive load, and make maintenance and testing hazardous.
Decomposing `wiki.js` into focused, single-responsibility submodules under `src/web/static/modules/studios/wiki/` makes Wiki Studio clean, cohesive, and maintainable while maintaining 100% backward compatibility for all public APIs (`initWikiStudio`, `exportMessageToWiki`) and existing Vitest suites.

---

## 2. What AutoReiv Does Now (Beat 2)

`src/web/static/modules/studios/wiki.js` houses all of the following heterogeneous concerns in a single monolithic 1,701-line file:
- Vault tree hierarchy loading, collapsible folder rendering across 00_Inbox, 01_Notes warehouse, 02_Resources, and 03_Archive.
- Folder selection, overview hero banner, notes summary grid, and protected root folder deletion guards.
- Note loading, markdown preview, raw textarea editing, note save, and note deletion.
- Collapsible YAML frontmatter inspector, badges, domain/topic pills, telemetry stats, and raw YAML clipboard copying.
- Structured wiki templates discovery, dynamic body prefilling, and new note creation modal.
- Rule-based inbox curation/graduation (`/api/wiki/curate`).
- Obsidian-style force-directed mindmap canvas, node/edge data structures, physics simulation loop, zoom/pan, hit testing, drag-drop, and tooltip rendering.
- Chat message export to Wiki Inbox (`exportMessageToWiki`).

---

## 3. What Will Change (Beat 3)

Decompose `src/web/static/modules/studios/wiki.js` into focused submodules under `src/web/static/modules/studios/wiki/`:
1. `src/web/static/modules/studios/wiki/mindmap.js` (<800 lines):
   Obsidian-style mind map modal, canvas rendering, node and edge graph generation, force-directed simulation loop integration (`stepSimulation`, `createSimulationRunner`), zoom, pan, hit-testing, drag-and-drop, and tooltip handling.
2. `src/web/static/modules/studios/wiki/tree.js` (<800 lines):
   Wiki vault tree loading (`loadWikiVault`), collapsible tree rendering (`renderWikiTree`), note item button creation (`createNoteTreeButton`), folder selection (`selectWikiFolder`), folder overview grid (`renderFolderOverview`), and folder deletion (`deleteWikiFolder`).
3. `src/web/static/modules/studios/wiki/note.js` (<800 lines):
   Note content loading (`loadWikiNote`), markdown preview vs edit mode switching (`setWikiViewMode`), note saving, note deletion, and collapsible YAML frontmatter inspector (`setFmExpanded`, `setFmMode`).
4. `src/web/static/modules/studios/wiki/templates.js` (<800 lines):
   Structured wiki templates loading (`loadWikiTemplates`), new note modal management, template selection change handlers, note submission, and rule-based inbox graduation (`curateWikiInbox`).
5. `src/web/static/modules/studios/wiki/export.js` (<800 lines):
   Export chat message turn to Wiki Inbox (`exportMessageToWiki`).
6. `src/web/static/modules/studios/wiki.js` (<1,000 lines):
   Root coordinator managing studio initialization (`initWikiStudio`), coordinating shared state across submodules (`activeWikiNotePath`, `activeWikiFolderPath`), and re-exporting all submodule symbols for complete drop-in compatibility.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Monolithic Inlining**:
  - Over 1,400 lines of tightly coupled monolithic functions in `wiki.js` retired in favor of cohesive submodule exports.
- **Redundant State & Selectors**:
  - Unused or duplicated DOM queries in `initWikiStudio` eliminated.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL keep all JavaScript files in `src/web/static/modules/studios/wiki/*.js` under 800 lines of code.
- **Ubiquitous**: THE SYSTEM SHALL keep `src/web/static/modules/studios/wiki.js` under 1,000 lines of code.
- **Ubiquitous**: THE SYSTEM SHALL maintain complete backward compatibility for all exports from `src/web/static/modules/studios/wiki.js` (`initWikiStudio`, `exportMessageToWiki`).
- **Event-Driven**: WHEN a user browses the vault tree, edits notes, views frontmatter, creates notes from templates, or opens the mindmap, THE WIKI STUDIO SHALL behave identically to baseline.
- **Negative Assertion**: Automated tests shall explicitly assert that `wiki.js` line count is strictly less than 1,000 lines.
- **Negative Assertion**: Automated tests shall assert that all submodules under `src/web/static/modules/studios/wiki/` are strictly less than 800 lines.
- **Negative Assertion**: Automated tests shall verify that all existing frontend Vitest and Playwright smoke tests pass with zero regressions.

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero breaking changes to existing tests.
- Feature branch cut from `qa`: `feat/card-399-wiki-monolith-decomposition`.
- Verification via `npm run test:unit:frontend`, `npm run lint:frontend`, and `npm run test:smoke`.

