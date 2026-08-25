# Technical Design: Defensive DOM Query & Null-Safety Audit Across All Studio Interfaces

> **Spec Status**: In Review  
> **Card Reference**: [CARD-033](file:///.github/cards/CARD-033-defensive-dom-query-and-null-safety-audit-across-all-studio-interfaces.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/defensive-dom-null-safety-audit/requirements.md)

---

## 1. Architectural Strategy & Safety Patterns

### Defensive Query & Event Architecture
```mermaid
flowchart TD
    A[Studio Modules (chat, wiki, etc.)] --> B[dom.js]
    B --> C["$(id) -> document.getElementById"]
    B --> D["$query(selector, root) -> root.querySelector"]
    B --> E["$queryAll(selector, root) -> Array.from(root.querySelectorAll)"]
    B --> F["$on(target, event, handler) -> target?.addEventListener(...)"]
    B --> G["safeCreateIcons(root) -> window.lucide?.createIcons()"]
```

---

## 2. API Contract & Helper Additions in `dom.js`

```javascript
/**
 * Defensive DOM query and event binding helpers.
 */

export function $(id) {
  if (typeof document === 'undefined') return null;
  return document.getElementById(id);
}

export function $query(selector, root = document) {
  if (!root || typeof root.querySelector !== 'function') return null;
  return root.querySelector(selector);
}

export function $queryAll(selector, root = document) {
  if (!root || typeof root.querySelectorAll !== 'function') return [];
  return Array.from(root.querySelectorAll(selector));
}

export function $on(targetOrId, event, handler, options) {
  const target = typeof targetOrId === 'string' ? $(targetOrId) : targetOrId;
  if (!target || typeof target.addEventListener !== 'function') return false;
  target.addEventListener(event, handler, options);
  return true;
}

export function safeCreateIcons(root) {
  if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons(root ? { root } : undefined);
  }
}
```

---

## 3. Automated Static Linting Test (`tests/unit/frontend/dom_audit.test.js`)
- Uses Node `fs` and `path` inside Vitest to scan all `.js` files in `src/web/static/modules/` (excluding `dom.js`).
- Regex checks for forbidden patterns:
  - `document.getElementById` (outside `dom.js`)
  - `document.querySelector` (outside `dom.js`)
  - `document.querySelectorAll` (outside `dom.js`)
- Reports offending file paths and line numbers upon assertion failure.
