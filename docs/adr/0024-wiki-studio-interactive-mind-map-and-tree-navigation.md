# ADR-0024: Wiki Studio Interactive Mind Map & Tree Navigation

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 23 (`CARD-023`)  
> **Requirements**: `[REQ-MIND-001]` through `[REQ-MIND-003]`

---

## Context
AutoReiv's Wiki Studio serves as a human-facing knowledge warehouse. Users need to visually explore connections across notes, tags, domains, and subjects through an Obsidian-style force-directed Graph View / Mind Map with search filters, dimension toggles, physics controls, and seamless tree navigation.

---

## Decision
1. **Collapsible 2-Level Taxonomy Tree**:
   - Level 1 Degree (`domain`) and Level 2 Subject (`topic`) folders are rendered as collapsible button elements with independent expand/collapse states stored in memory.
2. **Multi-Dimensional Mind Map Graph**:
   - Returns notes, tags, domains, and topics as nodes, with wikilinks, tag associations, and taxonomy hierarchies as typed edges.
3. **High-Performance 2D Canvas Physics Engine**:
   - Zero external library bloat: built directly with HTML5 Canvas using a 2D velocity-Verlet force-directed particle physics model.
   - Supports search filtering, entity dimension toggles (Notes, Tags, Domains), link toggles, hover inspection, drag & drop nodes, and click-to-open note action.

---

## Consequences
- Gives users an interactive Obsidian-grade exploration experience.
- Clean separation between core domain graph extraction and rich UI rendering.
