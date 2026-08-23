# ADR-0022: System Info Conceptual Knowledge Hub and Architectural Overviews

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Decision Makers**: Jacob Weber, Principal Agent Engineer  
> **Linked Issue / Card**: CARD-021

---

## 1. Context and Problem Statement

Initially, AutoReiv exposed a low-level "System & Specs" page that rendered raw internal engineering specifications (`requirements.md`, `design.md`, `tasks.md`, `rtm.json`, ADRs).
However, for users and operators, a raw specification dump creates cognitive noise and is already accessible in the GitHub repository.
Users need a clear, educational **System Info** knowledge hub explaining core concepts, architectural overviews, the 5-Tier Concept Hierarchy (Agents vs Workflows vs Routines vs Skill Packs vs Tools), Purpose Matrix routing, and safety mechanisms.

---

## 2. Considered Options

- **Option A: Keep Raw Spec Browser**:
  Retain raw repository file trees and low-level task lists in the UI.
- **Option B: Transform to System Info Knowledge Hub (Chosen)**:
  Provide a dedicated `SystemInfoService` delivering structured, high-signal educational chapters with visual Mermaid diagrams, conceptual definitions, and reference guides.

---

## 3. Decision Outcome

**Chosen Option**: **Option B**.

### Positive Consequences
- **High Pedagogical Signal**: Operators immediately understand how agents, workflows, routines, skill packs, and tools interact.
- **Comprehensive Reference**: Provides authoritative documentation on skill pack tool capabilities, hardware sizing formulas, and purpose cascades.
- **Enhanced User Experience**: Clean topic navigation with search and interactive Mermaid Pan-Tilt-Zoom inspection.
