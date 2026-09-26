/**
 * CARD-421: Tools Studio catalog browse and MCP attach.
 * REQ-421-001..007
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { DOCK_LAUNCHERS, VIEW_BY_TAB } from '../../../src/web/static/modules/ui/agent-desktop.js';
import { openWindow } from '../../../src/web/static/modules/ui/agent_desktop/window.js';
import {
  TOOLS_STUDIO_LABEL,
  TOOLS_STUDIO_TAB,
  planToolsStudioDeepLink,
} from '../../../src/web/static/modules/studios/tools_studio.js';
import {
  buildCatalogGroups,
  buildMcpSaveBody,
  fetchMcpServers,
  filterCatalogGroups,
  formatMcpAttachStatus,
  loadCatalogModel,
  mcpEndpoints,
  renderCatalogMarkup,
  renderMcpServerListMarkup,
  renderMcpStatusRowsMarkup,
  serverToSaveBody,
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

const sampleNamespaces = [
  {
    id: 'builtin',
    name: 'Built-in Primitives',
    source: 'builtin',
    tools: [
      { name: 'wiki_note_read', description: 'Read a wiki note' },
      { name: 'activate_skill', description: 'Activate a skill' },
    ],
  },
  {
    id: 'mcp:github',
    name: 'MCP: Github',
    source: 'mcp',
    tools: [
      { name: 'mcp_github_search', description: 'Search GitHub' },
    ],
  },
];

const platformServers = [
  {
    name: 'github',
    is_mounted: true,
    enabled: true,
    transport: 'stdio',
    command: ['uvx', 'mcp-github'],
    tools: ['mcp_github_search', 'mcp_github_issue'],
    tool_count: 2,
  },
  {
    name: 'quiet',
    is_mounted: false,
    enabled: true,
    transport: 'sse',
    url: 'http://127.0.0.1:9/sse',
    tools: [],
  },
];

describe('Tools Studio dock [CARD-421]', () => {
  const html = read('src/web/templates/index.html');
  const toolsView = sliceView(html, 'view-tools-studio', 'manageTonesModal');
  const settingsView = sliceView(html, 'view-settings', 'view-wiki');
  const agentsView = sliceView(html, 'view-agents', 'view-settings');
  const skillView = sliceView(html, 'view-skill-studio', 'artifactModal');

  it('dock open presents Tools Studio catalog and MCP attach [REQ-421-001]', () => {
    const launcher = DOCK_LAUNCHERS.find((item) => item.tab === TOOLS_STUDIO_TAB);
    expect(launcher).toBeTruthy();
    expect(launcher.id).toBe('dock-tools-studio');
    expect(launcher.label).toBe(TOOLS_STUDIO_LABEL);
    expect(launcher.label).toBe('Tools Studio');
    expect(VIEW_BY_TAB[TOOLS_STUDIO_TAB]).toBe('view-tools-studio');
    expect(html).toContain('id="tab-tools-studio"');

    const switched = [];
    const created = [];
    const win = openWindow(TOOLS_STUDIO_TAB, {}, {
      windows: new Map(),
      launcherForTabFn: (tab) => DOCK_LAUNCHERS.find((item) => item.tab === tab) || null,
      createWindowShellFn: (item) => {
        created.push(item.label);
        return {
          tab: item.tab,
          label: item.label,
          minimized: false,
          maximized: false,
          rect: { x: 32, y: 32, w: 960, h: 680 },
          el: { classList: { add() {}, remove() {} }, setAttribute() {} },
        };
      },
      focusWindowFn() {},
      applyRectFn() {},
      applyMobileLayoutFn() {},
      updateDockActiveFn() {},
      root: { classList: { add() {} } },
      viewportSizeFn: () => ({ width: 1280, height: 800, dockH: 72 }),
      switchTabFn: (tab) => switched.push(tab),
      scheduleSyncHostedViewsFn() {},
      schedulePersistFn() {},
      isMobileFn: () => false,
    });

    expect(created).toEqual(['Tools Studio']);
    expect(switched).toEqual(['tools-studio']);
    expect(win.tab).toBe('tools-studio');
    expect(toolsView).toContain('id="toolsStudioCatalog"');
    expect(toolsView).toContain('id="toolsStudioFilterSearch"');
    expect(toolsView).toContain('id="toolsStudioFilterSource"');
    expect(toolsView).toContain('id="toolsStudioFilterStatus"');
    expect(toolsView).toContain('id="toolsStudioMcpList"');
    expect(toolsView).toContain('id="toolsStudioMcpSaveBtn"');
    expect(toolsView).toContain('id="toolsStudioScopeSelect"');
    expect(toolsView).toContain('id="toolsStudioAgentSelect"');
    expect(toolsView).not.toContain('skill_tool_bindings');
  });

  it('does not ship MCP hosting controls or a tool code editor [REQ-421-006]', () => {
    expect(toolsView).not.toContain('Ask developer');
    expect(toolsView).not.toContain('/api/mcp/sse');
    expect(toolsView).not.toContain('Hosted MCP Server');
    expect(toolsView).not.toContain('id="toolsStudioCodeInput"');
    expect(toolsView).not.toContain('monaco');
    const studio = read('src/web/static/modules/studios/tools_studio.js');
    expect(studio).not.toContain('skill_tool_bindings');
    expect(studio).not.toContain('Ask developer');
    expect(studio).not.toContain('/api/mcp/sse');
  });

  it('Settings and Agent Studio are thin attach shells [REQ-421-005]', () => {
    expect(settingsView).toContain('id="settingsOpenToolsStudioBtn"');
    expect(settingsView).toContain('id="settingsMcpAttachStatus"');
    expect(settingsView).toContain('Hosted MCP Server Active');
    expect(settingsView).toContain('/api/mcp/sse');
    expect(settingsView).not.toContain('id="addMcpServerBtn"');
    expect(settingsView).not.toContain('id="mcpServerFormContainer"');
    expect(settingsView).not.toContain('id="saveMcpServerBtn"');
    expect(settingsView).not.toContain('id="testMcpServerBtn"');

    expect(agentsView).toContain('id="forgeMcpServersCard"');
    expect(agentsView).toContain('id="forgeMcpServerCountBadge"');
    expect(agentsView).toContain('id="forgeOpenToolsStudioBtn"');
    expect(agentsView).toContain('id="forgeMcpServerList"');
    expect(agentsView).not.toContain('id="forgeMcpServerForm"');
    expect(agentsView).not.toContain('id="forgeAddMcpServerBtn"');
    expect(agentsView).not.toContain('id="forgeMcpSaveBtn"');
    expect(agentsView).not.toContain('id="forgeMcpTestBtn"');

    const settingsJs = read('src/web/static/modules/studios/settings.js');
    expect(settingsJs).toContain('/api/settings/mcp');
    expect(settingsJs).not.toContain('/api/settings/mcp/test');
    expect(settingsJs).not.toContain('delete-mcp-btn');
    expect(settingsJs).toContain('settingsOpenToolsStudioBtn');

    const forgeTools = read('src/web/static/modules/studios/forge/tools.js');
    expect(forgeTools).toContain('loadAgentMcpServers');
    expect(forgeTools).toContain('forgeOpenToolsStudioBtn');
    expect(forgeTools).not.toContain('forgeMcpSaveBtn');
    expect(forgeTools).not.toContain('/mcp/test');
    expect(forgeTools).not.toContain('btn-delete-server');

    const saveCount = (html.match(/id="toolsStudioMcpSaveBtn"/g) || []).length;
    expect(saveCount).toBe(1);
  });

  it('Skill Studio still binds tools with catalog checkboxes [REQ-421-004]', () => {
    expect(skillView).toContain('id="factoryCapabilitiesContainer"');
    expect(skillView).toContain('Select to bind to skill');
    expect(skillView).toContain('id="factoryToolSearchInput"');
    const skillStudio = read('src/web/static/modules/studios/skill_studio.js');
    expect(skillStudio).toContain('type="checkbox"');
    expect(skillStudio).toContain('data-tool-name');
    expect(skillStudio).toContain('requires_tools');
    const markup = renderCatalogMarkup(buildCatalogGroups({
      namespaces: sampleNamespaces,
      platformServers,
    }));
    expect(markup).not.toContain('type="checkbox"');
    expect(markup).not.toContain('skill_tool_bindings');
  });
});

describe('Tools Studio catalog grouping and filters [CARD-421]', () => {
  const groups = buildCatalogGroups({
    namespaces: sampleNamespaces,
    platformServers,
    agentServers: [
      {
        name: 'lab',
        is_mounted: true,
        enabled: true,
        tools: ['mcp_lab_ping'],
      },
    ],
    agentId: 'researcher',
  });

  it('groups MCP tools under the server that provides them [REQ-421-007]', () => {
    const github = groups.find((group) => group.serverName === 'github' && group.scope === 'platform');
    expect(github).toBeTruthy();
    expect(github.source).toBe('mcp');
    expect(github.mounted).toBe(true);
    expect(github.tools.map((tool) => tool.name)).toEqual(['mcp_github_search', 'mcp_github_issue']);

    const lab = groups.find((group) => group.serverName === 'lab');
    expect(lab.scope).toBe('agent');
    expect(lab.agentId).toBe('researcher');
    expect(lab.tools.map((tool) => tool.name)).toEqual(['mcp_lab_ping']);

    expect(groups.find((group) => group.id === 'mcp:github')).toBeUndefined();
    const platform = groups.find((group) => group.id === 'builtin');
    expect(platform.source).toBe('platform');
    expect(platform.tools.map((tool) => tool.name)).toEqual(['wiki_note_read', 'activate_skill']);

    const markup = renderCatalogMarkup(groups);
    expect(markup).toContain('data-testid="tools-studio-catalog-row"');
    expect(markup).toContain('data-mcp-server="github"');
    expect(markup).toContain('mcp_github_search');
    expect(markup).toContain('data-mcp-server="lab"');
    const githubAt = markup.indexOf('data-mcp-server="github"');
    const labAt = markup.indexOf('data-mcp-server="lab"');
    expect(markup.indexOf('mcp_github_issue')).toBeGreaterThan(githubAt);
    expect(markup.indexOf('mcp_github_issue')).toBeLessThan(labAt);
  });

  it('search and source filters narrow the catalog [REQ-421-007]', () => {
    const searched = filterCatalogGroups(groups, { search: 'wiki_note' });
    const searchMarkup = renderCatalogMarkup(searched);
    expect(searchMarkup).toContain('wiki_note_read');
    expect(searchMarkup).not.toContain('mcp_github_search');
    expect(searchMarkup).not.toContain('activate_skill');

    const mcpOnly = filterCatalogGroups(groups, { source: 'mcp' });
    expect(mcpOnly.every((group) => group.source === 'mcp')).toBe(true);
    expect(renderCatalogMarkup(mcpOnly)).not.toContain('wiki_note_read');

    const mounted = filterCatalogGroups(groups, { status: 'mounted' });
    expect(mounted.map((group) => group.serverName).sort()).toEqual(['github', 'lab']);

    const cleared = filterCatalogGroups(groups, { search: '', source: '', status: '' });
    expect(cleared.length).toBe(groups.length);

    expect(renderCatalogMarkup(filterCatalogGroups(groups, { search: 'no-such-tool' })))
      .toContain('data-testid="tools-studio-catalog-empty"');
  });

  it('keeps namespace grouping when a server has no tool list [REQ-421-007]', () => {
    const fallback = buildCatalogGroups({
      namespaces: sampleNamespaces,
      platformServers: [{ name: 'github', is_mounted: false, tools: [] }],
    });
    const ns = fallback.find((group) => group.id === 'mcp:github');
    expect(ns).toBeTruthy();
    expect(ns.tools.map((tool) => tool.name)).toEqual(['mcp_github_search']);
    expect(fallback.find((group) => group.serverName === 'github' && group.scope === 'platform')).toBeUndefined();
  });
});

describe('Tools Studio MCP hydrate [CARD-421]', () => {
  it('loads platform servers from /api/settings/mcp [REQ-421-002]', async () => {
    const calls = [];
    const servers = await fetchMcpServers(async (url) => {
      calls.push(url);
      return {
        ok: true,
        json: async () => platformServers,
      };
    }, 'platform');
    expect(calls).toEqual(['/api/settings/mcp']);
    expect(servers).toHaveLength(2);
    const markup = renderMcpServerListMarkup(servers, { scope: 'platform' });
    expect(markup).toContain('data-testid="tools-studio-mcp-row"');
    expect(markup).toContain('github');
    expect(markup).toContain('Mounted (2 tools)');
    expect(markup).toContain('data-action="toggle"');
    expect(markup).toContain('data-action="delete"');
    expect(markup).not.toContain('type="checkbox"');
    expect(mcpEndpoints('platform').save).toBe('/api/settings/mcp');
    expect(mcpEndpoints('platform').test).toBe('/api/settings/mcp/test');
    expect(mcpEndpoints('platform').delete('github')).toBe('/api/settings/mcp/github');
  });

  it('loads agent servers from /api/agents/{id}/mcp only [REQ-421-003]', async () => {
    const calls = [];
    const servers = await fetchMcpServers(async (url) => {
      calls.push(url);
      return {
        ok: true,
        json: async () => [{ name: 'lab', is_mounted: false, enabled: true, url: 'http://lab/sse', transport: 'sse' }],
      };
    }, 'agent', 'researcher');
    expect(calls).toEqual(['/api/agents/researcher/mcp']);
    expect(mcpEndpoints('agent', 'researcher').save).toBe('/api/agents/researcher/mcp');
    expect(mcpEndpoints('agent', 'researcher').test).toBe('/api/agents/researcher/mcp/test');
    expect(mcpEndpoints('agent', 'researcher').delete('lab')).toBe('/api/agents/researcher/mcp/lab');
    expect(mcpEndpoints('agent', 'researcher').mount('lab')).toBe('/api/agents/researcher/mcp/lab/mount');
    expect(servers[0].name).toBe('lab');
    const empty = await fetchMcpServers(async () => {
      throw new Error('should not fetch');
    }, 'agent', '');
    expect(empty).toEqual([]);
  });

  it('catalog hydrate reads capabilities plus MCP lists without writing bindings', async () => {
    const calls = [];
    const groups = await loadCatalogModel(async (url) => {
      calls.push(url);
      if (url === '/api/tools_studio/capabilities') {
        return { ok: true, json: async () => ({ namespaces: sampleNamespaces }) };
      }
      if (url === '/api/settings/mcp') {
        return { ok: true, json: async () => platformServers };
      }
      if (url === '/api/agents/researcher/mcp') {
        return { ok: true, json: async () => [{ name: 'lab', is_mounted: true, tools: ['mcp_lab_ping'] }] };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }, { agentId: 'researcher' });
    expect(calls).toEqual([
      '/api/tools_studio/capabilities',
      '/api/settings/mcp',
      '/api/agents/researcher/mcp',
      '/api/tools/native',
    ]);
    expect(groups.some((group) => group.serverName === 'github')).toBe(true);
    expect(groups.some((group) => group.id === 'builtin')).toBe(true);
  });

  it('builds a durable save body and a one-line Settings status', () => {
    const built = buildMcpSaveBody({
      name: 'github',
      transport: 'stdio',
      commandText: 'uvx mcp-github',
      url: '',
      headersText: '',
      env: { TOKEN: 'secret' },
      enabled: false,
    });
    expect(built.ok).toBe(true);
    expect(built.body.command).toEqual(['uvx', 'mcp-github']);
    expect(built.body.enabled).toBe(false);
    expect(built.body.env).toEqual({ TOKEN: 'secret' });
    expect(buildMcpSaveBody({ name: '', transport: 'stdio', commandText: 'uvx' }).ok).toBe(false);

    const toggled = serverToSaveBody(platformServers[0], false);
    expect(toggled.name).toBe('github');
    expect(toggled.enabled).toBe(false);
    expect(toggled.command).toEqual(['uvx', 'mcp-github']);

    expect(formatMcpAttachStatus(platformServers)).toBe('2 platform MCP servers attached (1 mounted).');
    expect(formatMcpAttachStatus([])).toBe('No platform MCP servers attached.');
    const status = renderMcpStatusRowsMarkup(platformServers, { rowTestId: 'settings-mcp-status-row' });
    expect(status).toContain('data-testid="settings-mcp-status-row"');
    expect(status).not.toContain('data-action');
  });

  it('deep link from Agent Studio selects that agent only', () => {
    const plan = planToolsStudioDeepLink({ scope: 'agent', agentId: 'researcher' });
    expect(plan.tab).toBe('tools-studio');
    expect(plan.scope).toBe('agent');
    expect(plan.agentId).toBe('researcher');
    expect(planToolsStudioDeepLink({}).scope).toBe('platform');
  });
});
