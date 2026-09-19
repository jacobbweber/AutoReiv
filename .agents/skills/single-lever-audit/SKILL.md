---
name: single-lever-audit
description: >-
  Audits UI controls, event listeners, API endpoints, and service functions for duplicate paths or shadow functions. Use to enforce the Single Lever Invariant and eliminate technical debt.
---

# Single Lever Audit (Anti-Duplication & Shadow Path Elimination)

> **For Jacob (Plain Language)**: When you click a button or trigger an action in AutoReiv, there should be exactly **one** canonical code path that handles it. If there are two different buttons, two competing event listeners, or two duplicate functions doing the same job in slightly different ways, the app will eventually behave unpredictably. This audit finds duplicate levers and shadow functions so we can delete them.

---

## When to Run This Audit

- After adding or refactoring UI controls, modal actions, or API routes.
- When an action seems to fire twice, or when changing a setting in one place fails to update another.
- Whenever Jacob asks: _"Run single lever audit on `<studio/feature>`"_.

---

## The 4 Audit Vectors

### 1. UI Event Listeners (Duplicate DOM Triggers)

Inspect the targeted studio's JavaScript module for multiple `$on` or `addEventListener` bindings on the same DOM element or user action:

```bash
git grep -n "\$on(" src/web/static/modules/studios/<studio>.js
git grep -n "addEventListener" src/web/static/modules/studios/<studio>.js
```

**Invariant**: Exactly one listener per operator job. Never attach event listeners inside rendering loops.

### 2. API Routes (Duplicate Endpoints for One Job)

Inspect `src/web/routers/` and `src/web/app.py` for competing REST endpoints that mutate the same underlying entity:

```bash
git grep -n "@router\.\(post\|put\|patch\)" src/web/routers/
```

**Invariant**: Exactly one mutating endpoint per state transition. If a new endpoint is introduced, retire and prune the old one immediately.

### 3. Shadow Functions (Duplicate Logic)

Search for functions with similar names or purposes across frontend modules and backend services:

```bash
# Example: searching for redundant message-render or agent-fetch functions
git grep -n "function renderMessage" src/web/static/
git grep -n "def update_agent" src/
```

**Invariant**: No shadow functions. If a function is superseded, all callers must be migrated to the canonical function and the old function must be deleted.

### 4. Single Source of State (No Parallel Stores)

Inspect state management in `src/web/static/modules/state/store.js` vs studio local state:

- Shared domain data (agents, active session, models, system status) belongs **only** in `state/store.js`.
- Ephemeral UI state (e.g. dropdown open/closed, current input text) belongs in the local studio instance.
- Never mirror shared state into module-level global variables.

---

## Executing the Prune List (Beat 4)

When duplicate paths are discovered:

1. Declare the **Prune List** in plain English.
2. Re-route any remaining callers to the canonical single lever.
3. Delete the duplicate code, unused DOM IDs, and dead CSS rules.
4. Run `npm run lint:frontend` and `ruff check .` to guarantee zero orphaned references.
