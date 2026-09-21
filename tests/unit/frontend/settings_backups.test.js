import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';

describe('CARD-404 Automated scheduled backups, retention policy, and configurable backup directory', () => {
  const html = loadPageHtml();
  const settingsJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/settings.js'),
    'utf-8',
  );

  it('renders backup directory, schedule, retention, and history catalog controls in index.html', () => {
    expect(html).toContain('id="backupDirPath"');
    expect(html).toContain('id="backupSchedule"');
    expect(html).toContain('id="backupRetentionCount"');
    expect(html).toContain('id="saveBackupConfigBtn"');
    expect(html).toContain('id="runBackupBtn"');
    expect(html).toContain('id="backupCatalogTbody"');
    expect(html).toContain('data-card="404"');
  });

  it('implements catalog fetching, configuration saving, and immediate run in settings.js', () => {
    expect(settingsJs).toContain('/api/data-dir/backups');
    expect(settingsJs).toContain('/api/data-dir/backup-config');
    expect(settingsJs).toContain('loadBackupCatalogAndConfig');
    expect(settingsJs).toContain('saveBackupConfig');
    expect(settingsJs).toContain('runImmediateBackup');
    expect(settingsJs).toContain('renderBackupCatalogTable');
  });

  it('maintains action delegation for download, restore, and delete', () => {
    expect(settingsJs).toContain('backup-download-btn');
    expect(settingsJs).toContain('backup-restore-btn');
    expect(settingsJs).toContain('backup-delete-btn');
  });
});
