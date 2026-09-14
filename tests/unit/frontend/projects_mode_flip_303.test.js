import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-303 Projects Manager / Artifact Explorer flip', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'), 'utf-8');

  it('exposes two mode buttons and two full views', () => {
    expect(html).toContain('id="projectsModeManagerBtn"');
    expect(html).toContain('id="projectsModeExplorerBtn"');
    expect(html).toContain('id="projectsManagerView"');
    expect(html).toContain('id="projectsExplorerView"');
    expect(html).not.toContain('id="projectsToggleDrawerBtn"');
  });

  it('wires setProjectsMode and defaults explorer when Active exists', () => {
    expect(js).toContain('function setProjectsMode');
    expect(js).toContain("setProjectsMode('explorer')");
    expect(js).toContain("setProjectsMode('manager')");
  });
});
