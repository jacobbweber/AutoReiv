/**
 * CARD-532: live QA runner core (REQ-532-002..005, 009, 010, 011). Fake pages, no browser.
 */
import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
  JourneyRun, VIEWPORTS, clickExpect, defaultReportRoot, formatSummary, isAllowedFailure, judgeReply, reportDirFor,
} from '../../e2e/journeys/lib/runner.mjs';

const ROOT = path.resolve(__dirname, '../../..');

function fakePage({ banners = {}, text = {} } = {}) {
  const handlers = {};
  const page = {
    handlers,
    on: (evt, cb) => { (handlers[evt] = handlers[evt] || []).push(cb); },
    emit: (evt, arg) => (handlers[evt] || []).forEach((cb) => cb(arg)),
    locator: (sel) => {
      const n = banners[sel] ? 1 : 0;
      return { count: async () => n, nth: () => ({ isVisible: async () => true, innerText: async () => banners[sel] || '' }) };
    },
    getByText: (t) => ({ count: async () => (text[t] ? 1 : 0), first: () => ({ isVisible: async () => true }) }),
    screenshot: vi.fn(async () => {}),
  };
  return page;
}
const consoleMsg = (t) => ({ type: () => 'error', text: () => t });
const response = (status, url, method = 'GET') => ({ status: () => status, url: () => url, request: () => ({ method: () => method }) });

function newRun(page, extra = {}) {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'c532-'));
  return new JourneyRun({ page, viewport: VIEWPORTS[0], outDir, journeyId: 'j', ...extra }).watch();
}

describe('REQ-532-004 / D2: report folder', () => {
  it('defaults to <temp>/autoreiv-qa and is configurable', () => {
    expect(defaultReportRoot({}, 'C:\\T')).toBe(path.join('C:\\T', 'autoreiv-qa'));
    expect(defaultReportRoot({ AUTOREIV_QA_REPORT_DIR: 'X:\\qa' }, 'C:\\T')).toBe('X:\\qa');
    expect(reportDirFor('CARD-532', 'R')).toBe(path.join('R', 'card-532'));
  });
});

describe('REQ-532-005: viewports', () => {
  it('desktop 1280x800 and phone 390x844', () => {
    expect(VIEWPORTS.map((v) => `${v.name}:${v.width}x${v.height}`)).toEqual(['desktop:1280x800', 'phone:390x844']);
  });
});

describe('REQ-532-002: a dead button fails loudly', () => {
  it('clickExpect throws when the expected outcome never follows', async () => {
    const loc = { click: vi.fn(async () => {}) };
    await expect(clickExpect(loc, () => false, { label: 'Approve', what: 'the card state', timeoutMs: 300 })).rejects.toThrow(/Dead button: clicked Approve/);
    expect(loc.click).toHaveBeenCalledTimes(1);
  });
  it('clickExpect resolves when the outcome follows', async () => {
    const loc = { click: vi.fn(async () => {}) };
    await expect(clickExpect(loc, () => 'ok', { timeoutMs: 300 })).resolves.toBe('ok');
  });
  it('a dead button inside a step fails the step and skips the rest', async () => {
    const run = newRun(fakePage());
    await run.step('click', () => clickExpect({ click: async () => {} }, () => false, { timeoutMs: 200 }));
    await run.step('next', () => {});
    expect(run.results.map((r) => r.status)).toEqual(['fail', 'skipped']);
    expect(run.results[0].reason).toMatch(/Dead button/);
    expect(run.outcome()).toBe('fail');
  });
});

describe('REQ-532-003: error watchers fail the step', () => {
  it('a console error fails the step', async () => {
    const page = fakePage();
    const run = newRun(page);
    await run.step('s', () => { page.emit('console', consoleMsg('TypeError: x is undefined')); });
    expect(run.results[0].status).toBe('fail');
    expect(run.results[0].reason).toMatch(/console error: TypeError/);
  });
  it('a failed request fails the step unless the journey allows it', async () => {
    const page = fakePage();
    const run = newRun(page, { allow: [{ url: '/api/ok-to-fail', status: 404 }] });
    await run.step('allowed', () => { page.emit('response', response(404, 'http://h/api/ok-to-fail')); });
    await run.step('not allowed', () => { page.emit('response', response(500, 'http://h/api/chat/stream', 'POST')); });
    expect(run.results.map((r) => r.status)).toEqual(['pass', 'fail']);
    expect(run.results[1].reason).toMatch(/failed request: 500 POST/);
  });
  it('a visible "Reply failed" or error toast fails the step', async () => {
    const run1 = newRun(fakePage({ banners: { '.chat-stream-error': 'Reply failed: boom' } }));
    await run1.step('s', () => {});
    expect(run1.results[0].reason).toMatch(/error banner/);
    const run2 = newRun(fakePage({ banners: { '#toastContainer [role="alert"]': 'Could not save' } }));
    await run2.step('s', () => {});
    expect(run2.results[0].status).toBe('fail');
  });
  it('a clean step passes, a soft failure is a warning and the journey goes on; each step has a screenshot', async () => {
    const page = fakePage();
    const run = newRun(page);
    await run.step('ok', () => {});
    await run.step('soft', () => { throw new Error('model did not call the tool'); }, { soft: true, card: 'CARD-543' });
    await run.step('after', () => {});
    expect(run.results.map((r) => r.status)).toEqual(['pass', 'warn', 'pass']);
    expect(run.outcome()).toBe('warn');
    expect(page.screenshot).toHaveBeenCalledTimes(3);
    expect(run.results[0].screenshot).toMatch(/j-desktop-01-ok\.png$/);
  });
  it('CARD-559: soft without a card id fails the step', async () => {
    const run = newRun(fakePage());
    await run.step('soft', () => { throw new Error('flaky'); }, { soft: true });
    expect(run.results[0].status).toBe('fail');
    expect(run.results[0].reason).toMatch(/soft: true needs card/);
    expect(run.outcome()).toBe('fail');
  });
  it('CARD-559: a failing knownBug step is XFAIL naming the card, stops the journey, and is not red', async () => {
    const run = newRun(fakePage());
    await run.step('known', () => { throw new Error('no attach proposal'); }, { knownBug: 'CARD-535' });
    await run.step('after', () => {});
    expect(run.results.map((r) => r.status)).toEqual(['xfail', 'skipped']);
    expect(run.results[0].reason).toMatch(/^XFAIL CARD-535: no attach proposal/);
    expect(run.outcome()).toBe('xfail');
  });
  it('CARD-559: a passing knownBug step is XPASS and fails so the marker is removed', async () => {
    const run = newRun(fakePage());
    await run.step('known', () => {}, { knownBug: 'CARD-535' });
    expect(run.results[0].status).toBe('fail');
    expect(run.results[0].reason).toMatch(/XPASS: CARD-535 may be fixed; remove knownBug/);
    expect(run.outcome()).toBe('fail');
  });
  it('isAllowedFailure matches url and status', () => {
    expect(isAllowedFailure('http://h/a/b', 404, [{ url: '/a/' }])).toBe(true);
    expect(isAllowedFailure('http://h/a/b', 500, [{ url: '/a/', status: 404 }])).toBe(false);
    expect(isAllowedFailure('http://h/x', 404, [{ url: /\/x$/, status: [404, 409] }])).toBe(true);
  });
});

describe('REQ-532-004: summary', () => {
  it('lists journey, viewport, step, result, reason and screenshot', () => {
    const md = formatSummary([{ journey: 'card-530-x', viewport: 'phone', outcome: 'fail', steps: [{ step: 'Approve', status: 'fail', reason: 'Dead button', screenshot: 'C:\\s.png' }], notes: ['n1'] }]);
    expect(md).toContain('| card-530-x | phone | FAIL |');
    expect(md).toContain('| 1 | Approve | fail | Dead button | C:\\s.png |');
    expect(md).toContain('- n1');
  });
});

describe('REQ-532-010 / D3: judge is off by default', () => {
  it('returns null and calls nothing unless enabled', async () => {
    const fetchFn = vi.fn();
    expect(await judgeReply({ rubric: 'r', reply: 'x', url: 'http://j/v1', model: 'm', fetchFn })).toBeNull();
    expect(fetchFn).not.toHaveBeenCalled();
  });
  it('grades when enabled', async () => {
    const fetchFn = vi.fn(async () => ({ json: async () => ({ choices: [{ message: { content: 'PASS\nuses the tool' } }] }) }));
    const v = await judgeReply({ enabled: true, rubric: 'r', reply: 'x', url: 'http://j/v1', model: 'm', fetchFn });
    expect(v.verdict).toBe('pass');
  });
});

describe('REQ-532-011: first journeys exist and are wired', () => {
  it('CARD-520 and CARD-530 journey files export id, card and run', async () => {
    for (const f of ['card-520-teach-needs-tool.mjs', 'card-530-approve-mid-stream.mjs']) {
      const mod = (await import(`../../e2e/journeys/${f}`)).default;
      expect(mod.id).toBe(f.replace('.mjs', ''));
      expect(typeof mod.run).toBe('function');
      expect(mod.card).toMatch(/^CARD-5[23]0$/);
    }
  });
  it('journeys are not picked up by the smoke suite (not *.spec.js)', () => {
    const files = fs.readdirSync(path.join(ROOT, 'tests/e2e/journeys'));
    expect(files.some((f) => /\.spec\.js$|\.test\.js$/.test(f))).toBe(false);
  });
});

describe('REQ-532-009: no new dependencies', () => {
  it('package.json dependencies are unchanged and Playwright is reused', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8'));
    expect(Object.keys(pkg.dependencies || {})).toEqual([]);
    expect(Object.keys(pkg.devDependencies).sort()).toEqual(['@eslint/js', '@playwright/test', 'eslint', 'globals', 'prettier', 'vitest']);
    const runSrc = fs.readFileSync(path.join(ROOT, 'tests/e2e/journeys/run.mjs'), 'utf-8');
    expect(runSrc).toContain("from '@playwright/test'");
  });
});
