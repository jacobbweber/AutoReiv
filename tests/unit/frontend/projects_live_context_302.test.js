import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-302 Projects live context + drift overlay', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'), 'utf-8');
  const manifest = fs.readFileSync(
    path.resolve(__dirname, '../../../templates/sdlc-project/project_template_manifest.json'),
    'utf-8',
  );

  it('ships a versioned project template path manifest', () => {
    const data = JSON.parse(manifest);
    expect(data.template_version).toBeTruthy();
    expect(data.required_paths).toContain('AGENTS.md');
    expect(data.required_paths).toContain('.agents/steering/product.md');
  });

  it('renders drift banner + align control and drawer above workspace', () => {
    expect(html).toContain('id="projectsDriftBanner"');
    expect(html).toContain('id="projectsAlignBtn"');
    expect(html).toContain('id="projectsActiveRootBar"');
    expect(html).toMatch(/#projectsDrawer[^{]*\{[^}]*z-index:\s*60/);
  });

  it('wires Active switch to reload tree + drift from disk APIs', () => {
    expect(js).toContain('/api/projects/drift');
    expect(js).toContain('/api/projects/align');
    expect(js).toContain('loadDrift');
    expect(js).toContain("await loadTree('.', 'all')");
  });
});
