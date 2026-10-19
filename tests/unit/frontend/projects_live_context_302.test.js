import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-302 Projects live context (CARD-729: no template drift)', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'), 'utf-8');

  it('ships no project template to push onto repos', () => {
    expect(fs.existsSync(path.resolve(__dirname, '../../../templates/sdlc-project'))).toBe(false);
  });

  it('keeps the active root bar and drops the drift banner and Align control', () => {
    expect(html).toContain('id="projectsActiveRootBar"');
    // CARD-303: dedicated Explorer view replaces overlay z-index
    expect(html).toContain('id="projectsExplorerView"');
    expect(html).not.toContain('id="projectsDriftBanner"');
    expect(html).not.toContain('id="projectsAlignBtn"');
  });

  it('reloads the tree on Active switch and never calls the retired drift/align APIs', () => {
    expect(js).not.toContain('/api/projects/drift');
    expect(js).not.toContain('/api/projects/align');
    expect(js).not.toContain('loadDrift');
    expect(js).toContain("await loadTree('.', 'all')");
  });
});
