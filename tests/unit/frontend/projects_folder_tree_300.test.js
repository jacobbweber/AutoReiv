import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  normalizeBrowseRel,
  parentBrowseRel,
  filterFoldersOnly,
} from '../../../src/web/static/modules/studios/projects.js';

describe('CARD-300 Projects folder-only tree', () => {
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const projectsJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'),
    'utf-8',
  );

  it('renders folder browser chrome with Up/Root and folders-only list', () => {
    expect(html).toContain('id="projectsFolderBrowser"');
    expect(html).toContain('id="projectsBrowseUpBtn"');
    expect(html).toContain('id="projectsBrowseRootBtn"');
    expect(html).toContain('id="projectsList"');
    expect(html).toMatch(/Folders only/);
  });

  it('normalizes browse paths and parent for up/back', () => {
    expect(normalizeBrowseRel('Active/AutoReiv/')).toBe('Active/AutoReiv');
    expect(parentBrowseRel('Active/AutoReiv')).toBe('Active');
    expect(parentBrowseRel('Active')).toBe('.');
    expect(parentBrowseRel('.')).toBeNull();
  });

  it('wires browse API and set-active from tree selection', () => {
    expect(projectsJs).toContain('/api/projects/browse');
    expect(projectsJs).toContain('loadFolderBrowser');
    expect(projectsJs).toContain('data-act="set-active"');
  });

  it('filterFoldersOnly drops non-folder shaped rows', () => {
    const rows = filterFoldersOnly([
      { name: 'a', rel: 'a', path: '/a' },
      { name: 'file.txt', is_dir: false },
      null,
    ]);
    expect(rows.map((r) => r.name)).toEqual(['a']);
  });
});
