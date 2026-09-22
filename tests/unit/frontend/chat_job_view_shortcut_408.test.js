/**
 * CARD-408: View Job shortcut from Chat job chrome to Observe Studio.
 * REQ-408-001 button affordance, REQ-408-002 focus Observe, REQ-408-003 auto inspect,
 * REQ-408-004 failed lookup stays in the viewer.
 */
import { describe, expect, it, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  bindChatJobViewShortcut,
  buildViewJobShortcut,
  syncChatJobViewButton,
} from '../../../src/web/static/modules/studios/chat/chrome.js';
import {
  inspectObserveJob,
  openObserveJob,
} from '../../../src/web/static/modules/studios/observability.js';
import { resolveDesktopStudioTab } from '../../../src/web/static/modules/ui/agent-desktop.js';

const root = path.resolve(__dirname, '../../..');

function classList(initial = []) {
  const set = new Set(initial);
  return {
    contains: (c) => set.has(c),
    add: (c) => { set.add(c); },
    remove: (c) => { set.delete(c); },
    toggle(token, force) {
      const on = force === undefined ? !set.has(token) : Boolean(force);
      if (on) set.add(token);
      else set.delete(token);
      return on;
    },
  };
}

function makeViewButton(jobId = '') {
  const btn = {
    dataset: {},
    classList: classList(['hidden', 'chat-job-chrome-view-btn']),
    closest(sel) {
      return sel === '.chat-job-chrome-view-btn' ? btn : null;
    },
  };
  if (jobId) btn.dataset.jobId = jobId;
  const label = {
    closest(sel) {
      return btn.closest(sel);
    },
  };
  btn.label = label;
  return btn;
}

function makeStrip(btn) {
  const listeners = [];
  const strip = {
    dataset: {},
    btn,
    querySelector(sel) {
      return sel === '.chat-job-chrome-view-btn' ? btn : null;
    },
    addEventListener(type, fn) {
      listeners.push({ type, fn });
    },
    fire(target) {
      listeners.filter((l) => l.type === 'click').forEach((l) => l.fn({ target }));
    },
  };
  return strip;
}

function journeyPayload(jobId) {
  return {
    job_id: jobId,
    timeline: [
      { kind: 'phase', phase_index: 1, name: 'Execute', status: 'running', ts: '2026-09-22T00:00:00Z' },
    ],
    spans: [{ name: 'phase' }],
  };
}

describe('CARD-408 View Job shortcut', () => {
  afterEach(() => {
    delete globalThis.fetch;
  });

  it('[REQ-408-001] job strip markup includes View Job beside Copy, hidden until a job id is bound', () => {
    const html = loadPageHtml();
    const copyAt = html.indexOf('data-job-phase="copy-job-id"');
    const viewAt = html.indexOf('class="chat-job-chrome-view-btn');
    expect(html).toContain('id="jobPhaseStatusStrip"');
    expect(html).toContain('class="chat-job-chrome-id ');
    expect(html).toContain('chat-job-chrome-copy-btn');
    expect(html).toContain('data-testid="chat-job-chrome-view-btn"');
    expect(html).toContain('>View Job<');
    expect(copyAt).toBeGreaterThan(-1);
    expect(viewAt).toBeGreaterThan(copyAt);
    const viewTag = html.slice(viewAt - 120, viewAt + 80);
    expect(viewTag).toContain('hidden');
    expect(viewTag).not.toContain('onclick=');
  });

  it('[REQ-408-001] sync shows View Job only when a job id is present', () => {
    const btn = makeViewButton();
    const strip = makeStrip(btn);
    syncChatJobViewButton(strip, 'job_408_live');
    expect(btn.classList.contains('hidden')).toBe(false);
    expect(btn.dataset.jobId).toBe('job_408_live');

    syncChatJobViewButton(strip, '   ');
    expect(btn.classList.contains('hidden')).toBe(true);
    expect(btn.dataset.jobId).toBeUndefined();
    expect(buildViewJobShortcut('')).toBeNull();
    expect(buildViewJobShortcut('  ')).toBeNull();
  });

  it('[REQ-408-002] clicking View Job navigates to Observe with that job id', () => {
    const btn = makeViewButton('job_408_live');
    const strip = makeStrip(btn);
    const seen = [];
    bindChatJobViewShortcut(strip, { onViewJob: (nav) => seen.push(nav) });
    strip.fire(btn.label);
    expect(seen).toEqual([
      { studio: 'observe', tab: 'observability', jobId: 'job_408_live' },
    ]);

    const copy = { closest: () => null };
    strip.fire(copy);
    expect(seen).toHaveLength(1);

    const empty = makeViewButton('');
    const strip2 = makeStrip(empty);
    const seen2 = [];
    bindChatJobViewShortcut(strip2, { onViewJob: (nav) => seen2.push(nav) });
    strip2.fire(empty);
    expect(seen2).toEqual([]);
    expect(bindChatJobViewShortcut(strip, { onViewJob: () => {} })).toBe(false);
  });

  it('[REQ-408-002] desktop maps observe onto the Observability window', () => {
    expect(resolveDesktopStudioTab('observe')).toBe('observability');
    expect(resolveDesktopStudioTab('Observe')).toBe('observability');
    expect(resolveDesktopStudioTab('observability')).toBe('observability');
    expect(resolveDesktopStudioTab('chat')).toBe('chat');
    expect(resolveDesktopStudioTab('')).toBe('');
    expect(resolveDesktopStudioTab(null)).toBe('');
    const desktopJs = fs.readFileSync(
      path.join(root, 'src/web/static/modules/ui/agent-desktop.js'),
      'utf-8',
    );
    expect(desktopJs).toContain('openStudio: (studio, params = {}) => openWindow(studio, params)');
    expect(desktopJs).toContain('const resolved = resolveDesktopStudioTab(tab)');
    const chatJs = fs.readFileSync(
      path.join(root, 'src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
    expect(chatJs).toContain('bindChatJobViewShortcut');
    expect(chatJs).toContain('syncChatJobViewButton');
  });

  it('[REQ-408-003] Observe fills the job search and runs standing-journey lookup', async () => {
    const urls = [];
    const inputEl = { value: 'stale_job' };
    const statusEl = { textContent: '' };
    const timelineEl = { innerHTML: '' };
    const switched = [];
    const result = await openObserveJob('job_408_live', {
      switchTab: (tab) => switched.push(tab),
      inputEl,
      statusEl,
      timelineEl,
      fetchFn: async (url) => {
        urls.push(url);
        return { ok: true, status: 200, json: async () => journeyPayload('job_408_live') };
      },
    });
    expect(switched).toEqual(['observability']);
    expect(inputEl.value).toBe('job_408_live');
    expect(urls).toEqual(['/api/observability/standing-journey?job_id=job_408_live']);
    expect(result.ok).toBe(true);
    expect(result.studio).toBe('observe');
    expect(result.jobId).toBe('job_408_live');
    expect(timelineEl.innerHTML).toContain('Execute');
    expect(timelineEl.innerHTML).not.toContain('Failed to load standing journey');
    expect(statusEl.textContent).toMatch(/Loaded 1 events/);
  });

  it('[REQ-408-004] an unknown job id shows an error in the viewer and does not throw', async () => {
    const inputEl = { value: '' };
    const statusEl = { textContent: '' };
    const timelineEl = { innerHTML: '<div>previous</div>' };
    const switched = [];
    const result = await openObserveJob('job_missing', {
      switchTab: (tab) => switched.push(tab),
      inputEl,
      statusEl,
      timelineEl,
      fetchFn: async () => ({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'job not found' }),
      }),
    });
    expect(switched).toEqual(['observability']);
    expect(result.ok).toBe(false);
    expect(result.error).toContain('HTTP 404');
    expect(result.error).toContain('job not found');
    expect(statusEl.textContent).toContain('Load failed');
    expect(timelineEl.innerHTML).toContain('Failed to load standing journey');
    expect(timelineEl.innerHTML).toContain('job not found');
    expect(inputEl.value).toBe('job_missing');
  });

  it('[REQ-408-004] a blank job id does not navigate or query', async () => {
    const switched = [];
    let fetched = false;
    const result = await openObserveJob('   ', {
      switchTab: (tab) => switched.push(tab),
      fetchFn: async () => {
        fetched = true;
        return { ok: true, json: async () => ({}) };
      },
    });
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('missing_job_id');
    expect(switched).toEqual([]);
    expect(fetched).toBe(false);

    const statusEl = { textContent: '' };
    const empty = await inspectObserveJob('', {
      statusEl,
      inputEl: { value: '' },
      fetchFn: async () => {
        fetched = true;
        return { ok: true, json: async () => ({}) };
      },
    });
    expect(empty.ok).toBe(false);
    expect(empty.reason).toBe('missing_job_id');
    expect(fetched).toBe(false);
    expect(statusEl.textContent).toContain('Enter a job_id');
  });
});
