/**
 * CARD-153: Per-Agent LLM Provider and Model Configuration
 * Replaces Purpose Matrix with direct provider + model selectors on agent sheet.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Per-Agent LLM Configuration [CARD-153]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');
  const settingsJs = read('src/web/static/modules/studios/settings.js');

  it('renders forgeProviderSelect and forgeAgentModelSelect in index.html [REQ-MODEL-001]', () => {
    expect(indexHtml).toContain('id="forgeProviderSelect"');
    expect(indexHtml).toContain('id="forgeAgentModelSelect"');
    expect(indexHtml).toContain('Leave on Global Default to inherit from Settings');
  });

  it('defaults selectors to "Use Global Default" [REQ-MODEL-001]', () => {
    expect(indexHtml).toContain('<option value="default">Use Global Default</option>');
  });

  it('completely eliminates legacy Purpose Slot & Purpose Matrix from index.html [REQ-MODEL-005]', () => {
    expect(indexHtml).not.toContain('forgePurposeSelect');
    expect(indexHtml).not.toContain('forgeModelSelect');
    expect(indexHtml).not.toContain('saveMatrixBtn');
    expect(indexHtml).not.toContain('Purpose-Based Model Routing');
    expect(indexHtml).not.toContain('matrixGeneral');
    expect(indexHtml).not.toContain('matrixReasoning');
  });

  it('wires forgeProviderSelect and forgeAgentModelSelect in forge.js [REQ-MODEL-002]', () => {
    expect(forgeJs).toContain("const forgeProviderSelect = $('forgeProviderSelect');");
    expect(forgeJs).toContain("const forgeAgentModelSelect = $('forgeAgentModelSelect');");
    expect(forgeJs).toContain('populateAgentModelSelect');
    expect(forgeJs).toContain("provider: forgeProviderSelect ? forgeProviderSelect.value : 'default'");
    expect(forgeJs).toContain("model: forgeAgentModelSelect ? forgeAgentModelSelect.value : 'default'");
    expect(forgeJs).not.toContain('forgePurposeSelect');
    expect(forgeJs).not.toContain('forgeModelSelect');
  });

  it('removes purpose matrix handlers from settings.js [REQ-MODEL-005]', () => {
    expect(settingsJs).not.toContain('saveMatrixBtn');
    expect(settingsJs).not.toContain('.matrix-select');
    expect(settingsJs).not.toContain('/api/settings/matrix');
  });

  it('renders per-agent endpoint inputs and discovery button in index.html [CARD-156]', () => {
    expect(indexHtml).toContain('id="forgeProviderConfigContainer"');
    expect(indexHtml).toContain('id="forgeApiBaseUrlInput"');
    expect(indexHtml).toContain('id="forgeApiKeyInput"');
    expect(indexHtml).toContain('id="forgeContextWindowInput"');
    expect(indexHtml).toContain('id="forgeDiscoverModelsBtn"');
    expect(indexHtml).toContain('🔄 Refresh Models');
  });

  it('binds endpoint credentials and wires live model discovery in forge.js [CARD-156]', () => {
    expect(forgeJs).toContain("const forgeProviderConfigContainer = $('forgeProviderConfigContainer');");
    expect(forgeJs).toContain("const forgeApiBaseUrlInput = $('forgeApiBaseUrlInput');");
    expect(forgeJs).toContain("const forgeApiKeyInput = $('forgeApiKeyInput');");
    expect(forgeJs).toContain("const forgeContextWindowInput = $('forgeContextWindowInput');");
    expect(forgeJs).toContain("const forgeDiscoverModelsBtn = $('forgeDiscoverModelsBtn');");
    expect(forgeJs).toContain('updateProviderConfigVisibility');
    expect(forgeJs).toContain('discoverModelsForAgent');
    expect(forgeJs).toContain('api_base_url:');
    expect(forgeJs).toContain('api_key:');
    expect(forgeJs).toContain('context_window:');
  });
});
