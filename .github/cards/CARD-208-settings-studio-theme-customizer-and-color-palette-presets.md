# [CARD-208] Settings Studio Theme Customizer and Color Palette Presets

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:feature`, `domain:settings`, `domain:ui`, `domain:themes`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Prebuilt Themes in Settings Studio**:
   - Inside Settings Studio, users should see an **Appearance & Color Themes** section with instant one-click presets:
     - **AutoReiv Indigo** (Default high-tech indigo / slate navy)
     - **Orbital Monochrome** (Deep jet black with silver/white accents, inspired by spaceflight interfaces)
     - **Obsidian Slate** (Deep graphite with muted amethyst accents, inspired by dark note vaults)
     - **Amber Phosphor** (Warm retro terminal amber accents on deep bronze)
     - **Emerald Matrix** (Deep cyber forest green on pitch black)
2. **Custom Color Slider Palette**:
   - Beside or beneath the presets, users get a custom color tuner:
     - **Accent Hue Slider** (0° to 360° color wheel)
     - **Accent Saturation Slider** (Vibrancy from sleek grayscale to vibrant neon)
     - **Background Tone Slider** (From pitch pure black `#000000` up to slate midnight `#0f172a`)
   - A live preview box showing how buttons, window borders, and active tabs look.
   - An **Apply & Save Theme** button that locks in the custom palette across the whole app.
3. **Persistent Application Theme**:
   - The chosen theme (preset or custom) saves instantly to browser local storage (`autoreiv.theme.v1`).
   - When reloading AutoReiv or opening new desktop windows, the colors stay active across the desktop dock, window borders, buttons, headers, and badges.

---

### Beat 2: What AutoReiv Does Now
1. **Hardcoded Color Theme**:
   - In `src/web/templates/index.html` (lines 45-69), Tailwind and CSS hardcode brand colors:
     `brand.500: #6366f1`, `brand.600: #4f46e5`, background `#020617` / `#0f172a`.
2. **No Theme Controls in Settings Studio**:
   - Settings Studio (`#view-settings`) has sections for Updates, Providers, Remote Hosts, Storage, and Danger Zone, but no visual theme or appearance settings.
3. **CSS Variables Not Centrally Mapped for Realtime Swapping**:
   - Many elements use Tailwind classes like `bg-brand-600` or `border-brand-500` without root CSS custom property abstractions (`--theme-brand`, `--theme-bg`, `--theme-border`).

---

### Beat 3: What Will Change
1. **Theme CSS Custom Property Foundation**:
   - In `src/web/templates/index.html`, define root CSS custom variables:
     - `--theme-brand`: Primary brand accent color (used on active tabs, primary buttons, focus borders, glow shadows).
     - `--theme-brand-hover`: Darker/lighter state for hover transitions.
     - `--theme-bg-base`: Core background tone (desktop stage, window bodies).
     - `--theme-bg-surface`: Elevated card and container background.
     - `--theme-border`: Window chrome and card border highlight color.
   - Map Tailwind brand colors and key desktop styles to reference these CSS variables dynamically.
2. **Settings Studio Theme Section**:
   - In `src/web/templates/index.html`, add an **Appearance & Color Themes** card in Settings Studio (`#settingsThemeCard`).
   - Render selectable preset chips with swatch previews (AutoReiv Indigo, Orbital Monochrome, Obsidian Slate, Amber Phosphor, Emerald Matrix).
   - Render interactive sliders (Accent Hue `0-360`, Saturation `0-100%`, Darkness `0-100%`) with live color preview swatches.
   - Include **Save Theme** and **Reset to Default** buttons.
3. **Theme Engine Module (`src/web/static/modules/ui/theme-engine.js`)**:
   - Manages preset palettes, calculates HSL/HEX color values dynamically from slider input, applies CSS variables to `:root`, and persists configuration in `localStorage` (`autoreiv.theme.v1`).
   - Initializes on page boot so saved theme applies immediately before layout render.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1 (Prebuilt Presets)**:
  - Settings Studio displays at least 5 presets: AutoReiv Indigo, Orbital Monochrome, Obsidian Slate, Amber Phosphor, Emerald Matrix.
  - Clicking any preset immediately updates application accent colors, window borders, active buttons, and dock highlights.
- [x] **AC-2 (Slider-Style Custom Palette)**:
  - Users can adjust Accent Hue, Saturation, and Background Tone using smooth sliders.
  - A live swatch preview updates dynamically as sliders are moved.
  - Clicking "Save Theme" saves the custom color palette.
- [x] **AC-3 (Persistence Across Sessions & Windows)**:
  - Saved theme persists in browser storage (`localStorage['autoreiv.theme.v1']`).
  - Refreshing the browser or launching new desktop windows applies the saved theme instantly without flickering.
  - "Reset to Default" restores original AutoReiv Indigo.
- [x] **AC-4 (Automated Tests)**:
  - Unit tests verify theme preset values, HSL calculation, and localStorage persistence.
  - Smoke tests verify Settings Studio theme controls apply CSS variables correctly.
  - Full preflight passes cleanly: `python .agents/skills/rtm-sync/scripts/preflight.py`.

---

## 3. Constraints & Invariants
- Follows "How we walk cards with Jacob" in `AGENTS.md`.
- No third-party product names in card titles, code, or UI elements.
- Local `qa` branch workflow. Zero push, tag, or merge to `main`.
