/**
 * CARD-171: Lab Monitor artifact preview helpers and DOM contract.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Lab Monitor artifact preview path builders [CARD-171]', () => {
  it('exports buildExpectedPackPaths and collectPacketArtifacts from forge.js', async () => {
    const mod = await import('../../../src/web/static/modules/studios/forge.js');
    expect(typeof mod.buildExpectedPackPaths).toBe('function');
    expect(typeof mod.collectPacketArtifacts).toBe('function');

    const paths = mod.buildExpectedPackPaths('hyperv', [
      'tools/manage_hyperv.py',
      'skills/hyperv/SKILL.md',
    ]);
    expect(paths.length).toBe(2);
    expect(paths[0]).toContain('%LOCALAPPDATA%\\AutoReiv\\packs\\hyperv\\');
    expect(paths[0]).toContain('tools\\manage_hyperv.py');

    const arts = mod.collectPacketArtifacts([
      {
        sender_role: 'author',
        payload: {
          files_map: {
            'tools/manage_hyperv.py': 'print(1)',
            'skills/hyperv/SKILL.md': '# skill',
          },
          wiki_paths: ['wiki/grounding.md'],
        },
      },
    ]);
    expect(arts.some((a) => a.path === 'tools/manage_hyperv.py')).toBe(true);
    expect(arts.some((a) => a.path === 'skills/hyperv/SKILL.md')).toBe(true);
    expect(arts.some((a) => a.path === 'wiki/grounding.md')).toBe(true);
  });

  it('index.html has artifact preview modal with stable ids/data-testid', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="labArtifactPreviewModal"');
    expect(html).toContain('data-testid="lab-artifact-preview-modal"');
    expect(html).toContain('id="labArtifactPreviewTitle"');
    expect(html).toContain('id="labArtifactPreviewBody"');
    expect(html).toContain('id="labArtifactPreviewPaths"');
    expect(html).toContain('id="labArtifactPills"');
    expect(html).toContain('data-testid="lab-artifact-pills"');
  });

  it('forge.js wires clickable artifact pills and preview modal', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('labArtifactPills');
    expect(forgeJs).toContain('openLabArtifactPreview');
    expect(forgeJs).toContain('buildExpectedPackPaths');
    expect(forgeJs).toContain('Pre-promote');
    expect(forgeJs).toContain('data-testid');
  });
});
