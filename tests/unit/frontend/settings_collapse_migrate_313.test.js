import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-313 Settings collapse + migrate chrome', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');

  it('collapses settings sections by default', () => {
    const matches = html.match(/<details[^>]*class="[^"]*settings-section[^"]*"/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(4);
    matches.forEach((tag) => {
      expect(tag).not.toMatch(/\sopen(\s|=|>)/);
    });
  });

  it('gives Settings panel min-h-0 + overflow-y scroll contract', () => {
    expect(html).toMatch(/id="view-settings"[^>]*min-h-0/);
    expect(html).toContain('CARD-313');
    expect(html).toContain('/static/app.js?v=2.0.50');
  });

  it('exposes migrate Data UI controls', () => {
    expect(html).toContain('migrateDataDirBtn');
    expect(html).toContain('dataDirSourcePath');
    expect(html).toContain('dataDirDestinationPath');
  });

  it('keeps Providers / Data / Preferences / Connections groups', () => {
    expect(html).toMatch(/Providers/i);
    expect(html).toMatch(/Data/i);
    expect(html).toMatch(/Preferences/i);
    expect(html).toMatch(/Connections/i);
  });
});
