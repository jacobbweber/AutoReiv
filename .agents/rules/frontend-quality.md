# Rule: Frontend Quality Constitution (AutoReiv Web SPA)

This document establishes the frontend engineering standards, architectural boundaries, defensive DOM practices, and verification gates for the AutoReiv Web SPA interface.

---

## 1. Hard Invariants for Frontend

1. **No Unanchored Code**: No new feature or bugfix in `src/web/static/app.js`, `src/web/static/modules/`, or `src/web/templates/index.html` without an active GitHub Issue or `.github/cards/CARD-xxx.md` work card.
2. **Pure Logic Extraction**: Prefer extracting pure logic (calculators, date/token formatters, state reducers, physics helpers, frontmatter parsers) out of DOM code so it can be unit-tested in isolation without DOM mocks.
3. **Control Integrity Contract**: Every interactive control must have:
   - A stable `id` or `data-testid`.
   - Null-safe DOM access (never assume element existence).
   - Event listeners registered inside an isolated try/catch module initializer.
4. **Zero-Error Page Load**: Never introduce a page-load-breaking `ReferenceError` or `TypeError`. The automated Playwright smoke test must pass (zero console errors, zero unhandled rejections, main tabs rendered).
5. **Zero-Build Native ES Modules**: Preserve the zero-build/light-build philosophy unless an ADR and card explicitly sanction a change. Use native browser ES modules (`<script type="module">`).

---

## 2. Architecture & Modular Boundaries

```text
src/web/static/
├── app.js                   # Central orchestrator (initApp with isolated try/catches)
├── modules/
│   ├── dom.js               # Defensive DOM query & event helpers ($ helper with warnings)
│   ├── services/            # API clients, SSE stream consumers, fetch wrappers
│   ├── state/               # In-memory UI reactive state & active selections
│   ├── utils/               # Pure tested helpers (debounce, formatters, physics)
│   └── studios/             # Studio controllers (one module per studio/tab)
│       ├── chat.js          # Chat Studio, streaming, model picker
│       ├── wiki.js          # Wiki Studio, markdown renderer, mind-map graph
│       ├── forge.js         # Agent Forge, prompt builder, skill binder
│       ├── settings.js      # Settings Studio, LLM providers, model matrix
│       ├── observability.js # Event stream, KPI metrics, trace viewer
│       ├── docs.js          # Architecture docs & Mermaid pan-zoom inspector
│       └── routines.js      # Routine automation, cron schedule management
```

### Module Isolation Pattern
Each studio or subsystem must export an `initXxx()` lifecycle method. The central `app.js` executes each initializer in an isolated `try/catch` block:

```javascript
// Central Orchestrator Pattern in app.js
export function initApp() {
  const modules = [
    { name: 'DOM & Theme', init: initTheme },
    { name: 'Chat Studio', init: initChatStudio },
    { name: 'Wiki Studio', init: initWikiStudio },
    { name: 'Agent Forge', init: initAgentForge },
    { name: 'Settings Studio', init: initSettingsStudio },
    { name: 'Observability', init: initObservability },
    { name: 'Docs Studio', init: initDocsStudio },
    { name: 'Routines Studio', init: initRoutinesStudio }
  ];

  modules.forEach(mod => {
    try {
      mod.init();
    } catch (err) {
      console.error(`[AutoReiv UI] Failed to initialize ${mod.name}:`, err);
    }
  });
}
```

---

## 3. Defensive DOM Access & Helper Standards

Always use defensive helpers to prevent unhandled `null` or `undefined` dereferences:

```javascript
export function $(id) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[AutoReiv UI] Element #${id} not found in DOM.`);
  }
  return el;
}

export function $query(selector, parent = document) {
  return parent.querySelector(selector);
}

export function $queryAll(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}
```

---

## 4. Frontend Definition of Done (DoD) Gate

Before declaring any frontend card complete:
1. [ ] **Unit Tests (Vitest)**: All newly created or modified pure utility functions have passing unit tests.
2. [ ] **Playwright Smoke Test**: The Playwright test suite passes cleanly:
   - Initial application page loads successfully.
   - Zero console errors and zero uncaught exceptions in browser logs.
   - All core navigation tabs and studio containers are present in DOM.
3. [ ] **No Monolithic Pollution**: No large unbounded blocks appended to global scope; code is cleanly placed into appropriate ES modules.
4. [ ] **Human QA Runbook**: A concise step-by-step verification procedure (executable in < 2 minutes) included in the PR description.

---

## 5. Forbidden Anti-Patterns

- ❌ Attaching monolithic inline event handlers (`onclick="..."`) in HTML strings for new features (prefer module-bound listeners or event delegation).
- ❌ Unguarded direct DOM manipulation without null verification.
- ❌ Silent `catch (e) {}` blocks that mask UI breakage.
- ❌ Duplicating HTTP API call logic across multiple studio scripts.
- ❌ Adding heavy build frameworks (React, Vue, Webpack) without an approved Architecture Decision Record (ADR).
