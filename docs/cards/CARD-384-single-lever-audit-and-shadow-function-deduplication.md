---
id: CARD-384
title: "Single Lever Audit and Shadow Function Deduplication"
status: In Review
created: 2026-09-20
adr: none
labels:
  - type:refactor
  - domain:frontend
  - domain:web
  - clean-up
---

# [CARD-384] Single Lever Audit and Shadow Function Deduplication

> **Status**: In Review  
> **Created**: 2026-09-20  
> **Labels**: `type:refactor`, `domain:frontend`, `domain:web`, `clean-up`  
> **Branch**: `feat/card-384-single-lever-shadow-function-dedup` off `qa`  
> **Reply to build**: **build** or **build CARD-384**  

---

## 1. The Four Beats

### Beat 1: What Jacob Means
Deduplicate common utilities and eliminate shadow functions across the AutoReiv web frontend and backend routers. Ensure every utility operation (HTML escaping, mobile viewport detection, toast notifications, clipboard copying, and data directory path resolution) has **exactly one canonical implementation** rather than redundant copy-pasted helpers or ad-hoc wrappers scattered across studio files.

### Beat 2: What AutoReiv Does Now
1. **HTML Escaping**:
   - `src/web/static/modules/utils/formatters.js` exports canonical `escapeHtml` (re-exported by `dom.js`).
   - `src/web/static/modules/ui/agent-desktop.js` defines a local shadow function `escapeHtmlLite` (lines 1748-1753) and `escapeAttr` (lines 1755-1757).
   - `src/web/static/modules/studios/projects.js` defines another local shadow function `escapeHtml` (lines 88-94).
2. **Mobile Viewport Detection**:
   - `agent-desktop.js` (line 563) and `prompts.js` (line 37) declare local duplicate `isMobile()` functions returning `window.innerWidth < 768`.
   - `app.js`, `chat.js`, `wiki.js`, `skills.js`, and `projects.js` directly open-code `window.innerWidth < 768` in 11 separate places.
3. **Toast Notifications**:
   - `src/web/static/modules/ui/toast.js` exports canonical `showToast`.
   - `factory.js` creates a wrapper `function showToast(msg, type = 'info')` around `callbacks.showToast`, while `skills.js` and `projects.js` define `const toast = callbacks.showToast || (() => {})`.
4. **Clipboard Copying**:
   - `src/web/static/modules/utils/clipboard.js` exports `copyToClipboard` with fallback for non-secure contexts.
   - `factory.js`, `forge.js`, `projects.js`, and `wiki.js` call raw `navigator.clipboard.writeText` without fallback.
5. **Data Directory Resolution in Backend**:
   - `src/web/routers/settings.py` (line 69) and `src/web/routers/data_dir_migrate.py` (line 21) define identical duplicate `_data_dir_paths(request: Request)` functions.

### Beat 3: What Will Change
1. **Single Canonical HTML Escaping**:
   - Update `agent-desktop.js` and `projects.js` to import canonical `escapeHtml` from `../dom.js` (and prune `escapeHtmlLite` and local `escapeHtml`).
2. **Single Canonical `isMobile` Viewport Helper**:
   - Export `isMobile()` from `src/web/static/modules/dom.js` (`typeof window !== 'undefined' && window.innerWidth < 768`).
   - Import and use `isMobile` in `agent-desktop.js`, `prompts.js`, `app.js`, `chat.js`, `wiki.js`, `skills.js`, and `projects.js`.
3. **Single Canonical Toast Notification Lever**:
   - Unify `factory.js`, `skills.js`, and `projects.js` to import and use canonical `showToast` from `../ui/toast.js` (falling back to injected callback if specified).
4. **Single Canonical Clipboard Copy**:
   - Unify clipboard copying in `factory.js`, `forge.js`, `projects.js`, and `wiki.js` to import and use `copyToClipboard` from `../utils/clipboard.js`.
5. **Single Canonical Data Directory Helper**:
   - Consolidate `_data_dir_paths` into a single shared helper in `src/web/routers/common.py` or re-export from `settings.py`.
6. **Regression Sentinel Test**:
   - Author `tests/unit/frontend/single_lever_dedup_384.test.js` to assert that no shadow functions (`escapeHtmlLite`, local duplicate `isMobile`) remain in studio modules.

### Beat 4: What Dies Today (The Prune List)
1. `escapeHtmlLite` in `src/web/static/modules/ui/agent-desktop.js` (lines 1748-1753).
2. Duplicate `escapeHtml` in `src/web/static/modules/studios/projects.js` (lines 88-94).
3. Local duplicate `isMobile()` in `src/web/static/modules/ui/agent-desktop.js` (lines 563-565).
4. Local duplicate `isMobile()` in `src/web/static/modules/studios/prompts.js` (lines 37-39).
5. Open-coded `window.innerWidth < 768` scattered across `app.js`, `chat.js`, `wiki.js`, `skills.js`, and `projects.js`.
6. Open-coded raw `navigator.clipboard.writeText` in `factory.js`, `forge.js`, `projects.js`, and `wiki.js`.
7. Duplicate `_data_dir_paths` in `src/web/routers/data_dir_migrate.py`.

---

## 2. Acceptance Criteria (EARS)

- [x] **[REQ-384-001] (Canonical HTML Escaping)**: THE FRONTEND SHALL use canonical `escapeHtml` from `dom.js` everywhere, with zero shadow functions (`escapeHtmlLite` or local `escapeHtml` in `projects.js`).
- [x] **[REQ-384-002] (Canonical Viewport Invariant)**: THE FRONTEND SHALL export `isMobile()` from `dom.js` and use it for all 768px viewport checks across desktop and studio modules.
- [x] **[REQ-384-003] (Canonical Toast Notifications)**: THE FRONTEND SHALL import and invoke canonical `showToast` from `toast.js` across all studio modules without silent-failure wrapper stubs.
- [x] **[REQ-384-004] (Canonical Clipboard Invariant)**: THE FRONTEND SHALL use `copyToClipboard()` from `utils/clipboard.js` for all copy interactions, providing safe fallback on non-secure contexts.
- [x] **[REQ-384-005] (Single Data Directory Resolution)**: THE BACKEND SHALL share a single canonical `_data_dir_paths` resolver between `settings.py` and `data_dir_migrate.py`.
- [x] **[REQ-384-006] (Negative Assertion Regression Guard)**: Automated tests SHALL verify that no shadow `escapeHtmlLite`, local duplicate `isMobile`, or unhandled `navigator.clipboard` calls exist in the audited modules.
- [x] **[REQ-384-007] (Zero Regression)**: All existing 593 vitest tests, 1,777 pytest tests, and Playwright smoke tests SHALL pass.

---

## 3. Constraints & Verification Plan

- Isolated feature branch: `feat/card-384-single-lever-shadow-function-dedup` cut from `qa`.
- Subtractive engineering: prune duplicate functions and open-coded fragments.
- Pass `npm run preflight` before In Review.
