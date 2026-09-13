import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  DESKTOP_DOCK_Z,
  DESKTOP_WINDOW_Z_CAP,
  nextDesktopStackZ,
} from '../../../src/web/static/modules/ui/agent-desktop.js';

describe('CARD-297 Organize Windows always above open windows', () => {
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const desktopJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
    'utf-8',
  );

  it('keeps dock / Organize stack above the window z cap', () => {
    expect(DESKTOP_DOCK_Z).toBeGreaterThan(DESKTOP_WINDOW_Z_CAP);
    expect(DESKTOP_WINDOW_Z_CAP).toBeGreaterThan(100);
  });

  it('caps window stacking so focused windows cannot climb over the dock', () => {
    expect(nextDesktopStackZ(40)).toBe(41);
    expect(nextDesktopStackZ(DESKTOP_WINDOW_Z_CAP - 1)).toBe(DESKTOP_WINDOW_Z_CAP);
    expect(nextDesktopStackZ(DESKTOP_WINDOW_Z_CAP)).toBe(DESKTOP_WINDOW_Z_CAP);
    expect(nextDesktopStackZ(DESKTOP_WINDOW_Z_CAP + 50)).toBe(DESKTOP_WINDOW_Z_CAP);
    expect(DESKTOP_WINDOW_Z_CAP + 2).toBeLessThan(DESKTOP_DOCK_Z);
  });

  it('pins #desktopDock z-index to DESKTOP_DOCK_Z so Organize stays clickable', () => {
    const dockBlock = indexHtml.match(/#desktopDock,\s*\n\s*\.desktop-dock\s*\{[^}]+\}/);
    expect(dockBlock).toBeTruthy();
    expect(dockBlock[0]).toContain('z-index: ' + String(DESKTOP_DOCK_Z));
    expect(desktopJs).toMatch(/nextDesktopStackZ\(/);
  });
});
