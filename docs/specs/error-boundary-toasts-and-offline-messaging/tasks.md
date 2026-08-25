# Task Breakdown: Error Boundary Toasts & Offline Backend Messaging

> **Spec Status**: Implemented  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-040](file:///.github/cards/CARD-040-error-boundary-toasts-and-offline-backend-messaging.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/error-boundary-toasts-and-offline-messaging/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/error-boundary-toasts-and-offline-messaging/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Pure Toast Module & Unit Testing
- [x] **Task 1.1**: Author `src/web/static/modules/ui/toast.js` with `showToast`, `dismissToast`, and `initConnectivityMonitor` (`[REQ-TOAST-001]`, `[REQ-TOAST-003]`).
- [x] **Task 1.2**: Author unit test suite `tests/unit/frontend/toast.test.js` verifying toast queuing, ARIA roles, timeout auto-dismissal, and offline banner state (`[REQ-TOAST-004]`).

### Slice 2: HTML Integration & Studio Alert Migration
- [x] **Task 2.1**: Update `src/web/templates/index.html` with `#toastContainer` and `#offlineBanner` (`[REQ-TOAST-001]`, `[REQ-TOAST-003]`).
- [x] **Task 2.2**: Migrate all browser `alert()` invocations across `wiki.js`, `forge.js`, `routines.js`, `settings.js` to `showToast()` (`[REQ-TOAST-002]`).
- [x] **Task 2.3**: Wire `initConnectivityMonitor` into `src/web/static/app.js` (`[REQ-TOAST-003]`).

### Slice 3: Verification, Pre-Flight & Gate Closure
- [x] **Task 3.1**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-TOAST-004]`).
- [x] **Task 3.2**: Author ADR-0040 and sync `docs/rtm.json` with `[REQ-TOAST-001]` through `[REQ-TOAST-004]`.
- [x] **Task 3.3**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

