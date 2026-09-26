/**
 * Tools Studio catalog grouping, search/filter, and MCP attach payloads [CARD-421].
 * Read-only catalog helpers do not write skill_tool_bindings.
 * Attach helpers speak the existing /api/settings/mcp* and /api/agents/{id}/mcp* contracts.
 */

import { escapeHtml } from '../utils/formatters.js';

export const TOOLS_STUDIO_TAB = 'tools-studio';
export const TOOLS_STUDIO_LABEL = 'Tools Studio';

/**
 * @param {string|object|null|undefined} tool
 * @returns {{ name: string, description: string }|null}
 */
export function toolRecord(tool) {
  if (typeof tool === 'string') {
    const name = tool.trim();
    return name ? { name, description: '' } : null;
  }
  if (!tool || typeof tool !== 'object') return null;
  const name = String(tool.name || '').trim();
  if (!name) return null;
  return { name, description: String(tool.description || '') };
}

function serverToolRecords(server) {
  const raw = server && Array.isArray(server.tools) ? server.tools : [];
  const seen = new Set();
  const tools = [];
  raw.forEach((item) => {
    const rec = toolRecord(item);
    if (!rec || seen.has(rec.name)) return;
    seen.add(rec.name);
    tools.push(rec);
  });
  return tools;
}

function isMcpNamespace(ns) {
  if (!ns) return false;
  return ns.source === 'mcp' || String(ns.id || '').startsWith('mcp:');
}

function catalogSource(ns) {
  if (isMcpNamespace(ns)) return 'mcp';
  const raw = String((ns && ns.source) || '');
  if (raw === 'native_custom' || raw === 'native') return 'native_custom';
  if (raw === 'legacy_pack_tool') return 'legacy_pack_tool';
  return 'platform';
}

/**
 * Operator-facing origin [REQ-423-005].
 * @param {object} group
 * @returns {string}
 */
export function originLabel(group) {
  if (!group) return 'Platform';
  if (group.originLabel) return String(group.originLabel);
  if (group.source === 'legacy_pack_tool') return 'Legacy pack tool';
  if (group.source === 'native_custom') return 'Native custom';
  if (group.source === 'mcp') {
    const server = String(group.serverName || group.name || 'server').trim() || 'server';
    return `MCP · ${server}`;
  }
  return 'Platform';
}

/**
 * Tool check label for a native custom row [CARD-511 REQ-511-011].
 * @param {object|null|undefined} check
 * @returns {string}
 */
export function nativeCheckLabel(check) {
  if (!check || typeof check !== 'object') return 'Not checked';
  if (check.status === 'passed') return 'Checked';
  if (check.status === 'checked_without_call') {
    const reason = String(check.skip_reason || '').trim();
    return reason ? `Checked without a sample call: ${reason}` : 'Checked without a sample call';
  }
  return 'Not checked';
}

function nativeCheckKey(check) {
  if (check && typeof check === 'object' && (check.status === 'passed' || check.status === 'checked_without_call')) {
    return check.status;
  }
  return 'not_checked';
}

function groupKind(group) {
  if (!group) return 'platform';
  if (group.source === 'mcp') return 'mcp';
  if (group.source === 'native_custom') return 'native';
  if (group.source === 'legacy_pack_tool') return 'legacy_pack_tool';
  return 'platform';
}

function dataOrigin(group) {
  const source = group && group.source;
  if (source === 'native_custom' || source === 'mcp' || source === 'legacy_pack_tool') return source;
  return 'platform';
}

/**
 * Group live tools under the MCP server that lists them.
 * Platform / built-in namespaces stay in their own groups.
 * When a server has no tool list, capability namespaces keep the MCP grouping they already expose.
 *
 * `nativeTools` (from /api/tools/native) adds each native row's tool check label [CARD-511].
 *
 * @param {{ namespaces?: object[], platformServers?: object[], agentServers?: object[], agentId?: string, nativeTools?: object[]|null }} input
 * @returns {object[]}
 */
export function buildCatalogGroups({
  namespaces = [],
  platformServers = [],
  agentServers = [],
  agentId = '',
  nativeTools = null,
} = {}) {
  const groups = [];
  const claimed = new Set();
  const nativeChecks = Array.isArray(nativeTools)
    ? new Map(nativeTools.filter((row) => row && row.name).map((row) => [String(row.name), row.check || null]))
    : null;

  function pushServer(server, scope, ownerId) {
    if (!server || !server.name) return;
    const tools = serverToolRecords(server);
    if (!tools.length) return;
    tools.forEach((tool) => claimed.add(tool.name));
    groups.push({
      id: scope === 'agent' ? `agent-mcp:${ownerId}:${server.name}` : `platform-mcp:${server.name}`,
      name: String(server.name),
      serverName: String(server.name),
      source: 'mcp',
      originLabel: `MCP · ${server.name}`,
      scope,
      agentId: ownerId || '',
      mounted: Boolean(server.is_mounted),
      enabled: server.enabled !== false,
      tools,
    });
  }

  (Array.isArray(platformServers) ? platformServers : []).forEach((server) => {
    pushServer(server, 'platform', '');
  });
  const owner = String(agentId || '').trim();
  (Array.isArray(agentServers) ? agentServers : []).forEach((server) => {
    pushServer(server, 'agent', owner);
  });

  (Array.isArray(namespaces) ? namespaces : []).forEach((ns) => {
    if (!ns) return;
    const mcp = isMcpNamespace(ns);
    const source = catalogSource(ns);
    let tools = (Array.isArray(ns.tools) ? ns.tools : [])
      .map(toolRecord)
      .filter(Boolean)
      .filter((tool) => !claimed.has(tool.name));
    if (!tools.length) return;
    if (source === 'native_custom' && nativeChecks) {
      tools = tools.map((tool) => ({ ...tool, showCheck: true, check: nativeChecks.get(tool.name) || null }));
    }
    const serverName = mcp
      ? String(ns.server_name || ns.name || '').replace(/^MCP:\s*/i, '')
      : '';
    groups.push({
      id: String(ns.id || ns.name || (mcp ? 'mcp' : 'platform')),
      name: String(ns.name || ns.id || (mcp ? 'MCP' : 'Platform')),
      serverName,
      source,
      originLabel: String(ns.origin_label || '') || (source === 'native_custom'
        ? 'Native custom'
        : (source === 'legacy_pack_tool'
          ? 'Legacy pack tool'
          : (mcp ? `MCP · ${serverName || 'server'}` : 'Platform'))),
      scope: mcp ? 'catalog' : (source === 'native_custom' ? 'native' : 'platform'),
      agentId: '',
      mounted: null,
      enabled: true,
      tools,
    });
  });

  return groups;
}

/**
 * Search plus source/status filters in the spirit of Routines Studio.
 * source: '' | 'platform' | 'native' | 'mcp'
 * status: '' | 'available' | 'mounted' | 'configured'
 *
 * @param {object[]} groups
 * @param {{ search?: string, source?: string, status?: string }} [filters]
 * @returns {object[]}
 */
export function filterCatalogGroups(groups, filters = {}) {
  const list = Array.isArray(groups) ? groups : [];
  const q = String(filters.search || '').trim().toLowerCase();
  const source = String(filters.source || '').trim();
  const status = String(filters.status || '').trim();
  const out = [];

  list.forEach((group) => {
    if (!group) return;
    const kind = groupKind(group);
    if (source && kind !== source) return;
    if (status === 'available' && kind !== 'platform') return;
    if (status === 'mounted' && (group.source !== 'mcp' || group.mounted !== true)) return;
    if (status === 'configured' && (group.source !== 'mcp' || group.mounted !== false)) return;

    const nameHit = Boolean(q) && String(group.name || '').toLowerCase().includes(q);
    const tools = (Array.isArray(group.tools) ? group.tools : []).filter((tool) => {
      if (!q || nameHit) return true;
      const hay = `${tool.name || ''} ${tool.description || ''}`.toLowerCase();
      return hay.includes(q);
    });
    if (q && !nameHit && tools.length === 0) return;
    if (!tools.length) return;
    out.push({ ...group, tools });
  });

  return out;
}

function statusLabel(group) {
  if (group.source !== 'mcp') return 'Platform';
  if (group.mounted === true) return 'Mounted';
  if (group.mounted === false) return 'Configured';
  return 'Catalog';
}

/**
 * @param {object[]} groups
 * @returns {string}
 */
export function renderCatalogMarkup(groups) {
  const list = Array.isArray(groups) ? groups : [];
  if (!list.length) {
    return '<div class="text-[11px] text-slate-500 italic p-3" data-testid="tools-studio-catalog-empty">No tools match these filters.</div>';
  }
  return list.map((group) => {
    const serverAttr = group.source === 'mcp' && group.serverName
      ? ` data-mcp-server="${escapeHtml(group.serverName)}"`
      : '';
    const scopeNote = group.scope === 'agent' && group.agentId
      ? ` <span class="text-[10px] text-slate-500">Agent ${escapeHtml(group.agentId)}</span>`
      : '';
    const origin = dataOrigin(group);
    const rows = group.tools.map((tool) => `
      <div class="px-3 py-1.5 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between" data-testid="tools-studio-catalog-row" data-tool-name="${escapeHtml(tool.name)}" data-source="${escapeHtml(group.source)}" data-origin="${escapeHtml(origin)}"${serverAttr}>
        <div class="min-w-0 flex flex-col sm:flex-row sm:items-baseline sm:gap-2">
          <span class="font-mono text-[11px] text-slate-100">${escapeHtml(tool.name)}</span>
          ${tool.description ? `<span class="text-[11px] text-slate-400">${escapeHtml(tool.description)}</span>` : ''}
          ${tool.showCheck ? `<span data-testid="tools-studio-check-label" data-check-status="${escapeHtml(nativeCheckKey(tool.check))}" class="text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/[0.08] ${nativeCheckKey(tool.check) === 'not_checked' ? 'text-slate-400' : 'text-emerald-300'}">${escapeHtml(nativeCheckLabel(tool.check))}</span>` : ''}
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <button type="button" data-action="tools-studio-modify" data-tool-name="${escapeHtml(tool.name)}" class="px-2 py-1 rounded-lg bg-white/[0.04] text-[11px] text-slate-200 border border-white/[0.08]">Modify</button>
          <button type="button" data-action="tools-studio-delete-intent" data-tool-name="${escapeHtml(tool.name)}" class="px-2 py-1 rounded-lg bg-white/[0.04] text-[11px] text-rose-200 border border-white/[0.08]">Delete intent</button>
        </div>
      </div>`).join('');
    return `
      <section class="bg-[#13161f]/80 border border-white/[0.06] rounded-xl overflow-hidden" data-testid="tools-studio-catalog-group" data-source="${escapeHtml(group.source)}" data-origin="${escapeHtml(origin)}"${serverAttr}>
        <header class="px-3 py-2 bg-white/[0.02] border-b border-white/[0.04] flex items-center justify-between gap-2">
          <div class="min-w-0">
            <span class="text-xs font-semibold text-white">${escapeHtml(group.name)}</span>
            ${scopeNote}
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-white/[0.06]" data-testid="tools-studio-origin-label">${escapeHtml(originLabel(group))}</span>
            ${group.source === 'mcp' ? `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-white/[0.06]">${escapeHtml(statusLabel(group))}</span>` : ''}
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/50 text-cyan-300 border border-cyan-500/20">${group.tools.length}</span>
          </div>
        </header>
        <div class="divide-y divide-white/[0.04]">${rows}</div>
      </section>`;
  }).join('');
}

/**
 * @param {object[]} servers
 * @returns {string}
 */
export function formatMcpAttachStatus(servers) {
  const list = Array.isArray(servers) ? servers : [];
  const mounted = list.filter((server) => server && server.is_mounted).length;
  if (!list.length) return 'No platform MCP servers attached.';
  const noun = list.length === 1 ? 'server' : 'servers';
  return `${list.length} platform MCP ${noun} attached (${mounted} mounted).`;
}

/**
 * Read-only status rows. No attach actions.
 * @param {object[]} servers
 * @param {{ emptyHtml?: string, rowTestId?: string }} [opts]
 * @returns {string}
 */
export function renderMcpStatusRowsMarkup(servers, { emptyHtml = '', rowTestId = 'mcp-status-row' } = {}) {
  const list = Array.isArray(servers) ? servers : [];
  if (!list.length) {
    return emptyHtml || '<p class="text-[11px] text-slate-500">No MCP servers attached.</p>';
  }
  return list.map((server) => {
    const name = String(server.name || '');
    const mounted = Boolean(server.is_mounted);
    const enabled = server.enabled !== false;
    const count = Number(server.tool_count || (Array.isArray(server.tools) ? server.tools.length : 0)) || 0;
    let badge = 'Configured';
    if (!enabled) badge = 'Disabled';
    else if (mounted) badge = `Mounted (${count})`;
    const target = server.url || (Array.isArray(server.command) ? server.command.join(' ') : server.command || '');
    return `
      <div class="p-2.5 rounded-lg bg-[#08090c]/70 border border-white/[0.06] flex items-center justify-between gap-2" data-testid="${escapeHtml(rowTestId)}" data-server-name="${escapeHtml(name)}">
        <div class="min-w-0">
          <div class="text-xs font-mono text-slate-100">${escapeHtml(name)}</div>
          ${target ? `<div class="text-[11px] font-mono text-slate-500 truncate">${escapeHtml(String(target))}</div>` : ''}
        </div>
        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/[0.08] text-slate-300 shrink-0">${escapeHtml(badge)}</span>
      </div>`;
  }).join('');
}

/**
 * @param {object[]} servers
 * @returns {{ line: string, listHtml: string }}
 */
export function renderSettingsMcpStatus(servers) {
  return {
    line: formatMcpAttachStatus(servers),
    listHtml: renderMcpStatusRowsMarkup(servers, {
      rowTestId: 'settings-mcp-status-row',
      emptyHtml: '<div class="text-xs text-slate-500 italic p-3 text-center bg-[#08090c]/40 rounded-xl border border-white/[0.06]">No platform MCP servers attached. Open Tools Studio to attach one.</div>',
    }),
  };
}

/**
 * Full attach list for Tools Studio (edit / enable / test / delete).
 * @param {object[]} servers
 * @param {{ scope?: string }} [opts]
 * @returns {string}
 */
export function renderMcpServerListMarkup(servers, { scope = 'platform' } = {}) {
  const list = Array.isArray(servers) ? servers : [];
  if (!list.length) {
    return '<p data-testid="tools-studio-mcp-empty" class="text-[11px] text-slate-500 italic p-2">No MCP servers attached in this scope.</p>';
  }
  return list.map((server) => {
    const name = String(server.name || '');
    const safe = escapeHtml(name);
    const badge = mcpServerStatusBadge(server);
    const mounted = Boolean(server.is_mounted);
    const enabled = server.enabled !== false;
    const target = server.url || (Array.isArray(server.command) ? server.command.join(' ') : server.command || '');
    const connect = enabled && !mounted
      ? `<button type="button" data-action="connect" data-server-name="${safe}" class="px-2 py-1 rounded bg-emerald-950/50 text-emerald-300 border border-emerald-800/60 text-[11px]">Connect</button>`
      : '';
    return `
      <div class="p-3 rounded-lg bg-[#08090c]/80 border border-white/[0.06] space-y-2" data-testid="tools-studio-mcp-row" data-server-name="${safe}" data-mcp-scope="${escapeHtml(scope)}">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="min-w-0">
            <span class="text-xs font-mono font-semibold text-slate-100">${safe}</span>
            <span class="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/[0.08] text-slate-300" data-testid="tools-studio-mcp-status">${escapeHtml(badge)}</span>
          </div>
          <div class="flex flex-wrap items-center gap-1">
            <button type="button" data-action="edit" data-server-name="${safe}" class="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-white/[0.08] text-[11px]">Edit</button>
            <button type="button" data-action="toggle" data-server-name="${safe}" class="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-white/[0.08] text-[11px]">${enabled ? 'Disable' : 'Enable'}</button>
            <button type="button" data-action="test-saved" data-server-name="${safe}" class="px-2 py-1 rounded bg-slate-800 text-cyan-300 border border-cyan-800/50 text-[11px]">Test</button>
            ${connect}
            <button type="button" data-action="delete" data-server-name="${safe}" class="px-2 py-1 rounded bg-slate-800 text-rose-300 border border-rose-900/50 text-[11px]">Delete</button>
          </div>
        </div>
        ${target ? `<div class="text-[11px] font-mono text-slate-500 break-all">${escapeHtml(String(target))}</div>` : ''}
      </div>`;
  }).join('');
}

/**
 * @param {'platform'|'agent'} scope
 * @param {string} [agentId]
 * @returns {{ list: string, save: string, test: string, delete: (name: string) => string, mount: ((name: string) => string)|null }}
 */
export function mcpEndpoints(scope, agentId = '') {
  if (scope === 'agent') {
    const id = encodeURIComponent(String(agentId || '').trim());
    return {
      list: `/api/agents/${id}/mcp`,
      save: `/api/agents/${id}/mcp`,
      test: `/api/agents/${id}/mcp/test`,
      delete: (name) => `/api/agents/${id}/mcp/${encodeURIComponent(name)}`,
      mount: (name) => `/api/agents/${id}/mcp/${encodeURIComponent(name)}/mount`,
    };
  }
  return {
    list: '/api/settings/mcp',
    save: '/api/settings/mcp',
    test: '/api/settings/mcp/test',
    delete: (name) => `/api/settings/mcp/${encodeURIComponent(name)}`,
    mount: null,
  };
}

/**
 * @param {{ name?: string, transport?: string, commandText?: string, url?: string, headersText?: string, env?: object, enabled?: boolean }} fields
 * @returns {{ ok: true, body: object }|{ ok: false, error: string }}
 */
export function buildMcpSaveBody(fields = {}) {
  const name = String(fields.name || '').trim();
  const transport = fields.transport === 'sse' ? 'sse' : 'stdio';
  const commandText = String(fields.commandText || '').trim();
  const url = String(fields.url || '').trim();
  const headersText = String(fields.headersText || '').trim();
  const env = fields.env && typeof fields.env === 'object' && !Array.isArray(fields.env) ? fields.env : {};
  const enabled = fields.enabled !== false;
  if (!name) return { ok: false, error: 'Server name is required.' };
  if (transport === 'stdio' && !commandText) return { ok: false, error: 'Command is required for stdio.' };
  if (transport === 'sse' && !url) return { ok: false, error: 'Remote URL is required for HTTP/SSE.' };
  let headers = null;
  if (headersText) {
    try {
      headers = JSON.parse(headersText);
    } catch {
      return { ok: false, error: 'Custom headers are not valid JSON.' };
    }
    if (!headers || typeof headers !== 'object' || Array.isArray(headers)) {
      return { ok: false, error: 'Custom headers must be a JSON object.' };
    }
  }
  return {
    ok: true,
    body: {
      name,
      transport,
      command: commandText ? commandText.split(/\s+/) : null,
      url: url || null,
      headers,
      env,
      enabled,
    },
  };
}

/**
 * Tools Studio attach-row badge. Still-mounted copy is only for a live mount.
 * @param {object} server
 * @returns {string}
 */
export function mcpServerStatusBadge(server) {
  const mounted = Boolean(server && server.is_mounted);
  const enabled = !server || server.enabled !== false;
  const fromTools = server && Array.isArray(server.tools) ? server.tools.length : 0;
  const count = Number((server && server.tool_count) || fromTools) || 0;
  if (!enabled && mounted) return `Disabled (still mounted, ${count} tools)`;
  if (!enabled) return 'Disabled';
  if (mounted) return `Mounted (${count} tools)`;
  return 'Configured';
}

/**
 * Toast copy for a MCP save. Disable success is plain. Unmount failure stays a warning.
 * @param {object} body
 * @param {object} data
 * @returns {{ kind: 'success'|'warning', message: string }}
 */
export function describeMcpSaveNotice(body, data) {
  const name = String((body && body.name) || 'server');
  const disabling = Boolean(body && body.enabled === false);
  const payload = data && typeof data === 'object' ? data : {};
  const error = payload.error ? String(payload.error) : '';
  if (error && disabling) {
    if (payload.mounted !== false) {
      return { kind: 'warning', message: `Saved ${name}, but it is still mounted.` };
    }
    return { kind: 'warning', message: `Saved ${name}, but unmount failed.` };
  }
  if (error && payload.mounted === false) {
    return { kind: 'warning', message: `Saved ${name}, mount failed.` };
  }
  if (disabling) return { kind: 'success', message: `Disabled ${name}.` };
  return { kind: 'success', message: `Saved ${name}.` };
}

/**
 * Persist enable/disable by re-saving the stored server on the same contract.
 * @param {object} server
 * @param {boolean} enabled
 * @returns {object}
 */
export function serverToSaveBody(server, enabled) {
  const commandText = Array.isArray(server && server.command)
    ? server.command.join(' ')
    : String((server && server.command) || '');
  const headers = server && server.headers && typeof server.headers === 'object' ? server.headers : null;
  const built = buildMcpSaveBody({
    name: server && server.name,
    transport: (server && server.transport) || (server && server.url ? 'sse' : 'stdio'),
    commandText,
    url: (server && server.url) || '',
    headersText: headers ? JSON.stringify(headers) : '',
    env: (server && server.env) || {},
    enabled,
  });
  if (!built.ok) {
    return {
      name: server && server.name,
      transport: (server && server.transport) || 'stdio',
      command: Array.isArray(server && server.command) ? server.command : null,
      url: (server && server.url) || null,
      headers,
      env: (server && server.env) || {},
      enabled: Boolean(enabled),
    };
  }
  return built.body;
}

/**
 * @param {Function} fetchImpl
 * @param {'platform'|'agent'} scope
 * @param {string} [agentId]
 * @returns {Promise<object[]>}
 */
export async function fetchMcpServers(fetchImpl, scope, agentId = '') {
  if (scope === 'agent' && !String(agentId || '').trim()) return [];
  const endpoints = mcpEndpoints(scope, agentId);
  const res = await fetchImpl(endpoints.list);
  if (!res || !res.ok) {
    const status = res && res.status ? res.status : 0;
    throw new Error(`HTTP ${status}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/**
 * @param {Function} fetchImpl
 * @param {{ agentId?: string }} [opts]
 * @returns {Promise<object[]>}
 */
export async function loadCatalogModel(fetchImpl, { agentId = '' } = {}) {
  const capRes = await fetchImpl('/api/agent_training_factory/capabilities');
  const cap = capRes && capRes.ok ? await capRes.json() : { namespaces: [] };
  const platRes = await fetchImpl('/api/settings/mcp');
  const platformServers = platRes && platRes.ok ? await platRes.json() : [];
  let agentServers = [];
  const owner = String(agentId || '').trim();
  if (owner) {
    const agentRes = await fetchImpl(`/api/agents/${encodeURIComponent(owner)}/mcp`);
    agentServers = agentRes && agentRes.ok ? await agentRes.json() : [];
  }
  // CARD-511: native rows carry their tool check. The catalog still loads without it.
  let nativeTools = null;
  try {
    const nativeRes = await fetchImpl('/api/tools/native');
    if (nativeRes && nativeRes.ok) {
      const nativeData = await nativeRes.json();
      nativeTools = nativeData && Array.isArray(nativeData.tools) ? nativeData.tools : null;
    }
  } catch {
    nativeTools = null;
  }
  return buildCatalogGroups({
    namespaces: cap && Array.isArray(cap.namespaces) ? cap.namespaces : [],
    platformServers: Array.isArray(platformServers) ? platformServers : [],
    agentServers: Array.isArray(agentServers) ? agentServers : [],
    agentId: owner,
    nativeTools,
  });
}

/**
 * @param {{ scope?: string, agentId?: string|null }} [link]
 */
export function planToolsStudioDeepLink({ scope = 'platform', agentId = null } = {}) {
  const agent = String(agentId || '').trim();
  const resolved = scope === 'agent' || (scope !== 'platform' && agent) ? 'agent' : 'platform';
  return {
    tab: TOOLS_STUDIO_TAB,
    label: TOOLS_STUDIO_LABEL,
    scope: resolved,
    agentId: agent || null,
  };
}
