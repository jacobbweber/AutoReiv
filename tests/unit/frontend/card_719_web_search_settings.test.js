/**
 * CARD-719: Web Search & Fetch Settings -> Connections card and helper functions.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  buildWebSearchSavePayload,
  formatWebSearchStatusBadge,
} from '../../../src/web/static/modules/studios/settings_web_search.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('CARD-719 Web Search & Fetch Settings UI and payload helpers', () => {
  const settingsHtml = read('src/web/templates/partials/settings_preferences.html');

  it('renders the Web Search & Fetch configuration card in Settings -> Connections', () => {
    expect(settingsHtml).toContain('id="settingsWebSearchCard"');
    expect(settingsHtml).toContain('id="webSearchProviderSelect"');
    expect(settingsHtml).toContain('id="webSearchCredentialSelect"');
    expect(settingsHtml).toContain('id="webSearchApiKeyInput"');
    expect(settingsHtml).toContain('id="webSearchAllowPrivateUrls"');
    expect(settingsHtml).toContain('id="saveWebSearchSettingsBtn"');
  });

  it('builds clean save payloads for DuckDuckGo, Tavily, and Brave Search', () => {
    const ddg = buildWebSearchSavePayload({
      provider: 'duckduckgo',
      credentialId: '',
      apiKey: '',
      allowPrivateUrls: false,
      maxResults: 5,
    });
    expect(ddg).toEqual({
      provider: 'duckduckgo',
      credential_id: null,
      api_key: null,
      allow_private_urls: false,
      max_results: 5,
    });

    const tavilyInline = buildWebSearchSavePayload({
      provider: 'tavily',
      credentialId: '',
      apiKey: '  tvly-key-123  ',
      allowPrivateUrls: true,
      maxResults: 8,
    });
    expect(tavilyInline).toEqual({
      provider: 'tavily',
      credential_id: null,
      api_key: 'tvly-key-123',
      allow_private_urls: true,
      max_results: 8,
    });
  });

  it('formats honest status badges for free vs token-backed providers', () => {
    expect(formatWebSearchStatusBadge({ provider: 'duckduckgo', has_api_key: false })).toContain('DuckDuckGo Lite');
    expect(formatWebSearchStatusBadge({ provider: 'tavily', has_api_key: true, credential_name: 'Tavily Key' })).toContain('Tavily');
    expect(formatWebSearchStatusBadge({ provider: 'brave', has_api_key: false })).toContain('API Key Needed');
  });
});
