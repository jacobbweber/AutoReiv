/** CARD-605: Settings > Reply limits has a "Wiki look-ups per reply" field (1-50, default 8). */
import { describe, it, expect } from 'vitest';
import { LIMIT_FIELDS, loadReplyLimits, saveReplyLimits } from '../../../src/web/static/modules/studios/settings_reply_limits.js';

const ok = (body) => ({ ok: true, json: async () => body });
const fields = () => ({
  tokens: { value: '' }, seconds: { value: '' }, wiki: { value: '' },
  status: { textContent: '', className: '' },
});
const resolved = { max_tokens: 32768, max_seconds: 7200, wiki_lookups_per_reply: 8 };

describe('CARD-605 wiki look-ups setting', () => {
  it('is one of the Reply limits fields', () => {
    const f = LIMIT_FIELDS.find((x) => x.field === 'wiki_lookups_per_reply');
    expect(f).toMatchObject({ key: 'wiki', id: 'replyLimitWikiLookupsInput', min: 1, max: 50 });
  });

  it('loads the resolved value and saves a new one', async () => {
    const els = fields();
    await loadReplyLimits(els, { fetchFn: async () => ok(resolved) });
    expect(els.wiki.value).toBe('8');
    els.wiki.value = '20';
    let sent = null;
    await saveReplyLimits(els, { fetchFn: async (url, init) => { sent = JSON.parse(init.body); return ok({ ...resolved, wiki_lookups_per_reply: 20 }); } });
    expect(sent.wiki_lookups_per_reply).toBe(20);
    expect(els.wiki.value).toBe('20');
  });

  it('refuses a value above 50 without calling the server', async () => {
    const els = fields();
    els.wiki.value = '51';
    let called = false;
    const out = await saveReplyLimits(els, { fetchFn: async () => { called = true; return ok(resolved); } });
    expect(out).toBeNull();
    expect(called).toBe(false);
    expect(els.status.textContent).toContain('between 1 and 50');
  });

  it('empty clears back to the default', async () => {
    const els = fields();
    let sent = null;
    await saveReplyLimits(els, { fetchFn: async (url, init) => { sent = JSON.parse(init.body); return ok(resolved); } });
    expect(sent.wiki_lookups_per_reply).toBe(0);
  });
});
