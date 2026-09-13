# [CARD-235] Chat Composer Hit-Testing (Enable / Options Clicks)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: P0 Chat Studio hit-testing bug (Jacob screenshot); leftover CARD-215 goal theatre markup
> **Labels**: type:bug, AutoReiv.Chat, AutoReiv.UI, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. In Chat Studio the orange **Enable** pill, gray **x**, and **+ Options** look present but do not receive clicks.
2. Suspected dock / transparent overlay (`z-index` / `pointer-events`) covering the composer above the bottom nav.
3. Thin fix only — no new Studio, no Chat redesign.

### Beat 2: What AutoReiv Does Now
1. CARD-215 retired Goal theatre in JS but left orphan Enable/dismiss markup plus a stray `</div>` in `index.html`.
2. That stray close ends the composer `pointer-events-auto` wrapper early, stranding `#chatOptionsToggleBtn` under `#chatInputWrapper.pointer-events-none`.
3. Enable/x have no click handlers (theatre removed) but remain visible — look clickable, do nothing.
4. Maximized window south resize handles sit above hosted views and can steal bottom-edge clicks.

### Beat 3: What Will Change
1. Remove orphan Enable/dismiss markup; restore PE-auto nesting so Options/Send receive clicks.
2. CSS: maximized resize handles `pointer-events: none`; composer controls explicitly `pointer-events: auto`.
3. Unit proof + CHANGELOG; feat branch only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-CHAT-HIT-001]**: Orphan Enable / dismiss suggestion controls removed from Chat composer markup and JS refs.
- [x] **[REQ-CHAT-HIT-002]**: `#chatOptionsToggleBtn` remains inside a `pointer-events-auto` ancestor under `#chatInputWrapper` (not stranded under PE-none).
- [x] **[REQ-CHAT-HIT-003]**: Maximized `.desktop-win-resize` does not capture pointer events over the composer.
- [x] **[REQ-CHAT-HIT-004]**: Vitest proof in `tests/unit/frontend/chat_composer_hit_testing.test.js`; CHANGELOG [Unreleased]; push `feat/*` only.

## 3. Constraints & Honor Flags

- Branch: `feat/chat-composer-hit-testing` off `grok`. Never touch qa/main.
- Anti-theatre: finish CARD-215 cleanup — do not revive Goal Enable theatre.
- Out of scope: new Studio, Chat redesign, dock visual redesign.

## 4. Modules Likely Touched

- `src/web/templates/index.html` (composer markup + thin CSS)
- `src/web/static/modules/studios/chat.js` (dead refs)
- `tests/unit/frontend/chat_composer_hit_testing.test.js` (new)
- `tests/unit/frontend/chat_modes.test.js` (assert Enable gone)
- `CHANGELOG.md`

## 5. Marathon Build Notes (Jarvis 2026-09-11 ET)

- Root cause: incomplete CARD-215 HTML edit left Enable/x + extra `</div>` closing `pointer-events-auto` early → Options under PE-none; Enable had no handlers.
- Fix: delete orphan block; PE-auto on `#chatForm`; maximized resize PE-none; composer z/PE hardening.
- Proof: `npm run test:unit:frontend -- tests/unit/frontend/chat_composer_hit_testing.test.js` (+ chat_modes retirement asserts).
- Status: **Done**. Push feat only.
