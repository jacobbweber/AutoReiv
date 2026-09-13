# [CARD-051] Chat Session History Markdown & Rich Syntax Rendering Consistency

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/chat-history-markdown-rendering/
> **Labels**: `type:bugfix`, `area:web`, `quality-gate`

---

## 1. Why / Intent
During active live streaming in Chat Studio, incoming assistant tokens are parsed via Marked.js and formatted in real-time into rich typography, styled code blocks, and diagrams. However, when selecting and reloading a past conversational session from the history sidebar, messages can render as unformatted plain text or raw markdown because `renderMessageItem` / `appendMessageBubble` does not consistently await Marked.js parsing and mermaid diagram compilation.

The human user requires 100% visual parity: past chat sessions loaded from SQLite must display the exact same beautiful, styled markdown, syntax-highlighted code blocks, and interactive diagram accordions as live sessions.

---

## 2. What to Build
1. **Frontend Markdown Hydration Pipeline (`src/web/static/modules/studios/chat.js`)**:
   - Refactor `renderMessages()`, `renderMessageItem()`, and `appendMessageBubble()` to properly await `renderMarkdown()` across all historical turns.
   - Ensure syntax-highlighting styles, prose CSS classes (`prose prose-invert`), and typography wrappers are applied uniformly.
   - Deterministically trigger Mermaid diagram re-rendering and icon creation (`safeCreateIcons()`) upon session load.
2. **Defensive Formatting & Fallback (`src/web/static/modules/utils/formatters.js`)**:
   - Provide a safe, synchronous markdown rendering fallback if library scripts load asynchronously or if messages contain escaped markdown characters.
3. **Automated Verification**:
   - Add Vitest unit tests in `tests/unit/frontend/formatters.test.js` validating historical message formatting.
   - Add Playwright e2e test in `tests/e2e/smoke.spec.js` testing switching to a historical session and verifying rendered HTML DOM elements (`<pre><code>`, `<strong>`, `<table>`).

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-MD-001]: Historical chat messages loaded via `/api/sessions/{id}/messages` render formatted markdown (headers, bold text, lists, tables).
- [x] [REQ-MD-002]: Fenced code blocks (` ```python `) in past sessions render with syntax styling and dark-theme containers.
- [x] [REQ-MD-003]: Mermaid diagrams in past sessions render interactive SVGs with zoom/inspector triggers.
- [x] [REQ-MD-004]: Tool execution badges and delegation cards in past sessions render styled accordions.
- [x] Automated Vitest unit tests pass cleanly via `npm run test:unit:frontend`.
- [x] Playwright smoke test passes cleanly via `npm run test:smoke`.
- [x] Zero linting errors via `npm run lint:frontend` and `ruff check .`.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing passing tests.
- Maintain high-performance rendering (avoid blocking UI loop when loading long conversation histories).
