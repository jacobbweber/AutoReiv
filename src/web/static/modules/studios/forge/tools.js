/**
 * Agent Studio: Tools, Baseline Callables, Remote MCP status & Credential Grants [CARD-183, CARD-421]
 * Full MCP attach lives in Tools Studio. This card shows mounted-count status and opens Tools Studio.
 */

import { $, $queryAll, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { renderMcpStatusRowsMarkup } from '../tools_studio_catalog.js';

export function renderToolBadgeHtml(tool, activeAgent = null) {
  const tObj = typeof tool === 'string' ? { name: tool } : (tool || {});
  const name = tObj.name || '';
  const isMcp = Boolean(
    tObj.is_mcp ||
    tObj.deliverable_type === 'mcp' ||
    tObj.type === 'mcp' ||
    name.startsWith('mcp_') ||
    (activeAgent && activeAgent.mcp_server && activeAgent.mcp_server.enabled)
  );
  return isMcp
    ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 uppercase tracking-wide">MCP Server</span>'
    : '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/80 uppercase tracking-wide">Native Tool</span>';
}

export function baselineToolCardHtml(tool) {
  const tObj = typeof tool === 'string' ? { name: tool, description: '' } : (tool || {});
  const name = tObj.name || '';
  const desc = tObj.description || '';
  return `
    <div class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-emerald-950/70 border border-emerald-700/60 text-xs text-slate-200 select-none shadow-sm" title="${escapeHtml(desc)}">
      <input type="checkbox" checked disabled class="hidden" title="Enforced platform required for all agents">
      <i data-lucide="lock" class="w-3 h-3 text-emerald-400 shrink-0"></i>
      <span class="font-mono text-[11px] font-semibold text-emerald-200">${escapeHtml(name)}</span>
      <span class="px-1 py-0.2 rounded text-[8px] font-mono font-bold bg-emerald-900/80 text-emerald-300 border border-emerald-600/50 uppercase">OS BASELINE</span>
    </div>
  `;
}

export function renderBaselineTools(gridEl = null) {
  const grid = gridEl || $('forgeBaselineGrid');
  if (!grid) return;
  const requiredPrimitives = [
    { name: 'activate_skill', description: 'Activate a procedural skill runbook into the current session context.' },
    { name: 'ask_clarification', description: 'Ask the human operator a clarifying question when requirements are ambiguous.' },
    { name: 'handoff_to_agent', description: 'Handoff the conversation or task to another agent specialist.' },
    { name: 'lookup_agents', description: 'Query available agents and their capabilities.' },
    { name: 'get_session_info', description: 'Inspect active session metadata and runtime state.' },
  ];
  grid.innerHTML = requiredPrimitives.map((t) => baselineToolCardHtml(t)).join('');
  safeCreateIcons();
}

export async function loadAgentCapabilityGaps(agentId, callbacks = {}) {
  const agentBacklogList = $('agentBacklogList');
  const agentBacklogCountBadge = $('agentBacklogCountBadge');
  const forgeTrainAgentBtn = $('forgeTrainAgentBtn');
  if (!agentBacklogList) return;
  if (!agentId) {
    agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
    return;
  }
  try {
    const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps?status=pending`);
    const data = res.ok ? await res.json() : {};
    const items = Array.isArray(data) ? data : (data.gaps || []);
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = String(items.length);
    if (!items.length) {
      agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
      return;
    }
    agentBacklogList.innerHTML = items.map((gap) => `
      <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800 space-y-1.5" data-gap-id="${escapeHtml(gap.id)}">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-amber-300 font-mono">${escapeHtml(gap.identified_capability || gap.missing_capability || 'Missing Capability')}</span>
          <div class="flex items-center space-x-1.5">
            <button type="button" class="btn-open-factory-gap px-2 py-0.5 rounded bg-brand-600 hover:bg-brand-500 text-white text-[10px] font-semibold transition" data-gap-id="${escapeHtml(gap.id)}" title="Open Training Factory for this agent">Open Training Factory</button>
            <button type="button" class="btn-dismiss-gap px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-medium transition" data-gap-id="${escapeHtml(gap.id)}">Dismiss</button>
          </div>
        </div>
        ${gap.suggested_tool_name ? `<div class="text-[10px] text-slate-400 font-mono">Suggested tool: <span class="text-emerald-400">${escapeHtml(gap.suggested_tool_name)}</span></div>` : ''}
        <p class="text-[11px] text-slate-400 whitespace-pre-wrap">${escapeHtml(gap.turn_text || gap.user_prompt || '')}</p>
      </div>
    `).join('');

    agentBacklogList.querySelectorAll('.btn-open-factory-gap').forEach((btn) => {
      btn.addEventListener('click', () => {
        // CARD-306: Forge does not launch a second lab — open Training Factory for this agent
        if (typeof callbacks.openFactoryStudio === 'function') {
          callbacks.openFactoryStudio(agentId);
        } else if (typeof window !== 'undefined' && typeof window.openFactoryStudioForAgent === 'function') {
          window.openFactoryStudioForAgent(agentId);
        } else if (typeof forgeTrainAgentBtn !== 'undefined' && forgeTrainAgentBtn) {
          forgeTrainAgentBtn.click();
        } else {
          showToast('Open Factory Studio from the dock to train this gap.', 'info');
        }
      });
    });

    agentBacklogList.querySelectorAll('.btn-dismiss-gap').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const gapId = e.currentTarget.dataset.gapId;
        try {
          const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps/${encodeURIComponent(gapId)}`, { method: 'DELETE' });
          if (!delRes.ok) throw new Error('Failed to dismiss gap');
          showToast('Capability gap dismissed', 'info');
          await loadAgentCapabilityGaps(agentId, callbacks);
        } catch (err) {
          showToast(String(err.message || err), 'error');
        }
      });
    });
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load capability gaps:', err);
    agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
  }
}

export function renderAgentMcpServers(_agentId, servers, _opts = {}) {
  const forgeMcpServerList = $('forgeMcpServerList');
  const forgeMcpServerCountBadge = $('forgeMcpServerCountBadge');
  if (!forgeMcpServerList) return;
  const list = Array.isArray(servers) ? servers : [];
  if (forgeMcpServerCountBadge) {
    forgeMcpServerCountBadge.textContent = String(list.length);
  }
  forgeMcpServerList.innerHTML = renderMcpStatusRowsMarkup(list, {
    rowTestId: 'forge-mcp-status-row',
    emptyHtml: '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>',
  });
}

export async function loadAgentMcpServers(agentId, { getActiveAgent = null, onServersChanged = null } = {}) {
  const forgeMcpServerList = $('forgeMcpServerList');
  const forgeMcpServerCountBadge = $('forgeMcpServerCountBadge');
  if (!forgeMcpServerList) return [];
  if (!agentId) {
    forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>';
    if (forgeMcpServerCountBadge) forgeMcpServerCountBadge.textContent = '0';
    return [];
  }
  try {
    const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp`);
    const servers = res.ok ? await res.json() : [];
    const currentAgentMcpServers = Array.isArray(servers) ? servers : [];
    const activeAgent = typeof getActiveAgent === 'function' ? getActiveAgent() : null;
    if (activeAgent) {
      activeAgent.mcp_servers = currentAgentMcpServers;
    }
    if (typeof onServersChanged === 'function') {
      onServersChanged(currentAgentMcpServers);
    }
    renderAgentMcpServers(agentId, currentAgentMcpServers, { getActiveAgent, onServersChanged });
    return currentAgentMcpServers;
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load agent MCP servers:', err);
    forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">Failed to load MCP servers.</p>';
    return [];
  }
}

export async function loadAgentCredentialGrants(agent) {
  const forgeCredentialGrantsList = $('forgeCredentialGrantsList');
  const forgeCredentialCountBadge = $('forgeCredentialCountBadge');
  if (!forgeCredentialGrantsList) return;
  const allowed = new Set(agent ? (agent.allowed_credentials || []) : []);
  try {
    const res = await fetch('/api/vault/credentials');
    if (!res.ok) {
      forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">Failed to load credentials from vault.</p>';
      if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
      return;
    }
    const creds = await res.json();
    if (!Array.isArray(creds) || creds.length === 0) {
      forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">No credentials configured in Vault. Add credentials in Settings Studio.</p>';
      if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
      return;
    }

    forgeCredentialGrantsList.innerHTML = creds.map((c) => {
      const isChecked = allowed.has(c.id);
      return `
        <label class="flex items-center space-x-2.5 p-2 rounded-lg bg-slate-800/60 border border-slate-700/60 hover:border-slate-600 transition cursor-pointer">
          <input type="checkbox" value="${escapeHtml(c.id)}" class="forge-credential-checkbox rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/20 bg-slate-900 h-4 w-4" ${isChecked ? 'checked' : ''}>
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold text-slate-200 truncate">${escapeHtml(c.name)}</span>
              <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-700/50 text-slate-300 border border-slate-600/40 uppercase">${escapeHtml(c.type || 'generic')}</span>
            </div>
            <span class="text-[10px] font-mono text-slate-400 truncate block">${escapeHtml(c.id)}</span>
          </div>
        </label>
      `;
    }).join('');

    const updateCount = () => {
      const checkedCount = $queryAll('.forge-credential-checkbox:checked', forgeCredentialGrantsList).length;
      if (forgeCredentialCountBadge) {
        forgeCredentialCountBadge.textContent = String(checkedCount);
      }
    };

    $queryAll('.forge-credential-checkbox', forgeCredentialGrantsList).forEach((cb) => {
      cb.addEventListener('change', updateCount);
    });

    updateCount();
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load credential grants:', err);
    forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">Failed to load credentials.</p>';
    if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
  }
}

/**
 * Opens Tools Studio for this agent's MCP attach. The full form is not on this card. [CARD-421]
 * @param {{ openToolsStudio?: Function }} [opts]
 */
export function setupAgentMcpControls({ openToolsStudio = null } = {}) {
  const forgeOpenToolsStudioBtn = $('forgeOpenToolsStudioBtn');
  if (!forgeOpenToolsStudioBtn || forgeOpenToolsStudioBtn.dataset.bound === '1') return;
  forgeOpenToolsStudioBtn.dataset.bound = '1';
  forgeOpenToolsStudioBtn.addEventListener('click', () => {
    const select = $('forgeAgentSelect');
    const agentId = select ? String(select.value || '').trim() : '';
    if (typeof openToolsStudio === 'function') {
      openToolsStudio(agentId);
      return;
    }
    if (typeof window !== 'undefined' && typeof window.openToolsStudio === 'function') {
      window.openToolsStudio({ scope: agentId ? 'agent' : 'platform', agentId: agentId || null });
    }
  });
}
