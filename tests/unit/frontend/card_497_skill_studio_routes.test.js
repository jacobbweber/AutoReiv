/**
 * CARD-497 test 18: Skill Studio and Tools Studio call their own routes (D4).
 * No static file calls /api/agent_training_factory; the old paths only 308 for one release.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const STATIC = 'src/web/static';
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(path.join(repoRoot, dir), { withFileTypes: true })) {
    const rel = `${dir}/${entry.name}`;
    if (entry.isDirectory()) out.push(...walk(rel));
    else if (/\.(js|html|css)$/.test(entry.name)) out.push(rel);
  }
  return out;
}

describe('REQ-497-003: frontend call sites use the D4 routes', () => {
  it('skill_studio.js uses capabilities, runbook and save on the new routes', () => {
    const src = read(`${STATIC}/modules/studios/skill_studio.js`);
    expect(src).toContain('/api/tools_studio/capabilities');
    expect(src).toContain('/api/skill_studio/runbook');
    expect(src).toContain('/api/skill_studio/save');
  });

  it('skill_authoring.js SILENT_RUNBOOK_URL is /api/skill_studio/runbook', () => {
    const src = read(`${STATIC}/modules/studios/skill_authoring.js`);
    expect(src).toMatch(/SILENT_RUNBOOK_URL\s*=\s*['"]\/api\/skill_studio\/runbook['"]/);
  });

  it('skill_scope.js and workshop_meta.js open skills through /api/skill_studio/skills', () => {
    expect(read(`${STATIC}/modules/studios/skill_studio/skill_scope.js`)).toContain('/api/skill_studio/skills');
    expect(read(`${STATIC}/modules/studios/skill_studio/workshop_meta.js`)).toContain('/api/skill_studio/skills');
  });

  it('tools_studio_catalog.js loads /api/tools_studio/capabilities', () => {
    expect(read(`${STATIC}/modules/studios/tools_studio_catalog.js`)).toContain('/api/tools_studio/capabilities');
  });

  it('no static file or template references /api/agent_training_factory', () => {
    const files = [...walk(STATIC), 'src/web/templates/index.html'];
    for (const rel of files) {
      expect(read(rel), rel).not.toContain('/api/agent_training_factory');
    }
  });
});
