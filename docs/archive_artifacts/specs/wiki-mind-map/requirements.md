# Requirements Specification: Wiki Studio Interactive Mind Map & Tree Navigation

> **Document ID**: `SPEC-WIKI-MINDMAP-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-MIND-001]` through `[REQ-MIND-003]`

---

## 1. User Story

**As a** knowledge worker and human operator of AutoReiv,  
**I want** an interactive, Obsidian-style Mind Map graph view with multi-dimensional filtering and collapsible folder navigation in Wiki Studio,  
**So that** I can explore conceptual relationships across notes, tags, domains, and subjects, and navigate my entire knowledge vault effortlessly.

---

## 2. EARS Requirements

### [REQ-MIND-001] Nested Degree & Subject Tree Expand/Collapse (Ubiquitous)
The Wiki Studio sidebar explorer SHALL render both Degree Level 1 (`<domain>`) and Subject Level 2 (`<topic>`) directories as independent collapsible folders with distinct chevron toggle states, open/closed folder icons, child item counters, and persistent memory across search filtering and refreshes.

### [REQ-MIND-002] Multi-Dimensional Mind Map Data Model & API (Ubiquitous)
When a client requests `GET /api/wiki/mindmap`, the system SHALL return a unified multi-dimensional graph containing:
1. **Nodes**: Note nodes (id, title, path, domain, topic, tags, words, tokens), Tag nodes (id `#tag`, label, count), Domain nodes (id `domain:xxx`, label, count), Topic nodes (id `topic:xxx`, label, count).
2. **Edges**: `wikilink` edges (direct note-to-note internal links), `has_tag` edges (note-to-tag relationships), `in_topic` edges (note-to-topic memberships), and `in_domain` edges (topic-to-domain hierarchy).

### [REQ-MIND-003] Interactive Obsidian-Style 2D Physics Canvas View (Event-Driven)
When the user clicks the `[🧠 Mind Map]` button in Wiki Studio, the system SHALL open a full-featured interactive canvas modal featuring:
1. **2D Force-Directed Simulation**: Dynamic physics with repulsion, link spring tension, and centering forces.
2. **Live Search Filter**: Real-time filtering highlighting or isolating nodes by title, `#tag`, or `domain:`.
3. **Dimension & Entity Toggles**: Interactive filters to toggle visibility of Notes, Tags, Domains/Topics, Wikilinks, and Tag Connections.
4. **Interactive Hover & Click**: Rich tooltip metrics on node hover and immediate note opening in the editor upon node click.
