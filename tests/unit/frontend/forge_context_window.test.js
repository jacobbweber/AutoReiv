/**
 * CARD-162: Per-Agent Context Window Control in Agent Studio and Unified Fallback Cascade
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Per-Agent Context Window Control [CARD-162]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');

  it('renders forgeContextWindowInput outside of hidden forgeProviderConfigContainer in index.html', () => {
    // forgeContextWindowInput must be present
    expect(indexHtml).toContain('id="forgeContextWindowInput"');

    // It must NOT be nested inside forgeProviderConfigContainer
    const providerConfigStart = indexHtml.indexOf('id="forgeProviderConfigContainer"');
    expect(providerConfigStart).toBeGreaterThan(-1);

    // Find closing </div> of forgeProviderConfigContainer
    const providerConfigSub = indexHtml.slice(providerConfigStart, providerConfigStart + 1200);
    const ctxInputPosInConfig = providerConfigSub.indexOf('id="forgeContextWindowInput"');

    // Context window input must NOT be inside the conditional provider config container
    expect(ctxInputPosInConfig).toBe(-1);
  });

  it('provides descriptive placeholder and helper text for inheritance', () => {
    expect(indexHtml).toContain('placeholder="e.g. 131072 (leave empty to inherit)"');
    expect(indexHtml).toContain('Leave empty to inherit from this agent\'s model, or fallback to platform settings.');
  });

  it('saves context_window in forge.js regardless of whether provider is default', () => {
    // Must NOT contain the old gate: if (!forgeProviderSelect || forgeProviderSelect.value === 'default' || !forgeContextWindowInput) return null;
    expect(forgeJs).not.toContain("forgeProviderSelect.value === 'default' || !forgeContextWindowInput");

    // Must extract finite positive integer or null
    expect(forgeJs).toContain('context_window: (function () {');
    expect(forgeJs).toContain('const val = parseInt(forgeContextWindowInput.value, 10);');
  });
});
