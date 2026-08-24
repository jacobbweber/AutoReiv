# ADR-0027: Mobile-First Responsive Layout & Sticky Viewport

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 26 (`CARD-026`)  
> **Requirements**: `[REQ-RESP-001]`, `[REQ-RESP-002]`, `[REQ-RESP-003]`

---

## Context
AutoReiv previously operated with fixed multi-column split panes (`w-80`) and unbounded viewport height (`min-h-screen`), causing whole-page scrolling on mobile touch screens and making the chat input box scroll away.

---

## Decision
1. **Dynamic Viewport (`100dvh`)**:
   - Enforce `h-[100dvh]` root layout to eliminate outer page bouncing on mobile browsers (Safari/Chrome).
   - Chat input bar is pinned at the bottom (`flex-shrink-0 sticky bottom-0`), while message history scrolls independently.
2. **Off-Canvas Split Drawers**:
   - On screens `< 768px`, sidebars for Wiki Studio and System Info collapse into slide-out drawers toggled via mobile buttons (`[📁 Vault]` / `[☰ Topics]`) that auto-close upon selection.
3. **Responsive Modals & Canvas Touch**:
   - Modals and the 2D Mind Map adapt to full viewport width on mobile with touch drag support.

---

## Consequences
- Single unified codebase works seamlessly on both mobile phones and desktop displays.
