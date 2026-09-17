# Requirements Specification: Frontend Modernization & Cross-Platform Architecture

> **Spec Status**: Approved  
> **Target Release**: v1.0.0 (Modernized Client Architecture)  
> **Primary Component**: AutoReiv Web & Native Client (`src/web/client`)  
> **ADR Reference**: [ADR-0053](file:///d:/Projects/Active/AutoReiv/docs/adr/0053-frontend-modernization-and-cross-platform-architecture.md)

---

## 1. Executive Summary & Intent

This specification establishes the functional, architectural, and operational requirements for replacing AutoReiv's legacy 5,837-line monolithic `index.html` and 700 KB of imperative DOM scripts with a clean, high-performance, component-based frontend built on **Svelte 5 (Runes)**, **Tailwind CSS v4**, and **Tauri 2.0**.

The modernized client must provide:
1. An **Adaptive Information Architecture (Two-Mode Shell)** that delivers a multi-window workstation experience on desktop viewports (≥768px) and a fluid, touch-native companion experience on mobile viewports (<768px).
2. Flawless 60–120 tok/sec Server-Sent Event (SSE) token streaming without layout thrashing or Virtual DOM diffing overhead.
3. Native application distribution for **macOS, Windows, Linux, Android, and iOS** from a single shared TypeScript/Svelte codebase, while retaining zero-install web hosting via FastAPI.
4. Complete encapsulation and elimination of legacy technical debt (raw `innerHTML`, inline SVGs, duplicated styling, and monolithic HTML files).

---

## 2. EARS Functional Requirements

### Component 1: Adaptive Presentation Shell (Desktop & Mobile)

#### [REQ-MOD-001]: Adaptive Shell Layout Selection
- **Type**: State-Driven
- **EARS Statement**: `WHILE the viewport width is 768px or greater THE SYSTEM SHALL render the Desktop Canvas Shell, AND WHILE the viewport width is less than 768px THE SYSTEM SHALL render the Mobile Companion Stack Shell.`
- **Acceptance Criteria**:
  - [ ] Resizing viewport above/below 768px transitions layout without losing active session state or interrupting active LLM streams.
  - [ ] Desktop Canvas Shell displays the multi-window workspace, persistent bottom dock, and organize menus.
  - [ ] Mobile Companion Shell displays a pinned bottom navigation bar, full-screen active view, and safe-area inset padding.

#### [REQ-MOD-002]: Desktop Multi-Window Management
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator interacts with a desktop window header, resize handle, or dock icon THE SYSTEM SHALL update window coordinates, dimensions, minimized state, or z-index focus stack using fine-grained reactivity without re-rendering unrelated windows.`
- **Acceptance Criteria**:
  - [ ] Dragging and resizing windows runs at native display refresh rates (60Hz/120Hz) with 0ms framework lag.
  - [ ] Clicking a window raises its z-index to the top of the window stack below `DESKTOP_DOCK_Z` (10000) and `DESKTOP_MODAL_Z` (11000).
  - [ ] Dock buttons indicate open and minimized status and toggle window visibility on click.

#### [REQ-MOD-003]: Mobile Navigation & Drawer Transitions
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator taps a bottom navigation tab on mobile THE SYSTEM SHALL transition the primary viewport to the selected studio, AND WHEN an operator requests session history or tools THE SYSTEM SHALL open a touch-friendly slide-over drawer or bottom sheet.`
- **Acceptance Criteria**:
  - [ ] Mobile navigation tabs provide instant visual feedback with zero layout jump.
  - [ ] Touch gestures (swiping back, tapping backdrops) cleanly dismiss drawers and sheets.
  - [ ] Mobile viewports strictly prevent horizontal scrolling and overscroll bouncing (`overscroll-behavior: none`).

---

### Component 2: Real-time Streaming & Telemetry Engine

#### [REQ-MOD-004]: High-Frequency SSE Token Streaming
- **Type**: Event-Driven
- **EARS Statement**: `WHEN Server-Sent Events deliver token deltas, phase updates, or thought chunks THE SYSTEM SHALL append streaming text directly to the active message node using Svelte 5 Runes without triggering subtree Virtual DOM reconciliation.`
- **Acceptance Criteria**:
  - [ ] Sustains streaming at 120 tokens/sec with steady 60fps rendering.
  - [ ] Markdown formatting, code blocks, and syntax highlighting render progressively during streams.
  - [ ] Collapsible reasoning drawers (`<think>`) expand and collapse without breaking autoscroll.

#### [REQ-MOD-005]: Smart Autoscroll & Interruptibility
- **Type**: State-Driven
- **EARS Statement**: `WHILE an LLM stream is active AND the operator is scrolled within 64px of the viewport bottom THE SYSTEM SHALL automatically scroll to follow new tokens, BUT WHILE the operator scrolls up THE SYSTEM SHALL pin the scroll position and display a 'Jump to latest' control.`
- **Acceptance Criteria**:
  - [ ] Scrolling up during an active stream never yanks the operator's viewport down.
  - [ ] Clicking "Jump to latest" smoothly scrolls to the newest content and re-engages follow-tail.

---

### Component 3: Human-in-the-Loop (HITL) Execution Engine

#### [REQ-MOD-006]: Real-time HITL Prompt Surfacing
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent execution pauses for Human-in-the-Loop approval THE SYSTEM SHALL immediately render an interactive HITL approval card above the chat composer and inside the global desktop modal host.`
- **Acceptance Criteria**:
  - [ ] HITL prompt displays exact tool name, parameters, safety classification, and risk justification.
  - [ ] Approve and Reject actions submit decisions to `POST /api/hitl/decisions` with instant optimistic UI state update.
  - [ ] On mobile, HITL approvals surface as a pinned bottom sheet with full parameter visibility.

---

### Component 4: Unified Design System & Theming

#### [REQ-MOD-007]: Semantic Design Token Swapping
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator selects a theme preset (Indigo, Slate Graphite, Violet, Warm Sand, Teal, or Claymorphism) THE SYSTEM SHALL update CSS custom properties on the root element and persist the preference in browser storage.`
- **Acceptance Criteria**:
  - [ ] Theme switching executes instantaneously with zero page reload.
  - [ ] Selecting "Claymorphism" activates 3D inflated surfaces, soft outer drop-shadows, and compound inner bevel highlights.
  - [ ] Selecting enterprise flat themes restores neutral chrome borders and restrained brand accents.

---

### Component 5: Studio Suite Functional Parity

#### [REQ-MOD-008]: Complete 11-Studio Capability Parity
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide complete, unbroken functional parity across all 11 AutoReiv studios: Chat, Wiki, Projects, Agents/Forge, Factory, Routines, Observability, Settings, Prompts, Education, and Lumina.`
- **Acceptance Criteria**:
  - [ ] **Chat**: Sessions drawer, agent selector, goal/plan modes, file attachments, and export to Wiki.
  - [ ] **Wiki**: Hierarchical note tree, full markdown editor, Mermaid graph view, and inbox curation.
  - [ ] **Projects**: Directory explorer, code viewer, git context overlay, and mode flip.
  - [ ] **Agents (Forge)**: Manifest inspector, model cascades, skill allowlists, and constitution tuning.
  - [ ] **Factory**: Training pipeline timeline, question batteries, rubrics, and deliverable modal.
  - [ ] **Routines**: Frequency presets, interactive schedule builder, directive prompts, and immediate trigger.
  - [ ] **Observability**: Real-time telemetry KPIs, token attribution table, log streams, and audit export.
  - [ ] **Settings**: Provider keys (Ollama, vLLM, OpenAI, Anthropic, Gemini, DeepSeek), model refresh, theme tuner, and connection test.
  - [ ] **Prompts**: Template catalog browsing and insertion.
  - [ ] **Education**: Spaced repetition ledger, course progress, dual coding application labs, and delivery profiles.
  - [ ] **Lumina**: Cinema stage, dual coding visualizer, and narration audio player.

---

### Component 6: Cross-Platform Native Packaging & Serving

#### [REQ-MOD-009]: Single-Codebase Cross-Platform Compilation
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL compile into native application binaries for macOS, Windows, Linux, Android, and iOS via Tauri 2.0 from the same frontend source code that is statically hosted by FastAPI.`
- **Acceptance Criteria**:
  - [ ] Desktop binary idle memory consumption is under 50 MB.
  - [ ] Mobile packages compile into valid Xcode (`.ipa`) and Android Studio (`.apk`) projects.
  - [ ] Running `python -m uvicorn src.web.app:app` serves the compiled client to any LAN browser at `/` with zero external dependencies.

---

## 3. Non-Functional & Boundary Constraints

- **Zero Monolithic Templates**: The 5,837-line `index.html` must be completely replaced by a clean `< 50-line` HTML shell loading the compiled Svelte bundle.
- **Strict Code Cleanliness (SOLID & DRY)**: No raw `innerHTML` string concatenations; all UI components must be modular and reusable.
- **First-Paint Performance**: First Contentful Paint (FCP) < 400ms on desktop; Time to Interactive (TTI) < 800ms on mid-tier mobile devices.
- **Linting & Type Safety**: 100% TypeScript coverage with zero `any` types in public API interfaces; zero ESLint warnings or errors.

---

## 4. Out of Scope

- Modifying the underlying Python backend domain logic or SQLite database schemas (all changes are strictly frontend presentation, state, and client packaging).
- Adding third-party telemetry SaaS dependencies (all metrics remain local and self-contained).
