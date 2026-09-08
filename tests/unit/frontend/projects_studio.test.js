import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('Projects Studio Web Workspace UI [REQ-PROJ-010..014]', () => {
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8'
  );

  const projectsJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'),
    'utf-8'
  );

  it('declares Projects Studio top bar, active project indicator, and action buttons [REQ-PROJ-010]', () => {
    expect(indexHtml).toContain('id="view-projects"');
    expect(indexHtml).toContain('id="projectsActiveName"');
    expect(indexHtml).toContain('id="projectsActiveBadge"');
    expect(indexHtml).toContain('id="projectsToggleDrawerBtn"');
    expect(indexHtml).toContain('id="projectsRefreshBtn"');
  });

  it('declares collapsible project drawer and preserves root/creation inputs [REQ-SDLC-050, REQ-SDLC-051]', () => {
    expect(indexHtml).toContain('id="projectsDrawer"');
    expect(indexHtml).toContain('id="projectsRootInput"');
    expect(indexHtml).toContain('id="projectsRootSaveBtn"');
    expect(indexHtml).toContain('id="projectsSlugInput"');
    expect(indexHtml).toContain('id="projectsCreateBtn"');
    expect(indexHtml).toContain('id="projectsList"');
  });

  it('declares dual-pane workspace layout with tree explorer and viewer [REQ-PROJ-011]', () => {
    expect(indexHtml).toContain('id="projectsWorkspace"');
    expect(indexHtml).toContain('id="projectsTreePane"');
    expect(indexHtml).toContain('id="projectsViewerPane"');
  });

  it('declares category quick filter pills and file filter input [REQ-PROJ-012]', () => {
    expect(indexHtml).toContain('id="projectsCategoryPills"');
    expect(indexHtml).toContain('data-cat="all"');
    expect(indexHtml).toContain('data-cat="cards"');
    expect(indexHtml).toContain('data-cat="specs"');
    expect(indexHtml).toContain('data-cat="steering"');
    expect(indexHtml).toContain('data-cat="adr"');
    expect(indexHtml).toContain('id="projectsTreeFilter"');
    expect(indexHtml).toContain('id="projectsTreeList"');
  });

  it('declares artifact viewer containers and copy button [REQ-PROJ-013]', () => {
    expect(indexHtml).toContain('id="projectsViewerPath"');
    expect(indexHtml).toContain('id="projectsViewerMeta"');
    expect(indexHtml).toContain('id="projectsCopyPathBtn"');
    expect(indexHtml).toContain('id="projectsMarkdownContent"');
    expect(indexHtml).toContain('id="projectsCodeContent"');
    expect(indexHtml).toContain('id="projectsEmptyNotice"');
  });

  it('projects.js implements Set as Active, Active Project badge, and endpoints wiring [REQ-PROJ-010, REQ-PROJ-014]', () => {
    expect(projectsJs).toContain('Set as Active');
    expect(projectsJs).toContain('Active Project');
    expect(projectsJs).toContain('/api/projects/files/list');
    expect(projectsJs).toContain('/api/projects/files/read');
    expect(projectsJs).toContain('loadTree');
    expect(projectsJs).toContain('loadFileContent');
  });
});
