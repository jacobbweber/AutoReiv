# [CARD-342] Mobile Chat Sessions Drawer Button Portrait Visibility

> **Status**: Done
> **Created**: 2026-09-16
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:chat`, `domain:ui`, `domain:mobile`

---

## 1. Why / Intent

In Chat Studio, switching sessions or creating a new conversation relies on the in-studio Sessions drawer (`#chatSessionsDrawer`, introduced in CARD-296). On desktop and in horizontal (landscape) mobile view, operators click the panel toggle button (`#toggleSidebarBtn`) in the Chat top bar to open this drawer.

However, `#toggleSidebarBtn` is currently styled with `class="hidden md:flex"`. On mobile devices held in vertical portrait orientation (viewport width `< 768px`), the button is completely hidden. The operator cannot access past sessions or start a new chat without rotating the phone into landscape mode.

### The Three Beats
1. **What Jacob means**: On mobile, the chat sessions pop-out drawer button (`#toggleSidebarBtn`) must be visible and tap-friendly in standard vertical portrait view, not only in horizontal landscape orientation.
2. **What AutoReiv does now**:
   - `src/web/templates/index.html`: `#toggleSidebarBtn` has `class="hidden md:flex ..."`, hiding it on all screens smaller than 768px.
   - When rotated to landscape (width $\ge$ 768px), the button becomes visible.
   - In portrait view, mobile operators have no visible button in Chat Studio to toggle `#chatSessionsDrawer`.
3. **What will change**:
   - `src/web/templates/index.html`: Update `#toggleSidebarBtn` to `flex items-center ...` (removing `hidden md:flex`), ensuring the button is always visible on both mobile portrait and desktop.
   - Ensure touch-friendly tap targets (`min-h-[36px] min-w-[36px]`) and preserve responsive spacing with `#agentSelect` and action buttons so the header does not wrap or overflow on narrow screens (360px–390px).
   - Add frontend unit / DOM test asserting `#toggleSidebarBtn` is not hidden on small viewports.

---

## 2. What to Build

### 1. Chat Header Markup
- In `src/web/templates/index.html`:
  - Locate `#toggleSidebarBtn` in the Chat top bar (`#view-chat`).
  - Replace `hidden md:flex` with `flex` (styled with consistent touch target and padding).
  - Ensure title and aria-label clearly indicate "Toggle Chat sessions drawer".

### 2. Header Layout & Overflow Resilience
- Verify that on 360px portrait screens:
  - Left cluster (`#toggleSidebarBtn`, status dot, `#agentSelect`) and right cluster (`#workbenchToggleBtn`, `#exportThreadWikiBtn`, `#copyThreadBtn`) remain on a single clean row without text collision or vertical clipping.

### 3. Automated Verification
- In `tests/unit/frontend/`:
  - Add or update frontend tests in `chat_studio.test.js` or `responsive.test.js` asserting `#toggleSidebarBtn` does not contain `hidden` class and is present in DOM.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `#toggleSidebarBtn` is visible in both mobile portrait view (< 768px) and desktop view.
- [x] Tapping `#toggleSidebarBtn` in portrait view smoothly opens `#chatSessionsDrawer`.
- [x] Tapping the close button or selecting an existing session / new chat closes the drawer cleanly.
- [x] Top bar elements do not collide, overflow, or wrap unexpectedly on 360px-wide viewports.
- [x] Frontend tests pass (`npm run test:unit:frontend`).
- [x] Live verification on mobile/narrow viewport confirms drawer opens and closes without rotating the phone.

---

## 4. Constraints & Honor Flags

- Zero remote push (`git push` strictly forbidden).
- Isolated branch `feat/CARD-342-mobile-chat-sessions-drawer-button-portrait-visibility` cut from `qa`.
- Single active card rule honored.
