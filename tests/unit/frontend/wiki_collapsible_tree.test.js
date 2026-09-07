import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Wiki Collapsible Tree & Subfolder Deletion [CARD-177]', () => {
  let jsContent;
  let htmlContent;

  beforeEach(() => {
    jsContent = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki.js'), 'utf-8');
    htmlContent = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('renders wikiNavTree in the Wiki Studio surface [REQ-WIKI-020]', () => {
    expect(htmlContent).toContain('id="wikiNavTree"');
  });

  it('initializes expandedWikiFolders as an empty Set so folders start collapsed [REQ-WIKI-020]', () => {
    expect(jsContent).toMatch(/const\s+expandedWikiFolders\s*=\s*new\s+Set\(\s*\);/);
    // Ensure renderWikiTree does not unconditionally add roots at top
    expect(jsContent).not.toMatch(/function\s+renderWikiTree[^{]*\{\s*[^}]*expandedWikiFolders\.add\('inbox'\);/);
  });

  it('implements deleteWikiFolder targeting DELETE /api/wiki/folder [REQ-WIKI-024]', () => {
    expect(jsContent).toContain('async function deleteWikiFolder(');
    expect(jsContent).toContain('/api/wiki/folder?path=');
    expect(jsContent).toContain("method: 'DELETE'");
  });

  it('attaches wiki-folder-delete-btn to subfolder rows with event stopPropagation [REQ-WIKI-023]', () => {
    expect(jsContent).toContain('wiki-folder-delete-btn');
    expect(jsContent).toContain('e.stopPropagation()');
  });

  it('defines toolbar folder action containers and buttons in index.html [REQ-WIKI-025]', () => {
    expect(htmlContent).toContain('id="wikiNoteActionsGroup"');
    expect(htmlContent).toContain('id="wikiFolderActionsGroup"');
    expect(htmlContent).toContain('id="wikiRootFolderBadge"');
    expect(htmlContent).toContain('id="wikiDeleteFolderBtn"');
  });

  it('implements selectWikiFolder and renderFolderOverview in wiki.js [REQ-WIKI-024]', () => {
    expect(jsContent).toContain('function selectWikiFolder(');
    expect(jsContent).toContain('function renderFolderOverview(');
    expect(jsContent).toContain('activeWikiFolderPath');
    expect(jsContent).toContain('wikiDeleteFolderBtn');
  });

  it('wires wiki-folder-row clicks to selectWikiFolder and wiki-chevron-btn to collapse/expand [REQ-WIKI-021]', () => {
    expect(jsContent).toContain('wiki-folder-row');
    expect(jsContent).toContain('wiki-chevron-btn');
    expect(jsContent).toContain('selectWikiFolder(');
  });
});
