# [CARD-023] Wiki Studio Interactive Mind Map Graph View and Tree Navigation Fixes

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/wiki-mind-map/`
> **Labels**: `type:feature`, `milestone:23`, `domain:wiki`

---

_Parked 2026-08-29 board hygiene. Not in flight. Wiki mind-map still on this card if we pick it up._

## 1. Why / Intent
The human visionary requires:
1. Complete collapsible folder navigation for Degree (`domain`) and Subject (`topic`) levels in the Wiki Studio sidebar tree.
2. An interactive, Obsidian-style **Mind Map / Graph View** (`[🧠 Mind Map]`) with search filtering, dimension toggling (Notes, Tags, Domains/Topics, Wikilinks, Tag co-occurrence edges), node physics, pan/zoom, hover metrics, and one-click navigation directly to selected notes.

---

## 2. What to Build
1. **Tree Navigation Fixes**:
   - Make both Level 1 Degree (`domain`) and Level 2 Subject (`topic`) folders in `notes/` collapsible buttons with open/close chevron state and click handlers.
   - Maintain state in `expandedWikiFolders` so expanding/collapsing subtopics works seamlessly.
2. **Multi-Dimensional Mind Map API**:
   - `GET /api/wiki/mindmap?include_tags=true&include_domains=true`:
     - Returns multi-dimensional nodes: Notes (type: note), Tags (type: tag), Domains (type: domain), Topics (type: topic).
     - Returns multi-dimensional edges: Wikilinks (`source -> target`), Tag memberships (`note -> tag`), Taxonomy memberships (`note -> topic -> domain`).
3. **Obsidian-Style Interactive Mind Map Modal / Canvas (`#wikiMindMapModal`)**:
   - Top Bar: Search query filter input (live filter by title, `#tag`, `domain:name`), Dimension Filter Toggles (🔘 Notes, 🔘 Tags, 🔘 Domains, 🔘 Wikilinks, 🔘 Tag Links), Forces & Physics controls (Link Distance, Repulsion, Node Size), Reset View & Zoom controls.
   - Interactive HTML5 Canvas / SVG 2D Force-Directed Graph Engine with drag, pan, zoom, particle simulation, high-contrast Obsidian dark theme styling (glowing nodes, colored halos per domain/tag).
   - Tooltip on node hover: note title, UID, domain/topic, word count, tokens, tags, connected neighbors count.
   - Click node: instantly focuses and opens the note in Wiki Studio!

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-MIND-001]`: Nested Degree & Subject Tree Expand/Collapse with persistent memory.
- [ ] `[REQ-MIND-002]`: Multi-Dimensional Mind Map Data Model & API (`/api/wiki/mindmap`).
- [ ] `[REQ-MIND-003]`: Interactive Obsidian-style Mind Map 2D Physics Canvas with live search filtering, dimension toggles, and click-to-open note navigation.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Zero external heavy CDN libraries required (native canvas 2D force simulation).
- Clean responsive dark theme matching AutoReiv styling.
