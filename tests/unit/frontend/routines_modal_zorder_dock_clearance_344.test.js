import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  DESKTOP_DOCK_Z,
  DESKTOP_WINDOW_Z_CAP,
  DESKTOP_MODAL_Z,
} from '../../../src/web/static/modules/ui/agent-desktop.js';

describe('CARD-344 Routines Edit Modal Z-Order Stacking and Dock Clearance', () => {
  const html = loadPageHtml();
  const desktopJsPath = path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js');
  const desktopJs = fs.readFileSync(desktopJsPath, 'utf-8');

  it('exports DESKTOP_MODAL_Z and ensures it is higher than both dock and window z-caps', () => {
    expect(DESKTOP_MODAL_Z).toBeDefined();
    expect(typeof DESKTOP_MODAL_Z).toBe('number');
    expect(DESKTOP_MODAL_Z).toBeGreaterThan(DESKTOP_DOCK_Z);
    expect(DESKTOP_MODAL_Z).toBeGreaterThan(DESKTOP_WINDOW_Z_CAP);
    expect(DESKTOP_MODAL_Z).toBe(11000);
  });

  it('removes routineModal from inside view-routines section to prevent lower window stacking trap', () => {
    const viewRoutinesMatch = html.match(/<section\s+id="view-routines"[\s\S]*?<\/section>/);
    expect(viewRoutinesMatch).not.toBeNull();
    const viewRoutinesContent = viewRoutinesMatch[0];
    expect(viewRoutinesContent).not.toContain('id="routineModal"');

    // routineModal must exist at top-level outside <main>
    const mainMatch = html.match(/<main[\s\S]*?<\/main>/);
    expect(mainMatch).not.toBeNull();
    const mainContent = mainMatch[0];
    expect(mainContent).not.toContain('id="routineModal"');

    expect(html).toContain('id="routineModal"');
  });

  it('assigns modal dialogs z-index equal to or greater than DESKTOP_MODAL_Z in desktop CSS', () => {
    // Check desktop modal CSS rules in index.html
    const modalCssMatch = html.match(/body\.radical-desktop-demo\s+\.desktop-dialog-host[\s\S]*?z-index:\s*(\d+)\s*!important/);
    expect(modalCssMatch).not.toBeNull();
    const zValue = parseInt(modalCssMatch[1], 10);
    expect(zValue).toBeGreaterThanOrEqual(11000);
    expect(zValue).toBeGreaterThan(DESKTOP_DOCK_Z);
  });

  it('structures routineModal with pinned header, scrollable body, pinned footer, and dock clearance', () => {
    const modalIdx = html.indexOf('id="routineModal"');
    expect(modalIdx).toBeGreaterThan(-1);
    const modalEnd = html.indexOf('<!-- Fixed Toast Container', modalIdx);
    const modalSlice = html.slice(modalIdx, modalEnd > -1 ? modalEnd : modalIdx + 8000);

    // Overlay has dock clearance padding
    expect(modalSlice).toMatch(/pb-20|pb-24|calc\(100vh/);

    // Modal card is flex flex-col with max-h
    expect(modalSlice).toContain('flex-col');
    expect(modalSlice).toMatch(/max-h-\[(?:calc\(100vh-[^\]]+\)|85vh|80vh)\]/);

    // Header has flex-shrink-0
    expect(modalSlice).toMatch(/id="routineModalTitle"[\s\S]*?flex-shrink-0|flex-shrink-0[\s\S]*?id="routineModalTitle"/);

    // Form or body content has scrollable area
    expect(modalSlice).toMatch(/overflow-y-auto/);

    // Footer with cancel and save buttons is flex-shrink-0 outside or pinned at bottom of form
    expect(modalSlice).toMatch(/id="cancelRoutineModalBtn"[\s\S]*?id="saveRoutineBtn"/);
    expect(modalSlice).toMatch(/border-t[\s\S]*?id="saveRoutineBtn"|id="saveRoutineBtn"[\s\S]*?border-t/);
  });

  it('enhances routineModal in agent-desktop.js dialog host list', () => {
    expect(desktopJs).toContain("'routineModal'");
    expect(desktopJs).toMatch(/enhanceHitlDialogs[\s\S]*?'routineModal'/);
  });
});
