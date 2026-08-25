# Requirements Specification: Error Boundary Toasts & Offline Backend Messaging

> **Spec Status**: Approved  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-040](file:///.github/cards/CARD-040-error-boundary-toasts-and-offline-backend-messaging.md)  

> **Primary Component**: AutoReiv Web SPA UI & Toast Subsystem (`src/web/static/modules/ui/toast.js`, `src/web/static/app.js`, `src/web/templates/index.html`)

---

## 1. Executive Summary & Intent

**CARD-040** replaces intrusive browser `alert()` popups with a modern, non-blocking toast notification subsystem (`info`, `success`, `warning`, `error`) and adds proactive degraded/offline backend connectivity detection with automatic recovery messaging.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-TOAST-001] Accessible Toast Notification Subsystem
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide a centralized toast notification module (`showToast(message, type, duration)`) supporting `info`, `success`, `warning`, and `error` variants with proper ARIA attributes (`role="status"`, `aria-live="polite"` for non-errors; `role="alert"`, `aria-live="assertive"` for errors).

### [REQ-TOAST-002] Alert Migration & Studio Error Boundaries
- **EARS Pattern**: Event-Driven
- **Requirement**: When studio operations (saving agents, executing routines, creating wiki notes, fetching providers) succeed or encounter API errors, the system **shall** display an accessible toast message instead of browser `alert()`.

### [REQ-TOAST-003] Offline & Degraded Backend Connectivity Banner
- **EARS Pattern**: State-Driven
- **Requirement**: While the backend server is unreachable or returning persistent 502/503 errors, the system **shall** display a top-level offline status banner, and **shall** automatically dismiss the banner and show a reconnection toast when connectivity is restored.

### [REQ-TOAST-004] Toast Subsystem Unit & Smoke Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `npm run test:unit:frontend` and `npm run test:smoke`, the test runners **shall** verify toast queuing, timeout auto-dismissal, manual dismissal, ARIA live region announcements, and banner rendering with 100% green status.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: Calling `showToast('Saved', 'success')` renders a themed toast that auto-dismisses after duration.
- [ ] `AC-2`: All remaining browser `alert()` invocations across studios are replaced with `showToast()`.
- [ ] `AC-3`: Offline network banner appears when health check fails and clears on reconnect.
- [ ] `AC-4`: `npm run preflight` passes all 6 quality gates cleanly.
