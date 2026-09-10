# [CARD-209] Deep Desktop and Studio Theme Skinning

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:feature`, `domain:settings`, `domain:ui`, `domain:themes`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Substantial Visual Theme Changes**:
   - Choosing a theme (like Amber CRT, Emerald Matrix, Orbital Monochrome, or Obsidian) should dramatically transform the entire desktop and window experience, not just tint the outer window borders.
2. **Key Surfaces That Must Change With The Theme**:
   - **Desktop Wallpaper Stage**: The background glowing aura and gradients should match the active theme's accent color and background tone, instead of staying locked in the default indigo/blue cosmic gradient.
   - **Window Frames & Titlebars**: Window titlebars, title icons, and window backgrounds should reflect the chosen theme colors and darkness.
   - **Studio Cards & Content Panels**: Inside Settings, Observability, Routines, Chat, etc., the dark panels (currently hardcoded Tailwind slate-900 navy) should adopt the theme's background surface tone and border color.
   - **Action Buttons & Badges**: Primary buttons (e.g. "Check for Updates", "Save Settings", "Refresh Metrics") and active pills should switch to the theme's brand color.
   - **Key Metrics & Accent Text**: Highlighted metrics (e.g. Observability KPI counts, section headers, active labels) should glow with the theme's accent color.
3. **Contrast & Readability Preserved**:
   - Text remains high contrast (bright off-white / silver) so readability is never degraded.

---

### Beat 2: What AutoReiv Does Now
1. **Shallow Border-Only Theme Application**:
   - CARD-208 created `--theme-brand`, `--theme-bg-base`, `--theme-bg-surface`, and `--theme-border`, but only applied them to the outer `.desktop-window` border and box-shadow, and active dock buttons.
2. **Hardcoded Wallpaper**:
   - `#desktopStage .desktop-wallpaper` in `src/web/templates/index.html` (lines 260-268) hardcodes indigo (`rgba(79, 70, 229, 0.28)`), cyan (`rgba(14, 165, 233, 0.12)`), and purple radial glows with `#0b1224` dark navy base.
3. **Hardcoded Studio Cards and Buttons**:
   - Studio content inside hosted windows uses hardcoded Tailwind classes (`bg-slate-900`, `bg-slate-950`, `border-slate-800`, `bg-indigo-600`, `text-indigo-400`, `text-blue-400`). When Amber CRT is selected, only the window border turns amber, while the internal cards, buttons, and wallpaper remain slate navy/indigo.

---

### Beat 3: What Will Change
1. **Dynamic Wallpaper Theming**:
   - Update `.desktop-wallpaper` in `src/web/templates/index.html` to reference `var(--theme-brand-glow)`, `var(--theme-brand)`, `var(--theme-bg-surface)`, and `var(--theme-bg-base)`, allowing the desktop backdrop to organically match the selected palette.
2. **Deep Studio Surface & Panel Skinning**:
   - Scope desktop theme rules so interior studio panels (`.bg-slate-900`, `.bg-slate-950`, `.card-nested`) inherit `background-color: var(--theme-bg-surface)` and `border-color: var(--theme-border)`.
3. **Primary Action Buttons & Interactive Accents**:
   - Scope primary studio buttons (`button.bg-indigo-600`, `button.bg-blue-600`, `.btn-primary`) to use `background-color: var(--theme-brand)` with `hover: var(--theme-brand-hover)`.
   - Map key KPI highlights (`.text-indigo-400`, `.text-blue-400`) and window title icons (`.desktop-win-icon`) to `var(--theme-brand)`.
4. **Rich Preset Palette Color Tuning**:
   - Enhance preset color definitions in `src/web/static/modules/ui/theme-engine.js`:
     - **Amber CRT**: Deep warm bronze base (`#0a0804`), dark bronze-slate surfaces (`#18120a`), warm amber brand (`#f59e0b`).
     - **Emerald Matrix**: Deep cyber forest base (`#020b06`), dark forest surfaces (`#08190e`), neon emerald brand (`#10b981`).
     - **Orbital Monochrome**: Pure jet black base (`#000000`), stealth graphite surfaces (`#111115`), crisp silver/white brand (`#f8fafc`).
     - **Obsidian Slate**: Midnight amethyst base (`#090814`), dark violet-slate surfaces (`#131124`), amethyst purple brand (`#a855f7`).
     - **AutoReiv Indigo**: Signature electric violet/cyan and slate navy.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Wallpaper Aura)**: Changing themes dynamically updates the desktop wallpaper radial glow and background tone to match the active theme.
- [x] **AC-2 (Studio Surface & Card Skinning)**: Panels and cards inside hosted windows (Settings, Observability, Routines, Chat) dynamically adopt the theme's surface color and border color.
- [x] **AC-3 (Action Buttons & Accent Text)**: Studio primary buttons and KPI metrics dynamically adopt the theme's brand color.
- [x] **AC-4 (High Contrast Invariant)**: Text remains crisp, readable, and high-contrast across all prebuilt palettes and custom slider settings.
- [x] **AC-5 (Automated Test Proof)**: Unit and Playwright smoke tests assert dynamic wallpaper and studio card theme application.

