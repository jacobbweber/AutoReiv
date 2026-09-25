import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-472 - Workbench, artifact open and Teach modal wiring lost in the CARD-397 split.
 * Keep-and-fix scope (Factory retirement is CARD-495..498). Node env: tiny fake DOM, real template IDs.
 */

const ROOT = path.resolve(__dirname, '../../../src/web');
const html = fs.readFileSync(path.join(ROOT, 'templates/index.html'), 'utf-8');
const chatJs = fs.readFileSync(path.join(ROOT, 'static/modules/studios/chat.js'), 'utf-8');
const templateIds = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));

async function load(rel) {
  try {
    return await import(`../../../src/web/static/modules/studios/chat/${rel}`);
  } catch {
    return {};
  }
}

async function need(rel, name) {
  const m = await load(rel);
  expect(typeof m[name], `chat/${rel} must export ${name}`).toBe('function');
  return m[name];
}

function fakeEl(id = '', { classes = [] } = {}) {
  const listeners = {};
  const cls = new Set(classes);
  const attrs = {};
  const e = {
    id,
    textContent: '',
    innerHTML: '',
    value: '',
    dataset: {},
    _qsa: [],
    _closest: {},
    classList: {
      add: (...c) => c.forEach((x) => cls.add(x)),
      remove: (...c) => c.forEach((x) => cls.delete(x)),
      contains: (c) => cls.has(c),
      toggle: (c, force) => {
        const on = force === undefined ? !cls.has(c) : Boolean(force);
        if (on) cls.add(c); else cls.delete(c);
        return on;
      },
    },
    get className() { return [...cls].join(' '); },
    set className(v) { cls.clear(); String(v).split(/\s+/).filter(Boolean).forEach((c) => cls.add(c)); },
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    click(target) {
      const ev = { target: target || e, stopPropagation() {}, preventDefault() {} };
      (listeners.click || []).forEach((f) => f(ev));
    },
    closest(sel) { return e._closest[sel] || null; },
    querySelectorAll() { return e._qsa; },
    querySelector() { return null; },
    focus() {},
    hidden() { return cls.has('hidden'); },
  };
  return e;
}

const WB_KEYS = [
  'chatWorkbenchPane', 'workbenchArtifactTitle', 'workbenchArtifactMeta', 'workbenchContentPreview',
  'workbenchContentRaw', 'workbenchTabPreview', 'workbenchTabRaw', 'workbenchToggleBtn', 'workbenchCloseBtn',
  'workbenchMobileBackBtn', 'workbenchCopyBtn', 'workbenchSaveWikiBtn', 'workbenchArtifactBadge', 'messagesContainer',
];

function wbElements() {
  const els = {};
  WB_KEYS.forEach((k) => { els[k] = fakeEl(k); });
  els.chatWorkbenchPane.classList.add('hidden');
  return els;
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const flush = () => new Promise((r) => setTimeout(r, 0));

let savedDocument;
beforeEach(() => { savedDocument = globalThis.document; });
afterEach(() => {
  if (savedDocument === undefined) delete globalThis.document; else globalThis.document = savedDocument;
  vi.restoreAllMocks();
});

describe('CARD-472 Workbench', () => {
  it('REQ-472-008: collectWorkbenchElements() resolves every key to a real template element', async () => {
    const collect = await need('workbench.js', 'collectWorkbenchElements');
    globalThis.document = { getElementById: (id) => (templateIds.has(id) ? fakeEl(id) : null) };
    const els = collect();
    WB_KEYS.forEach((k) => {
      expect(els[k], `${k} must resolve from index.html`).toBeTruthy();
    });
  });

  it('REQ-472-001/005: toggle shows then hides; Close and Mobile back hide; tabs switch', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    const els = wbElements();
    initWorkbench(els, { renderMarkdownFn: vi.fn(), showToastFn: vi.fn() });
    els.workbenchToggleBtn.click();
    expect(els.chatWorkbenchPane.hidden()).toBe(false);
    els.workbenchToggleBtn.click();
    expect(els.chatWorkbenchPane.hidden()).toBe(true);
    els.workbenchToggleBtn.click();
    els.workbenchCloseBtn.click();
    expect(els.chatWorkbenchPane.hidden()).toBe(true);
    els.workbenchToggleBtn.click();
    els.workbenchMobileBackBtn.click();
    expect(els.chatWorkbenchPane.hidden()).toBe(true);
    els.workbenchTabRaw.click();
    expect(els.workbenchContentRaw.hidden()).toBe(false);
    expect(els.workbenchContentPreview.hidden()).toBe(true);
    els.workbenchTabPreview.click();
    expect(els.workbenchContentPreview.hidden()).toBe(false);
  });

  it('REQ-472-002: openWorkbench renders the preview through renderMarkdownFn and keeps raw verbatim', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    const els = wbElements();
    const renderMarkdownFn = vi.fn();
    const wb = initWorkbench(els, { renderMarkdownFn });
    wb.openWorkbench({ title: 'Agent Output', content: '**hi**' });
    expect(els.chatWorkbenchPane.hidden()).toBe(false);
    expect(els.workbenchArtifactTitle.textContent).toBe('Agent Output');
    expect(renderMarkdownFn).toHaveBeenCalledWith(els.workbenchContentPreview, '**hi**');
    expect(els.workbenchContentRaw.textContent).toBe('**hi**');
  });

  it('REQ-472-003: openArtifactById fetches once and opens the artifact', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    const els = wbElements();
    const fetchFn = vi.fn(async () => json(200, { success: true, artifact: { id: 'art_1', title: 'Weekly Report', content: '# Body' } }));
    const showToastFn = vi.fn();
    const wb = initWorkbench(els, { renderMarkdownFn: vi.fn(), showToastFn, fetchFn });
    expect(typeof wb.openArtifactById).toBe('function');
    await wb.openArtifactById('art_1');
    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(fetchFn.mock.calls[0][0]).toBe('/api/artifacts/art_1');
    expect(els.chatWorkbenchPane.hidden()).toBe(false);
    expect(els.workbenchArtifactTitle.textContent).toBe('Weekly Report');
    expect(els.workbenchArtifactMeta.textContent).toContain('art_1');
    expect(els.workbenchContentRaw.textContent).toBe('# Body');
    expect(showToastFn).not.toHaveBeenCalled();
  });

  it('REQ-472-003: 404, missing artifact or network error shows "Artifact not found" and keeps the pane closed', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    for (const fetchFn of [
      vi.fn(async () => json(404, { detail: 'nope' })),
      vi.fn(async () => json(200, { success: true })),
      vi.fn(async () => { throw new Error('offline'); }),
    ]) {
      const els = wbElements();
      const showToastFn = vi.fn();
      const wb = initWorkbench(els, { showToastFn, fetchFn });
      await wb.openArtifactById('art_missing');
      expect(showToastFn).toHaveBeenCalledWith('Artifact not found', 'error');
      expect(els.chatWorkbenchPane.hidden()).toBe(true);
    }
  });

  it('REQ-472-004: badge counts distinct artifacts through the bound refresh', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    const els = wbElements();
    const btn = (id) => { const b = fakeEl(); b.setAttribute('data-artifact-id', id); return b; };
    els.messagesContainer._qsa = [btn('a1'), btn('a2'), btn('a1')];
    const fetchFn = vi.fn(async () => json(200, { artifacts: [] }));
    const wb = initWorkbench(els, { fetchFn, getActiveSessionId: () => 's1' });
    await wb.refreshWorkbenchArtifactCount();
    expect(els.workbenchArtifactBadge.textContent).toBe('2');
    expect(els.workbenchArtifactBadge.hidden()).toBe(false);
    els.messagesContainer._qsa = [];
    await wb.refreshWorkbenchArtifactCount();
    expect(els.workbenchArtifactBadge.hidden()).toBe(true);
  });

  it('REQ-472-005: Copy toasts ("Artifact copied to clipboard", "success") and Save to Wiki exports raw', async () => {
    const initWorkbench = await need('workbench.js', 'initWorkbench');
    const els = wbElements();
    const copyToClipboardFn = vi.fn();
    const showToastFn = vi.fn();
    const exportMessageToWikiFn = vi.fn();
    const wb = initWorkbench(els, { copyToClipboardFn, showToastFn, exportMessageToWikiFn });
    wb.openWorkbench({ title: 't', content: 'raw text' });
    els.workbenchCopyBtn.click();
    expect(copyToClipboardFn).toHaveBeenCalledWith('raw text');
    expect(showToastFn).toHaveBeenCalledWith('Artifact copied to clipboard', 'success');
    els.workbenchSaveWikiBtn.click();
    expect(exportMessageToWikiFn).toHaveBeenCalledWith('raw text');
  });
});

describe('CARD-472 Teach modal (chat/teach_modal.js)', () => {
  function teachEls() {
    const els = {};
    ['teachAgentModal', 'teachAgentTargetAgentBadge', 'teachAgentGuidanceInput', 'submitTeachAgentBtn',
      'cancelTeachAgentBtn', 'closeTeachAgentModalBtn'].forEach((k) => { els[k] = fakeEl(k); });
    els.teachAgentModal.classList.add('hidden');
    return els;
  }

  it('REQ-472-006: X closes the modal and clears guidance without calling distill', async () => {
    const setupTeachAgentModal = await need('teach_modal.js', 'setupTeachAgentModal');
    const els = teachEls();
    const fetchFn = vi.fn();
    const ctrl = setupTeachAgentModal({ selectedAgentId: 'autoreiv', activeSessionId: 's1' }, els, {
      showToastFn: vi.fn(), callbacks: {}, messagesContainer: fakeEl('messagesContainer'), fetchFn,
    });
    ctrl.openTeachAgentModal({ messageId: 'm1', guidance: 'be careful' });
    expect(els.teachAgentModal.hidden()).toBe(false);
    els.closeTeachAgentModalBtn.click();
    expect(els.teachAgentModal.hidden()).toBe(true);
    expect(els.teachAgentGuidanceInput.value).toBe('');
    expect(fetchFn).not.toHaveBeenCalled();
  });

  function proposalCard(escalation, target = 'autoreiv') {
    const container = fakeEl('messagesContainer');
    const card = fakeEl('', { classes: ['skill-proposal-card'] });
    card.setAttribute('data-factory-escalation', JSON.stringify(escalation));
    card.setAttribute('data-target-agent-id', target);
    const btn = fakeEl('', { classes: ['btn-escalate-factory'] });
    btn._closest['.btn-escalate-factory'] = btn;
    btn._closest['.skill-proposal-card'] = card;
    return { container, btn };
  }

  it('REQ-472-007: the needs-tool button opens a Developer chat with the proposal attached', async () => {
    const setupTeachAgentModal = await need('teach_modal.js', 'setupTeachAgentModal');
    const { container, btn } = proposalCard({
      target_agent_id: 'autoreiv', seed_intent: 'Fetch weather for a city',
      suggested_tool_name: 'get_city_weather', starter_objectives: ['Return temperature'],
    });
    const fetchFn = vi.fn(async (url, init) => {
      const body = JSON.parse(init.body);
      return json(200, {
        session_id: 'dev1', agent_id: 'developer', opened_job: false, job_id: null,
        prompt: `Create tool ${body.draft.tool_name}: ${body.draft.behavior}`,
      });
    });
    const openDeveloperSessionFn = vi.fn(async () => {});
    const showToastFn = vi.fn();
    setupTeachAgentModal({ selectedAgentId: 'autoreiv' }, teachEls(), {
      showToastFn, callbacks: {}, messagesContainer: container, fetchFn, openDeveloperSessionFn,
    });
    container.click(btn);
    await flush(); await flush();
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('/api/tools_studio/authoring/talk');
    const body = JSON.parse(init.body);
    expect(body.intent).toBe('create');
    expect(body.draft.tool_name).toBe('get_city_weather');
    expect(body.draft.behavior).toContain('Fetch weather for a city');
    expect(body.draft.behavior).toContain('Return temperature');
    expect(openDeveloperSessionFn).toHaveBeenCalledWith('dev1', expect.stringContaining('get_city_weather'));
  });

  it('REQ-472-007: if the Developer chat cannot open, toast and fall back to Tools Studio', async () => {
    const setupTeachAgentModal = await need('teach_modal.js', 'setupTeachAgentModal');
    const { container, btn } = proposalCard({ target_agent_id: 'tutor', seed_intent: 'x', suggested_tool_name: 'y' }, 'tutor');
    const fetchFn = vi.fn(async () => json(503, { detail: 'Developer agent unavailable' }));
    const openToolsStudio = vi.fn();
    const showToastFn = vi.fn();
    setupTeachAgentModal({ selectedAgentId: 'autoreiv' }, teachEls(), {
      showToastFn, callbacks: { openToolsStudio }, messagesContainer: container, fetchFn, openDeveloperSessionFn: vi.fn(),
    });
    container.click(btn);
    await flush(); await flush();
    expect(showToastFn).toHaveBeenCalledWith(expect.stringContaining('Developer agent unavailable'), 'error');
    expect(openToolsStudio).toHaveBeenCalledWith('tutor');
  });
});

describe('CARD-472 guard: chat.js call shapes', () => {
  it('REQ-472-008: Workbench is built from collectWorkbenchElements(), never from state', () => {
    expect(chatJs).not.toMatch(/initWorkbench\(\s*state\b/);
    expect(chatJs).toMatch(/initWorkbench\(\s*collectWorkbenchElements\(\)/);
  });

  it('REQ-472-003/008: every chat markdown render uses the single artifact opener', () => {
    expect(chatJs).not.toMatch(/onOpenArtifact:\s*openWorkbench\b/);
    const fns = [...chatJs.matchAll(/renderMarkdownFn:\s*([A-Za-z_$][\w$]*)/g)].map((m) => m[1]);
    expect(fns.length).toBeGreaterThan(0);
    fns.forEach((fn) => expect(fn).toBe('renderChatMarkdown'));
    expect(chatJs).toMatch(/onOpenArtifact:\s*openArtifactById/);
  });

  it('REQ-472-001: the badge refresh no longer passes a bare session id', () => {
    expect(chatJs).not.toMatch(/refreshWorkbenchArtifactCountDirect\(\s*state\.activeSessionId\s*\)/);
  });
});
