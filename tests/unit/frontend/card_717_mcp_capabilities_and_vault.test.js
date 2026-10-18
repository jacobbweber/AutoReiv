/**
 * CARD-717: Settings & Agents Studio "Open in Capabilities Studio" label
 * and Capabilities Studio MCP Vault Credential picker (Bearer, Basic, Header, Env).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  buildMcpSaveBody,
  renderMcpServerListMarkup,
  renderSettingsMcpStatus,
  serverToSaveBody,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('CARD-717 Settings & Agents Studio MCP link labels and Capabilities Studio Vault Auth', () => {
  const indexHtml = read('src/web/templates/index.html');

  it('points Settings and Agents Studio MCP buttons and copy to Capabilities Studio', () => {
    expect(indexHtml).toContain('id="settingsOpenToolsStudioBtn"');
    expect(indexHtml).toContain('Open in Capabilities Studio');
    expect(indexHtml).not.toContain('Open in Tools Studio');
    expect(indexHtml).not.toContain('Open Tools Studio to attach one.');

    const emptyStatus = renderSettingsMcpStatus([]);
    expect(emptyStatus.listHtml).toContain('Open Capabilities Studio to attach one.');
    expect(emptyStatus.listHtml).not.toContain('Open Tools Studio');
  });

  it('renders Vault Credential and Auth Scheme controls in Capabilities Studio MCP form', () => {
    expect(indexHtml).toContain('id="capabilitiesMcpCredentialSelect"');
    expect(indexHtml).toContain('id="capabilitiesMcpAuthTypeSelect"');
    expect(indexHtml).toContain('id="capabilitiesMcpAuthHeaderInput"');
    expect(indexHtml).toContain('id="capabilitiesMcpManageVaultBtn"');
  });

  it('includes credential_id, auth_type, and auth_header in buildMcpSaveBody and serverToSaveBody', () => {
    const built = buildMcpSaveBody({
      name: 'http-bearer-mcp',
      transport: 'sse',
      url: 'https://mcp.example.com/sse',
      credentialId: 'vault-token-1',
      authType: 'bearer',
      authHeader: '',
      enabled: true,
    });
    expect(built.ok).toBe(true);
    expect(built.body).toEqual({
      name: 'http-bearer-mcp',
      transport: 'sse',
      command: null,
      url: 'https://mcp.example.com/sse',
      headers: null,
      env: {},
      credential_id: 'vault-token-1',
      auth_type: 'bearer',
      auth_header: null,
      enabled: true,
    });

    const roundTrip = serverToSaveBody(
      {
        ...built.body,
        auth_type: 'header',
        auth_header: 'X-MCP-Key',
      },
      false,
    );
    expect(roundTrip.credential_id).toBe('vault-token-1');
    expect(roundTrip.auth_type).toBe('header');
    expect(roundTrip.auth_header).toBe('X-MCP-Key');
    expect(roundTrip.enabled).toBe(false);
  });

  it('renders a Vault credential badge on MCP server rows when credential_id is configured', () => {
    const html = renderMcpServerListMarkup([
      {
        name: 'secure-http',
        transport: 'sse',
        url: 'https://mcp.example.com/sse',
        credential_id: 'prod-bearer',
        credential_name: 'Prod Bearer Token',
        auth_type: 'bearer',
        is_mounted: true,
        enabled: true,
        tool_count: 3,
      },
    ]);
    expect(html).toContain('data-testid="mcp-vault-auth-badge"');
    expect(html).toContain('Prod Bearer Token');
    expect(html).toContain('bearer');
  });
});
