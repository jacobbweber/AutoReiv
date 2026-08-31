/**
 * CARD-127: Platform skills and Agent Pack Studio layout.
 * Top-down hierarchy: Platform Skills & Tools, then Agent Pack Skills & Tools. Zero "Also ticked" stray tools.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Platform and Pack hierarchy [CARD-127]', () => {
  it('index.html contains Platform Skills & Tools and Agent Pack Skills & Tools headers', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgePlatformBox"');
    expect(html).toContain('Platform Skills & Tools');
    expect(html).toContain('id="forgePackBox"');
    expect(html).toContain('id="forgePackBoxTitle"');
    expect(html).not.toContain('Also ticked');
  });

  it('forge.js removes "Also ticked" and renders clean nested skill accordions', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('renderNestedHomes');
    expect(forgeJs).toContain('renderPlatformSkills');
    expect(forgeJs).toContain('renderPackSkills');
    expect(forgeJs).not.toContain('Also ticked');
    expect(forgeJs).not.toContain('ungrouped_pack_tools');
  });
});
