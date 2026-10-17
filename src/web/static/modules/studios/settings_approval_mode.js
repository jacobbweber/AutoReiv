/**
 * CARD-701: Settings Studio > Approval Mode (strict | balanced | hands_off).
 * Reads and saves GET/PUT /api/settings/approval-mode with precedence:
 * DB setting > AUTOREIV_APPROVAL_MODE env > default ("balanced").
 */

export const APPROVAL_MODE_URL = '/api/settings/approval-mode';

export const APPROVAL_MODES = [
  {
    value: 'strict',
    label: 'Strict — Hold all newly authored tools for review',
    summary: 'Every newly authored skill tool is saved disabled until you enable it in Tools Studio.',
  },
  {
    value: 'balanced',
    label: 'Balanced (Default) — Auto-enable read-only tools; hold state-changing & destructive tools',
    summary: 'Read-only tools mount automatically; state-changing and destructive tools wait for review.',
  },
  {
    value: 'hands_off',
    label: 'Hands-off — Auto-enable read-only & state-changing tools; hold destructive tools',
    summary: 'Read-only and state-changing tools mount automatically; destructive tools still wait for review.',
  },
];

function byId(doc, id) {
  return doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null;
}

function setStatus(els, text, ok = true) {
  if (!els?.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
}

function renderSummary(els, mode, source) {
  const entry = APPROVAL_MODES.find((m) => m.value === mode) || APPROVAL_MODES[1];
  if (els?.select) {
    els.select.value = entry.value;
  }
  if (els?.summary) {
    const srcNote = source ? ` (source: ${source})` : '';
    els.summary.textContent = `${entry.summary}${srcNote}`;
  }
}

export async function loadApprovalMode(
  els,
  { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {},
) {
  if (!fetchFn || !els?.select) return null;
  try {
    const res = await fetchFn(APPROVAL_MODE_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const mode = data.mode || data.approval_mode || 'balanced';
    renderSummary(els, mode, data.source);
    return data;
  } catch (err) {
    setStatus(els, `Could not load approval mode: ${err.message}`, false);
    return null;
  }
}

export async function saveApprovalMode(
  els,
  { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {},
) {
  if (!fetchFn || !els?.select) return null;
  const mode = String(els.select.value || 'balanced').trim();
  try {
    const res = await fetchFn(APPROVAL_MODE_URL, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    const resolved = data.mode || data.approval_mode || mode;
    renderSummary(els, resolved, data.source);
    setStatus(els, `Saved approval mode: ${resolved}.`, true);
    return data;
  } catch (err) {
    setStatus(els, `Could not save approval mode: ${err.message}`, false);
    return null;
  }
}

export function setupApprovalMode({
  doc = typeof document !== 'undefined' ? document : null,
  fetchFn = typeof fetch !== 'undefined' ? fetch : null,
} = {}) {
  if (!doc) return null;
  const els = {
    card: byId(doc, 'settingsApprovalModeCard'),
    select: byId(doc, 'approvalModeSelect'),
    saveBtn: byId(doc, 'approvalModeSaveBtn'),
    status: byId(doc, 'approvalModeStatus'),
    summary: byId(doc, 'approvalModeSummary'),
  };
  if (!els.select || !els.saveBtn) return null;

  if (els.saveBtn.dataset && els.saveBtn.dataset.wired !== '1') {
    els.saveBtn.dataset.wired = '1';
    els.saveBtn.addEventListener('click', () => {
      saveApprovalMode(els, { fetchFn });
    });
    els.select.addEventListener('change', () => {
      renderSummary(els, els.select.value, null);
    });
  }

  loadApprovalMode(els, { fetchFn });
  return els;
}
