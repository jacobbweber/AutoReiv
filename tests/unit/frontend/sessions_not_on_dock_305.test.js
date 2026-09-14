import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-305 Sessions not on dock', () => {
  const desktop = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
    'utf-8',
  );
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );

  it('DOCK_LAUNCHERS has no sessions tab', () => {
    const block = desktop.match(/export const DOCK_LAUNCHERS[\s\S]*?\];/)?.[0] || '';
    expect(block).toBeTruthy();
    expect(block).not.toMatch(/tab:\s*['"]sessions['"]/);
    expect(block.toLowerCase()).not.toContain("label: 'sessions'");
  });

  it('hard-redirects sessions openWindow to Chat drawer and scrubs prefs', () => {
    expect(desktop).toContain("if (tab === 'sessions')");
    expect(desktop).toContain('scrubSessionsFromDesktopPrefs');
    expect(desktop).toContain('chatSessionsDrawer');
  });

  it('keeps in-studio Chat sessions drawer', () => {
    expect(html).toContain('id="chatSessionsDrawer"');
  });
});
