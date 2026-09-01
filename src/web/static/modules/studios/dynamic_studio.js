/**
 * Dynamic Studio Module [CARD-133].
 * Renders declarative agent pack dashboards (dashboard.json) with interactive
 * stat groups, action buttons, data tables, and live markdown editors.
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';

let activePackId = null;
let cachedDashboards = [];

export async function initDynamicStudio() {
  const refreshBtn = $('dynamicStudioRefreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      if (activePackId) {
        loadAndRenderDashboard(activePackId, true);
      }
    });
  }

  await refreshDynamicStudioTabs();
}

export async function refreshDynamicStudioTabs() {
  try {
    const resp = await fetch('/api/agent-packs/dashboards');
    if (!resp.ok) return;
    cachedDashboards = await resp.json();
    mountDynamicTabs(cachedDashboards);
  } catch (err) {
    console.warn('[DynamicStudio] Failed to load dashboards:', err);
  }
}

function mountDynamicTabs(dashboards) {
  const sidebarNav = $('sidebarNav');
  if (!sidebarNav) return;

  // Remove previously mounted dynamic tabs
  const oldTabs = $queryAll('.dynamic-studio-tab', sidebarNav);
  oldTabs.forEach(t => t.remove());

  dashboards.forEach(dash => {
    const tabId = `tab-dynamic-${dash.pack_id}`;
    const btn = document.createElement('button');
    btn.id = tabId;
    btn.setAttribute('data-tab', `dynamic-${dash.pack_id}`);
    btn.setAttribute('data-pack-id', dash.pack_id);
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-selected', 'false');
    btn.setAttribute('aria-controls', 'view-dynamic');
    btn.className = 'tab-btn dynamic-studio-tab w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800';
    
    const iconName = dash.icon || 'layout-dashboard';
    btn.innerHTML = `
      <i data-lucide="${escapeHtml(iconName)}" class="w-4 h-4 text-brand-400 flex-shrink-0"></i>
      <span class="truncate">${escapeHtml(dash.tab_title)}</span>
    `;

    btn.addEventListener('click', () => {
      switchToDynamicStudio(dash.pack_id);
    });

    sidebarNav.appendChild(btn);
  });

  safeCreateIcons();
}

export async function switchToDynamicStudio(packId) {
  activePackId = packId;

  // Deactivate other tabs
  const sidebarNav = $('sidebarNav');
  if (sidebarNav) {
    $queryAll('.tab-btn', sidebarNav).forEach(btn => {
      btn.classList.remove('active', 'bg-brand-600', 'text-white', 'shadow-sm', 'shadow-brand-500/20');
      btn.classList.add('text-slate-400');
      btn.setAttribute('aria-selected', 'false');
    });
  }

  const activeBtn = $(`tab-dynamic-${packId}`);
  if (activeBtn) {
    activeBtn.classList.add('active', 'bg-brand-600', 'text-white', 'shadow-sm', 'shadow-brand-500/20');
    activeBtn.classList.remove('text-slate-400');
    activeBtn.setAttribute('aria-selected', 'true');
  }

  // Hide all standard views
  $queryAll('.tab-view').forEach(view => {
    view.classList.add('hidden');
    view.setAttribute('aria-hidden', 'true');
  });

  // Show dynamic view
  const dynView = $('view-dynamic');
  if (dynView) {
    dynView.classList.remove('hidden');
    dynView.setAttribute('aria-hidden', 'false');
  }

  await loadAndRenderDashboard(packId);
}

async function loadAndRenderDashboard(packId, isRefresh = false) {
  try {
    const resp = await fetch(`/api/agent-packs/${encodeURIComponent(packId)}/dashboard`);
    if (!resp.ok) {
      showToast(`Could not load dashboard for ${packId}`, 'error');
      return;
    }
    const manifest = await resp.json();
    renderDashboard(manifest);
    if (isRefresh) {
      showToast('Dashboard data refreshed', 'success');
    }
  } catch (err) {
    showToast(`Error loading dashboard: ${err.message}`, 'error');
  }
}

function renderDashboard(manifest) {
  const titleEl = $('dynamicStudioTitle');
  const descEl = $('dynamicStudioDescription');
  const iconContainer = $('dynamicStudioIconContainer');
  const grid = $('dynamicStudioGrid');

  if (titleEl) titleEl.textContent = manifest.tab_title || 'Specialist Studio';
  if (descEl) descEl.textContent = manifest.description || `${manifest.pack_id} dashboard`;
  if (iconContainer) {
    iconContainer.innerHTML = `<i data-lucide="${escapeHtml(manifest.icon || 'layout-dashboard')}" class="w-4 h-4"></i>`;
  }

  if (!grid) return;
  grid.innerHTML = '';

  const cards = manifest.cards || [];
  if (cards.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-500 bg-slate-900/30 border border-slate-800 rounded-2xl p-8">
        <i data-lucide="layout-grid" class="w-10 h-10 mx-auto text-slate-600 mb-3"></i>
        <p class="text-sm font-semibold text-slate-300">No dashboard cards declared.</p>
        <p class="text-xs text-slate-500 mt-1">This pack has a studio tab but no card definitions yet.</p>
      </div>
    `;
    safeCreateIcons();
    return;
  }

  cards.forEach(card => {
    const cardEl = createCardElement(card, manifest.pack_id);
    grid.appendChild(cardEl);
  });

  safeCreateIcons();
}

function createCardElement(card, packId) {
  const colSpanClass = card.width === 'full' 
    ? 'col-span-full' 
    : card.width === 'half' 
    ? 'col-span-1 md:col-span-1 lg:col-span-1' 
    : 'col-span-1';

  const container = document.createElement('div');
  container.className = `bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur flex flex-col space-y-4 ${colSpanClass}`;

  // Card Header
  const header = document.createElement('div');
  header.className = 'flex items-center justify-between border-b border-slate-800/80 pb-3';
  header.innerHTML = `
    <div class="flex items-center space-x-2.5">
      ${card.icon ? `<div class="p-1.5 rounded-lg bg-slate-800 text-brand-400 border border-slate-700/60"><i data-lucide="${escapeHtml(card.icon)}" class="w-4 h-4"></i></div>` : ''}
      <div>
        <h3 class="font-bold text-sm text-white">${escapeHtml(card.title || 'Card')}</h3>
        ${card.description ? `<p class="text-[11px] text-slate-400">${escapeHtml(card.description)}</p>` : ''}
      </div>
    </div>
  `;
  container.appendChild(header);

  // Card Body by Type
  const body = document.createElement('div');
  body.className = 'flex-1';

  switch (card.type) {
    case 'stat_group':
      renderStatGroup(body, card);
      break;
    case 'action_group':
      renderActionGroup(body, card, packId);
      break;
    case 'data_table':
      renderDataTable(body, card, packId);
      break;
    case 'markdown_editor':
      renderMarkdownEditor(body, card, packId);
      break;
    case 'markdown_viewer':
      renderMarkdownViewer(body, card);
      break;
    default:
      body.innerHTML = `<p class="text-xs text-slate-400">Unknown card type: ${escapeHtml(card.type)}</p>`;
  }

  container.appendChild(body);
  return container;
}

function renderStatGroup(body, card) {
  const stats = card.stats || [];
  const grid = document.createElement('div');
  grid.className = 'grid grid-cols-1 sm:grid-cols-2 gap-3';

  stats.forEach(stat => {
    const accentBorder = stat.accent === 'emerald' ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-400'
      : stat.accent === 'rose' ? 'border-rose-500/30 bg-rose-950/20 text-rose-400'
      : stat.accent === 'amber' ? 'border-amber-500/30 bg-amber-950/20 text-amber-400'
      : 'border-brand-500/30 bg-brand-950/20 text-brand-400';

    const item = document.createElement('div');
    item.className = `p-3.5 rounded-xl border ${accentBorder} flex items-center justify-between`;
    item.innerHTML = `
      <div>
        <span class="text-[11px] font-semibold text-slate-400 block">${escapeHtml(stat.label)}</span>
        <span class="text-lg font-bold text-white mt-0.5 block">${escapeHtml(stat.value || '--')}</span>
      </div>
      ${stat.icon ? `<i data-lucide="${escapeHtml(stat.icon)}" class="w-5 h-5 opacity-80"></i>` : ''}
    `;
    grid.appendChild(item);
  });

  body.appendChild(grid);
}

function renderActionGroup(body, card, packId) {
  const actions = card.actions || [];
  const flexWrap = document.createElement('div');
  flexWrap.className = 'flex flex-wrap gap-2.5';

  actions.forEach(act => {
    const btn = document.createElement('button');
    const isDanger = act.variant === 'danger';
    const isSuccess = act.variant === 'success';
    
    btn.className = isDanger 
      ? 'px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center space-x-2'
      : isSuccess
      ? 'px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center space-x-2'
      : 'px-3.5 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center space-x-2';

    btn.innerHTML = `
      ${act.icon ? `<i data-lucide="${escapeHtml(act.icon)}" class="w-3.5 h-3.5"></i>` : ''}
      <span>${escapeHtml(act.label)}</span>
    `;

    btn.addEventListener('click', async () => {
      if (act.confirm_message && !confirm(act.confirm_message)) return;
      
      const originalText = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin mr-1">⏳</span> Executing...`;

      try {
        const resp = await fetch(`/api/agent-packs/${encodeURIComponent(packId)}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: act.tool,
            args: act.args || {},
          }),
        });
        const res = await resp.json();
        if (res.success) {
          showToast(typeof res.output === 'string' ? res.output : `${act.label} completed successfully!`, 'success');
        } else {
          showToast(`Action failed: ${res.error || 'Unknown error'}`, 'error');
        }
      } catch (err) {
        showToast(`Request failed: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        safeCreateIcons();
      }
    });

    flexWrap.appendChild(btn);
  });

  body.appendChild(flexWrap);
}

function renderDataTable(body, card, packId) {
  const columns = card.columns || [];
  const rows = card.rows || [];
  const rowActions = card.row_actions || [];

  const tableContainer = document.createElement('div');
  tableContainer.className = 'overflow-x-auto border border-slate-800 rounded-xl';

  const table = document.createElement('table');
  table.className = 'w-full text-left text-xs text-slate-300';

  // Thead
  const thead = document.createElement('thead');
  thead.className = 'bg-slate-800/80 text-slate-400 font-semibold border-b border-slate-700/80';
  let theadHtml = '<tr>';
  columns.forEach(col => {
    theadHtml += `<th class="px-4 py-2.5">${escapeHtml(col.label)}</th>`;
  });
  if (rowActions.length > 0) {
    theadHtml += `<th class="px-4 py-2.5 text-right">Actions</th>`;
  }
  theadHtml += '</tr>';
  thead.innerHTML = theadHtml;
  table.appendChild(thead);

  // Tbody
  const tbody = document.createElement('tbody');
  tbody.className = 'divide-y divide-slate-800/60';

  if (rows.length === 0) {
    const colCount = columns.length + (rowActions.length > 0 ? 1 : 0);
    tbody.innerHTML = `<tr><td colspan="${colCount}" class="px-4 py-6 text-center text-slate-500">No entries recorded.</td></tr>`;
  } else {
    rows.forEach(row => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition';
      
      let rowHtml = '';
      columns.forEach(col => {
        const val = row[col.key] !== undefined ? row[col.key] : '--';
        rowHtml += `<td class="px-4 py-3 font-medium text-slate-200">${escapeHtml(String(val))}</td>`;
      });

      if (rowActions.length > 0) {
        rowHtml += `<td class="px-4 py-3 text-right space-x-1.5"></td>`;
      }
      tr.innerHTML = rowHtml;

      if (rowActions.length > 0) {
        const actionTd = $query('td:last-child', tr);
        rowActions.forEach(act => {
          const actBtn = document.createElement('button');
          actBtn.className = 'px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-[11px] font-semibold text-slate-200 transition';
          actBtn.textContent = act.label;
          actBtn.addEventListener('click', async () => {
            const mappedArgs = {};
            if (act.arg_mapping) {
              for (const [argKey, rowKey] of Object.entries(act.arg_mapping)) {
                mappedArgs[argKey] = row[rowKey];
              }
            }
            try {
              const resp = await fetch(`/api/agent-packs/${encodeURIComponent(packId)}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tool: act.tool, args: mappedArgs }),
              });
              const res = await resp.json();
              if (res.success) {
                showToast(`${act.label} succeeded!`, 'success');
              } else {
                showToast(`Action failed: ${res.error}`, 'error');
              }
            } catch (err) {
              showToast(`Error: ${err.message}`, 'error');
            }
          });
          if (actionTd) actionTd.appendChild(actBtn);
        });
      }

      tbody.appendChild(tr);
    });
  }

  table.appendChild(tbody);
  tableContainer.appendChild(table);
  body.appendChild(tableContainer);
}

function renderMarkdownViewer(body, card) {
  const container = document.createElement('div');
  container.className = 'prose prose-invert max-w-none text-xs leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800 overflow-y-auto max-h-96';
  
  const rawMarkdown = card.content || '# Document\n\nNo content available.';
  if (window.marked && typeof window.marked.parse === 'function') {
    container.innerHTML = window.marked.parse(rawMarkdown);
  } else {
    container.textContent = rawMarkdown;
  }
  body.appendChild(container);
}

function renderMarkdownEditor(body, card, packId) {
  const wrapper = document.createElement('div');
  wrapper.className = 'space-y-3';

  const toolbar = document.createElement('div');
  toolbar.className = 'flex items-center justify-between';
  toolbar.innerHTML = `
    <div class="text-[11px] text-slate-400 font-mono">${escapeHtml(card.file_path || 'journal.md')}</div>
    <button class="save-md-btn px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5">
      <i data-lucide="save" class="w-3.5 h-3.5"></i>
      <span>Save Document</span>
    </button>
  `;

  const textarea = document.createElement('textarea');
  textarea.className = 'w-full h-64 bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none focus:border-brand-500 transition resize-y';
  textarea.value = card.content || '# Daily Garden Journal\n\n- [x] Morning check completed\n- [ ] Afternoon soil inspection\n';

  const saveBtn = $query('.save-md-btn', toolbar);
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      saveBtn.disabled = true;
      saveBtn.innerHTML = `<span>Saving...</span>`;
      try {
        // Save markdown document
        const saveTool = card.save_tool || 'write_project_file';
        const resp = await fetch(`/api/agent-packs/${encodeURIComponent(packId)}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: saveTool,
            args: {
              path: card.file_path || 'docs/journal.md',
              content: textarea.value,
            },
          }),
        });
        await resp.json();
        showToast('Document saved successfully!', 'success');
      } catch (err) {
        showToast(`Failed to save document: ${err.message}`, 'error');
      } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save Document</span>`;
        safeCreateIcons();
      }
    });
  }

  wrapper.appendChild(toolbar);
  wrapper.appendChild(textarea);
  body.appendChild(wrapper);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
