# ADR-0040: Error Boundary Toasts and Offline Connectivity Architecture

## Context and Problem Statement
Prior to this work, asynchronous errors, validation failures, and mutation confirmations across the 7 AutoReiv studios relied on blocking native browser `alert()` dialogs. Furthermore, when the FastAPI backend or network connection was disrupted, the SPA provided no proactive user notification or automated recovery detection.

## Decision Drivers
- **Non-Blocking User Experience**: Replace all modal `alert()` popups with lightweight, accessible toast notifications.
- **Accessibility & ARIA Standards**: Toasts must use `role="status"` and `aria-live="polite"` for non-critical updates, and `role="alert"` / `aria-live="assertive"` for errors.
- **Proactive Offline & Reconnection Detection**: Poll `/api/health` in the background to show a top-level banner upon disconnect and trigger reconnection toasts when connectivity is restored.

## Considered Options
1. **Option 1**: Introduce an external toast library (e.g. Toastify, Sonner).
2. **Option 2 (Accepted)**: Author a pure, zero-dependency toast and connectivity monitor module (`src/web/static/modules/ui/toast.js`).

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- 100% elimination of blocking `alert()` popups across the entire codebase.
- Accessible, non-blocking toast notifications with auto-dismiss timers and manual close buttons.
- Proactive offline connectivity banner and automatic recovery notifications.
- 6 new Vitest unit tests in `tests/unit/frontend/toast.test.js`.

### Negative Consequences / Trade-offs
- Requires background health check polling (every 20s).
