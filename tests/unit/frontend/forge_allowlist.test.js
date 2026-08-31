/**
 * CARD-115: Forge 12-tool allowlist warning is removed.
 * CARD-121: tools checklist is two groups (Pack-owned / Platform), not skill-pack RBAC.
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

describe('Forge tools checklist [CARD-121]', () => {
  it('groups tools as Pack-owned and Platform without skill-pack masters', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('renderToolsChecklist');
    expect(forgeJs).toContain('No pack-owned tools yet.');
    expect(forgeJs).toContain('Pack-owned');
    expect(forgeJs).toContain('Platform');
    expect(forgeJs).not.toContain('pack-master-checkbox');
    expect(forgeJs).not.toContain('data-pack=');
    expect(forgeJs).not.toContain('skill_packs');
    expect(forgeJs).not.toContain('RBAC');
    expect(forgeJs).not.toContain('Skill Capabilities');
    expect(forgeJs).not.toContain('Hermes');
  });

  it('Agent Studio tools card copy is a checklist, not RBAC', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('Ticked schemas go to the model');
    expect(html).not.toContain('RBAC');
    expect(html).not.toContain('rbac');
    expect(html).not.toContain('Skill Capabilities');
    expect(html).not.toContain('pack-master-checkbox');
    expect(html).not.toContain('Hermes');
  });

  it('CARD-117 skills runbooks card is still present', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('Skills (runbooks)');
    expect(html).toContain('forgeRunbooksGrid');
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('forge-skill-checkbox');
    expect(forgeJs).toContain('allowed_skill');
  });
});
