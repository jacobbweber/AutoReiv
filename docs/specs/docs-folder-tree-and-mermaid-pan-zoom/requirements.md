# Requirements: System Documentation Folder Tree & Interactive Mermaid Pan-Zoom Inspector

> **Standard**: AWS Kiro EARS (Easy Approach to Requirements Syntax)  
> **Traceability Prefix**: `[REQ-DOCS-xxx]`  
> **Target Component**: `AutoReiv.Web`

---

## 1. System Context & User Stories

As an **Operator & System Architect**,  
I want to **navigate platform documentation and specs through an interactive, collapsible folder tree structure on the left pane**,  
And I want **the ability to click and inspect any Mermaid architectural diagram in a dedicated modal with smooth pan and zoom controls**,  
So that **I can easily explore large specifications and inspect complex system architectures at high resolution without cognitive friction**.

---

## 2. EARS Requirements Specification

### [REQ-DOCS-001]: Nested Folder Tree Navigation API
- **Type**: Ubiquitous
- **Statement**: The system shall structure `GET /api/docs/nav` to return a recursive, nested folder tree representation of repository documentation, grouping milestone specifications by their subfolder directories (`docs/specs/<feature>/requirements.md`, `design.md`, `tasks.md`), ADRs (`docs/adr/`), SDLC rules (`.agents/rules/`), and root files.

### [REQ-DOCS-002]: Interactive Collapsible Tree Sidebar UI
- **Type**: Event-Driven
- **Statement**: When an operator views `#view-docs`, the sidebar shall render an interactive nested directory tree with expand/collapse chevron toggles, folder state indicators (open/closed folder icons), active document highlighting, and real-time search filtering across all tree depths.

### [REQ-DOCS-003]: Interactive Mermaid Diagram Overlay & Inspector Modal
- **Type**: Event-Driven
- **Statement**: When a Mermaid diagram is rendered within documentation or chat bubbles, the system shall attach an interactive inspection overlay (`[🔍 Inspect & Zoom]`). Clicking the diagram or button shall open a dedicated high-resolution inspector modal (`#mermaidZoomModal`).

### [REQ-DOCS-004]: Pan-Tilt-Zoom (PTZ) Canvas Controls
- **Type**: Ubiquitous
- **Statement**: The Mermaid inspector modal shall provide smooth pan-and-zoom capabilities: mouse-wheel zooming, click-and-drag panning, zoom in/out action buttons (`+` / `-`), a reset view button (`↺ 100%`), and a fullscreen toggle (`⛶`).
