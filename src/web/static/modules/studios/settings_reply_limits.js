/**
 * CARD-574: Settings > Models: reply limits (CARD-567) for every streaming model reply.
 * Reads and saves GET/PUT /api/settings/reply-limits. An empty or 0 field clears the saved value
 * (back to env AUTOREIV_MAX_REPLY_TOKENS / AUTOREIV_MAX_REPLY_SECONDS, then the defaults 32768 / 1200).
 * CARD-585: the seconds count from the model's first token.
 * CARD-592: three more waits live in the same setting: provider silence, one job phase / developer turn, one helper
 * call. Defaults 7200 s per reply, 1800 s silence, 21600 s per phase, 1800 s per helper call.
 * CARD-605: wiki look-ups per reply (1-50, default 8).
 */

export const REPLY_LIMITS_URL = '/api/settings/reply-limits';

/** els key -> API field, label, element id. Only fields present on the page are read and sent. */
export const LIMIT_FIELDS = [
  { key: 'tokens', field: 'max_tokens', label: 'Max tokens per reply', id: 'replyLimitMaxTokensInput' },
  { key: 'seconds', field: 'max_seconds', label: 'Max seconds per reply', id: 'replyLimitMaxSecondsInput' },
  { key: 'idle', field: 'provider_idle_seconds', label: 'Provider silence (s)', id: 'replyLimitProviderIdleInput' },
  { key: 'phase', field: 'phase_seconds', label: 'Job phase / developer turn (s)', id: 'replyLimitPhaseSecondsInput' },
  { key: 'helper', field: 'helper_seconds', label: 'Helper call (s)', id: 'replyLimitHelperSecondsInput' },
  { key: 'wiki', field: 'wiki_lookups_per_reply', label: 'Wiki look-ups per reply', id: 'replyLimitWikiLookupsInput', min: 1, max: 50 }, // CARD-605
];

function byId(doc, id) {
  return doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null;
}

/** Field value -> number to send (0 clears). Throws on a negative or non-number value. */
export function parseLimitField(raw, label) {
  const text = String(raw ?? '').trim();
  if (!text) return 0;
  const n = Number(text);
  if (!Number.isInteger(n) || n < 0) throw new Error(`${label} must be a whole number of 0 or more.`);
  return n;
}

function show(els, data) {
  for (const f of LIMIT_FIELDS) {
    if (els[f.key]) els[f.key].value = data && data[f.field] ? String(data[f.field]) : '';
  }
}

function setStatus(els, text, ok) {
  if (!els.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
}

/** Load the current limits into the fields. Returns the API body or null. */
export async function loadReplyLimits(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!fetchFn) return null;
  try {
    const res = await fetchFn(REPLY_LIMITS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    show(els, data);
    return data;
  } catch (err) {
    setStatus(els, `Could not load reply limits: ${err.message}`, false);
    return null;
  }
}

/** Save every field on the page; the fields then show what the server resolved. */
export async function saveReplyLimits(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  let body;
  try {
    body = {};
    for (const f of LIMIT_FIELDS) {
      if (f.key === 'tokens' || f.key === 'seconds' || els[f.key]) {
        const n = parseLimitField(els[f.key] && els[f.key].value, f.label);
        if (n && f.max && (n < f.min || n > f.max)) throw new Error(`${f.label} must be between ${f.min} and ${f.max}.`);
        body[f.field] = n;
      }
    }
  } catch (err) {
    setStatus(els, err.message, false);
    return null;
  }
  try {
    const res = await fetchFn(REPLY_LIMITS_URL, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    show(els, data);
    setStatus(els, `Saved: ${data.max_tokens} tokens, ${data.max_seconds} s per reply.`, true);
    return data;
  } catch (err) {
    setStatus(els, `Could not save reply limits: ${err.message}`, false);
    return null;
  }
}

/** Wire the Settings card once and load the values. */
export function setupReplyLimits(doc = typeof document !== 'undefined' ? document : null, { fetchFn } = {}) {
  const els = {
    save: byId(doc, 'replyLimitsSaveBtn'),
    status: byId(doc, 'replyLimitsStatus'),
  };
  for (const f of LIMIT_FIELDS) els[f.key] = byId(doc, f.id);
  if (!els.tokens || !els.seconds) return null;
  const opts = fetchFn ? { fetchFn } : {};
  if (els.save && els.save.dataset && els.save.dataset.wired !== '1') {
    els.save.dataset.wired = '1';
    els.save.addEventListener('click', () => { saveReplyLimits(els, opts); });
  }
  loadReplyLimits(els, opts);
  return els;
}
