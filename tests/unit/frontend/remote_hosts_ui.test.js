/**
 * CARD-160: Remote Host and SSH Connectivity UI Tests.
 * Verifies UI controls and bindings in index.html and settings.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Remote SSH Hosts UI [CARD-160]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const settingsJs = read('src/web/static/modules/studios/settings.js');

  it('renders Remote Hosts elements in Settings Studio [CARD-160]', () => {
    expect(indexHtml).toContain('id="settingsRemoteHosts"');
    expect(indexHtml).toContain('id="addRemoteHostBtn"');
    expect(indexHtml).toContain('id="remoteHostFormContainer"');
    expect(indexHtml).toContain('id="hostLabelInput"');
    expect(indexHtml).toContain('id="hostAddressInput"');
    expect(indexHtml).toContain('id="hostPortInput"');
    expect(indexHtml).toContain('id="hostUsernameInput"');
    expect(indexHtml).toContain('id="hostCredentialSelect"');
    expect(indexHtml).toContain('id="saveRemoteHostBtn"');
    expect(indexHtml).toContain('id="remoteHostsTableBody"');
  });

  it('binds Remote Hosts API and functions in settings.js [CARD-160]', () => {
    expect(settingsJs).toContain('/api/remote_hosts');
    expect(settingsJs).toContain('loadRemoteHosts');
    expect(settingsJs).toContain('remoteHostsTableBody');
    expect(settingsJs).toContain('saveRemoteHostBtn');
    expect(settingsJs).toContain('data-test-host');
  });
});
