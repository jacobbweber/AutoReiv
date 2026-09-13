---
id: CARD-137
title: "Modern Systematic UI Overhaul and Ergonomic Multi-Agent Control Plane"
status: Done
priority: High
created: 2026-09-02
owner: Antigravity
description: "Comprehensive frontend redesign of AutoReiv's interface for desktop and mobile, maximizing vertical chat space, implementing a systematic concentric radius system (inner = outer - padding, edge touching = 0, ring = inner + gap), and unifying the chat input toolbar while preserving 100% of surfaced controls."
---

# CARD-137: Modern Systematic UI Overhaul and Ergonomic Multi-Agent Control Plane

## 1. Why / Intent
AutoReiv is a local-first Multi-Agent Control Plane. Over successive feature iterations, numerous powerful capabilities have been surfaced (Agent switching, Tone directives, Goal mode, Self-Verification, Workflow templates, HITL approval toggles, Journey timelines, and Debug inspectors). However, the interface accumulated vertical bars and disjointed controls that consumed valuable screen space and lacked visual hierarchy.

The human visionary provided a systematic UI design guide based on 5 core principles:
1. **Concentric Nested Corners**: `inner = outer - padding` so inner elements share the same corner center without visual distortion.
2. **Edge Touching**: If an element touches a screen or container edge (header, sidebar, bottom toolbar, slide-out drawer), that touching edge has zero radius.
3. **Ring Offsets**: Active focus and selection rings follow `outer = inner + gap` so rings don't pinch.
4. **Radius Follows Size**: Strict scale hierarchy:
   - `sm` (4px / `rounded`): tags, micro-badges, code snippets.
   - `md` (8px / `rounded-lg`): buttons, inputs, dropdowns, icon controls.
   - `lg` (12px / `rounded-xl`): cards, message bubbles, panels.
   - `xl` (16px / `rounded-2xl`): modals, sheets, slide-over drawers.
   - `full` (9999px / `rounded-full`): status dots, avatars, toggle pills.
5. **Shape vs Number**: Pill shape is reserved for small standalone chips and toggles; multiline containers always use geometric numbers.

The goal is to maximize vertical and horizontal chat space, establish a coherent and elegant dark-mode aesthetic, and keep 100% of existing controls and DOM contracts fully functional.

## 2. What to Build

### Slice 1: Systematic Design System & CSS Utility Foundation
- Add custom design system classes in `src/web/templates/index.html` enforcing the radius scale, concentric nesting, ring offsets, and edge-touching rules.
- Maintain dark-mode slate/indigo color tokens with refined contrast and subtle borders (`border-slate-800/80` and `border-slate-700/60`).

### Slice 2: Unified Ergonomic Floating Chat Input Card
- Refactor `#chatInputWrapper` to maximize vertical space:
  - Collapse the separate multi-row options strip into a single, unified floating card container (`rounded-xl` or `rounded-2xl` desktop, touching-edge mobile).
  - Main input area: Auto-expanding textarea (`#promptInput`).
  - Integrated bottom action bar inside the card:
    - Left side: Mode chips for `#verifyToggle` (Self-Verify), `#goalToggle` (Goal Mode), `#approvalToggle` (Auto-run), and `#workflowPicker` / `#saveAsWorkflowBtn`.
    - Right side: Dynamic status indicator pills (`#verifyBadge`, `#approvalBadge`, `#goalBadge`) and primary action button (`#sendBtn` / `#stopBtn`).
  - Preserves all element IDs, change listeners, and accessibility attributes.

### Slice 3: Streamlined Header & Control Center
- Refine Chat Top Bar:
  - Left: Agent selector (`#chatTopBarAgentSelect`), active status pulse, persona tone indicator (`#activeAgentTone`), agent title (`#activeAgentTitle`).
  - Right: Control center action group with concentric buttons for `#chatShowJourneyBtn` (Journey), `#chatDebugToggleBtn` (Debug), `#exportThreadWikiBtn` (Wiki), and `#copyThreadBtn` (Copy).
- Refine Job/Phase status strip (`#jobPhaseStatusStrip`) into a sleek, non-intrusive progress ribbon.

### Slice 4: Concentric Slide-Over Drawers (Journey & Debug)
- Refactor `#chatJourneyDrawer` and `#chatDebugPane`:
  - Apply edge-touching rule (`rounded-l-2xl rounded-r-none` or full-height on mobile).
  - Nest timeline cards and debug panes using `inner = outer - padding`.
  - Preserve all tabs (`#chatDebugTabMessages`, `#chatDebugTabTools`, `#chatDebugTabMetrics`, `#chatDebugTabSystem`) and copy button (`#chatDebugCopyBtn`).

### Slice 5: Automated Verification & Invariant Proofs
- Update frontend DOM audit and unit test suites (`journey_debug.test.js`, `dom_audit.test.js`, `accessibility.test.js`).
- Ensure all 100+ Vitest tests and 685 Pytest tests remain 100% green.
- Verify zero linting issues via `npm run lint:frontend`.

## 3. Acceptance Criteria (Definition of Done)
- [x] Systematic radius scale applied across all components without arbitrary conflicting classes.
- [x] Chat vertical space increased by at least 32-48px via unified input card.
- [x] All existing controls, switches, buttons, and badges preserved and operational.
- [x] Desktop and mobile layouts fully responsive with safe-area insets.
- [x] Frontend unit tests pass (`npm run test:unit:frontend`).
- [x] Frontend linter passes (`npm run lint:frontend`).
- [x] Backend test suite passes (`pytest tests/unit`).
- [x] CHANGELOG.md updated and conventional commit created on `qa`.
