import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-313 Settings collapse + data migrate', () => {
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const settingsJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/settings.js'),
    'utf-8',
  );

  it('gives Settings panel min-h-0 + overflow-y scroll contract', () => {
    expect(html).toMatch(/id="view-settings"[^>]*min-h-0/);
    expect(html).toContain('CARD-313: Settings collapse');
    expect(html).toContain('#view-settings details.settings-section[open]');
    expect(html).toContain('overflow: visible');
    expect(html).toMatch(/\/static\/app\.js\?v=2\.0\.\d+/);
  });

  it('wraps Settings groups as collapsed details.settings-section', () => {
    const names = ['providers', 'data', 'preferences', 'connections'];
    for (const name of names) {
      expect(html).toContain(`data-settings-section="${name}"`);
    }
    const matches = html.match(/<details class="settings-section"[^>]*>/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(4);
    for (const tag of matches) {
      expect(tag).not.toMatch(/\sopen\b/);
    }
  });

  it('exposes real migrate controls under Data (not theatre)', () => {
    expect(html).toContain('id="dataDirMigrateSource"');
    expect(html).toContain('id="dataDirMigrateDest"');
    expect(html).toContain('id="migrateDataDirBtn"');
    expect(settingsJs).toContain('/api/data-dir/migrate');
    expect(settingsJs).toContain('migrateDataDir');
  });

  it('keeps backup/restore controls', () => {
    expect(html).toContain('id="backupDataDirBtn"');
    expect(html).toContain('id="restoreDataDirBtn"');
  });
});
