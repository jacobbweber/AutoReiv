/**
 * CARD-423: catalog labels for platform, native custom, and MCP tools.
 * REQ-423-003, REQ-423-005. Packaging stays a note. No folder picker.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  buildCatalogGroups,
  filterCatalogGroups,
  originLabel,
  renderCatalogMarkup,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

function sliceView(html, startId, endId) {
  const start = html.indexOf(`id="${startId}"`);
  const end = html.indexOf(`id="${endId}"`, start + 1);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return html.slice(start, end);
}

const namespaces = [
  {
    id: 'builtin',
    name: 'Built-in Primitives',
    source: 'builtin',
    origin_label: 'Platform',
    tools: [{ name: 'activate_skill', description: 'Activate a skill' }],
  },
  {
    id: 'native_custom',
    name: 'Native custom',
    source: 'native_custom',
    origin_label: 'Native custom',
    tools: [{ name: 'echo_token', description: 'Echo a token' }],
  },
  {
    id: 'mcp:desk',
    name: 'MCP: Desk',
    source: 'mcp',
    server_name: 'desk',
    origin_label: 'MCP · desk',
    tools: [{ name: 'mcp_desk_ping', description: 'Ping the desk server' }],
  },
];

describe('Tools Studio origin labels [CARD-423]', () => {
  const html = read('src/web/templates/index.html');
  const toolsView = sliceView(html, 'view-tools-studio', 'manageTonesModal');

  it('labels platform, native custom, and MCP by server [REQ-423-005]', () => {
    const groups = buildCatalogGroups({ namespaces });
    expect(groups.map((group) => group.source)).toEqual(['platform', 'native_custom', 'mcp']);
    expect(groups.map((group) => originLabel(group))).toEqual([
      'Platform',
      'Native custom',
      'MCP · desk',
    ]);

    const markup = renderCatalogMarkup(groups);
    expect(markup).toContain('data-origin="platform"');
    expect(markup).toContain('data-origin="native_custom"');
    expect(markup).toContain('data-origin="mcp"');
    expect(markup).toContain('data-mcp-server="desk"');
    expect(markup).toContain('Native custom');
    expect(markup).toContain('MCP · desk');
    expect(markup).toContain('Platform');

    const nativeOnly = filterCatalogGroups(groups, { source: 'native' });
    expect(nativeOnly.map((group) => group.source)).toEqual(['native_custom']);
    expect(renderCatalogMarkup(filterCatalogGroups(groups, { source: 'platform' }))).not.toContain('echo_token');
    expect(renderCatalogMarkup(filterCatalogGroups(groups, { source: 'mcp' }))).not.toContain('echo_token');
    expect(renderCatalogMarkup(filterCatalogGroups(groups, { status: 'available' }))).not.toContain('echo_token');
    expect(renderCatalogMarkup(filterCatalogGroups(groups, { status: 'available' }))).toContain('activate_skill');
  });

  it('keeps a path as text and does not add a folder picker [REQ-423-003]', () => {
    expect(toolsView).toContain('id="toolsStudioPathInput"');
    expect(toolsView).toContain('type="text"');
    expect(toolsView).toContain('value="native"');
    expect(toolsView).toContain('note only');
    expect(toolsView).toContain('value="native">Native custom');
    expect(toolsView).not.toContain('webkitdirectory');
    expect(toolsView).not.toContain('type="file"');
    expect(toolsView).not.toContain('folder picker');
    const authoring = read('src/web/static/modules/studios/tools_studio_authoring.js');
    expect(authoring).toContain("throw new Error('Tools Studio must not apply tool packaging from this form.')");
  });
});
