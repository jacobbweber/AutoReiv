# [CARD-210] Enterprise Neutral Chrome and Restrained Theme Accents

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:ui`, `domain:themes`, `domain:desktop`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Calibrated Enterprise Aesthetics**:
   - Instead of vibrant neon/halo borders around floating windows, the window chrome and borders should remain clean, neutral (`rgba(255, 255, 255, 0.10)`), professional, and restrained.
2. **Professional Palette Naming & Tuning**:
   - The preset palettes are calibrated for professional enterprise workstations:
     - **Indigo** (Electric brand accent)
     - **Slate Graphite** (Minimalist dark enterprise slate)
     - **Violet** (Restrained amethyst)
     - **Warm Sand** (Muted bronze/amber)
     - **Teal** (Cybernetic teal)
3. **Migration & Storage Guardrails**:
   - Upgraded local storage key to `autoreiv.theme.v2` to prevent legacy neon/high-saturation test settings from sticking across browser sessions.

---

### Beat 2: What AutoReiv Does Now
1. **Slightly Over-Saturated Window Halos**:
   - CARD-209 added brand-colored window glows (`--theme-brand-glow`) on the outer window shells, which felt slightly too colorful for enterprise productivity.
2. **Storage Key v1**:
   - Storage key was `autoreiv.theme.v1`.

---

### Beat 3: What Will Change
1. **Neutral Window Elevation & Borders**:
   - Window shells (`.desktop-window`) use neutral `rgba(255, 255, 255, 0.10)` borders and drop shadows without a colored brand halo.
   - Titlebar icons retain neutral slate chrome (`#94a3b8`).
2. **Calibrated Presets**:
   - Muted, professional HSL targets across Indigo, Slate Graphite, Violet, Warm Sand, and Teal.
3. **Storage Key Upgrade**:
   - Upgraded to `autoreiv.theme.v2` with legacy v1 cleanup.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Neutral Chrome Invariant)**: Window shells and focused borders use neutral white/alpha borders and elevation shadows without brand halos.
- [x] **AC-2 (Enterprise Presets)**: Presets configured with enterprise names and calibrated tones.
- [x] **AC-3 (Storage Key v2)**: Themes persist under `autoreiv.theme.v2` with legacy v1 purging.
- [x] **AC-4 (Automated Tests Green)**: All unit and Playwright smoke tests pass cleanly.
