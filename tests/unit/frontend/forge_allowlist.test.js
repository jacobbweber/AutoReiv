/**
 * CARD-115: Forge 12-tool allowlist warning is removed.
 * Tests that previously expected the CARD-078 banner now expect it gone.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Forge allowlist warning removed [CARD-115]', () => {
  it('does not keep FORGE_ALLOWLIST_WARN_AT or forge_allowlist.js', () => {
    const helperPath = path.join(repoRoot, 'src/web/static/modules/utils/forge_allowlist.js');
    expect(fs.existsSync(helperPath)).toBe(false);

    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).not.toContain('FORGE_ALLOWLIST_WARN_AT');
    expect(forgeJs).not.toContain('forge_allowlist');
    expect(forgeJs).not.toContain('updateAllowlistWarning');
    expect(forgeJs).not.toContain('allowlistWarningVisible');
    expect(forgeJs).not.toContain('formatAllowlistWarning');
  });

  it('does not render #forgeAllowlistWarning in Agent Studio', () => {
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('forgeAllowlistWarning');
    expect(html).not.toContain('forgeAllowlistWarningText');
  });
});
