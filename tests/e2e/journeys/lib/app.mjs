/**
 * CARD-532 shared AutoReiv UI helpers for journeys (real clicks against the real SPA).
 */
import fs from 'node:fs';
import path from 'node:path';
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

/** Switch to `#view-<tabName>` across desktop and phone viewports [CARD-732]. */
export async function openTab(page, tabName) {
  const viewId = `#view-${tabName}`;
  if (await page.locator(viewId).isVisible().catch(() => false)) return;
  const dockBtn = page.locator(`#dock-${tabName}`);
  if (await dockBtn.isVisible().catch(() => false)) {
    await dockBtn.click();
  } else {
    const mobileMenu = page.locator('#mobileMenuBtn');
    if (await mobileMenu.isVisible().catch(() => false)) {
      const sidebarTab = page.locator(`#tab-${tabName}`);
      if (!(await sidebarTab.isVisible().catch(() => false))) {
        await mobileMenu.click();
      }
      await sidebarTab.waitFor({ state: 'visible', timeout: 10000 });
      await sidebarTab.click();
    } else {
      await page.locator(`#tab-${tabName}`).click();
    }
  }
  await page.locator(viewId).waitFor({ state: 'visible', timeout: 20000 });
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

/** CARD-728: an empty folder for a fixture project inside the server's user-data projects folder. */
export async function freshProjectDir(request, base, slug) {
  const listed = await getJson(request, `${base}/api/projects`);
  if (!listed.projects_root) throw new Error('GET /api/projects returned no projects_root');
  const root = path.join(listed.projects_root, slug);
  fs.rmSync(root, { recursive: true, force: true });
  fs.mkdirSync(root, { recursive: true });
  return root;
}

/** Latest job status for a chat session (journey API), or ''. */
export async function sessionJobStatus(request, base, sessionId) {
  const j = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sessionId)}/journey`);
  const jobs = Array.isArray(j.jobs) ? j.jobs : [];
  const job = jobs[jobs.length - 1] || jobs[0];
  return job ? String(job.status || '') : '';
}

/** Send text, approve every approval card until done() or the turn goes idle; returns approvals pressed. */
export async function askAndApprove(
  page,
  streams,
  text,
  done,
  timeoutMs,
  { idleLimit = 8, progress = null, onApprove = null } = {},
) {
  const n = streams.count;
  await send(page, text);
  await waitFor(() => streams.count > n, { timeoutMs: 20000 });
  let approvals = 0;
  let idlePolls = 0;
  let lastProgress = -1;
  await waitFor(
    async () => {
      const cards = page.locator(HITL_CARD);
      const count = await cards.count();
      for (let i = 0; i < count; i += 1) {
        const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
        if (await approve.isVisible().catch(() => false)) {
          if (onApprove) {
            const label = (await cards.nth(i).innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 80);
            onApprove(label);
          }
          await approve.click();
          approvals += 1;
          idlePolls = 0;
          await page.waitForTimeout(1500);
          return false;
        }
      }
      const deciding =
        (await page.locator(`${HITL_CARD} .hitl-card-status`).filter({ hasText: /Developer is working|Approving/ }).count()) > 0;
      const streaming = (await isStreaming(page)) || deciding;
      if (!streaming && (await done())) return true;
      const p = progress ? await progress() : 0;
      const moved = p !== lastProgress;
      lastProgress = p;
      idlePolls = streaming || moved ? 0 : idlePolls + 1;
      return idlePolls >= idleLimit;
    },
    { timeoutMs, intervalMs: 2000 },
  ).catch(() => {});
  await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
  return approvals;
}

