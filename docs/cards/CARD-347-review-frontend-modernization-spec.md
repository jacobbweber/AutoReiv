# [CARD-347] Review Frontend Modernization Spec

> **Status**: Backlog
> **Created**: 2026-09-17
> **Spec Reference**: [docs/specs/frontend-modernization/](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modernization/)
> **Labels**: `type:spec`, `domain:frontend`, `domain:architecture`, `initiative:modernization`, `backlog`

---

## 1. Why / Intent

Review and revise the frontend modernization and cross-platform migration specification (`docs/specs/frontend-modernization/` and `ADR-0053`) before any future implementation attempt. An initial prototype demonstrated a crisp, modern visual direction (Svelte 5 Runes, Tailwind CSS v4, Tauri 2.0 shell), but attempting a monolithic one-shot cut revealed a significant loss of existing UI capabilities, buttons, studio controls, and modals across the application's 11 studios. 

This card anchors the initiative in the backlog so that the architectural specifications, tasks breakdown, and migration strategy can be thoroughly audited, ensuring that any future migration is executed incrementally, studio-by-studio, with zero loss of functionality.

### The Three Beats

1. **What Jacob means**:
   - The modernization concept (Svelte 5 + Runes, Tailwind CSS v4, Tauri 2.0 desktop/mobile shell) is desirable for performance, maintainability, and cross-platform support.
   - However, AutoReiv's 11 studios have substantial depth (HITL approval cards, training handshakes, model routing, routines orchestration, workbench artifact previews, telemetry, pack inspection). A broad rewrite risks silently dropping capabilities.
   - The specification must be reviewed and restructured into an incremental, risk-mitigated plan where every existing button, modal, and flow is inventoried and preserved.
   - No code or branch work should proceed until this backlog review establishes a rigorous studio-by-studio roadmap.

2. **What AutoReiv does now**:
   - AutoReiv runs in production on vanilla JavaScript modules (`src/web/static/modules/`) and a single comprehensive HTML template (`src/web/templates/index.html`) backed by FastAPI.
   - All 11 studios and 517 frontend unit tests operate against this baseline with zero regressions.
   - The current specification suite in `docs/specs/frontend-modernization/` (`requirements.md`, `design.md`, `migration-plan.md`, `tasks.md`) specifies a full 7-phase rewrite, but lacks a detailed per-studio feature parity matrix and an incremental dual-engine coexistence strategy.

3. **What will change**:
   - The modernization documentation suite will be reviewed and updated to include a comprehensive catalog of all existing controls, views, and modals.
   - The migration strategy will transition from a high-risk monolithic replacement to an incremental, studio-by-studio migration plan (e.g. migratable studio components mounted alongside legacy views or partitioned into distinct, verified feature cards).
   - Interaction patterns defined in `.agents/rules/ui-ux-design.md` (smart autoscroll, progress honesty, discoverability, interruptibility) will be explicitly mapped to each studio before any implementation branch is cut.

---

## 2. What to Review & Refine

1. **Feature Parity Audit across all 11 Studios**:
   - **Chat Studio**: Progressive SSE stream decoding, reasoning drawer toggles, inline job phase status strips, HITL approval/rejection cards with JSON diffs, session switching, agent picker, quick actions.
   - **Routines Studio**: Routine creation/editing modals, cron scheduling expressions, trigger configs, job run history, pause/resume toggles.
   - **Workbench Studio**: Split-pane artifact preview, syntax highlighting, diff viewer, export and download actions.
   - **Agents Studio**: Agent configuration, pack bindings, system prompt editor, tool/skill selection matrix, memory inspect drawers.
   - **Packs Studio**: Factory pack seeding, import/export, local storage inspectors, pack metadata cards.
   - **Jobs Studio**: Live running task feeds, cancel/kill controls, log inspection drawers, task timing metrics.
   - **Tools & Skills Studios**: Tool parameter definitions, execution testing consoles, skill runbook markdown editors.
   - **Observability / Telemetry Studio**: Event logs, token counter charts, latency graphs, trace inspection.
   - **Models Studio**: Provider routing keys, model parameter sliders, endpoint testing pings.
   - **Settings Studio**: Local storage directory paths, server port settings, theme selectors.

2. **Migration Strategy Evaluation**:
   - Assess feasibility of an incremental hybrid bridge (e.g., embedding new Svelte studio components into the existing shell or running studios via a micro-frontend architecture) versus an all-at-once switch.
   - Define exact rollback and dual-run verification gates so that `qa` remains 100% green and shippable at all times.

3. **Specification Updates**:
   - Update [`docs/specs/frontend-modernization/requirements.md`](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modernization/requirements.md) with EARS-formatted requirements for each studio's complete feature set.
   - Update [`docs/specs/frontend-modernization/tasks.md`](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modernization/tasks.md) to decompose the migration into isolated, independently shippable work cards (e.g. CARD-xxx Chat Studio, CARD-yyy Routines Studio) rather than a single monolithic card.
   - Review [ADR-0053](file:///d:/Projects/Active/AutoReiv/docs/adr/0053-frontend-modernization-and-cross-platform-architecture.md) to document any updated consensus on phased rollout.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Complete UI and feature inventory completed for all 11 studios documenting every button, modal, form input, and interaction pattern.
- [ ] Revised `docs/specs/frontend-modernization/tasks.md` reflecting an incremental, studio-by-studio migration roadmap with explicit feature-parity test gates.
- [ ] Clear technical decision documented on dual-engine coexistence / incremental mounting strategy during migration.
- [ ] Specification reviewed and formally approved by Jacob prior to scheduling or cutting any feature branch.
- [ ] Card remains in `Backlog` status until prioritized by the product owner.

---

## 4. Constraints & Honor Flags

- **Backlog Only**: This is a future backlog initiative. Do NOT cut a feature branch, generate code, or modify production files under this card until prioritized.
- **Zero QA Impact**: Creating and maintaining this card on `qa` introduces no functional changes or breaking edits to AutoReiv.
- **Single Card Standard**: When implementation is eventually prioritized, each studio or phase will be scaffolded as its own isolated work card under `docs/cards/`.

