/** CARD-602: Settings > Allowed browser origins (phone reverse proxy extras). */

export const ALLOWED_ORIGINS_URL = '/api/settings/allowed-origins';

export function parseOriginsField(raw) {
  return String(raw ?? '')
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export async function loadAllowedOrigins(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!fetchFn || !els?.input) return null;
  const res = await fetchFn(ALLOWED_ORIGINS_URL);
  if (!res.ok) throw new Error(`Load failed (${res.status})`);
  const data = await res.json();
  els.input.value = Array.isArray(data.origins) ? data.origins.join('\n') : '';
  return data;
}

export async function saveAllowedOrigins(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!fetchFn || !els?.input) return null;
  const origins = parseOriginsField(els.input.value);
  const res = await fetchFn(ALLOWED_ORIGINS_URL, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ origins }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Save failed (${res.status})`);
  els.input.value = (data.origins || []).join('\n');
  return data;
}

export function setupAllowedOrigins({
  doc = typeof document !== 'undefined' ? document : null,
  fetchFn = typeof fetch !== 'undefined' ? fetch : null,
} = {}) {
  if (!doc) return;
  const els = {
    input: doc.getElementById('allowedOriginsInput'),
    saveBtn: doc.getElementById('allowedOriginsSaveBtn'),
    status: doc.getElementById('allowedOriginsStatus'),
  };
  if (!els.input || !els.saveBtn) return;
  const setStatus = (text, ok) => {
    if (!els.status) return;
    els.status.textContent = text;
    els.status.className = `text-[11px] ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
  };
  loadAllowedOrigins(els, { fetchFn }).catch((err) => setStatus(String(err.message || err), false));
  els.saveBtn.addEventListener('click', async () => {
    try {
      await saveAllowedOrigins(els, { fetchFn });
      setStatus('Saved.', true);
    } catch (err) {
      setStatus(String(err.message || err), false);
    }
  });
}
