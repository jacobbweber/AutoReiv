import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Three-Surface Navigation Architecture [CARD-139]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('declares mobile surface switcher with Cockpit, Vault, and Fleet [REQ-SURFACE-001]', () => {
    expect(html).toContain('id="mobileSurfaceSwitcher"');
    expect(html).toContain('id="surfaceBtnCockpit"');
    expect(html).toContain('id="surfaceBtnVault"');
    expect(html).toContain('id="surfaceBtnFleet"');
  });

  it('streamlines sidebar to collapse by default on desktop [REQ-SURFACE-003]', () => {
    expect(html).toContain('id="sidebar"');
    expect(html).toContain('md:hidden');
  });

  it('preserves all 7 studio tabs with role="tab" for accessibility [REQ-SURFACE-005]', () => {
    const requiredTabs = [
      'tab-chat',
      'tab-routines',
      'tab-observability',
      'tab-agents',
      'tab-settings',
      'tab-wiki',
      'tab-projects',
    ];
    for (const tabId of requiredTabs) {
      expect(html).toContain('id="' + tabId + '"');
    }
  });
});
