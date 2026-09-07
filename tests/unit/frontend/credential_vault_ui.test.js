/**
 * CARD-168: Credential Vault and Per-Agent Access Control UI Tests.
 * Verifies UI controls and bindings in index.html, settings.js, and forge.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Credential Vault and Per-Agent Grants UI [CARD-168]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const settingsJs = read('src/web/static/modules/studios/settings.js');
  const forgeJs = read('src/web/static/modules/studios/forge.js');

  it('renders Credential Vault elements in Settings Studio [CARD-168]', () => {
    expect(indexHtml).toContain('id="addCredentialBtn"');
    expect(indexHtml).toContain('id="credentialFormContainer"');
    expect(indexHtml).toContain('id="credNameInput"');
    expect(indexHtml).toContain('id="credIdInput"');
    expect(indexHtml).toContain('id="credTypeSelect"');
    expect(indexHtml).toContain('id="credSecretInput"');
    expect(indexHtml).toContain('id="saveCredentialBtn"');
    expect(indexHtml).toContain('id="credentialsTableBody"');
  });

  it('renders Credential Grants card in Agent Studio [CARD-168]', () => {
    expect(indexHtml).toContain('id="forgeCredentialGrantsCard"');
    expect(indexHtml).toContain('id="forgeCredentialCountBadge"');
    expect(indexHtml).toContain('id="forgeCredentialGrantsList"');
  });

  it('binds Credential Vault API in settings.js [CARD-168]', () => {
    expect(settingsJs).toContain('/api/vault/credentials');
    expect(settingsJs).toContain('loadCredentials');
    expect(settingsJs).toContain('credentialsTableBody');
    expect(settingsJs).toContain('saveCredentialBtn');
  });

  it('binds Credential Grants and allowed_credentials in forge.js [CARD-168]', () => {
    expect(forgeJs).toContain('forgeCredentialGrantsList');
    expect(forgeJs).toContain('forgeCredentialCountBadge');
    expect(forgeJs).toContain('allowed_credentials');
    expect(forgeJs).toContain('loadAgentCredentialGrants');
  });
});
