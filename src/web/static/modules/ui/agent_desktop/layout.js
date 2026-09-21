/**
 * Agent Desktop - Layout & Geometry Calculations
 * Pure geometry, grid snapping, and window placement calculations.
 */

export const MIN_W = 320;
export const MIN_H = 240;
export const GRID_SIZE = 16;
/** Dock + Organize Windows stay above every studio window. */
export const DESKTOP_DOCK_Z = 10000;
/** Modal dialogs (routineModal, chatToolsModal, etc.) sit above all windows and dock [CARD-344]. */
export const DESKTOP_MODAL_Z = 11000;
export const DESKTOP_WINDOW_Z_CAP = 9000;

/**
 * Next window stack value, capped so win.z + 2 never reaches the dock.
 * @param {number} currentZ
 * @param {number} [cap]
 * @returns {number}
 */
export function nextDesktopStackZ(currentZ, cap = DESKTOP_WINDOW_Z_CAP) {
  const cur = Number(currentZ) || 0;
  const top = Number(cap) || DESKTOP_WINDOW_Z_CAP;
  return Math.min(cur + 1, top);
}

/**
 * Cascade offset for newly opened windows (deterministic, no RNG).
 * @param {number} index
 * @returns {{ x: number, y: number }}
 */
export function cascadeOffset(index) {
  const i = Math.max(0, Number(index) || 0);
  const step = 28;
  return { x: 48 + (i % 8) * step, y: 36 + (i % 8) * step };
}

/**
 * Snap a numeric value to the desktop grid.
 * @param {number} value
 * @param {number} [grid]
 * @param {boolean} [disable]
 * @returns {number}
 */
export function snapToGrid(value, grid = GRID_SIZE, disable = false) {
  if (disable) return value;
  const g = Math.max(1, Number(grid) || GRID_SIZE);
  return Math.round(Number(value) / g) * g;
}

/**
 * Snap a window rect to the grid (position + size).
 * @param {{ x: number, y: number, w: number, h: number }} rect
 * @param {number} [grid]
 * @param {boolean} [disable]
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function snapRectToGrid(rect, grid = GRID_SIZE, disable = false) {
  if (disable) return { ...rect };
  return {
    x: snapToGrid(rect.x, grid, false),
    y: snapToGrid(rect.y, grid, false),
    w: Math.max(MIN_W, snapToGrid(rect.w, grid, false)),
    h: Math.max(MIN_H, snapToGrid(rect.h, grid, false)),
  };
}

/**
 * Clamp a window rect inside the desktop viewport (leaves room for dock).
 * @param {{ x: number, y: number, w: number, h: number }} rect
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function clampWindowRect(rect, viewport) {
  const dockH = viewport.dockH ?? 72;
  const maxW = Math.max(MIN_W, viewport.width - 16);
  const maxH = Math.max(MIN_H, viewport.height - dockH - 16);
  const w = Math.min(Math.max(MIN_W, rect.w || MIN_W), maxW);
  const h = Math.min(Math.max(MIN_H, rect.h || MIN_H), maxH);
  const maxX = Math.max(0, viewport.width - w);
  const maxY = Math.max(0, viewport.height - dockH - h);
  const x = Math.min(Math.max(0, rect.x || 0), maxX);
  const y = Math.min(Math.max(0, rect.y || 0), maxY);
  return { x, y, w, h };
}

/**
 * Compute tiled grid rects for N windows.
 * @param {number} count
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeTileRects(count, viewport) {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  if (!n) return [];
  const dockH = viewport.dockH ?? 72;
  const areaW = Math.max(MIN_W, viewport.width - 16);
  const areaH = Math.max(MIN_H, viewport.height - dockH - 16);
  const cols = Math.ceil(Math.sqrt(n));
  const rows = Math.ceil(n / cols);
  const cellW = Math.floor(areaW / cols);
  const cellH = Math.floor(areaH / rows);
  /** @type {Array<{ x: number, y: number, w: number, h: number }>} */
  const rects = [];
  for (let i = 0; i < n; i += 1) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    rects.push(
      clampWindowRect(
        {
          x: 8 + col * cellW,
          y: 8 + row * cellH,
          w: Math.max(MIN_W, cellW - 8),
          h: Math.max(MIN_H, cellH - 8),
        },
        viewport
      )
    );
  }
  return rects;
}

/**
 * Cascade layout rects for N windows.
 * @param {number} count
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @param {{ w?: number, h?: number }} [size]
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeCascadeRects(count, viewport, size = {}) {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  const w = size.w || 640;
  const h = size.h || 480;
  /** @type {Array<{ x: number, y: number, w: number, h: number }>} */
  const rects = [];
  for (let i = 0; i < n; i += 1) {
    const off = cascadeOffset(i);
    rects.push(clampWindowRect({ x: off.x, y: off.y, w, h }, viewport));
  }
  return rects;
}

/**
 * Snap focused window to left or right half of the desktop.
 * @param {'left'|'right'} side
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function computeSnapHalf(side, viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const halfW = Math.floor((viewport.width - gap * 3) / 2);
  const h = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  const x = side === 'right' ? gap * 2 + halfW : gap;
  return clampWindowRect({ x, y: gap, w: halfW, h }, viewport);
}

/**
 * Compute side-by-side 50/50 two-column layout rects [CARD-279].
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeTwoColumnsRects(viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const colW = Math.max(MIN_W, Math.floor((viewport.width - gap * 3) / 2));
  const h = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  return [
    clampWindowRect({ x: gap, y: gap, w: colW, h }, viewport),
    clampWindowRect({ x: gap * 2 + colW, y: gap, w: colW, h }, viewport),
  ];
}

/**
 * Compute 3 equal-width columns layout rects [CARD-279].
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeThreeColumnsRects(viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const colW = Math.max(MIN_W, Math.floor((viewport.width - gap * 4) / 3));
  const h = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  return [
    clampWindowRect({ x: gap, y: gap, w: colW, h }, viewport),
    clampWindowRect({ x: gap * 2 + colW, y: gap, w: colW, h }, viewport),
    clampWindowRect({ x: gap * 3 + colW * 2, y: gap, w: colW, h }, viewport),
  ];
}

/**
 * Compute 3-window layout rects: Left side has 2 vertically stacked windows (50% w, 50% h),
 * Right side has 1 full-height window (50% w, 100% h). Matches Jacob's cockpit layout [CARD-279].
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeLeftStackedRightFullRects(viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const halfW = Math.max(MIN_W, Math.floor((viewport.width - gap * 3) / 2));
  const fullH = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  const halfH = Math.max(MIN_H, Math.floor((fullH - gap) / 2));
  const botH = Math.max(MIN_H, fullH - gap - halfH);
  return [
    // Window 0: Top-left
    clampWindowRect({ x: gap, y: gap, w: halfW, h: halfH }, viewport),
    // Window 1: Bottom-left
    clampWindowRect({ x: gap, y: gap * 2 + halfH, w: halfW, h: botH }, viewport),
    // Window 2: Right full
    clampWindowRect({ x: gap * 2 + halfW, y: gap, w: halfW, h: fullH }, viewport),
  ];
}

/**
 * Compute 3-window layout rects: Left side has 1 full-height window (50% w, 100% h),
 * Right side has 2 vertically stacked windows (50% w, 50% h) [CARD-279].
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeLeftFullRightStackedRects(viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const halfW = Math.max(MIN_W, Math.floor((viewport.width - gap * 3) / 2));
  const fullH = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  const halfH = Math.max(MIN_H, Math.floor((fullH - gap) / 2));
  const botH = Math.max(MIN_H, fullH - gap - halfH);
  return [
    // Window 0: Left full
    clampWindowRect({ x: gap, y: gap, w: halfW, h: fullH }, viewport),
    // Window 1: Top-right
    clampWindowRect({ x: gap * 2 + halfW, y: gap, w: halfW, h: halfH }, viewport),
    // Window 2: Bottom-right
    clampWindowRect({ x: gap * 2 + halfW, y: gap * 2 + halfH, w: halfW, h: botH }, viewport),
  ];
}

/**
 * Maximize rect filling space above the dock.
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function computeMaximizeRect(viewport) {
  const dockH = viewport.dockH ?? 72;
  return clampWindowRect(
    {
      x: 8,
      y: 8,
      w: viewport.width - 16,
      h: viewport.height - dockH - 16,
    },
    viewport
  );
}

/**
 * Mobile layout: every focused window fills the area above the dock (no 50/50 stack).
 * openCount/index retained for API compatibility; always returns full maximize rect.
 * @param {number} _openCount
 * @param {number} _index
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number, mode: 'full' }}
 */
export function computeMobileLayout(_openCount, _index, viewport) {
  const dockH = viewport.dockH ?? 72;
  const w = viewport.width;
  const usableH = Math.max(MIN_H, viewport.height - dockH);
  return { x: 0, y: 0, w, h: usableH, mode: 'full' };
}
