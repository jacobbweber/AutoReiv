import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * Unit & Static Contract Tests for CARD-207:
 * Desktop Window Resize, Scrollable Studios, and Sessions Cleanup
 */
describe('CARD-207 Desktop Window Layout & Scroll Invariants', () => {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');
  const desktopJsPath = path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js');
  const desktopJs = fs.readFileSync(desktopJsPath, 'utf-8');

  it('hides redundant #sidebarNav in desktop mode when Sessions window is open', () => {
    // #sidebarNav ("All Studios") must be hidden when desktop sessions window is open
    expect(indexHtml).toMatch(
      /body\.radical-desktop-demo\.desktop-sessions-open\s+#sidebarNav\s*\{[^}]*display:\s*none\s*!important/
    );
  });

  it('hides redundant #sidebarDrawerHeader in desktop mode so conversations sit cleanly under window titlebar', () => {
    expect(indexHtml).toMatch(
      /body\.radical-desktop-demo\.desktop-sessions-open\s+#sidebarDrawerHeader,\s*\n\s*body\.radical-desktop-demo\.desktop-sessions-open\s+#closeSidebarBtn\s*\{[^}]*display:\s*none\s*!important/
    );
  });

  it('does not override left and top on #sidebar with inset: auto', () => {
    // inset: auto !important would override left: var(--dw-l) and top: var(--dw-t)
    expect(indexHtml).not.toMatch(/desktop-sessions-open\s+#sidebar\s*\{[^}]*inset:\s*auto\s*!important/);
  });

  it('allows page-style hosted views (settings, routines, observability) to scroll vertically', () => {
    // Hosted views must allow overflow-y: auto so settings/routines/observe content is not cut off
    expect(indexHtml).toMatch(
      /body\.radical-desktop-demo\s+#view-settings\.desktop-view-hosted[^{]*\{[^}]*overflow-y:\s*auto\s*!important/
    );
    expect(indexHtml).toMatch(
      /body\.radical-desktop-demo\s+#view-routines\.desktop-view-hosted[^{]*\{[^}]*overflow-y:\s*auto\s*!important/
    );
    expect(indexHtml).toMatch(
      /body\.radical-desktop-demo\s+#view-observability\.desktop-view-hosted[^{]*\{[^}]*overflow-y:\s*auto\s*!important/
    );
  });

  it('does not restrict #desktopWindowLayer to z-index 30 below hosted views', () => {
    // #desktopWindowLayer must not cap child windows at z-index: 30
    expect(indexHtml).not.toMatch(/#desktopWindowLayer[^}]*z-index:\s*30/);
  });

  it('does not hardcode sidebar to z-index: 50 !important over dynamic window stacking', () => {
    // #sidebar must not override window stacking with static z-index: 50 !important
    expect(indexHtml).not.toMatch(/desktop-sessions-open\s+#sidebar\s*\{[^}]*z-index:\s*50\s*!important/);
  });

  it('elevates window shell and resize handles above hosted view content', () => {
    // Window shell/handles must sit above view (e.g. win.z + 2 vs win.z + 1)
    expect(desktopJs).toMatch(/style\.zIndex\s*=\s*String\(win\.z\s*\+\s*2\)/);
  });
});
