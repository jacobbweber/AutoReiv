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

describe('CARD-511: native catalog rows show the tool check', () => {
  const CATALOG = '../../../src/web/static/modules/studios/tools_studio_catalog.js';
  const namespaces = [{
    id: 'native_custom',
    name: 'Native custom',
    source: 'native_custom',
    origin_label: 'Native custom',
    tools: [{ name: 'good_t', description: 'good' }, { name: 'skip_t', description: 'skip' }, { name: 'old_t', description: 'old' }],
  }];
  const nativeTools = [
    { name: 'good_t', check: { status: 'passed' } },
    { name: 'skip_t', check: { status: 'checked_without_call', skip_reason: 'high risk: sample call skipped' } },
    { name: 'old_t', check: null },
  ];

  function rowLabel(markup, name) {
    const start = markup.indexOf(`data-tool-name="${name}"`);
    expect(start).toBeGreaterThan(-1);
    const next = markup.indexOf('data-testid="tools-studio-catalog-row"', start + 1);
    const slice = markup.slice(start, next === -1 ? undefined : next);
    const m = slice.match(/data-testid="tools-studio-check-label" data-check-status="([^"]*)"[^>]*>([^<]*)</);
    return m ? { status: m[1], text: m[2] } : null;
  }

  it('labels passed, checked_without_call and old rows (REQ-511-011)', async () => {
    const { buildCatalogGroups: build, renderCatalogMarkup: render, nativeCheckLabel } = await import(CATALOG);
    expect(nativeCheckLabel({ status: 'passed' })).toBe('Checked');
    expect(nativeCheckLabel({ status: 'checked_without_call', skip_reason: 'sends email' })).toBe('Checked without a sample call: sends email');
    expect(nativeCheckLabel(null)).toBe('Not checked');
    expect(nativeCheckLabel(undefined)).toBe('Not checked');
    const markup = render(build({ namespaces, nativeTools }));
    expect(rowLabel(markup, 'good_t')).toEqual({ status: 'passed', text: 'Checked' });
    expect(rowLabel(markup, 'skip_t')).toEqual({ status: 'checked_without_call', text: 'Checked without a sample call: high risk: sample call skipped' });
    expect(rowLabel(markup, 'old_t')).toEqual({ status: 'not_checked', text: 'Not checked' });
  });

  it('shows no check label for platform rows or when the native list was not loaded', async () => {
    const { buildCatalogGroups: build, renderCatalogMarkup: render } = await import(CATALOG);
    const platform = [{ id: 'builtin', name: 'Built-in', source: 'builtin', tools: [{ name: 'activate_skill' }] }];
    expect(render(build({ namespaces: platform, nativeTools }))).not.toContain('tools-studio-check-label');
    expect(render(build({ namespaces }))).not.toContain('tools-studio-check-label');
  });

  it('loadCatalogModel reads /api/tools/native for the labels and survives its failure', async () => {
    const { loadCatalogModel: load, renderCatalogMarkup: render } = await import(CATALOG);
    const ok = await load(async (url) => {
      if (url === '/api/tools_studio/capabilities') return { ok: true, json: async () => ({ namespaces }) };
      if (url === '/api/tools/native') return { ok: true, json: async () => ({ tools: nativeTools }) };
      return { ok: true, json: async () => [] };
    });
    expect(render(ok)).toContain('>Checked<');
    const down = await load(async (url) => {
      if (url === '/api/tools_studio/capabilities') return { ok: true, json: async () => ({ namespaces }) };
      if (url === '/api/tools/native') throw new Error('offline');
      return { ok: true, json: async () => [] };
    });
    expect(render(down)).toContain('good_t');
    expect(render(down)).not.toContain('tools-studio-check-label');
  });
});
