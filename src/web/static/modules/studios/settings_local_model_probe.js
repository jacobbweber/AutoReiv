/**
 * CARD-703: Local inference port auto-probing in Models / Settings Studio.
 * Scans local inference ports (8000, 8006, 11434 + configured local URLs) via POST /api/models/probe-local
 * and renders one-click "Use Model" cards that activate the selected endpoint and model.
 */

export const PROBE_LOCAL_URL = '/api/models/probe-local';

function byId(doc, id) {
  return doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null;
}

function escapeText(raw) {
  return String(raw ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function setStatus(els, text, ok = true) {
  if (!els?.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
}

function ensureDomElements(doc) {
  let card = byId(doc, 'settingsLocalProbeCard');
  let scanBtn = byId(doc, 'scanLocalServersBtn');
  let status = byId(doc, 'localModelProbeStatus');
  let results = byId(doc, 'localModelProbeResults');

  if (!scanBtn && doc && typeof doc.createElement === 'function') {
    const anchor = byId(doc, 'settingsApprovalModeCard') || byId(doc, 'discoverModelsBtn')?.closest('div');
    if (anchor && anchor.parentNode) {
      card = doc.createElement('div');
      card.id = 'settingsLocalProbeCard';
      card.setAttribute('data-testid', 'settings-local-probe-card');
      card.className =
        'p-5 rounded-xl bg-[#0e1015]/90 border border-white/[0.06] space-y-3 backdrop-blur-sm shadow-sm';
      card.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-bold text-white flex items-center space-x-2">
              <i data-lucide="radar" class="w-4 h-4 text-cyan-400"></i>
              <span>Local Inference Auto-Probe</span>
            </h3>
            <p class="text-xs text-slate-400">Scan local ports (8000, 8006, 11434) and LAN endpoints for OpenAI-compatible /v1/models servers.</p>
          </div>
          <button id="scanLocalServersBtn" data-testid="scan-local-servers-btn" type="button" class="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all">
            Scan Local Servers
          </button>
        </div>
        <p id="localModelProbeStatus" data-testid="local-model-probe-status" class="text-[11px] text-slate-400">Click "Scan Local Servers" to probe ports 8000, 8006, and 11434.</p>
        <div id="localModelProbeResults" data-testid="local-model-probe-results" class="grid grid-cols-1 md:grid-cols-2 gap-2.5"></div>
      `;
      if (anchor.id === 'settingsApprovalModeCard' && anchor.nextSibling) {
        anchor.parentNode.insertBefore(card, anchor.nextSibling);
      } else {
        anchor.parentNode.appendChild(card);
      }
      scanBtn = byId(doc, 'scanLocalServersBtn');
      status = byId(doc, 'localModelProbeStatus');
      results = byId(doc, 'localModelProbeResults');
    }
  }

  return {
    doc,
    card,
    scanBtn,
    status,
    results,
    presetSelect: byId(doc, 'provPresetSelect'),
    hostInput: byId(doc, 'provHostInput'),
    modelSelect: byId(doc, 'provModelSelect'),
    activeProviderTag: byId(doc, 'activeProviderTag'),
  };
}

export async function activateLocalModel(
  item,
  els,
  { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {},
) {
  if (!fetchFn || !item?.model || !item?.base_url) return null;
  try {
    const res = await fetchFn(PROBE_LOCAL_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        activate: {
          provider_id: item.provider_id || 'vllm',
          base_url: item.base_url,
          model: item.model,
        },
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    const act = data.activated || item;
    if (els?.presetSelect) {
      els.presetSelect.value = act.provider_id;
    }
    if (els?.hostInput) {
      els.hostInput.value = act.base_url;
    }
    if (els?.activeProviderTag) {
      els.activeProviderTag.textContent = act.provider_id;
    }
    if (els?.modelSelect) {
      const existing = Array.from(els.modelSelect.options || []).find((o) => o.value === act.model);
      if (!existing && els.doc && typeof els.doc.createElement === 'function') {
        const opt = els.doc.createElement('option');
        opt.value = act.model;
        opt.textContent = `${act.model} (${act.provider_id})`;
        els.modelSelect.appendChild(opt);
      }
      els.modelSelect.value = act.model;
    }
    setStatus(els, `Activated ${act.model} (${act.provider_id} @ ${act.base_url}).`, true);
    return data;
  } catch (err) {
    setStatus(els, `Could not activate model: ${err.message}`, false);
    return null;
  }
}

export function renderProbeResults(els, data, { fetchFn } = {}) {
  if (!els?.results) return;
  const models = Array.isArray(data?.models) ? data.models : [];
  els.results.innerHTML = '';
  if (models.length === 0) {
    els.results.innerHTML =
      '<div class="col-span-full p-3 rounded-lg bg-[#08090c]/60 border border-white/[0.06] text-xs text-slate-400">No active local inference endpoints responded on scanned ports.</div>';
    return;
  }

  for (const item of models) {
    const card = els.doc.createElement('div');
    card.setAttribute('data-testid', 'local-model-card');
    card.setAttribute('data-model-id', item.model);
    card.setAttribute('data-provider-id', item.provider_id);
    card.className =
      'p-3 rounded-lg bg-[#08090c]/80 border border-white/[0.08] flex items-center justify-between gap-2';
    card.innerHTML = `
      <div class="min-w-0 flex-1">
        <div class="font-mono text-xs font-semibold text-white truncate" title="${escapeText(item.model)}">${escapeText(item.model)}</div>
        <div class="text-[11px] text-slate-400 truncate">${escapeText(item.provider_id)} &bull; ${escapeText(item.base_url)} (${escapeText(item.latency_ms ?? 0)}ms)</div>
      </div>
      <button type="button" data-use-local-model="${escapeText(item.model)}" class="shrink-0 px-2.5 py-1 rounded-md bg-brand-600 hover:bg-brand-500 text-white text-[11px] font-semibold transition-all">
        Use Model
      </button>
    `;
    const useBtn = card.querySelector('[data-use-local-model]');
    if (useBtn) {
      useBtn.addEventListener('click', async () => {
        useBtn.disabled = true;
        const out = await activateLocalModel(item, els, { fetchFn });
        useBtn.disabled = false;
        if (out) {
          useBtn.textContent = 'Active';
        }
      });
    }
    els.results.appendChild(card);
  }
}

export async function scanLocalServers(
  els,
  { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {},
) {
  if (!fetchFn || !els) return null;
  if (els.scanBtn) els.scanBtn.disabled = true;
  setStatus(els, 'Scanning local ports (8000, 8006, 11434)...', true);
  try {
    const res = await fetchFn(PROBE_LOCAL_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    renderProbeResults(els, data, { fetchFn });
    const totalModels = Number(data.total_models || (data.models || []).length || 0);
    const totalServers = Number(data.total_servers || (data.servers || []).length || 0);
    setStatus(
      els,
      `Discovered ${totalModels} model(s) across ${totalServers} local server(s).`,
      totalModels > 0,
    );
    return data;
  } catch (err) {
    setStatus(els, `Local scan failed: ${err.message}`, false);
    return null;
  } finally {
    if (els.scanBtn) els.scanBtn.disabled = false;
  }
}

export function setupLocalModelProbe({
  doc = typeof document !== 'undefined' ? document : null,
  fetchFn = typeof fetch !== 'undefined' ? fetch : null,
} = {}) {
  if (!doc) return null;
  const els = ensureDomElements(doc);
  if (!els.scanBtn) return null;
  if (els.scanBtn.dataset && els.scanBtn.dataset.wired !== '1') {
    els.scanBtn.dataset.wired = '1';
    els.scanBtn.addEventListener('click', () => {
      scanLocalServers(els, { fetchFn });
    });
  }
  return els;
}
