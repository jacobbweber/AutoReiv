/**
 * CARD-196: In-App Software Updates and Upstream Repository Sync UI Tests.
 * Verifies UI controls and bindings in index.html and settings.js [REQ-UPD-001..REQ-UPD-005].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('System & Software Updates UI [CARD-196, REQ-UPD-001..005]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const settingsJs = read('src/web/static/modules/studios/settings.js');

  it('renders System & Software Updates card elements in Settings Studio [REQ-UPD-001]', () => {
    expect(indexHtml).toContain('id="settingsSystemUpdatesCard"');
    expect(indexHtml).toContain('id="systemVersionPill"');
    expect(indexHtml).toContain('id="systemDeploymentBadge"');
    expect(indexHtml).toContain('id="systemCommitSha"');
    expect(indexHtml).toContain('id="systemBranchName"');
    expect(indexHtml).toContain('id="systemTreeStatus"');
    expect(indexHtml).toContain('id="systemPlatform"');
  });

  it('renders Upstream Repository Source inputs and save button [REQ-UPD-002]', () => {
    expect(indexHtml).toContain('id="updateRepoUrlInput"');
    expect(indexHtml).toContain('id="updateBranchInput"');
    expect(indexHtml).toContain('id="saveUpdateConfigBtn"');
    expect(indexHtml).toContain('id="saveUpdateConfigStatus"');
  });

  it('renders Check for Updates and Apply Update action controls [REQ-UPD-003, REQ-UPD-004]', () => {
    expect(indexHtml).toContain('id="checkForUpdatesBtn"');
    expect(indexHtml).toContain('id="applyUpdateBtn"');
    expect(indexHtml).toContain('id="updateStatusBanner"');
    expect(indexHtml).toContain('id="updateStatusDot"');
    expect(indexHtml).toContain('id="updateStatusMessage"');
    expect(indexHtml).toContain('id="updateNotesContainer"');
    expect(indexHtml).toContain('id="updateReleaseNotesText"');
    expect(indexHtml).toContain('id="updateManualDockerHelper"');
  });

  it('binds System Updates API endpoints in settings.js [REQ-UPD-001..005]', () => {
    expect(settingsJs).toContain('/api/system/version');
    expect(settingsJs).toContain('/api/system/updates/config');
    expect(settingsJs).toContain('/api/system/updates/check');
    expect(settingsJs).toContain('/api/system/updates/apply');
    expect(settingsJs).toContain('loadSystemVersionInfo');
    expect(settingsJs).toContain('loadUpdateConfig');
    expect(settingsJs).toContain('checkForUpdatesBtn');
    expect(settingsJs).toContain('applyUpdateBtn');
  });
});
