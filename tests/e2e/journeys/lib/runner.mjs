/**
 * CARD-532 live QA runner core (REQ-532-002..005, 010).
 * Pure Node module: no Playwright import here, so Vitest can load it. `run.mjs` passes the browser in.
 * A journey is a list of named steps. Each step gets a screenshot. A step fails on a thrown error, a click
 * whose expected outcome never follows (dead button), a browser console error, a failed request that the
 * journey did not allow, or a visible error banner ("Reply failed", an error toast).
 */
import fs from 'fs';
import os from 'os';
import path from 'path';

export const DESKTOP = Object.freeze({ name: 'desktop', width: 1280, height: 800 });
export const PHONE = Object.freeze({ name: 'phone', width: 390, height: 844 });
export const VIEWPORTS = Object.freeze([DESKTOP, PHONE]);

/** Visible error banners that fail a step (REQ-532-003). */
export const ERROR_BANNER_SELECTORS = Object.freeze([
  '.chat-stream-error',
  '#toastContainer [role="alert"]',
]);
export const ERROR_BANNER_TEXT = 'Reply failed';

/** Report root (D2): AUTOREIV_QA_REPORT_DIR, else <temp>/autoreiv-qa (on Jarvis C:\Users\jacob\AppData\Local\Temp\autoreiv-qa). */
export function defaultReportRoot(env = process.env, tmpdir = os.tmpdir()) {
  const configured = String((env && env.AUTOREIV_QA_REPORT_DIR) || '').trim();
  return configured || path.join(tmpdir, 'autoreiv-qa');
}

/** One folder per card: <root>/<card-id lower-case>, e.g. ...\autoreiv-qa\card-532. */
export function reportDirFor(card, root) {
  return path.join(root, String(card || 'journeys').toLowerCase());
}

export function slug(text) {
  return String(text || 'step').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48) || 'step';
}

/**
 * Allowlist entries: { url: substring | RegExp, status?: number | number[] }.
 * @returns {boolean} true when this failed response is allowed by the journey.
 */
export function isAllowedFailure(url, status, allow = []) {
  return (allow || []).some((entry) => {
    if (!entry) return false;
    const u = entry.url;
    const urlOk = u instanceof RegExp ? u.test(url) : String(url).includes(String(u || ''));
    if (!urlOk) return false;
    if (entry.status == null) return true;
    const statuses = Array.isArray(entry.status) ? entry.status : [entry.status];
    return statuses.includes(status);
  });
}

/** Console errors the journey allows: substrings or RegExps. */
export function isAllowedConsole(text, allowConsole = []) {
  return (allowConsole || []).some((a) => (a instanceof RegExp ? a.test(text) : String(text).includes(String(a))));
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Poll `probe` until it returns truthy or `timeoutMs` passes. Returns the truthy value or null. */
export async function waitFor(probe, { timeoutMs = 10000, intervalMs = 250 } = {}) {
  const end = Date.now() + timeoutMs;
  for (;;) {
    let value;
    try { value = await probe(); } catch { value = null; }
    if (value) return value;
    if (Date.now() >= end) return null;
    await sleep(intervalMs);
  }
}

/**
 * REQ-532-002: click the real element, then require the expected outcome within the timeout.
 * Throws "Dead button: ..." when nothing follows.
 */
export async function clickExpect(locator, expectFn, { what = 'the expected result', label = 'button', timeoutMs = 15000 } = {}) {
  await locator.click();
  const ok = await waitFor(expectFn, { timeoutMs });
  if (!ok) throw new Error(`Dead button: clicked ${label} but ${what} did not follow within ${timeoutMs} ms`);
  return ok;
}

/** Optional judge (D3: off by default). Returns null unless enabled; never throws into the journey. */
export async function judgeReply({ enabled = false, url = '', model = '', rubric = '', reply = '', fetchFn = globalThis.fetch } = {}) {
  if (!enabled || !url || !model || !rubric) return null;
  try {
    const res = await fetchFn(`${url.replace(/\/$/, '')}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        temperature: 0,
        messages: [
          { role: 'system', content: 'You grade an assistant reply against a rubric. Answer with PASS or FAIL on the first line, then one sentence of reasoning.' },
          { role: 'user', content: `Rubric:\n${rubric}\n\nReply:\n${reply}` },
        ],
      }),
    });
    const data = await res.json();
    const text = String(data?.choices?.[0]?.message?.content || '').trim();
    return { verdict: /^\s*PASS/i.test(text) ? 'pass' : 'fail', reasoning: text.slice(0, 500) };
  } catch (err) {
    return { verdict: 'error', reasoning: String(err).slice(0, 200) };
  }
}

/** One journey at one viewport. */
export class JourneyRun {
  constructor({ page, viewport, outDir, journeyId, allow = [], allowConsole = [] }) {
    this.page = page;
    this.viewport = viewport;
    this.outDir = outDir;
    this.journeyId = journeyId;
    this.allow = allow;
    this.allowConsole = allowConsole;
    this.results = [];
    this.consoleErrors = [];
    this.failedRequests = [];
    this.notes = [];
    this.stopped = false;
    fs.mkdirSync(outDir, { recursive: true });
  }

  /** Attach the error watchers (REQ-532-003). */
  watch() {
    const { page } = this;
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      const text = m.text();
      if (!isAllowedConsole(text, this.allowConsole)) this.consoleErrors.push(text.slice(0, 300));
    });
    page.on('pageerror', (err) => this.consoleErrors.push(`pageerror: ${String(err).slice(0, 300)}`));
    page.on('response', (res) => {
      const status = res.status();
      if (status >= 400 && !isAllowedFailure(res.url(), status, this.allow)) {
        this.failedRequests.push(`${status} ${res.request().method()} ${res.url()}`);
      }
    });
    page.on('requestfailed', (req) => {
      const reason = (req.failure() && req.failure().errorText) || 'failed';
      // Aborted streams after navigation are not errors the operator sees.
      if (/ERR_ABORTED|NS_BINDING_ABORTED/i.test(reason)) return;
      if (!isAllowedFailure(req.url(), 0, this.allow)) this.failedRequests.push(`network ${req.method()} ${req.url()} (${reason})`);
    });
    return this;
  }

  note(text) { this.notes.push(String(text)); }

  async visibleErrorBanner() {
    for (const sel of ERROR_BANNER_SELECTORS) {
      const loc = this.page.locator(sel);
      const n = await loc.count();
      for (let i = 0; i < n; i += 1) {
        if (await loc.nth(i).isVisible()) return `${sel}: ${(await loc.nth(i).innerText()).slice(0, 160)}`;
      }
    }
    const txt = this.page.getByText(ERROR_BANNER_TEXT, { exact: false });
    if ((await txt.count()) > 0 && (await txt.first().isVisible())) return `"${ERROR_BANNER_TEXT}" is visible`;
    return null;
  }

  async screenshot(label) {
    const n = String(this.results.length + 1).padStart(2, '0');
    const file = path.join(this.outDir, `${this.journeyId}-${this.viewport.name}-${n}-${slug(label)}.png`);
    try { await this.page.screenshot({ path: file }); return file; } catch { return null; }
  }

  /**
   * Run one step. `fn` gets { page, run }. Options: timeoutMs, soft (a failure is a warning and the journey continues).
   * After `fn`, any new console error, disallowed failed request or visible error banner fails the step.
   */
  async step(name, fn, { timeoutMs = 60000, soft = false } = {}) {
    if (this.stopped) {
      this.results.push({ step: name, status: 'skipped', reason: 'an earlier step failed', screenshot: null, ms: 0 });
      return null;
    }
    const c0 = this.consoleErrors.length;
    const f0 = this.failedRequests.length;
    const t0 = Date.now();
    let value = null;
    let reason = '';
    let timer = null;
    try {
      value = await Promise.race([
        Promise.resolve().then(() => fn({ page: this.page, run: this })),
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`step timed out after ${timeoutMs} ms`)), timeoutMs); }),
      ]);
    } catch (err) {
      reason = String((err && err.message) || err).split('\n')[0].slice(0, 400);
    } finally {
      if (timer) clearTimeout(timer);
    }
    if (!reason) {
      const newConsole = this.consoleErrors.slice(c0);
      const newFailed = this.failedRequests.slice(f0);
      const banner = await this.visibleErrorBanner().catch(() => null);
      if (newConsole.length) reason = `console error: ${newConsole[0]}`;
      else if (newFailed.length) reason = `failed request: ${newFailed[0]}`;
      else if (banner) reason = `error banner: ${banner}`;
    }
    const screenshot = await this.screenshot(name);
    const status = !reason ? 'pass' : (soft ? 'warn' : 'fail');
    this.results.push({ step: name, status, reason, screenshot, ms: Date.now() - t0 });
    if (status === 'fail') this.stopped = true;
    return value;
  }

  outcome() {
    if (this.results.some((r) => r.status === 'fail')) return 'fail';
    if (this.results.some((r) => r.status === 'warn')) return 'warn';
    return 'pass';
  }

  toJSON() {
    return {
      journey: this.journeyId,
      viewport: this.viewport.name,
      outcome: this.outcome(),
      steps: this.results,
      notes: this.notes,
      consoleErrors: this.consoleErrors,
      failedRequests: this.failedRequests,
    };
  }
}

/** Plain-text summary (REQ-532-004): one table row per step. */
export function formatSummary(runs, { title = 'Live QA', startedAt = '', base = '' } = {}) {
  const lines = [`# ${title}`, ''];
  if (startedAt) lines.push(`Started: ${startedAt}`);
  if (base) lines.push(`Server: ${base}`);
  lines.push('');
  lines.push('| Journey | Viewport | Outcome |', '|---|---|---|');
  runs.forEach((r) => lines.push(`| ${r.journey} | ${r.viewport} | ${r.outcome.toUpperCase()} |`));
  runs.forEach((r) => {
    lines.push('', `## ${r.journey} (${r.viewport}): ${r.outcome.toUpperCase()}`, '', '| # | Step | Result | Reason | Screenshot |', '|---|---|---|---|---|');
    r.steps.forEach((s, i) => lines.push(`| ${i + 1} | ${s.step} | ${s.status} | ${String(s.reason || '').replace(/\|/g, '/')} | ${s.screenshot || ''} |`));
    if (r.notes && r.notes.length) { lines.push('', 'Notes:'); r.notes.forEach((n) => lines.push(`- ${n}`)); }
  });
  return `${lines.join('\n')}\n`;
}

export function writeReport(outDir, runs, meta = {}) {
  fs.mkdirSync(outDir, { recursive: true });
  const jsonPath = path.join(outDir, 'report.json');
  const mdPath = path.join(outDir, 'summary.md');
  fs.writeFileSync(jsonPath, JSON.stringify({ ...meta, runs }, null, 2));
  fs.writeFileSync(mdPath, formatSummary(runs, meta));
  return { jsonPath, mdPath };
}
