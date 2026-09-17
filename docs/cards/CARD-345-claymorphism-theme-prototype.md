# [CARD-345] Claymorphism Theme Prototype

> **Status**: Done
> **Created**: 2026-09-17
> **Spec Reference**: none
> **Labels**: `type:feature`, `domain:ui`, `domain:desktop`, `domain:theme`

---

## 1. Why / Intent

Jacob wants to experiment with a Claymorphism visual theme prototype in AutoReiv to evaluate its aesthetic appeal, tactile feel, and usability on the desktop environment without disrupting existing functionality.

### The Three Beats

1. **What Jacob means**:
   - A live, switchable prototype of a **Claymorphism** theme inspired by tactile 3D UI kits (smooth, inflated clay surfaces, high border radiuses, outer floating shadows, and compound inner bevel highlights).
   - It should apply to the key desktop chrome elements:
     - The **Bottom Dock** and launcher icons (chunky, pressable clay pads with tactile press effects).
     - **Desktop Window Chrome** (rounded titlebars, tactile window control buttons for minimize/maximize/close).
     - **Studio Buttons & Cards** (tactile 3D primary buttons and soft inset cards).
   - It should be safely selectable in **Settings Studio** under Appearance & Color Themes alongside existing presets (or reset back to Indigo/Default anytime) without breaking window physics, dragging, resizing, or existing unit tests.

2. **What AutoReiv does now**:
   - The UI uses enterprise flat/dark neutral surfaces (`#09090b` base, `#12141a` surface) with sharp 1px borders (`rgba(255, 255, 255, 0.08)`), flat window headers, and subtle 1D drop shadows.
   - `theme-engine.js` manages color variables (`--theme-brand`, `--theme-bg-base`, `--theme-bg-surface`, `--theme-border`) across 5 preset themes (Indigo, Slate Graphite, Violet, Warm Sand, Teal) plus custom HSL sliders.
   - All desktop dock buttons and window headers use hardcoded flat linear gradients or plain translucent fills.

3. **What will change**:
   - **Theme Engine Support (`theme-engine.js`)**:
     - Add a dedicated `claymorphism` preset (and theme attribute `data-theme="claymorphism"`) with tuned clay palette tokens (soft charcoal clay base with tactile coral/blue accents inspired by the reference design).
     - Wire the new Claymorphism preset into the Settings Studio appearance picker with a dedicated preview swatch.
   - **Claymorphism CSS Utility & Chrome Styles (`src/web/templates/index.html`)**:
     - Add scoped claymorphism rules activated when the clay theme is active (`[data-theme="claymorphism"]`):
       - **Dock Bar & Launcher Buttons**: Rounded 18px-20px pill shapes, soft ambient outer elevation, and top-left/bottom-right compound inner bevel shadows. On `:active`, a realistic tactile button-press depth shift.
       - **Desktop Windows**: Softened 18px corners, extruded clay perimeter bevel, and cushion-style titlebar with 3D tactile minimize/maximize/close buttons.
       - **Tactile Action Buttons**: Puffy 3D primary buttons that depress on click.
   - **Automated Tests**:
     - Unit tests verifying the Claymorphism theme preset exists in `PRESET_THEMES`, can be applied, updates CSS custom variables and theme attributes, and persists across storage.
     - Vitest and ESLint checks green.

---

## 2. What to Build

### 1. Theme Engine Preset & Attribute Binding (`src/web/static/modules/ui/theme-engine.js`)
- Add `'claymorphism'` preset configuration to `PRESET_THEMES` with characteristic clay surface tones and tactile brand accent.
- In `applyTheme(theme, rootEl)`, toggle `data-theme="claymorphism"` on `document.documentElement` when the claymorphism preset is selected, and remove it for standard flat presets.

### 2. Settings Studio Swatch (`src/web/templates/index.html`)
- Add a Claymorphism theme preset button to `#themePresetsList` in Settings Studio with a tactile pill swatch indicator.

### 3. Claymorphic Desktop Styles (`src/web/templates/index.html`)
- Add scoped CSS rules under `[data-theme="claymorphism"]`:
  - `.desktop-dock-bar`, `.desktop-dock-shell`, and `.desktop-dock-btn`: Claymorphic pads, compound inset shadows, and bouncy `:active` press effects.
  - `.desktop-dock-icon`: 16px radius, inflated matte extrusion.
  - `.desktop-window`: 18px radius, double inset shadow lighting, smooth outer drop-shadow.
  - `.desktop-win-titlebar`: Soft rounded header.
  - `.desktop-win-btn`: Pill-like inset buttons.
  - Primary button styling: 3D clay button with pressed state.

### 4. Automated Tests
- Create `tests/unit/frontend/theme_claymorphism_preset_345.test.js` validating preset registration, attribute switching, and storage persistence.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `PRESET_THEMES` in `theme-engine.js` contains the `claymorphism` preset with tactile color tokens.
- [x] Selecting "Claymorphism" in Settings Studio immediately sets `data-theme="claymorphism"` on `:root` and saves to browser storage.
- [x] Selecting any other theme (Indigo, Slate Graphite, etc.) cleanly removes `data-theme="claymorphism"`.
- [x] When Claymorphism is active, the bottom dock buttons exhibit smooth 3D clay elevation, inner bevel lighting, and a tactile click response.
- [x] When Claymorphism is active, desktop window frames and titlebars display rounded clay corners (18px) and dual inset bevel shadows without breaking drag/resize handles.
- [x] Switching between themes does not cause layout shifts, script errors, or window physics breaks.
- [x] Automated frontend unit tests pass (`npm run test:unit:frontend`).
- [x] Zero lint errors (`npm run lint:frontend`).

---

## 4. Constraints & Honor Flags

- Zero remote push (`git push` strictly forbidden).
- No code changes before Jacob gives the explicit command `build`.
- Isolated `feat/claymorphism-prototype` branch cut from `qa`.
