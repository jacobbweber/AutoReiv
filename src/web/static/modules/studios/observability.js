/**
 * Observability Studio Module [REQ-FE-001, REQ-WEB-005, REQ-OBS-006]
 */

import { $, $query } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { debounce } from '../utils/debounce.js';

export function initObservability(state, _callbacks = {}) {
  const refreshKpiBtn = $('refreshKpiBtn');
  const kpiTotalTurns = $('kpiTotalTurns');
  const kpiTotalTokens = $('kpiTotalTokens');
  const kpiAvgDuration = $('kpiAvgDuration');
  const kpiErrorRate = $('kpiErrorRate');
  const agentKpiTableBody = $('agentKpiTableBody');
  const toolKpiTableBody = $('toolKpiTableBody');

  const systemLogsTerminal = $('systemLogsTerminal');
  const logLevelSelect = $('logLevelSelect');
  const logSearchInput = $('logSearchInput');
  const logStreamToggleBtn = $('logStreamToggleBtn');
  const logStreamToggleText = $('logStreamToggleText');
  const clearLogsBtn = $('clearLogsBtn');

  let isLogStreamPaused = false;

  async function loadObservability() {
    try {
      const res = await fetch('/api/observability/kpi');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (kpiTotalTurns) kpiTotalTurns.textContent = data.overview.total_turns || 0;
      if (kpiTotalTokens) kpiTotalTokens.textContent = (data.overview.total_tokens || 0).toLocaleString();
      if (kpiAvgDuration) kpiAvgDuration.textContent = `${data.overview.avg_turn_duration_ms || 0} ms`;
      if (kpiErrorRate) kpiErrorRate.textContent = `${data.overview.error_rate_pct || 0}%`;

      // Render Agents table
      if (agentKpiTableBody) {
        agentKpiTableBody.innerHTML = '';
        (data.agents || []).forEach((a) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(a.agent_id)}</td>
            <td class="p-2.5">${a.turn_count}</td>
            <td class="p-2.5 font-mono text-indigo-400">${(a.total_tokens || 0).toLocaleString()}</td>
            <td class="p-2.5">${a.tool_call_count}</td>
            <td class="p-2.5 text-rose-400">${a.error_count}</td>
            <td class="p-2.5">${a.avg_duration_ms} ms</td>
          `;
          agentKpiTableBody.appendChild(row);
        });
      }

      // Render Tools table
      if (toolKpiTableBody) {
        toolKpiTableBody.innerHTML = '';
        (data.tools || []).forEach((t) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(t.tool_name)}</td>
            <td class="p-2.5">${t.total_invocations}</td>
            <td class="p-2.5 text-emerald-400">${t.success_count}</td>
            <td class="p-2.5 text-rose-400">${t.failure_count}</td>
            <td class="p-2.5 font-bold text-cyan-400">${t.success_rate_pct}%</td>
            <td class="p-2.5">${t.avg_duration_ms} ms</td>
          `;
          toolKpiTableBody.appendChild(row);
        });
      }

      // Also refresh logs
      await loadSystemLogs();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load observability data:', err);
    }
  }

  async function loadSystemLogs() {
    if (!systemLogsTerminal || isLogStreamPaused) return;
    try {
      const level = logLevelSelect ? logLevelSelect.value : 'ALL';
      const query = logSearchInput ? logSearchInput.value.trim() : '';
      const url = `/api/observability/logs?limit=150&level=${encodeURIComponent(level)}&query=${encodeURIComponent(query)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const logs = await res.json();

      if (!logs || logs.length === 0) {
        systemLogsTerminal.innerHTML = '<div class="text-slate-500 italic py-2">No matching logs in buffer.</div>';
        return;
      }

      const isAtBottom =
        systemLogsTerminal.scrollHeight - systemLogsTerminal.scrollTop <= systemLogsTerminal.clientHeight + 40;

      systemLogsTerminal.innerHTML = logs
        .map((l) => {
          let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
          if (l.level === 'ERROR') badgeColor = 'bg-rose-950 text-rose-300 border-rose-800';
          else if (l.level === 'WARN' || l.level === 'WARNING')
            badgeColor = 'bg-amber-950 text-amber-300 border-amber-800';
          else if (l.level === 'INFO') badgeColor = 'bg-indigo-950 text-indigo-300 border-indigo-800';

          const timeStr = l.timestamp ? l.timestamp.split(' ')[1] || l.timestamp : '';
          return `
          <div class="flex items-start space-x-2 py-0.5 leading-relaxed hover:bg-slate-900/50 px-1 rounded transition">
            <span class="text-slate-500 text-[10px] select-none flex-shrink-0 font-mono">${escapeHtml(timeStr)}</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold uppercase border flex-shrink-0 ${badgeColor}">${escapeHtml(l.level)}</span>
            <span class="text-slate-400 font-mono text-[11px] flex-shrink-0">[${escapeHtml(l.logger)}]</span>
            <span class="text-slate-200 break-all">${escapeHtml(l.message)}</span>
          </div>
        `;
        })
        .join('');

      if (isAtBottom) {
        systemLogsTerminal.scrollTop = systemLogsTerminal.scrollHeight;
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to fetch system logs:', err);
    }
  }

  if (logLevelSelect) logLevelSelect.addEventListener('change', loadSystemLogs);
  if (logSearchInput) logSearchInput.addEventListener('input', debounce(loadSystemLogs, 300));

  if (logStreamToggleBtn) {
    logStreamToggleBtn.addEventListener('click', () => {
      isLogStreamPaused = !isLogStreamPaused;
      if (logStreamToggleText) logStreamToggleText.textContent = isLogStreamPaused ? 'Resume' : 'Pause';
      logStreamToggleBtn.classList.toggle('text-emerald-400', isLogStreamPaused);
      if (!isLogStreamPaused) loadSystemLogs();
    });
  }

  if (clearLogsBtn) {
    clearLogsBtn.addEventListener('click', async () => {
      try {
        await fetch('/api/observability/logs/clear', { method: 'POST' });
        if (systemLogsTerminal)
          systemLogsTerminal.innerHTML = '<div class="text-slate-500 italic py-2">Buffer cleared.</div>';
      } catch (err) {
        console.error('[AutoReiv UI] Failed to clear logs:', err);
      }
    });
  }

  if (refreshKpiBtn) refreshKpiBtn.addEventListener('click', loadObservability);

  // Poll logs periodically when in Observability view
  setInterval(() => {
    const activeTab = $query('.tab-view:not(.hidden)');
    if (activeTab && activeTab.id === 'view-observability' && !isLogStreamPaused) {
      loadSystemLogs();
    }
  }, 2500);

  return {
    loadObservability,
    loadSystemLogs,
  };
}
