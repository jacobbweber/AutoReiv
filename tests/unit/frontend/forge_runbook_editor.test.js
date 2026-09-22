/**
 * CARD-167 close/cancel lived on the Agent Studio inline runbook inspector.
 * CARD-419 removed that inspector. Skill detail is Open in Skill Studio only.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio has no inline runbook inspector [CARD-419]', () => {
  const html = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');

  it('index.html does not mount #studioRunbookEditor or its dismiss controls', () => {
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('id="studioRunbookCloseBtn"');
    expect(html).not.toContain('id="studioRunbookCancelBtn"');
    expect(html).not.toContain('studio-runbook-open-btn');
  });

  it('forge does not open or mount an inline runbook viewer', () => {
    expect(forgeJs).not.toContain('hideRunbookEditor');
    expect(forgeJs).not.toContain('openRunbookEditor');
    expect(forgeJs).not.toContain('studioRunbookEditor');
    expect(forgeJs).toContain('Open in Skill Studio');
    expect(forgeJs).toContain('forge-skill-pill');
  });
});
