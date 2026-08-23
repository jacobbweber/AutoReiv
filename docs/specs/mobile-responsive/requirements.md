# Requirements Specification: Mobile-First Responsive Layout & Viewport Overhaul

> **Document ID**: `SPEC-RESP-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-RESP-001]`, `[REQ-RESP-002]`, `[REQ-RESP-003]`

---

## 1. User Story

**As a** mobile and desktop user of AutoReiv,  
**I want** the control plane to dynamically adapt to any screen size (from 375px mobile phones to 4K monitors),  
**So that** Chat Studio keeps the input bar pinned at the bottom, navigation sidebars collapse into touch drawers, and documents take up the full screen width.

---

## 2. EARS Requirements

### [REQ-RESP-001] Dynamic 100dvh Viewport & Sticky Chat Input Bar (Ubiquitous)
The AutoReiv layout container SHALL enforce a fixed dynamic viewport height (`100dvh`) without outer window body scrolling, keeping the Chat Studio message history independently scrollable (`flex-1 overflow-y-auto`) and the chat prompt input bar pinned at the bottom (`flex-shrink-0 sticky bottom-0`).

### [REQ-RESP-002] Responsive Off-Canvas Split Drawers (Event-Driven)
WHERE the viewport width is below the medium breakpoint (`< 768px`), the Wiki Studio and System Info sidebars SHALL collapse into off-canvas drawer overlays toggled via dedicated mobile action buttons (`[📁 Vault]` / `[☰ Topics]`) and automatically dismiss upon note/topic selection.

### [REQ-RESP-003] Mobile Modal & Touch-Optimized Physics Canvas (Ubiquitous)
All modal dialogs and the 2D Mind Map canvas SHALL adjust to 100% viewport width and height on mobile screens with responsive touch dragging and pan/zoom capabilities.
