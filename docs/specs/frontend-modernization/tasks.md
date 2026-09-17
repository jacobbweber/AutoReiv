# Implementation Tasks: Frontend Modernization & Cross-Platform Architecture

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference `[REQ-MOD-xxx]` tags.  
> **ADR Reference**: [ADR-0053](file:///d:/Projects/Active/AutoReiv/docs/adr/0053-frontend-modernization-and-cross-platform-architecture.md)

---

## Phased Vertical Slice Breakdown

### Phase 1: Tooling, Build Pipeline & Reusable Component Primitives
- [ ] **Task 1.1** `[REQ-MOD-007]`: Initialize `src/web/client/` with Vite, Svelte 5, TypeScript, and Tailwind CSS v4. Configure sub-second HMR and API proxying (`/api` -> `http://127.0.0.1:8000`).
- [ ] **Task 1.2** `[REQ-MOD-007]`: Implement universal design token dictionary in `app.css` supporting both Enterprise Flat and Tactile Claymorphism palettes.
- [ ] **Task 1.3** `[REQ-MOD-007]`: Build reusable UI primitives: `<Button>`, `<Input>`, `<Textarea>`, `<Select>`, `<Modal>`, `<Sheet>`, `<Drawer>`, `<Badge>`, and `<Card>`.
- [ ] **Task 1.4** `[REQ-MOD-007]`: Write unit tests for component primitives verifying accessible ARIA attributes, event firing, and theme token binding.

### Phase 2: Core Reactive State Stores & SSE Streaming Engine
- [ ] **Task 2.1** `[REQ-MOD-004]`: Implement `services/sse.ts` parsing high-speed Server-Sent Events (`job_created`, `phase_start`, `react_state`, `token_delta`, `approval_required`, `complete`).
- [ ] **Task 2.2** `[REQ-MOD-004]`: Implement `stores/session.svelte.ts` using Svelte 5 Runes for fine-grained reactivity, progressive token delta buffering, and thought accordion tracking.
- [ ] **Task 2.3** `[REQ-MOD-006]`: Implement `stores/hitl.svelte.ts` managing pending approval cards, parameter schemas, and optimistic submission dispatch.
- [ ] **Task 2.4** `[REQ-MOD-002]`: Implement `stores/window.svelte.ts` handling window positions, dimensions, minimize/maximize state, and z-index focus stacking.
- [ ] **Task 2.5** `[REQ-MOD-007]`: Implement `stores/theme.svelte.ts` managing presets (Indigo, Slate Graphite, Violet, Warm Sand, Teal, Claymorphism) and storage persistence.
- [ ] **Task 2.6**: Write Vitest unit tests for all state stores verifying deterministic state updates.

### Phase 3: Adaptive Information Architecture Shell
- [ ] **Task 3.1** `[REQ-MOD-001]`: Implement `layouts/Shell.svelte` with responsive viewport listener switching between Desktop Canvas and Mobile Stack.
- [ ] **Task 3.2** `[REQ-MOD-002]`: Implement `components/desktop/WindowFrame.svelte` supporting smooth 60/120Hz dragging, edge resizing, and grid snapping.
- [ ] **Task 3.3** `[REQ-MOD-002]`: Implement `components/desktop/Dock.svelte` and `OrganizeMenu.svelte` with tactile clay and flat variants.
- [ ] **Task 3.4** `[REQ-MOD-003]`: Implement `components/mobile/BottomNav.svelte`, `MobileHeader.svelte`, and slide-over session drawers.
- [ ] **Task 3.5**: Verify zero scroll bouncing and strict safe-area inset compliance across both shells.

### Phase 4: Flagship Studios Migration (Chat & Wiki)
- [ ] **Task 4.1** `[REQ-MOD-004]`, `[REQ-MOD-005]`: Build `studios/chat/ChatStudio.svelte`, `MessageList.svelte`, and `StreamBubble.svelte` with smart autoscroll and "Jump to latest".
- [ ] **Task 4.2** `[REQ-MOD-004]`: Implement `ReasoningDrawer.svelte` for collapsible `<think>` blocks.
- [ ] **Task 4.3** `[REQ-MOD-006]`: Implement `HitlCard.svelte` rendering approval prompts both above the composer and in modal/sheet hosts.
- [ ] **Task 4.4** `[REQ-MOD-008]`: Build `studios/wiki/WikiStudio.svelte`, `NoteTree.svelte`, `NoteEditor.svelte`, and interactive `GraphView.svelte`.
- [ ] **Task 4.5**: Verify full Chat and Wiki workflows via Vitest and Playwright smoke tests.

### Phase 5: Complete Studio Fleet Migration
- [ ] **Task 5.1** `[REQ-MOD-008]`: Implement `studios/projects/ProjectsStudio.svelte` and `WorkspaceExplorer.svelte` with live context drift overlay.
- [ ] **Task 5.2** `[REQ-MOD-008]`: Implement `studios/agents/AgentsStudio.svelte` and `ForgeManifestEditor.svelte`.
- [ ] **Task 5.3** `[REQ-MOD-008]`: Implement `studios/factory/FactoryStudio.svelte` and `DeliverableModal.svelte`.
- [ ] **Task 5.4** `[REQ-MOD-008]`: Implement `studios/routines/RoutinesStudio.svelte` and `RoutineModal.svelte` with the interactive structured schedule picker.
- [ ] **Task 5.5** `[REQ-MOD-008]`: Implement `studios/observability/ObservabilityStudio.svelte` with KPI cards and token attribution breakdown.
- [ ] **Task 5.6** `[REQ-MOD-008]`: Implement `studios/settings/SettingsStudio.svelte` with provider API keys, model discovery, and theme customizer.
- [ ] **Task 5.7** `[REQ-MOD-008]`: Implement `studios/prompts/PromptsStudio.svelte`.
- [ ] **Task 5.8** `[REQ-MOD-008]`: Implement `studios/education/EducationStudio.svelte` and `studios/lumina/LuminaStudio.svelte`.

### Phase 6: Cross-Platform Packaging & Production Serving
- [ ] **Task 6.1** `[REQ-MOD-009]`: Update `src/web/app.py` to serve Vite's production output (`dist/`) statically at `/` with SPA route fallbacks.
- [ ] **Task 6.2** `[REQ-MOD-009]`: Configure Tauri 2.0 project (`src-tauri/`) with desktop targets (macOS, Windows, Linux) and mobile targets (Android, iOS).
- [ ] **Task 6.3** `[REQ-MOD-009]`: Verify local build and packaging scripts (`npm run build`, `npm run tauri build`).

### Phase 7: Dead Code Purge, RTM Synchronization & Definition of Done
- [ ] **Task 7.1**: Permanently delete legacy `src/web/templates/index.html` (5,837 lines) and obsolete `src/web/static/modules/` (700 KB).
- [ ] **Task 7.2**: Prune dead tests in `tests/unit/frontend/` that scraper-tested monolithic HTML strings; retain component and store tests.
- [ ] **Task 7.3**: Update `docs/rtm.json` linking all modernized components to `[REQ-MOD-xxx]`.
- [ ] **Task 7.4**: Run complete test suite (`preflight`: Ruff, Pytest, ESLint, Vitest, Playwright, RTM).
- [ ] **Task 7.5**: Update `CHANGELOG.md` and complete Human QA verification on all platforms.
