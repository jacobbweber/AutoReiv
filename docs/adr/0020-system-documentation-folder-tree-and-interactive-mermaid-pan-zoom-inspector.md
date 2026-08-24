# ADR-0020: System Documentation Folder Tree Navigation and Interactive Mermaid Pan-Zoom Inspector

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Decision Makers**: Jacob Weber, Principal Agent Engineer  
> **Linked Issue / Card**: CARD-019

---

## 1. Context and Problem Statement

AutoReiv's System & Specs view contains dozens of specifications, ADRs, SDLC rules, and complex architectural diagrams (such as C4 component models, sequence flows, and state machines).
Operators need:
1. A clean nested folder tree navigation sidebar (e.g. `docs/specs/<feature>/requirements.md`, `design.md`, `tasks.md`) rather than a single flat list.
2. The ability to inspect and navigate complex Mermaid diagrams with full Pan-Tilt-Zoom (PTZ) mouse controls, zoom slider, reset view, and high-resolution modal inspection.

---

## 2. Considered Options

- **Option A: Static Mermaid Blocks and Flat Sidebar (Status Quo)**:
  Mermaid blocks scale only to document column width and cannot be zoomed or panned; navigation is flat.
- **Option B: Recursive Tree Navigation & Dedicated PTZ Mermaid Inspector (Chosen)**:
  Hierarchical folder sidebar with collapsible branches and an interactive Mermaid inspector modal with mouse-wheel zoom, drag-to-pan, and zoom toolbar.

---

## 3. Decision Outcome

**Chosen Option**: **Option B**.

### Positive Consequences
- **Effortless Discovery**: Specifications are organized by feature folders rather than sprawling flat lists.
- **High-Resolution Inspection**: Complex multi-node Mermaid diagrams can be zoomed up to 500% and panned smoothly.
