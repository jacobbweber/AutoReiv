# [ADR-0053] Frontend Modernization: Svelte 5, Adaptive Shell Architecture & Cross-Platform Tauri Distribution

> **Status**: Accepted  
> **Date**: 2026-09-17  
> **Deciders**: Jacob (Visionary & Product Owner), Antigravity (Principal Software Engineer)  
> **Spec Reference**: [`docs/specs/frontend-modernization/`](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modernization/)  
> **Supersedes / Modernizes**: [ADR-0008](file:///d:/Projects/Active/AutoReiv/docs/adr/0008-fastapi-web-application-rest-streaming-api-and-responsive-multi-view-spa.md), [ADR-0030](file:///d:/Projects/Active/AutoReiv/docs/adr/0030-web-ui-tab-hydration-and-rendering-architecture.md), [ADR-0031](file:///d:/Projects/Active/AutoReiv/docs/adr/0031-frontend-modularization-foundation-and-quality-gates.md)

---

## 1. Context & Problem Statement

AutoReiv has grown from a simple single-page web view into a rich, autonomous personal agent operating system featuring 11 integrated studios (Chat, Wiki, Projects, Agents/Forge, Factory, Routines, Observability, Settings, Prompts, Education, Lumina), real-time Server-Sent Event (SSE) token streaming at 60–120 tokens/sec, an OS-style multi-window desktop environment, and Human-in-the-Loop (HITL) approval workflows.

However, the presentation layer suffers from fundamental architectural debt inherited from early rapid prototyping:

1. **Monolithic DOM Structure (`index.html`)**:
   - The entire frontend markup lives in a single, 5,837-line HTML template (`src/web/templates/index.html`).
   - Adding, modifying, or testing any visual element requires traversing thousands of deeply nested, hardcoded HTML tags.
2. **Imperative DOM Manipulation Overload**:
   - 14 studio modules in `src/web/static/modules/studios/` total over 700 KB of manual DOM querying (`$()`, `$queryAll()`), string concatenation (`innerHTML = \`...\``), and defensive class mutation (`classList.add('hidden')`).
   - There are zero reusable component boundaries: a single button, modal, badge, or card is re-invented and re-coded across disparate studio files.
3. **High-Frequency Rendering Fragility**:
   - High-speed token streaming and 120Hz window dragging/resizing continuously trigger imperative style and DOM changes, leading to layout thrashing, brittle event bindings, and tight coupling between styling and business logic.
4. **Cross-Platform Delivery Gap**:
   - The operator needs AutoReiv accessible across **macOS, Windows, Linux, Android, and iOS**.
   - The current web UI relies on desktop-specific floating window coordinates that break or become unusable on small mobile phone screens (<768px portrait).
   - There is no native installer or mobile shell; users must run a web browser pointed at a local IP address.

---

## 2. Decision & Architectural Pillars

We adopt a modern, high-performance, component-driven frontend architecture decoupled from the Python backend, packaged for desktop and mobile via **Tauri 2.0**, and served natively by FastAPI.

### Pillar 1: Component Framework — Svelte 5 (with Runes)
- **Why Svelte 5 over React / Vue**:
  - **Zero Virtual DOM**: Svelte 5 compiles directly to surgical, fine-grained DOM operations. During heavy LLM token streaming (60–120 tokens/sec), Svelte updates only the specific text node without diffing virtual component subtrees.
  - **Fluid Physics & Dragging**: Window dragging, resizing, and snapping operate with 0ms framework overhead, running at native 60/120Hz display refresh rates.
  - **Reactivity via Runes**: Modern `$state`, `$derived`, `$effect`, and `$props` provide explicit, type-safe reactive primitives without boilerplate state managers or hook dependency arrays.
  - **Single-File Component (SFC) Encapsulation**: Markup, TypeScript logic, and scoped styles reside in `.svelte` files, completely eliminating the 5,837-line monolithic HTML file.

### Pillar 2: Styling & Design Token Engine — Tailwind CSS v4
- **CSS-First Theme Tokens**: Built on Tailwind v4 using `@theme` and semantic CSS variables (`--surface-base`, `--surface-raised`, `--surface-border`, `--color-brand`).
- **Tactile Claymorphism & Enterprise Neutral Palettes**:
  - Full, first-class support for the Claymorphism tactile theme (CARD-345) and enterprise dark/light palettes via CSS custom properties.
  - Theme changes toggle a clean token layer on `:root`, updating all components universally without overriding hundreds of utility classes.

### Pillar 3: Adaptive Information Architecture (Two-Mode Shell)
Rather than forcing desktop multi-window mechanics onto a mobile screen or gutting desktop capabilities for mobile simplicity, the frontend employs an **Adaptive Responsive Shell**:
1. **Desktop / Tablet Canvas Mode (Viewport ≥ 768px)**:
   - OS-style desktop canvas with floating, draggable, resizable, and snappable windows.
   - Persistent bottom dock, window organize actions (tile, cascade, split half), and z-index focus stacking.
2. **Mobile Companion Stack Mode (Viewport < 768px)**:
   - Automatically morphs into a native mobile application experience.
   - Pinned native bottom navigation bar for primary studios (Chat, Wiki, Routines, Observe, Settings).
   - Full-screen view transitions, slide-over drawers for session history, and bottom-sheet modals for HITL approvals and parameter tuning.
   - Safe-area insets (`env(safe-area-inset-bottom)`) and dynamic keyboard avoidance (`interactive-widget=resizes-content`).

Both modes share 100% of the underlying business logic, state stores, and studio child components (`<ChatMessages />`, `<WikiEditor />`, `<RoutineCard />`).

### Pillar 4: Cross-Platform Packaging — Tauri 2.0
- Single web codebase distributed to all 5 target operating systems:
  - **Desktop**: macOS (`.dmg`), Windows (`.exe` / `.msi`), Linux (`.deb` / AppImage) using the native OS Webview (WebView2 on Windows, WebKit on macOS, WebKitGTK on Linux).
  - **Mobile**: iOS (`.ipa`) and Android (`.apk`) using native mobile webviews.
  - **Web / LAN**: The compiled `dist/` bundle is statically hosted by FastAPI at `http://<host>:8000/`.
- **Memory Footprint**: Desktop apps idle at ~30–40 MB of RAM (versus 400–700 MB for Electron).

### Pillar 5: Strict SOLID & DRY Engineering Standards
- **Single Responsibility Principle (SRP)**:
  - UI components only handle presentation.
  - Business logic, SSE streaming, and API communication reside strictly in service modules (`services/api.ts`, `services/sse.ts`) and reactive stores (`stores/session.svelte.ts`, `stores/window.svelte.ts`).
- **Open/Closed Principle (OCP)**:
  - New studios or widgets register into a modular registry without modifying core navigation or window manager code.
- **Don't Repeat Yourself (DRY)**:
  - Universal design system component primitives: `<Button>`, `<Input>`, `<Modal>`, `<Drawer>`, `<Badge>`, `<Card>`, `<Dropdown>`, `<WindowFrame>`.
  - Zero duplicated HTML or repeated inline SVG icons.

---

## 3. Technology Stack Specification

| Responsibility | Technology Choice | Rationale |
| :--- | :--- | :--- |
| **Framework** | **Svelte 5** | Compiler-based reactivity (Runes), zero Virtual DOM, minimal bundle footprint (<35KB). |
| **Language** | **TypeScript 5+** | Strict end-to-end type safety against FastAPI Pydantic schema contracts. |
| **Build Tooling** | **Vite 6** | Sub-second HMR in development, optimal tree-shaken static production bundles. |
| **Styling** | **Tailwind CSS v4** | CSS-first token configuration, zero runtime CSS injection overhead. |
| **Icons** | **Lucide-Svelte** | Tree-shaken native SVG icon components replacing runtime DOM script injection. |
| **Markdown / Code** | **Marked.js + Shiki** | High-speed, secure client-side markdown and syntax-highlighted code rendering. |
| **Diagrams** | **Mermaid.js** | Dynamic pan/zoom system architecture and wiki knowledge graph rendering. |
| **Testing** | **Vitest + Playwright** | Unit tests for components and stores; end-to-end smoke tests for complete workflows. |
| **Desktop / Mobile Shell**| **Tauri 2.0** | Cross-platform compilation to Windows, macOS, Linux, Android, and iOS. |

---

## 4. Operational & Deployment Architecture

```
[Development Workflow]
Vite Dev Server (http://localhost:5173)
  │ (HMR / Fast Refresh)
  ▼
Proxy /api & /api/chat/stream ──▶ FastAPI Backend (http://127.0.0.1:8000)

[Production Self-Hosted (FastAPI Web)]
npm run build ──▶ Output to src/web/dist/
FastAPI app.py mounts StaticFiles("/static", src/web/dist/assets)
FastAPI serves src/web/dist/index.html at "/"

[Production Native Desktop & Mobile (Tauri 2.0)]
Tauri CLI wraps src/web/dist/
  ├── macOS / Windows / Linux Native Binary
  └── iOS / Android Native Binary (Connects to LAN / Tailscale host)
```

---

## 5. Consequences & Trade-offs

### Positive
- **Elimination of Fragility**: The 5,837-line monolithic `index.html` and 700 KB of imperative DOM scripts are completely retired and replaced by clean, modular, testable components.
- **Flawless Mobile & Desktop UX**: Mobile users get a native phone app feel (bottom tabs, sheet modals); desktop users retain the powerful multi-window OS workspace.
- **Performance**: Svelte 5 eliminates stream stuttering, frame drops during window movement, and memory leaks from manual event listeners.
- **Cross-Platform Native Distribution**: Official installers for Mac, Windows, Linux, iOS, and Android from a single source of truth.
- **Type Safety**: TypeScript contracts prevent runtime bugs when backend APIs evolve.

### Trade-offs & Mitigations
- **Build Step Requirement**: Requires `npm run build` to generate `dist/` before running production FastAPI.
  - *Mitigation*: Automated preflight scripts and local dev mode proxy seamlessly; build step completes in < 3 seconds with Vite.
- **Migration Effort**: 11 studios must be converted from imperative DOM to declarative Svelte.
  - *Mitigation*: Executed through a phased, vertical-slice migration plan with parallel coexistence during the transition.

---

## 6. Verification & Definition of Done

- All 11 studios functional with 100% feature parity.
- Zero raw `innerHTML` string concatenations in business logic.
- Automated tests green across Vitest (unit/component) and Playwright (cross-platform E2E).
- Clean linting with zero ESLint and TypeScript errors.
