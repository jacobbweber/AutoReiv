/**
 * CARD-532 shared AutoReiv UI helpers for journeys (real clicks against the real SPA).
 */
import { waitFor } from './runner.mjs';

export const STREAM_PATH = '/api/chat/stream';
export const HITL_CARD = '#pendingHitlHost [data-approval-id]';

/** Count POST /api/chat/stream requests (and resume ones) on a page. */
export function trackStreams(page) {
  const t = { posts: [], get count() { return this.posts.length; }, get resumes() { return this.posts.filter((b) => b && b.resume).length; } };
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().endsWith(STREAM_PATH)) {
      let body;
      try { body = req.postDataJSON(); } catch { body = null; }
      t.posts.push(body);
    }
  });
  return t;
}

export async function openApp(page, base) {
  await page.goto(base, { waitUntil: 'domcontentloaded' });
  await page.locator('#dock-chat').waitFor({ state: 'visible', timeout: 20000 });
}

export async function isStreaming(page) {
  return page.locator('#stopBtn').isVisible().catch(() => false);
}

/** Wait until the chat reply is idle (Stop hidden) for `settleMs`. */
export async function waitReplyIdle(page, { timeoutMs = 300000, settleMs = 2500 } = {}) {
  const ok = await waitFor(async () => {
    if (await isStreaming(page)) return false;
    await page.waitForTimeout(settleMs);
    return !(await isStreaming(page));
  }, { timeoutMs, intervalMs: 500 });
  if (!ok) throw new Error(`reply still streaming after ${timeoutMs} ms`);
}

/** Open a chat session by title through the real sessions drawer (the list is per agent: pass agentId to switch first). */
export async function openSessionByTitle(page, title, { agentId = '' } = {}) {
  // The dock button toggles: clicking it while Chat is open minimizes the window.
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) await page.locator('#dock-chat').click();
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  if (agentId && (await page.locator('#agentSelect').inputValue()) !== agentId) {
    await page.selectOption('#agentSelect', agentId);
    await page.waitForTimeout(800);
  }
  await page.locator('#toggleSidebarBtn').click();
  const item = page.locator('#sessionList > div', { hasText: title }).first();
  await item.waitFor({ state: 'visible', timeout: 15000 });
  await item.click();
  await page.waitForTimeout(1000);
}

export async function send(page, text) {
  await page.locator('#promptInput').fill(text);
  await page.locator('#promptInput').press('Enter');
}

export async function jobStripText(page) {
  const strip = page.locator('#jobPhaseStatusStrip');
  if (!(await strip.isVisible().catch(() => false))) return '';
  return (await strip.innerText()).replace(/\s+/g, ' ').trim();
}

export async function getJson(request, url) {
  const res = await request.get(url);
  if (!res.ok()) throw new Error(`GET ${url} -> ${res.status()}`);
  return res.json();
}

/** Latest job status for a chat session (journey API), or ''. */
export async function sessionJobStatus(request, base, sessionId) {
  const j = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sessionId)}/journey`);
  const jobs = Array.isArray(j.jobs) ? j.jobs : [];
  const job = jobs[jobs.length - 1] || jobs[0];
  return job ? String(job.status || '') : '';
}
